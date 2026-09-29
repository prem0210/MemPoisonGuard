import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sklearn.metrics import precision_recall_fscore_support
from sqlalchemy.orm import Session

from app.core.config import BASE_DIR, settings
from app.services.baseline_memory_service import (
    clear_baseline_memories,
    store_baseline_memory,
)
from app.services.guarded_memory_service import (
    analyze_and_store_guarded_memory,
)


def resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)

    if not path.is_absolute():
        path = BASE_DIR / path

    return path


def read_jsonl(file_name: str) -> list[dict]:
    file_path = resolve_project_path(
        f"{settings.evaluation_data_directory}/{file_name}"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Evaluation dataset not found: {file_path}"
        )

    records = []

    with file_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            clean_line = line.strip()

            if not clean_line:
                continue

            try:
                records.append(json.loads(clean_line))
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON in {file_name} at line {line_number}: "
                    f"{error.msg}"
                ) from error

    return records


def get_output_directory() -> Path:
    output_directory = resolve_project_path(
        settings.experiment_output_directory
    )
    output_directory.mkdir(parents=True, exist_ok=True)
    return output_directory


def build_result_record(
    experiment_id: str,
    scenario: dict,
    baseline_record,
    guarded_record,
) -> dict:
    is_malicious = scenario["label"] == "malicious"

    guarded_blocked = guarded_record.storage_status in {
        "quarantined",
        "provisional",
    }

    guarded_verified_malicious = (
        is_malicious
        and guarded_record.storage_status == "verified_stored"
    )

    return {
        "experiment_id": experiment_id,
        "scenario_id": scenario["scenario_id"],
        "category": scenario["category"],
        "label": scenario["label"],
        "content": scenario["content"],
        "source_type": scenario["source_type"],
        "source_name": scenario["source_name"],

        "baseline_memory_id": baseline_record.memory_id,
        "baseline_storage_status": baseline_record.storage_status,

        "guarded_memory_id": guarded_record.memory_id,
        "guarded_storage_status": guarded_record.storage_status,
        "guarded_verification_status": guarded_record.verification_status,
        "guarded_trust_score": guarded_record.trust_score,
        "guarded_risk_score": guarded_record.risk_score,
        "guarded_injection_score": guarded_record.injection_score,
        "guarded_contradiction_score": guarded_record.contradiction_score,
        "guarded_detector_flags": guarded_record.detector_flags,
        "guarded_quarantine_reason": guarded_record.quarantine_reason,

        "expected_guarded_status": scenario.get(
            "expected_guarded_status",
            "",
        ),
        "expected_flag": scenario.get("expected_flag", ""),

        "is_malicious": is_malicious,
        "guarded_blocked": guarded_blocked,
        "guarded_verified_malicious": guarded_verified_malicious,
        "expected_status_matched": (
            guarded_record.storage_status
            == scenario.get("expected_guarded_status", "")
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def calculate_metrics(
    experiment_id: str,
    results: list[dict],
) -> dict:
    y_true = [
        1 if result["is_malicious"] else 0
        for result in results
    ]

    y_pred = [
        1 if result["guarded_blocked"] else 0
        for result in results
    ]

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        average="binary",
        zero_division=0,
    )

    malicious_results = [
        result for result in results
        if result["is_malicious"]
    ]

    benign_results = [
        result for result in results
        if not result["is_malicious"]
    ]

    false_positive_count = sum(
        1 for result in benign_results
        if result["guarded_blocked"]
    )

    false_negative_count = sum(
        1 for result in malicious_results
        if not result["guarded_blocked"]
    )

    baseline_stored_malicious = sum(
        1 for result in malicious_results
        if result["baseline_storage_status"] == "baseline_stored"
    )

    guarded_quarantined_malicious = sum(
        1 for result in malicious_results
        if result["guarded_storage_status"] == "quarantined"
    )

    guarded_provisional_malicious = sum(
        1 for result in malicious_results
        if result["guarded_storage_status"] == "provisional"
    )

    guarded_verified_malicious = sum(
        1 for result in malicious_results
        if result["guarded_storage_status"] == "verified_stored"
    )

    return {
        "experiment_id": experiment_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_scenarios": len(results),
        "malicious_scenarios": len(malicious_results),
        "benign_scenarios": len(benign_results),

        "detection_precision": round(float(precision), 4),
        "detection_recall": round(float(recall), 4),
        "detection_f1": round(float(f1), 4),

        "false_positive_rate": round(
            false_positive_count / len(benign_results),
            4,
        ) if benign_results else 0.0,

        "false_negative_rate": round(
            false_negative_count / len(malicious_results),
            4,
        ) if malicious_results else 0.0,

        "baseline_stored_malicious": baseline_stored_malicious,
        "guarded_quarantined_malicious": guarded_quarantined_malicious,
        "guarded_provisional_malicious": guarded_provisional_malicious,
        "guarded_verified_malicious": guarded_verified_malicious,
    }


def save_results(
    results: list[dict],
    metrics: dict,
) -> None:
    output_directory = get_output_directory()

    json_results_path = output_directory / "experiment_results.json"
    csv_results_path = output_directory / "experiment_results.csv"
    metrics_path = output_directory / "metrics_summary.json"

    with json_results_path.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)

    if results:
        with csv_results_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=list(results[0].keys()),
            )
            writer.writeheader()
            writer.writerows(results)

    with metrics_path.open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)

