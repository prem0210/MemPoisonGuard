from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MemoryRecord(Base):
    __tablename__ = "memory_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    memory_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)

    source_type: Mapped[str] = mapped_column(String(50))
    source_name: Mapped[str] = mapped_column(String(255))
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    trust_score: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    injection_score: Mapped[float] = mapped_column(Float, default=0.0)
    contradiction_score: Mapped[float] = mapped_column(Float, default=0.0)
    provenance_score: Mapped[float] = mapped_column(Float, default=0.0)

    verification_status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        index=True,
    )
    storage_status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        index=True,
    )

    detector_flags: Mapped[str] = mapped_column(Text, default="[]")
    analysis_evidence: Mapped[str] = mapped_column(Text, default="{}")
    quarantine_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )