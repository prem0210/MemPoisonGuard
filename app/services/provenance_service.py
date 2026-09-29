from datetime import datetime, timezone


SOURCE_TRUST_POLICY = {
    "trusted_knowledge": 0.90,
    "user_prompt": 0.75,
    "document": 0.45,
    "retrieved_content": 0.55,
    "unknown": 0.25,
}


def calculate_provenance_score(source_type: str) -> float:
    return SOURCE_TRUST_POLICY.get(
        source_type.strip().lower(),
        SOURCE_TRUST_POLICY["unknown"],
    )


def create_provenance_metadata(
    source_type: str,
    source_name: str,
    source_reference: str | None,
) -> dict:
    return {
        "source_type": source_type.strip().lower(),
        "source_name": source_name.strip(),
        "source_reference": source_reference.strip()
        if source_reference
        else None,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "provenance_score": calculate_provenance_score(source_type),
    }