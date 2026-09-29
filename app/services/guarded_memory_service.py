import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.database_models import MemoryRecord
from app.services.injection_detector import detect_injection_patterns
from app.services.sensitive_claim_detector import detect_sensitive_claims
from app.services.contradiction_detector import detect_contradiction
from app.services.provenance_service import create_provenance_metadata
from app.services.trust_risk_engine import (
    calculate_risk_score,
    calculate_trust_score,
    decide_memory_action,
)
from app.services.vector_store import chroma_client


def create_content_hash(content: str) -> str:
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


def get_collection_for_status(storage_status: str):
    if storage_status == "verified_stored":
        collection_name = settings.verified_collection_name
    elif storage_status == "quarantined":
        collection_name = settings.quarantine_collection_name
    else:
        return None

    return chroma_client.get_or_create_collection(name=collection_name)


def analyze_and_store_guarded_memory(
    db: Session,
    content: str,
    source_type: str,
    source_name: str,
    source_reference: str | None = None,
) -> MemoryRecord:
    clean_content = content.strip()
    memory_id = f"guarded_{uuid4().hex}"
    content_hash = create_content_hash(clean_content)

    provenance = create_provenance_metadata(
        source_type=source_type,
        source_name=source_name,
        source_reference=source_reference,
    )

    injection_result = detect_injection_patterns(clean_content)

    sensitive_claim_result = detect_sensitive_claims(
        content=clean_content,
        source_type=provenance["source_type"],
    )

    contradiction_result = detect_contradiction(clean_content)

    contradiction_score = contradiction_result["contradiction_score"]
    anomaly_score = contradiction_result["duplicate_score"]

    risk_score = calculate_risk_score(
        injection_score=injection_result["injection_score"],
        provenance_score=provenance["provenance_score"],
        contradiction_score=contradiction_score,
        anomaly_score=anomaly_score,
    )

    trust_score = calculate_trust_score(
        provenance_score=provenance["provenance_score"],
        injection_score=injection_result["injection_score"],
        contradiction_score=contradiction_score,
    )

    decision = decide_memory_action(
        risk_score=risk_score,
        trust_score=trust_score,
        injection_score=injection_result["injection_score"],
        contradiction_score=contradiction_score,
    )

    if sensitive_claim_result["high_risk_authorization_claim"]:
        decision = {
            "verification_status": "rejected",
            "storage_status": "quarantined",
            "quarantine_reason": (
                "Unverified high-risk authorization or confidential "
                "disclosure claim detected."
            ),
        }

    record = MemoryRecord(
        memory_id=memory_id,
        content=clean_content,
        content_hash=content_hash,
        source_type=provenance["source_type"],
        source_name=provenance["source_name"],
        source_reference=provenance["source_reference"],
        provenance_score=provenance["provenance_score"],
        injection_score=injection_result["injection_score"],
        contradiction_score=contradiction_score,
        trust_score=trust_score,
        risk_score=risk_score,
        verification_status=decision["verification_status"],
        storage_status=decision["storage_status"],
        detector_flags=json.dumps(
            injection_result["flags"]
            + sensitive_claim_result["flags"]
            + contradiction_result["flags"]
        ),
        analysis_evidence=json.dumps(
            {
                "injection_analysis": injection_result,
                "sensitive_claim_analysis": sensitive_claim_result,
                "contradiction_analysis": contradiction_result,
            }
        ),
        quarantine_reason=decision["quarantine_reason"],
        created_at=datetime.now(timezone.utc),
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    collection = get_collection_for_status(record.storage_status)

    if collection is not None:
        collection.add(
            ids=[record.memory_id],
            documents=[record.content],
            metadatas=[
                {
                    "memory_id": record.memory_id,
                    "source_type": record.source_type,
                    "source_name": record.source_name,
                    "provenance_score": record.provenance_score,
                    "injection_score": record.injection_score,
                    "trust_score": record.trust_score,
                    "contradiction_score": record.contradiction_score,
                    "risk_score": record.risk_score,
                    "verification_status": record.verification_status,
                    "storage_status": record.storage_status,
                }
            ],
        )

    return record


def list_guarded_memories(
    db: Session,
    storage_status: str | None = None,
) -> list[MemoryRecord]:
    statement = (
        select(MemoryRecord)
        .where(MemoryRecord.memory_id.like("guarded_%"))
        .order_by(MemoryRecord.created_at.desc())
    )

    if storage_status:
        statement = statement.where(
            MemoryRecord.storage_status == storage_status
        )

    return list(db.scalars(statement).all())