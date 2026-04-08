from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM provider
    llm_provider: str = "anthropic"  # "anthropic" | "openai"
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    llm_model: str = "claude-sonnet-4-6"
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.7

    # Scraping
    scrape_timeout_seconds: int = 30
    scrape_user_agent: str = (
        "Mozilla/5.0 (compatible; DatasetBot/1.0; +https://github.com/example/dataset-pipeline)"
    )
    max_articles_per_feed: int = 5

    # Database
    database_url: str = "sqlite:///stock_news.db"


settings = Settings()
