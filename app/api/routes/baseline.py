from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.schemas import (
    BaselineChatRequest,
    BaselineChatResponse,
    BaselineMemoryCreate,
    BaselineMemoryResponse,
    BaselineRetrieveRequest,
    BaselineRetrieveResponse,
    DeleteResponse,
    RetrievedBaselineMemory,
)
from app.services.baseline_memory_service import (
    clear_baseline_memories,
    list_baseline_memories,
    retrieve_baseline_memories,
    store_baseline_memory,
)
from app.services.ollama_service import generate_baseline_response


router = APIRouter(
    prefix="/baseline",
    tags=["Baseline Agent"],
)


def to_memory_response(record) -> BaselineMemoryResponse:
    return BaselineMemoryResponse(
        memory_id=record.memory_id,
        content=record.content,
        source_type=record.source_type,
        source_name=record.source_name,
        source_reference=record.source_reference,
        storage_status=record.storage_status,
        created_at=record.created_at,
    )


@router.post(
    "/memories",
    response_model=BaselineMemoryResponse,
    summary="Store a memory without security verification",
)
def create_memory(
    payload: BaselineMemoryCreate,
    db: Session = Depends(get_db),
):
    record = store_baseline_memory(
        db=db,
        content=payload.content,
        source_type=payload.source_type,
        source_name=payload.source_name,
        source_reference=payload.source_reference,
    )

    return to_memory_response(record)


@router.get(
    "/memories",
    response_model=list[BaselineMemoryResponse],
    summary="List baseline memories",
)
def get_memories(db: Session = Depends(get_db)):
    records = list_baseline_memories(db)
    return [to_memory_response(record) for record in records]


@router.post(
    "/retrieve",
    response_model=BaselineRetrieveResponse,
    summary="Retrieve baseline memories through semantic similarity",
)
def retrieve_memories(payload: BaselineRetrieveRequest):
    memories = retrieve_baseline_memories(
        query=payload.query,
        top_k=payload.top_k,
    )

    return BaselineRetrieveResponse(
        query=payload.query,
        retrieved_memories=[
            RetrievedBaselineMemory(**memory)
            for memory in memories
        ],
    )


@router.post(
    "/chat",
    response_model=BaselineChatResponse,
    summary="Chat with the unprotected memory-enabled baseline agent",
)
async def chat(
    payload: BaselineChatRequest,
):
    memories = retrieve_baseline_memories(
        query=payload.message,
        top_k=payload.top_k,
    )

    try:
        answer = await generate_baseline_response(
            user_message=payload.message,
            retrieved_memories=memories,
        )
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"Ollama generation failed: {str(error)}",
        ) from error

    return BaselineChatResponse(
        answer=answer,
        model="configured_ollama_model",
        retrieved_memories=[
            RetrievedBaselineMemory(**memory)
            for memory in memories
        ],
    )


@router.delete(
    "/memories",
    response_model=DeleteResponse,
    summary="Clear all baseline memories",
)
def delete_memories(db: Session = Depends(get_db)):
    deleted_count = clear_baseline_memories(db)

    return DeleteResponse(
        message="Baseline memories cleared successfully.",
        deleted_count=deleted_count,
    )