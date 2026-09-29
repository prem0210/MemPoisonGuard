import os
import re
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
from functools import lru_cache

from app.core.config import settings
from app.services.vector_store import chroma_client


NLI_LABELS = [
    "contradiction",
    "entailment",
    "neutral",
]


@lru_cache(maxsize=1)
def get_nli_model():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(settings.nli_model_name)


def get_verified_collection():
    return chroma_client.get_or_create_collection(
        name=settings.verified_collection_name
    )

def has_explicit_negation(text: str) -> bool:
    negation_pattern = (
        r"\b("
        r"not|never|no|none|neither|nor|without|"
        r"cannot|can't|won't|isn't|aren't|doesn't|don't|"
        r"didn't|wasn't|weren't"
        r")\b"
    )

    return bool(
        re.search(
            negation_pattern,
            text.lower(),
            flags=re.IGNORECASE,
        )
    )


def is_comparable_memory_pair(
    candidate_content: str,
    reference_content: str,
    distance: float,
) -> bool:
    if distance > settings.nli_enforcement_distance_threshold:
        return False

    candidate_has_negation = has_explicit_negation(candidate_content)
    reference_has_negation = has_explicit_negation(reference_content)

    if candidate_has_negation != reference_has_negation:
        return True

    return distance <= 0.35

def find_related_verified_memories(
    candidate_content: str,
) -> list[dict]:
    collection = get_verified_collection()

    if collection.count() == 0:
        return []

    result = collection.query(
        query_texts=[candidate_content],
        n_results=min(
            settings.nli_candidate_limit,
            collection.count(),
        ),
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    related_memories = []

    for document, metadata, distance in zip(documents, metadatas, distances):
        related_memories.append(
            {
                "memory_id": metadata.get("memory_id", ""),
                "content": document,
                "distance": float(distance),
                "source_name": metadata.get("source_name", "unknown"),
                "trust_score": float(metadata.get("trust_score", 0.0)),
            }
        )

    return related_memories


def get_nli_probabilities(
    premise: str,
    hypothesis: str,
) -> dict:
    model = get_nli_model()

    scores = model.predict(
        [(premise, hypothesis)],
        apply_softmax=True,
    )[0]

    return {
        label: round(float(score), 4)
        for label, score in zip(NLI_LABELS, scores)
    }


def detect_contradiction(
    candidate_content: str,
) -> dict:
    related_memories = find_related_verified_memories(candidate_content)

    if not related_memories:
        return {
            "contradiction_score": 0.0,
            "entailment_score": 0.0,
            "duplicate_score": 0.0,
            "flags": [],
            "evidence": [],
            "explanation": (
                "No verified memories exist yet for contradiction comparison."
            ),
        }

    evidence = []
    highest_contradiction = 0.0
    highest_entailment = 0.0
    duplicate_score = 0.0

    for memory in related_memories:
        probabilities = get_nli_probabilities(
            premise=memory["content"],
            hypothesis=candidate_content,
        )

        contradiction_probability = probabilities["contradiction"]
        entailment_probability = probabilities["entailment"]

        comparable_pair = is_comparable_memory_pair(
            candidate_content=candidate_content,
            reference_content=memory["content"],
            distance=memory["distance"],
        )

        if comparable_pair:
            highest_contradiction = max(
                highest_contradiction,
                contradiction_probability,
            )

        highest_entailment = max(
            highest_entailment,
            entailment_probability,
        )

        is_near_duplicate = (
            memory["distance"]
            <= settings.duplicate_similarity_threshold
        )

        if is_near_duplicate:
            duplicate_score = max(
                duplicate_score,
                round(1.0 - memory["distance"], 3),
            )

        evidence.append(
            {
                "memory_id": memory["memory_id"],
                "reference_content": memory["content"],
                "distance": round(memory["distance"], 4),
                "nli_probabilities": probabilities,
                "is_comparable_pair": comparable_pair,
                "is_near_duplicate": is_near_duplicate,
            }
        )

    flags = []

    if highest_contradiction >= settings.nli_contradiction_threshold:
        flags.append("nli_contradiction_detected")

    if duplicate_score > 0.0:
        flags.append("near_duplicate_memory")

    return {
        "contradiction_score": round(highest_contradiction, 3),
        "entailment_score": round(highest_entailment, 3),
        "duplicate_score": duplicate_score,
        "flags": flags,
        "evidence": evidence,
        "explanation": (
            "Compared candidate memory against semantically related "
            "verified memories using NLI. Contradiction enforcement "
            "was applied only to semantically comparable memory pairs."
        ),
    }