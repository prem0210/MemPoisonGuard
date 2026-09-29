from pathlib import Path

import chromadb

from app.core.config import BASE_DIR, settings


def resolve_storage_path(path_value: str) -> str:
    path = Path(path_value)
    if not path.is_absolute():
        path = BASE_DIR / path
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


chroma_client = chromadb.PersistentClient(
    path=resolve_storage_path(settings.chroma_persist_directory)
)


def initialize_collections() -> dict[str, str]:
    collections = [
        settings.verified_collection_name,
        settings.baseline_collection_name,
        settings.quarantine_collection_name,
    ]

    for collection_name in collections:
        chroma_client.get_or_create_collection(name=collection_name)

    return {
        "verified": settings.verified_collection_name,
        "baseline": settings.baseline_collection_name,
        "quarantine": settings.quarantine_collection_name,
    }


def collection_counts() -> dict[str, int]:
    collection_names = {
        "verified": settings.verified_collection_name,
        "baseline": settings.baseline_collection_name,
        "quarantine": settings.quarantine_collection_name,
    }

    return {
        label: chroma_client.get_or_create_collection(name=name).count()
        for label, name in collection_names.items()
    }