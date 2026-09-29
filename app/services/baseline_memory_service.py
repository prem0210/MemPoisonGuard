import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.database_models import MemoryRecord
from app.services.vector_store import chroma_client


def create_content_hash(content: str) -> str:
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


def get_baseline_collection():
    return chroma_client.get_or_create_collection(
        name=settings.baseline_collection_name
    )


def store_baseline_memory(
    db: Session,
    content: str,
    source_type: str,
    source_name: str,
    source_reference: str | None = None,
) -> MemoryRecord:
    clean_content = content.strip()
    memory_id = f"baseline_{uuid4().hex}"
    content_hash = create_content_hash(clean_content)

    record = MemoryRecord(
        memory_id=memory_id,
        content=clean_content,
        content_hash=content_hash,
        source_type=source_type,
        source_name=source_name,
        source_reference=source_reference,
        trust_score=0.0,
        risk_score=0.0,
        verification_status="not_checked",
        storage_status="baseline_stored",
        detector_flags=json.dumps([]),
        created_at=datetime.now(timezone.utc),
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    collection = get_baseline_collection()
    collection.add(
        ids=[memory_id],
        documents=[clean_content],
        metadatas=[
            {
                "memory_id": memory_id,
                "source_type": source_type,
                "source_name": source_name,
                "storage_status": "baseline_stored",
            }
        ],
    )

    return record


def list_baseline_memories(db: Session) -> list[MemoryRecord]:
    statement = (
        select(MemoryRecord)
        .where(MemoryRecord.storage_status == "baseline_stored")
        .order_by(MemoryRecord.created_at.desc())
    )
    return list(db.scalars(statement).all())


def retrieve_baseline_memories(
    query: str,
    top_k: int,
) -> list[dict]:
    collection = get_baseline_collection()

    if collection.count() == 0:
        return []

    result = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    retrieved_memories = []

    for document, metadata, distance in zip(documents, metadatas, distances):
        retrieved_memories.append(
            {
                "memory_id": metadata.get("memory_id", ""),
                "content": document,
                "source_type": metadata.get("source_type", "unknown"),
                "source_name": metadata.get("source_name", "unknown"),
                "similarity_distance": float(distance),
            }
        )

    return retrieved_memories


def clear_baseline_memories(db: Session) -> int:
    statement = delete(MemoryRecord).where(
        MemoryRecord.storage_status == "baseline_stored"
    )
    result = db.execute(statement)
    db.commit()

    collection = get_baseline_collection()

    if collection.count() > 0:
        existing = collection.get(include=[])
        ids = existing.get("ids", [])

        if ids:
            collection.delete(ids=ids)

    return result.rowcount or 0