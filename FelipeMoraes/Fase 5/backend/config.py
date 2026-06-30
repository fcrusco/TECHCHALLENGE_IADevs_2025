from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    llm_provider: Literal["openai", "ollama", "lmstudio"] = "openai"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llava"

    lmstudio_base_url: str = "http://localhost:1234/v1"
    lmstudio_model: str = "local-model"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"


settings = Settings()
