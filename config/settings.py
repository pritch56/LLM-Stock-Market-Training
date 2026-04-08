import os
from pathlib import Path
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
    scrape_concurrency: int = 5
    scrape_delay_seconds: float = 1.0
    scrape_timeout_seconds: int = 30
    scrape_max_retries: int = 3
    scrape_user_agent: str = (
        "Mozilla/5.0 (compatible; DatasetBot/1.0; +https://github.com/example/dataset-pipeline)"
    )

    # Generation
    generation_concurrency: int = 3
    generation_batch_size: int = 10
    pairs_per_document: int = 3

    # Filtering
    min_instruction_length: int = 20
    min_output_length: int = 50
    max_output_length: int = 4000
    min_input_text_length: int = 200
    allowed_languages: list[str] = ["en"]

    # Storage
    output_dir: Path = Path("output")
    database_url: str = "sqlite:///pipeline.db"
    sources_file: Path = Path("config/sources.yaml")

    # HuggingFace export
    hf_dataset_name: Optional[str] = None
    hf_token: Optional[str] = None


settings = Settings()