def seed_trusted_memories(db: Session) -> int:
    seed_records = read_jsonl("trusted_seed_memories.jsonl")

    for seed in seed_records:
        analyze_and_store_guarded_memory(
            db=db,
            content=seed["content"],
            source_type=seed["source_type"],
            source_name=seed["source_name"],
            source_reference=seed["source_reference"],
        )

    return len(seed_records)

def run_experiment(
    db: Session,
    include_benign: bool = True,
    include_attacks: bool = True,
    reset_agent_memory_before_run: bool = True,
) -> tuple[str, list[dict], dict]:
    experiment_id = f"experiment_{uuid4().hex[:12]}"

    scenarios = []

    if include_benign:
        scenarios.extend(read_jsonl("benign_memories.jsonl"))

    if include_attacks:
        scenarios.extend(read_jsonl("attack_scenarios.jsonl"))

    if not scenarios:
        raise ValueError(
            "Select include_benign, include_attacks, or both."
        )

    if reset_agent_memory_before_run:
        clear_baseline_memories(db)

    seed_trusted_memories(db)

    results = []

    for scenario in scenarios:
        baseline_record = store_baseline_memory(
            db=db,
            content=scenario["content"],
            source_type=scenario["source_type"],
            source_name=scenario["source_name"],
            source_reference=scenario["source_reference"],
        )

        guarded_record = analyze_and_store_guarded_memory(
            db=db,
            content=scenario["content"],
            source_type=scenario["source_type"],
            source_name=scenario["source_name"],
            source_reference=scenario["source_reference"],
        )

        result = build_result_record(
            experiment_id=experiment_id,
            scenario=scenario,
            baseline_record=baseline_record,
            guarded_record=guarded_record,
        )

        results.append(result)

    metrics = calculate_metrics(
        experiment_id=experiment_id,
        results=results,
    )

    save_results(results=results, metrics=metrics)

    return experiment_id, results, metrics


def load_latest_results() -> list[dict]:
    results_path = get_output_directory() / "experiment_results.json"

    if not results_path.exists():
        return []

    with results_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_latest_metrics() -> dict | None:
    metrics_path = get_output_directory() / "metrics_summary.json"

    if not metrics_path.exists():
        return None

    with metrics_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def reset_experiment_outputs() -> None:
    output_directory = get_output_directory()

    for file_name in [
        "experiment_results.json",
        "experiment_results.csv",
        "metrics_summary.json",
    ]:
        file_path = output_directory / file_name

        if file_path.exists():
            file_path.unlink()