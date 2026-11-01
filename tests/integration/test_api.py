"""
Integration tests for the FastAPI application routes.

Covers:
- /api/health
- /api/datasets/validate
- /api/experiments/ (create, list, get, delete)
- /api/comparisons/ (create, get)
- /api/reports/ (markdown, json, csv)
"""

from __future__ import annotations

import io
import json
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from llm_eval_lab.api.main import create_app
from llm_eval_lab.config import settings


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "api_test.db"
    monkeypatch.setattr(settings, "db_path", db_path)
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr("llm_eval_lab.storage._storage", None)

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_dataset_path(tmp_path: Path) -> Path:
    data = [
        {"id": "c1", "input": "Hello", "reference": "Hello world", "context": "Greeting"},
        {
            "id": "c2",
            "input": "What is Python?",
            "reference": "Python is a language",
            "context": "Code",
        },
    ]
    p = tmp_path / "sample.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
    return p


def test_health_check(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


def test_validate_dataset_upload(client: TestClient, sample_dataset_path: Path):
    with open(sample_dataset_path, "rb") as f:
        response = client.post(
            "/api/datasets/validate",
            files={"file": ("sample.jsonl", f, "application/json")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["valid_cases"] == 2
    assert data["is_valid"] is True


def test_validate_dataset_invalid_extension(client: TestClient):
    response = client.post(
        "/api/datasets/validate",
        files={"file": ("sample.txt", io.BytesIO(b"some content"), "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_experiment_lifecycle_and_reports(client: TestClient, sample_dataset_path: Path):
    # 1. Create experiment
    payload = {
        "name": "API Experiment 1",
        "dataset_path": str(sample_dataset_path),
        "provider_name": "mock",
        "model": "mock-v1",
        "system_prompt": "You are helpful.",
        "user_template": "{input}",
        "exact_match": True,
        "token_f1": True,
    }
    create_res = client.post("/api/experiments/", json=payload)
    assert create_res.status_code == 200
    exp1_data = create_res.json()
    exp1_id = exp1_data["experiment_id"]
    assert exp1_data["status"] == "completed"

    # 2. List experiments
    list_res = client.get("/api/experiments/")
    assert list_res.status_code == 200
    exp_list = list_res.json()["experiments"]
    assert any(e["id"] == exp1_id for e in exp_list)

    # 3. Get experiment details
    get_res = client.get(f"/api/experiments/{exp1_id}")
    assert get_res.status_code == 200
    assert get_res.json()["config"]["name"] == "API Experiment 1"

    # 4. Reports (Markdown, JSON, CSV)
    md_res = client.get(f"/api/reports/experiments/{exp1_id}/markdown")
    assert md_res.status_code == 200
    assert "LLM Evaluation Lab" in md_res.text

    json_res = client.get(f"/api/reports/experiments/{exp1_id}/json")
    assert json_res.status_code == 200
    assert "results" in json_res.json()

    csv_res = client.get(f"/api/reports/experiments/{exp1_id}/csv")
    assert csv_res.status_code == 200
    assert "case_id" in csv_res.text

    # 5. Create candidate experiment for comparison
    payload["name"] = "API Experiment 2"
    create_res2 = client.post("/api/experiments/", json=payload)
    exp2_id = create_res2.json()["experiment_id"]

    # 6. Compare
    comp_res = client.post(
        "/api/comparisons/", json={"baseline_id": exp1_id, "candidate_id": exp2_id}
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert "overall_decision" in comp_data
    comp_id = comp_data["comparison_id"]

    # 7. Get comparison report
    comp_get = client.get(f"/api/comparisons/{comp_id}")
    assert comp_get.status_code == 200
    assert comp_get.json()["comparison_id"] == comp_id

    # 8. Delete experiment
    del_res = client.delete(f"/api/experiments/{exp1_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] == exp1_id


def test_path_traversal_rejected(client: TestClient):
    """Attempting path traversal out of data_dir must be rejected with HTTP 400."""
    payload = {
        "name": "Traversal Attack",
        "dataset_path": "../../etc/passwd",
        "provider_name": "mock",
    }
    res = client.post("/api/experiments/", json=payload)
    assert res.status_code == 400
    assert "outside the allowed data directory" in res.json()["detail"]


def test_dataset_not_found_inside_data_dir(client: TestClient, tmp_path: Path):
    """Nonexistent dataset inside data_dir must return 400."""
    payload = {
        "name": "Missing File",
        "dataset_path": str(tmp_path / "does_not_exist.jsonl"),
        "provider_name": "mock",
    }
    res = client.post("/api/experiments/", json=payload)
    assert res.status_code == 400
    assert "Dataset not found" in res.json()["detail"]


def test_upload_oversized_file_rejected(client: TestClient):
    """Uploaded files exceeding 10MB must be rejected with HTTP 413."""
    # Create an in-memory stream exceeding 10MB (10 * 1024 * 1024 + 1024 bytes)
    oversized_data = b"x" * (10 * 1024 * 1024 + 1024)
    res = client.post(
        "/api/datasets/validate",
        files={"file": ("large.jsonl", io.BytesIO(oversized_data), "application/jsonl")},
    )
    assert res.status_code == 413
    assert "File too large" in res.json()["detail"]


@pytest.mark.asyncio
async def test_api_event_loop_responsiveness_during_experiment(tmp_path: Path, monkeypatch):
    """Verify that a slow/blocking experiment execution in asyncio.to_thread does

    not block concurrent requests (e.g. /api/health) on the FastAPI event loop.
    """
    db_path = tmp_path / "async_test.db"
    monkeypatch.setattr(settings, "db_path", db_path)
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr("llm_eval_lab.storage._storage", None)

    # Write a dataset with 5 cases
    data = [
        {"id": f"c{i}", "input": f"What is item {i}?", "reference": f"Item {i}"} for i in range(4)
    ]
    p = tmp_path / "slow_eval.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        # Check health initially
        init_health = await async_client.get("/api/health")
        assert init_health.status_code == 200

        # Start experiment payload
        exp_payload = {
            "name": "Threaded Evaluation",
            "dataset_path": str(p),
            "provider_name": "mock",
            "model": "mock-v1",
        }

        # Concurrently fire the experiment and a health check
        start_time = time.perf_counter()
        import asyncio

        exp_task = asyncio.create_task(async_client.post("/api/experiments/", json=exp_payload))
        # Wait a tiny moment to ensure the experiment task is running
        await asyncio.sleep(0.02)

        health_task = asyncio.create_task(async_client.get("/api/health"))

        health_res, exp_res = await asyncio.gather(health_task, exp_task)
        elapsed = time.perf_counter() - start_time
        assert elapsed >= 0.0

        assert health_res.status_code == 200
        assert health_res.json()["status"] == "ok"
        assert exp_res.status_code == 200
        assert exp_res.json()["status"] == "completed"
