from pathlib import Path

from app.core.config import BASE_DIR, settings
from app.core.database import Base, engine
from app.services.vector_store import chroma_client


def clear_collection(collection_name: str) -> None:
    try:
        chroma_client.delete_collection(name=collection_name)
    except Exception:
        pass

    chroma_client.get_or_create_collection(name=collection_name)


for collection_name in [
    settings.baseline_collection_name,
    settings.verified_collection_name,
    settings.quarantine_collection_name,
]:
    clear_collection(collection_name)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

experiment_directory = BASE_DIR / settings.experiment_output_directory

if experiment_directory.exists():
    for file_path in experiment_directory.iterdir():
        if file_path.is_file():
            file_path.unlink()

print("Evaluation storage reset complete.")