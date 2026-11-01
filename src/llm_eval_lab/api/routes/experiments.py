"""Experiment API routes: create, list, get, delete."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from llm_eval_lab.config import settings
from llm_eval_lab.runner import run_experiment
from llm_eval_lab.schemas import (
    EvaluatorConfig,
    ExperimentConfig,
    PromptTemplate,
    ProviderConfig,
)
from llm_eval_lab.storage import get_storage

router = APIRouter()


class RunExperimentRequest(BaseModel):
    name: str = "experiment"
    dataset_path: str
    provider_name: str = "mock"
    model: str = ""
    system_prompt: str = ""
    user_template: str = "{input}"
    exact_match: bool = True
    token_f1: bool = True
    json_validity: bool = False


def _validate_dataset_path(raw_path: str) -> Path:
    """Resolve and validate that a dataset path is contained within data_dir.

    Raises HTTPException(400) for paths outside the allowed directory or that
    do not exist.  Protects against path traversal (``../``) and symlink
    escapes by comparing canonical resolved paths.
    """
    allowed_dir = settings.data_dir.resolve()

    try:
        requested = Path(raw_path).resolve()
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid dataset path.") from exc

    # Containment check: resolved path must be inside data_dir
    try:
        requested.relative_to(allowed_dir)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Dataset path is outside the allowed data directory. "
                "Place dataset files inside the configured data directory."
            ),
        ) from exc

    if not requested.exists():
        raise HTTPException(status_code=400, detail="Dataset not found.")
    if not requested.is_file():
        raise HTTPException(status_code=400, detail="Dataset path is not a file.")

    return requested


@router.post("/")
async def create_experiment(req: RunExperimentRequest, background_tasks: BackgroundTasks):
    """Create and run an experiment.

    Execution is dispatched to an async worker thread via asyncio.to_thread to
    avoid blocking the FastAPI event loop during model provider calls or retries.
    """
    dataset_path = _validate_dataset_path(req.dataset_path)

    config = ExperimentConfig(
        name=req.name,
        dataset_path=str(dataset_path),
        provider=ProviderConfig(name=req.provider_name, model=req.model),
        prompt=PromptTemplate(system_prompt=req.system_prompt, user_template=req.user_template),
        evaluators=EvaluatorConfig(
            exact_match=req.exact_match,
            token_overlap_f1=req.token_f1,
            json_validity=req.json_validity,
        ),
    )

    experiment = await asyncio.to_thread(run_experiment, config)
    storage = get_storage()
    await asyncio.to_thread(storage.save_experiment, experiment)

    return {
        "experiment_id": experiment.experiment_id,
        "status": experiment.status.value,
        "summary": experiment.summary.model_dump(),
    }


@router.get("/")
async def list_experiments(limit: int = 20):
    """List recent experiments."""
    storage = get_storage()
    return {"experiments": storage.list_experiments(limit)}


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get a specific experiment by ID."""
    storage = get_storage()
    exp = storage.load_experiment(experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return exp.model_dump()


@router.delete("/{experiment_id}")
async def delete_experiment(experiment_id: str):
    """Delete an experiment."""
    storage = get_storage()
    found = storage.delete_experiment(experiment_id)
    if not found:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return {"deleted": experiment_id}
