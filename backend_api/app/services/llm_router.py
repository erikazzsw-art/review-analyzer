"""V4-T4 Step 4: 多模型 Fallback 链路（locale-aware）.

模型优先级按 locale 切换：
- locale="en"（海外）：GPT-4o-mini → DeepSeek → Qwen
- locale="zh"（国内）：DeepSeek → GPT-4o-mini → Qwen

熔断机制（V4-出海-M4.3 硬化）：
- 每模型独立配置：threshold / cooldown（ModelConfig 字段）
- 半开探测：冷却期满后放行 1 条请求 → 成功则关闭熔断，失败则重新计时
- OpenAI 429：解析 Retry-After header + 指数退避（初始 1s，最大 30s，最多 3 次）
- 所有切换写入日志，便于监控

业务代码调用 `router_completion()` 替代直接 OpenAI 调用，无感知切换。
"""
from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from threading import Lock
from typing import Any

from openai import OpenAI, RateLimitError

logger = logging.getLogger(__name__)

TraceCallback = Callable[[str, str, dict[str, Any]], None]

CIRCUIT_BREAK_THRESHOLD = 3
COOLDOWN_SECONDS = 60.0

# OpenAI 生产硬化常量
OPENAI_MAX_RETRIES = 3
OPENAI_RETRY_BASE_DELAY = 1.0
OPENAI_RETRY_MAX_DELAY = 30.0


def _parse_retry_after(exc: Exception) -> float:
    """从 RateLimitError 响应头解析 Retry-After（秒）；解析失败返回 1.0."""
    try:
        headers = getattr(getattr(exc, "response", None), "headers", None) or {}
        raw = headers.get("Retry-After", "1")
        try:
            return float(raw)
        except (ValueError, TypeError):
            # HTTP-date 格式
            retry_dt = parsedate_to_datetime(raw)
            wait = (retry_dt - datetime.now(timezone.utc)).total_seconds()
            return max(0.0, wait)
    except Exception:
        return 1.0


def _emit_trace(
    trace_callback: TraceCallback | None,
    kind: str,
    name: str,
    **details: Any,
) -> None:
    if trace_callback is None:
        return
    try:
        trace_callback(kind, name, details)
    except Exception as exc:
        logger.debug("llm_router trace callback failed (non-fatal): %s", exc)


@dataclass
class ModelConfig:
    name: str
    model_id: str
    base_url: str
    api_key_env: str
    timeout: float = 30.0
    circuit_threshold: int = 3
    circuit_cooldown: float = 60.0


_DEEPSEEK = ModelConfig(
    name="deepseek",
    model_id="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key_env="DEEPSEEK_API_KEY",
    circuit_threshold=5,
    circuit_cooldown=60.0,
)
_OPENAI = ModelConfig(
    name="openai",
    model_id="gpt-4o-mini",
    base_url="https://api.openai.com/v1",
    api_key_env="OPENAI_API_KEY",
    circuit_threshold=3,
    circuit_cooldown=30.0,
)
_QWEN = ModelConfig(
    name="qwen",
    model_id="qwen-plus",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key_env="Qwen_API_KEY",
    circuit_threshold=3,
    circuit_cooldown=120.0,
)

MODELS_EN: list[ModelConfig] = [_OPENAI, _DEEPSEEK, _QWEN]
MODELS_ZH: list[ModelConfig] = [_DEEPSEEK, _OPENAI, _QWEN]

# 向后兼容：默认列表（国内优先）
MODELS: list[ModelConfig] = MODELS_ZH


def _models_for_locale(locale: str) -> list[ModelConfig]:
    if locale.startswith("en"):
        return MODELS_EN
    return MODELS_ZH


@dataclass
class _CircuitState:
    consecutive_failures: int = 0
    tripped_at: float = 0.0
    is_open: bool = False
    is_half_open: bool = False


