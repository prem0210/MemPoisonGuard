from pathlib import Path
import shutil

from app.services.vector_store import chroma_client
from app.core.config import settings


def reset_collection(name: str) -> None:
    try:
        chroma_client.delete_collection(name=name)
    except Exception:
        pass

    chroma_client.get_or_create_collection(name=name)


for collection_name in [
    settings.baseline_collection_name,
    settings.verified_collection_name,
    settings.quarantine_collection_name,
]:
    reset_collection(collection_name)

database_path = Path("storage/mempoisonguard.db")

if database_path.exists():
    database_path.unlink()

print("Storage reset complete. Restart the FastAPI server now.")