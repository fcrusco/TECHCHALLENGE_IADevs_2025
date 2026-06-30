from openai import AsyncOpenAI
from config import settings
from models.schemas import ProviderType


def get_llm_client(provider: ProviderType | None = None) -> tuple[AsyncOpenAI, str]:
    """Returns (client, model_name) for the given provider."""
    provider = provider or settings.llm_provider

    if provider == "openai":
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        return client, settings.openai_model

    if provider == "ollama":
        client = AsyncOpenAI(
            base_url=f"{settings.ollama_base_url}/v1",
            api_key="ollama",
        )
        return client, settings.ollama_model

    if provider == "lmstudio":
        client = AsyncOpenAI(
            base_url=settings.lmstudio_base_url,
            api_key="lm-studio",
        )
        return client, settings.lmstudio_model

    raise ValueError(f"Unknown provider: {provider}")