@dataclass
class LLMRouter:
    """线程安全的多模型路由器，带熔断和自动恢复.

    models 字段保留为"熔断状态种子"（所有可能出现的模型都要有 CircuitState），
    实际每次 completion 用哪个链路由 locale 决定，见 _models_for_locale.
    """

    models: list[ModelConfig] = field(default_factory=lambda: [_DEEPSEEK, _OPENAI, _QWEN])
    threshold: int = CIRCUIT_BREAK_THRESHOLD
    cooldown: float = COOLDOWN_SECONDS
    _states: dict[str, _CircuitState] = field(default_factory=dict)
    _clients: dict[str, OpenAI] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def __post_init__(self) -> None:
        # 种子所有可能的模型（避免 locale 切换时找不到 state）
        seen: set[str] = set()
        for m in list(self.models) + MODELS_EN + MODELS_ZH:
            if m.name in seen:
                continue
            seen.add(m.name)
            self._states[m.name] = _CircuitState()

    def _get_client(self, model: ModelConfig) -> OpenAI | None:
        if model.name in self._clients:
            return self._clients[model.name]
        api_key = os.getenv(model.api_key_env)
        if not api_key:
            return None
        import httpx
        client = OpenAI(
            api_key=api_key,
            base_url=model.base_url,
            timeout=httpx.Timeout(model.timeout, connect=5.0),
            max_retries=0,
        )
        self._clients[model.name] = client
        return client

    def _is_available(self, model: ModelConfig) -> bool:
        state = self._states[model.name]
        if not state.is_open:
            return True
        # 冷却期满 → 进入半开状态，允许一次探测请求
        cooldown = getattr(model, "circuit_cooldown", self.cooldown)
        if time.time() - state.tripped_at >= cooldown:
            with self._lock:
                if state.is_open and time.time() - state.tripped_at >= cooldown:
                    state.is_open = False
                    state.is_half_open = True
            logger.info("llm_router: %s circuit half-open (cooldown expired), allowing 1 probe", model.name)
            return True
        return False

    def _record_success(self, model: ModelConfig) -> dict[str, Any] | None:
        with self._lock:
            state = self._states[model.name]
            was_half_open = state.is_half_open
            state.consecutive_failures = 0
            state.is_open = False
            state.is_half_open = False
            if was_half_open:
                logger.info("llm_router: %s half-open probe SUCCESS, circuit closed", model.name)
                return {
                    "provider": model.name,
                    "model": model.model_id,
                    "state": "closed",
                    "reason": "half_open_probe_success",
                }
        return None

    def _record_failure(self, model: ModelConfig) -> dict[str, Any] | None:
        with self._lock:
            state = self._states[model.name]
            state.consecutive_failures += 1
            threshold = getattr(model, "circuit_threshold", self.threshold)
            cooldown = getattr(model, "circuit_cooldown", self.cooldown)
            if state.is_half_open:
                # 半开探测失败 → 立即重新熔断
                state.is_open = True
                state.tripped_at = time.time()
                state.is_half_open = False
                logger.warning(
                    "llm_router: %s half-open probe FAILED, circuit re-opened for %.0fs",
                    model.name, cooldown,
                )
                return {
                    "provider": model.name,
                    "model": model.model_id,
                    "state": "open",
                    "reason": "half_open_probe_failed",
                    "cooldown_seconds": cooldown,
                    "consecutive_failures": state.consecutive_failures,
                }
            elif state.consecutive_failures >= threshold:
                state.is_open = True
                state.tripped_at = time.time()
                logger.warning(
                    "llm_router: %s circuit OPEN after %d consecutive failures (threshold=%d)",
                    model.name, state.consecutive_failures, threshold,
                )
                return {
                    "provider": model.name,
                    "model": model.model_id,
                    "state": "open",
                    "reason": "failure_threshold_reached",
                    "threshold": threshold,
                    "cooldown_seconds": cooldown,
                    "consecutive_failures": state.consecutive_failures,
                }
        return None

    def completion(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
        temperature: float = 0,
        max_tokens: int = 800,
        locale: str = "zh",
        disabled_providers: Iterable[str] | None = None,
        request_timeout: float | None = None,
        max_model_attempts: int | None = None,
        trace_callback: TraceCallback | None = None,
    ) -> tuple[Any, str]:
        """调用 LLM，自动 fallback.

        Args:
            locale: "en" 走 GPT-4o-mini 优先链，其它（含 "zh"）走 DeepSeek 优先链.
            disabled_providers: 本次调用要跳过的 provider name，例如 {"deepseek"}。
            request_timeout: 本次调用传给 OpenAI-compatible client 的 per-request timeout。
            max_model_attempts: 本次调用最多实际请求多少个 provider；None 表示完整 fallback 链。

        Returns:
            (response, model_id) — OpenAI 兼容 response 对象 + 实际使用的模型 ID
        Raises:
            RuntimeError: 所有模型均不可用
        """
        errors: list[str] = []
        chain = _models_for_locale(locale)
        disabled = {
            str(provider).strip().lower()
            for provider in (disabled_providers or [])
            if str(provider).strip()
        }
        attempted_models = 0
        _emit_trace(
            trace_callback,
            "event",
            "llm_router_chain",
            locale=locale,
            provider_chain=[model.name for model in chain],
            disabled_providers=sorted(disabled),
            max_model_attempts=max_model_attempts,
        )

        for model_index, model in enumerate(chain):
            if model.name.lower() in disabled:
                logger.info("llm_router: %s skipped by per-call disabled_providers", model.name)
                _emit_trace(
                    trace_callback,
                    "event",
                    "llm_provider_skipped",
                    provider=model.name,
                    model=model.model_id,
                    reason="disabled_provider",
                )
                continue
            if model.name not in self._states:
                # 兜底：动态加入未见过的 model（自定义 router 场景）
                self._states[model.name] = _CircuitState()
            state = self._states[model.name]
            was_open = state.is_open
            if not self._is_available(model):
                cooldown = getattr(model, "circuit_cooldown", self.cooldown)
                cooldown_remaining = max(0.0, cooldown - (time.time() - state.tripped_at))
                _emit_trace(
                    trace_callback,
                    "event",
                    "llm_provider_circuit",
                    provider=model.name,
                    model=model.model_id,
                    state="open",
                    action="skip",
                    cooldown_remaining_seconds=round(cooldown_remaining, 2),
                    consecutive_failures=state.consecutive_failures,
                )
                continue
            if was_open and state.is_half_open:
                _emit_trace(
                    trace_callback,
                    "event",
                    "llm_provider_circuit",
                    provider=model.name,
                    model=model.model_id,
                    state="half_open",
                    action="probe",
                    consecutive_failures=state.consecutive_failures,
                )

            client = self._get_client(model)
            if client is None:
                _emit_trace(
                    trace_callback,
                    "event",
                    "llm_provider_skipped",
                    provider=model.name,
                    model=model.model_id,
                    reason="missing_api_key",
                )
                continue
            if max_model_attempts is not None and attempted_models >= max_model_attempts:
                _emit_trace(
                    trace_callback,
                    "event",
                    "llm_provider_skipped",
                    provider=model.name,
                    model=model.model_id,
                    reason="max_model_attempts_reached",
                    max_model_attempts=max_model_attempts,
                )
                break
            attempted_models += 1

            kwargs: dict[str, Any] = {
                "model": model.model_id,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if response_format:
                kwargs["response_format"] = response_format
            if request_timeout is not None and request_timeout > 0:
                kwargs["timeout"] = request_timeout

            # 429 指数退避重试（最多 3 次），仅针对 RateLimitError
            last_exc: Exception | None = None
            last_retry_attempt = 0
            for attempt in range(OPENAI_MAX_RETRIES):
                last_retry_attempt = attempt + 1
                attempt_t0 = time.perf_counter()
                try:
                    _emit_trace(
                        trace_callback,
                        "event",
                        "llm_provider_attempt",
                        provider=model.name,
                        model=model.model_id,
                        provider_attempt=attempted_models,
                        retry_attempt=attempt + 1,
                        max_retries=OPENAI_MAX_RETRIES,
                    )
                    resp = client.chat.completions.create(**kwargs)
                    latency_ms = int((time.perf_counter() - attempt_t0) * 1000)
                    circuit_event = self._record_success(model)
                    self._log_cache_stats(model, resp)
                    _emit_trace(
                        trace_callback,
                        "event",
                        "llm_provider_success",
                        provider=model.name,
                        model=model.model_id,
                        provider_attempt=attempted_models,
                        retry_attempt=attempt + 1,
                        latency_ms=latency_ms,
                    )
                    if circuit_event:
                        _emit_trace(trace_callback, "event", "llm_provider_circuit", **circuit_event)
                    return resp, model.model_id
                except RateLimitError as e:
                    last_exc = e
                    if attempt == OPENAI_MAX_RETRIES - 1:
                        break  # 最后一次重试也失败了 → 退出 retry 循环
                    retry_after = _parse_retry_after(e)
                    wait = min(max(retry_after, OPENAI_RETRY_BASE_DELAY) * (2 ** attempt), OPENAI_RETRY_MAX_DELAY)
                    logger.warning(
                        "llm_router: %s 429 rate limited, retry %d/%d in %.1fs (Retry-After: %.0fs)",
                        model.name, attempt + 1, OPENAI_MAX_RETRIES, wait, retry_after,
                    )
                    _emit_trace(
                        trace_callback,
                        "event",
                        "llm_provider_429_retry",
                        provider=model.name,
                        model=model.model_id,
                        retry_attempt=attempt + 1,
                        next_retry_attempt=attempt + 2,
                        wait_seconds=round(wait, 2),
                        retry_after_seconds=round(retry_after, 2),
                    )
                    time.sleep(wait)
                except Exception as e:
                    last_exc = e
                    break  # 非 429 错误不重试，直接尝试下一个模型

            # 所有重试或非 429 错误 → 记录失败
            err_msg = f"{model.name}: {str(last_exc)[:150]}" if last_exc else f"{model.name}: unknown error"
            errors.append(err_msg)
            logger.warning("llm_router: %s failed: %s", model.name, str(last_exc)[:200] if last_exc else "unknown")
            error_type = "rate_limit" if isinstance(last_exc, RateLimitError) else type(last_exc).__name__
            _emit_trace(
                trace_callback,
                "event",
                "llm_provider_failure",
                provider=model.name,
                model=model.model_id,
                provider_attempt=attempted_models,
                retry_attempts=last_retry_attempt,
                error_type=error_type,
                error_detail=str(last_exc)[:200] if last_exc else "unknown",
                will_fallback=any(m.name.lower() not in disabled for m in chain[model_index + 1 :]),
            )
            circuit_event = self._record_failure(model)
            if circuit_event:
                _emit_trace(trace_callback, "warning", "llm_provider_circuit", **circuit_event)
            fallback_chain = [
                candidate.name
                for candidate in chain[model_index + 1 :]
                if candidate.name.lower() not in disabled
            ]
            if fallback_chain:
                _emit_trace(
                    trace_callback,
                    "event",
                    "llm_provider_fallback",
                    from_provider=model.name,
                    from_model=model.model_id,
                    remaining_providers=fallback_chain,
                    reason=error_type,
                )

        raise RuntimeError(
            f"All LLM models exhausted. Errors: {'; '.join(errors)}"
        )

    def _log_cache_stats(self, model: ModelConfig, resp: Any) -> None:
        usage = getattr(resp, "usage", None)
        if not usage:
            return
        prompt_tokens = getattr(usage, "prompt_tokens", 0)
        cache_hit = getattr(usage, "prompt_cache_hit_tokens", None)
        if cache_hit is None:
            cache_hit = getattr(usage, "cache_hit_tokens", None)
        if cache_hit:
            logger.info(
                "llm_router prefix_cache: model=%s prompt_tokens=%d cache_hit_tokens=%d (%.0f%%)",
                model.name, prompt_tokens, cache_hit,
                (cache_hit / prompt_tokens * 100) if prompt_tokens else 0,
            )

    def status(self) -> dict[str, Any]:
        """返回各模型的熔断状态（用于监控/调试）."""
        result = {}
        all_models = {m.name: m for m in MODELS_EN + MODELS_ZH + self.models}
        for name, model in all_models.items():
            state = self._states.get(name) or _CircuitState()
            has_key = bool(os.getenv(model.api_key_env))
            result[name] = {
                "available": self._is_available(model) and has_key,
                "has_api_key": has_key,
                "consecutive_failures": state.consecutive_failures,
                "circuit_open": state.is_open,
                "circuit_half_open": state.is_half_open,
                "circuit_threshold": getattr(model, "circuit_threshold", self.threshold),
                "circuit_cooldown": getattr(model, "circuit_cooldown", self.cooldown),
            }
        return result


_default_router: LLMRouter | None = None
_router_lock = Lock()


def get_router() -> LLMRouter:
    """获取全局单例路由器."""
    global _default_router
    if _default_router is None:
        with _router_lock:
            if _default_router is None:
                _default_router = LLMRouter()
    return _default_router


def router_completion(
    messages: list[dict[str, str]],
    response_format: dict[str, str] | None = None,
    temperature: float = 0,
    max_tokens: int = 800,
    locale: str = "zh",
    disabled_providers: Iterable[str] | None = None,
    request_timeout: float | None = None,
    max_model_attempts: int | None = None,
    trace_callback: TraceCallback | None = None,
) -> tuple[Any, str]:
    """便捷函数：调用全局路由器的 completion.

    Args:
        locale: "en" 走 GPT-4o-mini 优先链，其它（含 "zh"）走 DeepSeek 优先链.
    """
    return get_router().completion(
        messages=messages,
        response_format=response_format,
        temperature=temperature,
        max_tokens=max_tokens,
        locale=locale,
        disabled_providers=disabled_providers,
        request_timeout=request_timeout,
        max_model_attempts=max_model_attempts,
        trace_callback=trace_callback,
    )
