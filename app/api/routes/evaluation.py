from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.evaluation.experiment_service import (
    load_latest_metrics,
    load_latest_results,
    reset_experiment_outputs,
    run_experiment,
)
from app.models.schemas import (
    EvaluationMetricsResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
)


router = APIRouter(
    prefix="/evaluation",
    tags=["Evaluation"],
)


@router.post(
    "/run",
    response_model=EvaluationRunResponse,
    summary="Run controlled baseline-versus-guarded memory experiment",
)
def run_controlled_experiment(
    payload: EvaluationRunRequest,
    db: Session = Depends(get_db),
):
    try:
        experiment_id, results, _ = run_experiment(
            db=db,
            include_benign=payload.include_benign,
            include_attacks=payload.include_attacks,
            reset_agent_memory_before_run=(
                payload.reset_agent_memory_before_run
            ),
        )
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Experiment execution failed: {str(error)}",
        ) from error

    benign_count = sum(
        1 for result in results
        if not result["is_malicious"]
    )

    malicious_count = sum(
        1 for result in results
        if result["is_malicious"]
    )

    return EvaluationRunResponse(
        experiment_id=experiment_id,
        total_scenarios=len(results),
        benign_scenarios=benign_count,
        malicious_scenarios=malicious_count,
        message=(
            "Experiment completed. Results and metrics were saved "
            "under storage/experiments."
        ),
    )


@router.get(
    "/results",
    summary="Get latest experiment attack-level results",
)
def get_latest_results():
    return {
        "results": load_latest_results(),
    }


@router.get(
    "/metrics",
    response_model=EvaluationMetricsResponse,
    summary="Get latest experiment security metrics",
)
def get_latest_metrics():
    metrics = load_latest_metrics()

    if metrics is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No experiment metrics found. Run POST /evaluation/run first."
            ),
        )

    return metrics


@router.post(
    "/reset",
    summary="Delete saved experiment result files only",
)
def reset_evaluation_results():
    reset_experiment_outputs()

    return {
        "message": (
            "Experiment result files deleted. "
            "Agent memories were not changed."
        )
    }