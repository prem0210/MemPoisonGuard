import re


SENSITIVE_CLAIM_PATTERNS = [
    (
        "unverified_authorization_claim",
        0.90,
        r"\b(user|customer|owner|administrator|admin)\b.{0,80}\b("
        r"approved|authorized|consented|permitted|allowed"
        r")\b",
    ),
    (
        "broad_confidential_disclosure_claim",
        0.95,
        r"\b(share|reveal|disclose|provide|send)\b.{0,100}\b("
        r"confidential|private|secret|restricted"
        r")\b",
    ),
    (
        "unbounded_recipient_claim",
        0.80,
        r"\b(anyone|any requester|every requester|all users|public)\b",
    ),
]


def detect_sensitive_claims(
    content: str,
    source_type: str,
) -> dict:
    normalized_content = re.sub(
        r"\s+",
        " ",
        content.lower(),
    ).strip()

    matches = []

    for flag_name, severity, pattern in SENSITIVE_CLAIM_PATTERNS:
        if re.search(pattern, normalized_content, flags=re.IGNORECASE):
            matches.append(
                {
                    "flag": flag_name,
                    "severity": severity,
                }
            )

    untrusted_source = source_type in {
        "document",
        "retrieved_content",
        "unknown",
    }

    flags = [match["flag"] for match in matches]

    high_risk_authorization_claim = (
        untrusted_source
        and "unverified_authorization_claim" in flags
        and (
            "broad_confidential_disclosure_claim" in flags
            or "unbounded_recipient_claim" in flags
        )
    )

    severity_score = max(
        [match["severity"] for match in matches],
        default=0.0,
    )

    return {
        "sensitive_claim_score": round(severity_score, 3),
        "flags": flags,
        "high_risk_authorization_claim": high_risk_authorization_claim,
        "explanation": (
            "Detected sensitive authorization or disclosure claim."
            if matches
            else "No sensitive authorization or disclosure claim detected."
        ),
    }