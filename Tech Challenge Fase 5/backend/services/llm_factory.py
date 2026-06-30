import logging
import time
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_openai import ChatOpenAI

from config import settings
from models.schemas import ProviderType

logger = logging.getLogger(__name__)


class LLMLogger(BaseCallbackHandler):
    """Callback that logs LLM call start, finish, and errors."""

    def __init__(self) -> None:
        self._start: float = 0.0

    def on_llm_start(self, serialized: dict, prompts: list[str], **kwargs: Any) -> None:
        self._start = time.time()
        model = serialized.get("kwargs", {}).get("model_name", "?")
        logger.info("  ┌─ LLM call start | model=%s | messages=%d", model, len(prompts))

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        elapsed = time.time() - self._start
        usage   = {}
        if response.llm_output:
            usage = response.llm_output.get("token_usage", {})
        finish  = response.generations[0][0].generation_info.get("finish_reason", "?") \
                  if response.generations and response.generations[0] else "?"
        chars   = len(response.generations[0][0].text) if response.generations and response.generations[0] else 0
        logger.info(
            "  └─ LLM call done  | %.1fs | finish=%s | chars=%d | tokens: prompt=%s completion=%s total=%s",
            elapsed,
            finish,
            chars,
            usage.get("prompt_tokens", "?"),
            usage.get("completion_tokens", "?"),
            usage.get("total_tokens", "?"),
        )

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        logger.error("  └─ LLM call error | %s: %s", type(error).__name__, error)


_llm_logger = LLMLogger()


def get_llm_client(
    provider: ProviderType | None = None,
    override_url: str | None = None,
    override_model: str | None = None,
) -> tuple[ChatOpenAI, str]:
    """Returns (ChatOpenAI, model_name).

    override_url/model take precedence over .env values,
    allowing the frontend to supply custom local endpoints at runtime.
    """
    provider = provider or settings.llm_provider

    if provider == "openai":
        model = override_model or settings.openai_model
        llm   = ChatOpenAI(
            model=model,
            api_key=settings.openai_api_key,
            temperature=0,
            callbacks=[_llm_logger],
        )
        logger.debug("[factory] OpenAI | model=%s", model)
        return llm, model

    if provider == "ollama":
        base  = (override_url or settings.ollama_base_url).rstrip("/")
        url   = base if base.endswith("/v1") else f"{base}/v1"
        model = override_model or settings.ollama_model
        llm   = ChatOpenAI(
            model=model,
            base_url=url,
            api_key="ollama",
            temperature=0,
            callbacks=[_llm_logger],
        )
        logger.debug("[factory] Ollama | url=%s model=%s", url, model)
        return llm, model

    if provider == "lmstudio":
        model = override_model or settings.lmstudio_model
        llm   = ChatOpenAI(
            model=model,
            base_url=override_url or settings.lmstudio_base_url,
            api_key="lm-studio",
            temperature=0,
            callbacks=[_llm_logger],
        )
        logger.debug("[factory] LM Studio | model=%s", model)
        return llm, model

    raise ValueError(f"Unknown provider: {provider}")
