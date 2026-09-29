def calculate_risk_score(
    injection_score: float,
    provenance_score: float,
    contradiction_score: float = 0.0,
    anomaly_score: float = 0.0,
) -> float:
    provenance_penalty = 1.0 - provenance_score

    risk_score = (
        0.50 * injection_score
        + 0.20 * contradiction_score
        + 0.20 * provenance_penalty
        + 0.10 * anomaly_score
    )

    return round(min(1.0, max(0.0, risk_score)), 3)


def calculate_trust_score(
    provenance_score: float,
    injection_score: float,
    contradiction_score: float = 0.0,
    validation_score: float = 0.70,
) -> float:
    trust_score = (
        0.45 * provenance_score
        + 0.25 * validation_score
        + 0.20 * (1.0 - contradiction_score)
        + 0.10 * (1.0 - injection_score)
    )

    return round(min(1.0, max(0.0, trust_score)), 3)


def decide_memory_action(
    risk_score: float,
    trust_score: float,
    injection_score: float,
    contradiction_score: float = 0.0,
) -> dict:
    if injection_score >= 0.80:
        return {
            "verification_status": "rejected",
            "storage_status": "quarantined",
            "quarantine_reason": "High-confidence prompt injection pattern detected.",
        }

    if contradiction_score >= 0.70:
        return {
            "verification_status": "rejected",
            "storage_status": "quarantined",
            "quarantine_reason": "High-confidence contradiction with trusted memory.",
        }

    if risk_score >= 0.70:
        return {
            "verification_status": "rejected",
            "storage_status": "quarantined",
            "quarantine_reason": "Overall risk score exceeds automatic quarantine threshold.",
        }

    if risk_score >= 0.40:
        return {
            "verification_status": "pending_review",
            "storage_status": "provisional",
            "quarantine_reason": None,
        }

    if trust_score >= 0.65:
        return {
            "verification_status": "verified",
            "storage_status": "verified_stored",
            "quarantine_reason": None,
        }

    return {
        "verification_status": "pending_review",
        "storage_status": "provisional",
        "quarantine_reason": None,
    }
    