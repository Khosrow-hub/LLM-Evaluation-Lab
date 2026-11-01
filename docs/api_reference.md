# REST API Reference

The `LLM Evaluation Lab` backend provides a high-performance REST API built with FastAPI.

**Base URL:** `http://127.0.0.1:8000/api`  
**Interactive Docs:** `http://127.0.0.1:8000/api/docs`  
**OpenAPI Specification:** `http://127.0.0.1:8000/api/openapi.json`

---

## 1. System Endpoints

### Health Check
`GET /api/health`

**Response (`200 OK`):**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

## 2. Dataset Endpoints

### Validate Dataset Upload
`POST /api/datasets/validate`

Uploads and validates a `.jsonl` dataset file against schema rules (max 10MB).

**Request (`multipart/form-data`):**
- `file`: JSONL file.

**Response (`200 OK`):**
```json
{
  "filename": "sample_dataset.jsonl",
  "valid_cases": 12,
  "invalid_cases": 0,
  "total_cases": 12,
  "categories": ["Support", "Factual QA", "JSON Formatting"],
  "errors": [],
  "is_valid": true
}
```

---

## 3. Experiment Endpoints

### Create & Run Experiment
`POST /api/experiments/`

Runs an evaluation experiment against a dataset.

**Request (`application/json`):**
```json
{
  "name": "GPT-4o-mini Benchmark",
  "dataset_path": "examples/sample_dataset.jsonl",
  "provider_name": "mock",
  "model": "mock-default",
  "system_prompt": "You are a concise AI assistant.",
  "user_template": "{input}",
  "exact_match": true,
  "token_f1": true,
  "json_validity": false
}
```

**Response (`200 OK`):**
```json
{
  "experiment_id": "4fb76991-7ea2-4105-9bd1-b52c84542819",
  "status": "completed",
  "total_cases": 12,
  "success_rate": 1.0,
  "aggregate_metrics": {
    "exact_match": 0.75,
    "token_overlap_f1": 0.88
  }
}
```

### List Experiments
`GET /api/experiments/?limit=50`

**Response (`200 OK`):**
```json
{
  "experiments": [
    {
      "id": "4fb76991-7ea2-4105-9bd1-b52c84542819",
      "name": "GPT-4o-mini Benchmark",
      "status": "completed",
      "started_at": "2026-10-29T12:00:00Z",
      "completed_at": "2026-10-29T12:00:05Z",
      "error": null
    }
  ]
}
```

### Get Experiment Details
`GET /api/experiments/{experiment_id}`

Returns the full experiment object, including config, summary statistics, and all individual test case outputs and metric scores.

### Delete Experiment
`DELETE /api/experiments/{experiment_id}`

Deletes the experiment and cascades deletion to all associated test results.

**Response (`200 OK`):**
```json
{
  "deleted": "4fb76991-7ea2-4105-9bd1-b52c84542819"
}
```

---

## 4. Comparison Endpoints

### Compare Two Experiments
`POST /api/comparisons/`

Executes paired bootstrap resampling to compare candidate against baseline.

**Request (`application/json`):**
```json
{
  "baseline_id": "exp-baseline-uuid",
  "candidate_id": "exp-candidate-uuid"
}
```

**Response (`200 OK`):**
```json
{
  "comparison_id": "comp-7b56a1b2",
  "baseline_id": "exp-baseline-uuid",
  "candidate_id": "exp-candidate-uuid",
  "overall_decision": "IMPROVED",
  "metric_comparisons": [
    {
      "metric_name": "exact_match",
      "baseline_mean": 0.60,
      "candidate_mean": 0.80,
      "absolute_change": 0.20,
      "relative_change_pct": 33.33,
      "ci": {
        "lower": 0.0833,
        "upper": 0.3167,
        "level": 0.95
      },
      "decision": "IMPROVED",
      "n_paired": 12
    }
  ],
  "cases_improved": ["support-001", "qa-003"],
  "cases_regressed": []
}
```

---

## 5. Report Endpoints

### Export Experiment Report
`GET /api/reports/experiments/{experiment_id}/{format}`

- Supported formats: `markdown`, `json`, `csv`.
- Returns downloadable audit evidence with appropriate `Content-Type`.

### Export Comparison Report
`GET /api/reports/comparisons/{comparison_id}/{format}`

- Supported formats: `markdown`, `json`.
- Returns detailed regression reports formatted for GitHub PR comments, compliance documentation, or analytics ingestion.

---

## 6. Security & Deployment Model

- **Local-By-Default:** The API binds to `127.0.0.1` by default and has no built-in user authentication layer. It is designed for trusted local developer workflows and secure CI runners.
- **Non-Loopback Warning:** If `API_HOST` is configured to bind to a non-loopback interface (such as `0.0.0.0`), a prominent security warning is emitted at startup. In multi-user or production cloud deployments, place the API behind an authenticating reverse proxy (e.g., Nginx, Caddy, Cloudflare Access) with TLS encryption.
- **Dataset Path Containment:** The `/api/experiments/` endpoint resolves and validates all requested dataset paths using canonical path containment relative to the configured `LLM_EVAL_DATA_DIR`. Attempts to traverse outside the allowed directory (`../`, absolute paths, symlink escapes) are rejected with HTTP 400.
- **Bounded Streaming Uploads:** The `/api/datasets/validate` and `/api/datasets/preview` endpoints stream uploaded files in 64KB bounded chunks up to a 10MB hard ceiling before parsing. Files exceeding the limit are rejected immediately with HTTP 413 without loading the full file into server memory. Temporary files are guaranteed to be cleaned up in a `finally` block.
- **Zero Secret Exposure:** Model provider API keys are read directly from local environment variables or runtime configurations and are never persisted in the database, logged, or returned in API responses.
