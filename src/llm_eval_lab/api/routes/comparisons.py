"""Comparison API routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from llm_eval_lab.regression import compare_experiments
from llm_eval_lab.schemas import RegressionConfig
from llm_eval_lab.storage import get_storage

router = APIRouter()


class CompareRequest(BaseModel):
    baseline_id: str
    candidate_id: str
    bootstrap_n: int = 2000
    bootstrap_seed: int = 42
    confidence_level: float = 0.95


@router.post("/")
async def create_comparison(req: CompareRequest):
    """Compare baseline and candidate experiments."""
    storage = get_storage()
    baseline = await asyncio.to_thread(storage.load_experiment, req.baseline_id)
    candidate = await asyncio.to_thread(storage.load_experiment, req.candidate_id)

    if baseline is None:
        raise HTTPException(
            status_code=404, detail=f"Baseline experiment not found: {req.baseline_id}"
        )
    if candidate is None:
        raise HTTPException(
            status_code=404, detail=f"Candidate experiment not found: {req.candidate_id}"
        )

    report = await asyncio.to_thread(
        compare_experiments,
        baseline,
        candidate,
        regression_config=RegressionConfig(),
        bootstrap_n=req.bootstrap_n,
        bootstrap_seed=req.bootstrap_seed,
        confidence_level=req.confidence_level,
    )
    await asyncio.to_thread(storage.save_comparison, report)

    return report.model_dump()


@router.get("/")
async def list_comparisons(limit: int = 20):
    storage = get_storage()
    return {"comparisons": storage.list_comparisons(limit)}


@router.get("/{comparison_id}")
async def get_comparison(comparison_id: str):
    storage = get_storage()
    report = storage.load_comparison(comparison_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Comparison not found.")
    return report.model_dump()
