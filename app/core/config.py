from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "MemPoisonGuard"
    app_env: str = "development"
    debug: bool = True

    host: str = "0.0.0.0"
    port: int = 8000

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_seconds: int = 120

    sqlite_database_url: str = "sqlite:///./storage/mempoisonguard.db"
    chroma_persist_directory: str = "./storage/chroma"

    verified_collection_name: str = "verified_memories"
    baseline_collection_name: str = "baseline_memories"
    quarantine_collection_name: str = "quarantined_memories"

    nli_model_name: str = "cross-encoder/nli-distilroberta-base"
    nli_contradiction_threshold: float = 0.70
    nli_candidate_limit: int = 5
    nli_enforcement_distance_threshold: float = 0.75

    duplicate_similarity_threshold: float = 0.15

    evaluation_data_directory: str = "./data/evaluation"
    experiment_output_directory: str = "./storage/experiments"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()