from app.core.config import settings
from app.services.vector_store import chroma_client


def get_verified_collection():
    return chroma_client.get_or_create_collection(
        name=settings.verified_collection_name
    )


def distance_to_relevance(distance: float) -> float:
    return round(1.0 / (1.0 + max(distance, 0.0)), 4)


def calculate_safe_retrieval_score(
    relevance_score: float,
    trust_score: float,
    risk_score: float,
) -> float:
    score = (
        0.65 * relevance_score
        + 0.25 * trust_score
        - 0.10 * risk_score
    )

    return round(max(0.0, min(1.0, score)), 4)


def retrieve_verified_memories(
    query: str,
    top_k: int,
) -> list[dict]:
    collection = get_verified_collection()

    if collection.count() == 0:
        return []

    candidate_limit = min(
        max(top_k * 3, top_k),
        collection.count(),
    )

    result = collection.query(
        query_texts=[query],
        n_results=candidate_limit,
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    safe_memories = []

    for document, metadata, distance in zip(documents, metadatas, distances):
        trust_score = float(metadata.get("trust_score", 0.0))
        risk_score = float(metadata.get("risk_score", 1.0))
        semantic_distance = float(distance)
        relevance_score = distance_to_relevance(semantic_distance)

        safe_score = calculate_safe_retrieval_score(
            relevance_score=relevance_score,
            trust_score=trust_score,
            risk_score=risk_score,
        )

        safe_memories.append(
            {
                "memory_id": metadata.get("memory_id", ""),
                "content": document,
                "source_type": metadata.get("source_type", "unknown"),
                "source_name": metadata.get("source_name", "unknown"),
                "provenance_score": float(
                    metadata.get("provenance_score", 0.0)
                ),
                "trust_score": trust_score,
                "risk_score": risk_score,
                "semantic_distance": round(semantic_distance, 4),
                "relevance_score": relevance_score,
                "safe_retrieval_score": safe_score,
            }
        )

    safe_memories.sort(
        key=lambda memory: memory["safe_retrieval_score"],
        reverse=True,
    )

    return safe_memories[:top_k]