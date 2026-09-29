import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schemas import (
    GuardedChatRequest,
    GuardedChatResponse,
    GuardedMemoryCreate,
    GuardedMemoryListResponse,
    GuardedMemoryResponse,
    GuardedRetrieveRequest,
    GuardedRetrieveResponse,
    GuardedStatsResponse,
    RetrievedGuardedMemory,
)
from app.services.guarded_memory_service import (
    analyze_and_store_guarded_memory,
    list_guarded_memories,
)

from sqlalchemy import func, select

from app.models.database_models import MemoryRecord
from app.services.ollama_service import generate_guarded_response
from app.services.safe_retrieval_service import retrieve_verified_memories


router = APIRouter(
    prefix="/guarded",
    tags=["MemPoisonGuard"],
)


def to_guarded_response(record) -> GuardedMemoryResponse:
    return GuardedMemoryResponse(
        memory_id=record.memory_id,
        content=record.content,
        content_hash=record.content_hash,
        source_type=record.source_type,
        source_name=record.source_name,
        source_reference=record.source_reference,
        provenance_score=record.provenance_score,
        injection_score=record.injection_score,
        contradiction_score=record.contradiction_score,
        trust_score=record.trust_score,
        risk_score=record.risk_score,
        verification_status=record.verification_status,
        storage_status=record.storage_status,
        detector_flags=json.loads(record.detector_flags),
        analysis_evidence=json.loads(record.analysis_evidence),
        quarantine_reason=record.quarantine_reason,
        created_at=record.created_at,
    )


@router.post(
    "/memories",
    response_model=GuardedMemoryResponse,
    summary="Analyze and store a candidate memory using MemPoisonGuard",
)
def create_guarded_memory(
    payload: GuardedMemoryCreate,
    db: Session = Depends(get_db),
):
    record = analyze_and_store_guarded_memory(
        db=db,
        content=payload.content,
        source_type=payload.source_type,
        source_name=payload.source_name,
        source_reference=payload.source_reference,
    )

    return to_guarded_response(record)


@router.get(
    "/memories",
    response_model=GuardedMemoryListResponse,
    summary="List guarded memory records and their security decisions",
)
def get_guarded_memories(
    storage_status: str | None = Query(
        default=None,
        description=(
            "Optional: verified_stored, provisional, or quarantined."
        ),
    ),
    db: Session = Depends(get_db),
):
    records = list_guarded_memories(
        db=db,
        storage_status=storage_status,
    )

    memories = [
        to_guarded_response(record)
        for record in records
    ]

    return GuardedMemoryListResponse(
        total=len(memories),
        memories=memories,
    )

@router.post(
    "/retrieve",
    response_model=GuardedRetrieveResponse,
    summary="Retrieve verified memories only",
)
def retrieve_guarded_memories(
    payload: GuardedRetrieveRequest,
):
    memories = retrieve_verified_memories(
        query=payload.query,
        top_k=payload.top_k,
    )

    return GuardedRetrieveResponse(
        query=payload.query,
        retrieved_memories=[
            RetrievedGuardedMemory(**memory)
            for memory in memories
        ],
    )


@router.post(
    "/chat",
    response_model=GuardedChatResponse,
    summary="Chat using verified memory only",
)
async def chat_with_guarded_memory(
    payload: GuardedChatRequest,
):
    memories = retrieve_verified_memories(
        query=payload.message,
        top_k=payload.top_k,
    )

    try:
        answer = await generate_guarded_response(
            user_message=payload.message,
            retrieved_memories=memories,
        )
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"Guarded Ollama generation failed: {str(error)}",
        ) from error

    return GuardedChatResponse(
        answer=answer,
        model="configured_ollama_model",
        retrieved_memories=[
            RetrievedGuardedMemory(**memory)
            for memory in memories
        ],
        security_notice=(
            "Only verified memories were eligible for retrieval. "
            "Provisional and quarantined memories were excluded."
        ),
    )


@router.get(
    "/quarantine",
    response_model=GuardedMemoryListResponse,
    summary="Review quarantined memory records",
)
def get_quarantined_memories(
    db: Session = Depends(get_db),
):
    records = list_guarded_memories(
        db=db,
        storage_status="quarantined",
    )

    memories = [
        to_guarded_response(record)
        for record in records
    ]

    return GuardedMemoryListResponse(
        total=len(memories),
        memories=memories,
    )


@router.get(
    "/stats",
    response_model=GuardedStatsResponse,
    summary="Get guarded memory status counts",
)
def get_guarded_memory_stats(
    db: Session = Depends(get_db),
):
    guarded_filter = MemoryRecord.memory_id.like("guarded_%")

    def count_by_status(status: str) -> int:
        statement = select(func.count()).select_from(MemoryRecord).where(
            guarded_filter,
            MemoryRecord.storage_status == status,
        )
        return int(db.scalar(statement) or 0)

    verified_count = count_by_status("verified_stored")
    provisional_count = count_by_status("provisional")
    quarantined_count = count_by_status("quarantined")

    return GuardedStatsResponse(
        verified_stored=verified_count,
        provisional=provisional_count,
        quarantined=quarantined_count,
        total_guarded_memories=(
            verified_count + provisional_count + quarantined_count
        ),
    )