"""V4-T4 Step 4: 多模型 Fallback 链路（locale-aware）.

模型优先级按 locale 切换：
- locale="en"（海外）：GPT-4o-mini → DeepSeek → Qwen
- locale="zh"（国内）：DeepSeek → GPT-4o-mini → Qwen

熔断机制：
- 连续 N 次失败（默认 3）自动切换到下一个模型
- 冷却期（默认 60s）过后自动尝试恢复主模型
- 所有切换写入日志，便于监控

业务代码调用 `router_completion()` 替代直接 OpenAI 调用，无感知切换。
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

CIRCUIT_BREAK_THRESHOLD = 3
COOLDOWN_SECONDS = 60.0


@dataclass
class ModelConfig:
    name: str
    model_id: str
    base_url: str
    api_key_env: str
    timeout: float = 30.0


_DEEPSEEK = ModelConfig(
    name="deepseek",
    model_id="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key_env="DEEPSEEK_API_KEY",
)
_OPENAI = ModelConfig(
    name="openai",
    model_id="gpt-4o-mini",
    base_url="https://api.openai.com/v1",
    api_key_env="OPENAI_API_KEY",
)
_QWEN = ModelConfig(
    name="qwen",
    model_id="qwen-plus",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key_env="Qwen_API_KEY",
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
        if time.time() - state.tripped_at >= self.cooldown:
            state.is_open = False
            state.consecutive_failures = 0
            logger.info("llm_router: %s circuit closed (cooldown expired), retrying", model.name)
            return True
        return False

    def _record_success(self, model: ModelConfig) -> None:
        with self._lock:
            state = self._states[model.name]
            state.consecutive_failures = 0
            state.is_open = False

    def _record_failure(self, model: ModelConfig) -> None:
        with self._lock:
            state = self._states[model.name]
            state.consecutive_failures += 1
            if state.consecutive_failures >= self.threshold:
                state.is_open = True
                state.tripped_at = time.time()
                logger.warning(
                    "llm_router: %s circuit OPEN after %d consecutive failures",
                    model.name, state.consecutive_failures,
                )

    def completion(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
        temperature: float = 0,
        max_tokens: int = 800,
        locale: str = "zh",
    ) -> tuple[Any, str]:
        """调用 LLM，自动 fallback.

        Args:
            locale: "en" 走 GPT-4o-mini 优先链，其它（含 "zh"）走 DeepSeek 优先链.

        Returns:
            (response, model_name) — OpenAI 兼容 response 对象 + 实际使用的模型名
        Raises:
            RuntimeError: 所有模型均不可用
        """
        errors: list[str] = []
        chain = _models_for_locale(locale)

        for model in chain:
            if model.name not in self._states:
                # 兜底：动态加入未见过的 model（自定义 router 场景）
                self._states[model.name] = _CircuitState()
            if not self._is_available(model):
                continue

            client = self._get_client(model)
            if client is None:
                continue

            try:
                kwargs: dict[str, Any] = {
                    "model": model.model_id,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if response_format:
                    kwargs["response_format"] = response_format

                resp = client.chat.completions.create(**kwargs)
                self._record_success(model)
                self._log_cache_stats(model, resp)
                return resp, model.name
            except Exception as e:
                err_msg = f"{model.name}: {str(e)[:150]}"
                errors.append(err_msg)
                logger.warning("llm_router: %s failed: %s", model.name, str(e)[:200])
                self._record_failure(model)

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
    )
