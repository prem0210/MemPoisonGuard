import re


INJECTION_PATTERNS = [
    (
        "instruction_override",
        0.95,
        r"\b(ignore|disregard|override|bypass)\b.{0,80}\b("
        r"previous|prior|above|system|developer|safety|security|rules?|instructions?"
        r")\b",
    ),
    (
        "system_prompt_reference",
        0.80,
        r"\b(system prompt|developer message|hidden prompt|internal instructions?)\b",
    ),
    (
        "persistent_behavior_instruction",
        0.75,
        r"\b(always|permanently|from now on|for every future|in all future)\b"
        r".{0,100}\b(answer|respond|recommend|obey|follow|say|do)\b",
    ),
    (
        "data_exfiltration_attempt",
        0.95,
        r"\b(reveal|expose|leak|show|print|disclose)\b.{0,100}\b("
        r"secret|password|token|credential|private|confidential|system prompt"
        r")\b",
    ),
    (
        "security_bypass",
        0.85,
        r"\b(disable|turn off|bypass|avoid|skip)\b.{0,80}\b("
        r"security|safety|verification|validation|guard|filter|check"
        r")\b",
    ),
    (
        "authority_spoofing",
        0.65,
        r"\b(admin|administrator|developer|system|security team|official policy)\b"
        r".{0,80}\b(authorize[sd]?|requires?|says?|instructs?|approve[sd]?)\b",
    ),
    (
        "memory_manipulation",
        0.75,
        r"\b(store|save|remember|memorize)\b.{0,80}\b("
        r"permanently|forever|as a rule|as an instruction|priority"
        r")\b",
    ),
]


def detect_injection_patterns(content: str) -> dict:
    normalized_content = re.sub(r"\s+", " ", content.lower()).strip()

    matches = []

    for flag_name, severity, pattern in INJECTION_PATTERNS:
        if re.search(pattern, normalized_content, flags=re.IGNORECASE):
            matches.append(
                {
                    "flag": flag_name,
                    "severity": severity,
                }
            )

    if not matches:
        return {
            "injection_score": 0.0,
            "flags": [],
            "explanation": "No known prompt-injection pattern detected.",
        }

    maximum_severity = max(match["severity"] for match in matches)
    combined_score = min(
        1.0,
        maximum_severity + (0.05 * (len(matches) - 1)),
    )

    return {
        "injection_score": round(combined_score, 3),
        "flags": [match["flag"] for match in matches],
        "explanation": (
            f"Detected {len(matches)} suspicious pattern(s): "
            f"{', '.join(match['flag'] for match in matches)}."
        ),
    }