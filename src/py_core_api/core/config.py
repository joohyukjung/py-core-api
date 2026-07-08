from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-5"
    anthropic_max_tokens: int = 8192


settings = Settings()  # ty: ignore[missing-argument]
