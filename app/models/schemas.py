from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BaselineMemoryCreate(BaseModel):
    content: str = Field(
        ...,
        min_length=3,
        max_length=10000,
        description="Text to store as a baseline long-term memory.",
    )
    source_type: Literal["user_prompt", "document", "retrieved_content"] = "user_prompt"
    source_name: str = Field(
        default="manual_api_input",
        min_length=1,
        max_length=255,
    )
    source_reference: str | None = Field(
        default=None,
        max_length=255,
    )


class BaselineMemoryResponse(BaseModel):
    memory_id: str
    content: str
    source_type: str
    source_name: str
    source_reference: str | None
    storage_status: str
    created_at: datetime


class BaselineRetrieveRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=5000)
    top_k: int = Field(default=5, ge=1, le=10)


class RetrievedBaselineMemory(BaseModel):
    memory_id: str
    content: str
    source_type: str
    source_name: str
    similarity_distance: float | None = None


class BaselineRetrieveResponse(BaseModel):
    query: str
    retrieved_memories: list[RetrievedBaselineMemory]


class BaselineChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    top_k: int = Field(default=5, ge=1, le=10)


class BaselineChatResponse(BaseModel):
    answer: str
    model: str
    retrieved_memories: list[RetrievedBaselineMemory]


class DeleteResponse(BaseModel):
    message: str
    deleted_count: int

class GuardedMemoryCreate(BaseModel):
    content: str = Field(
        ...,
        min_length=3,
        max_length=10000,
        description="Candidate text to be analyzed before memory storage.",
    )
    source_type: Literal[
        "trusted_knowledge",
        "user_prompt",
        "document",
        "retrieved_content",
        "unknown",
    ] = "user_prompt"
    source_name: str = Field(
        default="manual_guarded_input",
        min_length=1,
        max_length=255,
    )
    source_reference: str | None = Field(default=None, max_length=255)


class GuardedMemoryResponse(BaseModel):
    memory_id: str
    content: str
    content_hash: str

    source_type: str
    source_name: str
    source_reference: str | None

    provenance_score: float
    injection_score: float
    contradiction_score: float
    trust_score: float
    risk_score: float

    verification_status: str
    storage_status: str
    detector_flags: list[str]
    analysis_evidence: dict
    quarantine_reason: str | None
    created_at: datetime


class GuardedMemoryListResponse(BaseModel):
    total: int
    memories: list[GuardedMemoryResponse]

class GuardedRetrieveRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=5000)
    top_k: int = Field(default=5, ge=1, le=10)


class RetrievedGuardedMemory(BaseModel):
    memory_id: str
    content: str
    source_type: str
    source_name: str
    provenance_score: float
    trust_score: float
    risk_score: float
    semantic_distance: float
    relevance_score: float
    safe_retrieval_score: float


class GuardedRetrieveResponse(BaseModel):
    query: str
    retrieved_memories: list[RetrievedGuardedMemory]


class GuardedChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    top_k: int = Field(default=5, ge=1, le=10)


class GuardedChatResponse(BaseModel):
    answer: str
    model: str
    retrieved_memories: list[RetrievedGuardedMemory]
    security_notice: str


class GuardedStatsResponse(BaseModel):
    verified_stored: int
    provisional: int
    quarantined: int
    total_guarded_memories: int

class EvaluationRunRequest(BaseModel):
    include_benign: bool = True
    include_attacks: bool = True
    reset_agent_memory_before_run: bool = True


class EvaluationRunResponse(BaseModel):
    experiment_id: str
    total_scenarios: int
    benign_scenarios: int
    malicious_scenarios: int
    message: str


class EvaluationMetricsResponse(BaseModel):
    experiment_id: str | None
    total_scenarios: int
    malicious_scenarios: int
    benign_scenarios: int

    detection_precision: float
    detection_recall: float
    detection_f1: float
    false_positive_rate: float
    false_negative_rate: float

    baseline_stored_malicious: int
    guarded_quarantined_malicious: int
    guarded_verified_malicious: int
    guarded_provisional_malicious: int