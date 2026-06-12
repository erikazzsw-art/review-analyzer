"""V4-T4 Step 4: 多模型 Fallback 链路.

三级模型优先级：
1. DeepSeek-V3（deepseek-chat）— 主模型，中文优势 + 成本最低
2. OpenAI gpt-4o-mini — 备 1，API 稳定性最高，JSON mode 可靠
3. Qwen-Plus（通义千问）— 备 2，国内可用性兜底

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


MODELS: list[ModelConfig] = [
    ModelConfig(
        name="deepseek",
        model_id="deepseek-chat",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
    ),
    ModelConfig(
        name="openai",
        model_id="gpt-4o-mini",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
    ),
    ModelConfig(
        name="qwen",
        model_id="qwen-plus",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_env="Qwen_API_KEY",
    ),
]


@dataclass
class _CircuitState:
    consecutive_failures: int = 0
    tripped_at: float = 0.0
    is_open: bool = False


@dataclass
class LLMRouter:
    """线程安全的多模型路由器，带熔断和自动恢复."""

    models: list[ModelConfig] = field(default_factory=lambda: list(MODELS))
    threshold: int = CIRCUIT_BREAK_THRESHOLD
    cooldown: float = COOLDOWN_SECONDS
    _states: dict[str, _CircuitState] = field(default_factory=dict)
    _clients: dict[str, OpenAI] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def __post_init__(self) -> None:
        for m in self.models:
            self._states[m.name] = _CircuitState()

    def _get_client(self, model: ModelConfig) -> OpenAI | None:
        if model.name in self._clients:
            return self._clients[model.name]
        api_key = os.getenv(model.api_key_env)
        if not api_key:
            return None
        client = OpenAI(api_key=api_key, base_url=model.base_url, timeout=model.timeout)
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
    ) -> tuple[Any, str]:
        """调用 LLM，自动 fallback.

        Returns:
            (response, model_name) — OpenAI 兼容 response 对象 + 实际使用的模型名
        Raises:
            RuntimeError: 所有模型均不可用
        """
        errors: list[str] = []

        for model in self.models:
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
                return resp, model.name
            except Exception as e:
                err_msg = f"{model.name}: {str(e)[:150]}"
                errors.append(err_msg)
                logger.warning("llm_router: %s failed: %s", model.name, str(e)[:200])
                self._record_failure(model)

        raise RuntimeError(
            f"All LLM models exhausted. Errors: {'; '.join(errors)}"
        )

    def status(self) -> dict[str, Any]:
        """返回各模型的熔断状态（用于监控/调试）."""
        result = {}
        for model in self.models:
            state = self._states[model.name]
            has_key = bool(os.getenv(model.api_key_env))
            result[model.name] = {
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
) -> tuple[Any, str]:
    """便捷函数：调用全局路由器的 completion."""
    return get_router().completion(
        messages=messages,
        response_format=response_format,
        temperature=temperature,
        max_tokens=max_tokens,
    )
