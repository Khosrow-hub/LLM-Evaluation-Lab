# Implementation Plan — LLM Evaluation Lab Stabilization & Hardening

**Target Release:** 0.1.1  
**Author:** Senior Engineering Agent  
**Status:** In Progress / Verifying  

---

## 1. Overview & Strategy

This implementation plan outlines the systematic sequence of engineering improvements to eliminate CI failures, correct mathematical and statistical discrepancies, harden API endpoints against common attack vectors, expand testing coverage, and bring documentation into 100% agreement with the running code.

---

## 2. Phase Breakdown

### Phase 1: Repository Audit & Planning
- [x] Scan complete repository structure and Git history.
- [x] Inspect existing schemas, evaluator logic, regression algorithms, API routes, and test suites.
- [x] Produce `docs/TECHNICAL_AUDIT.md`.
- [x] Produce `docs/IMPLEMENTATION_PLAN.md`.

### Phase 2: CI/CD Pipeline Stabilization
- [x] Resolve all Ruff linting violations (I001, UP017, UP042, F401, B008, B904, SIM108).
- [x] Format entire repository with `ruff format .`.
- [x] Configure `[tool.ruff.lint.flake8-bugbear]` with `extend-immutable-calls` for FastAPI & Typer factories.
- [x] Modernize `.github/workflows/ci.yml`:
  - Split lint/format checks from test execution.
  - Separate unit tests and integration tests with pytest markers/paths.
  - Add package build and wheel inspection steps.
  - Ensure Windows and Linux matrix coverage across Python 3.11 and 3.12.

### Phase 3: Statistical Methodology & Regression Engine
- [x] Audit Paired Bootstrap resampling implementation in `src/llm_eval_lab/statistics.py`.
- [x] Clarify and standardize practical significance policy:
  - Default $\tau = 0.0$ in code ensures tests require statistically robust non-zero intervals without imposing arbitrary domain thresholds.
  - Add documentation explaining how to specify $\tau > 0$ (e.g., $\tau = 0.02$) for absolute point difference requirements.
  - Distinguish absolute differences, percentage points, and relative change ($\Delta\% = \frac{d}{\|base\|} \times 100$).
- [x] Clarify decision engine rules in `src/llm_eval_lab/regression.py` and `docs/regression_engine.md`:
  - `IMPROVED`: CI lower bound exceeds $\tau$ for higher-is-better metrics.
  - `REGRESSED`: CI upper bound falls below $-\tau$ for higher-is-better metrics.
  - `INCONCLUSIVE`: CI crosses zero or fails to clear $\tau$.
  - `INSUFFICIENT_DATA`: Paired count $n < 5$.
- [x] Ensure `latency_ms` is explicitly treated as an informational metric in overall decision aggregation, while remaining independently reported and visible.

### Phase 4: Evaluator Integrity & Accuracy
- [x] Reconcile `docs/metrics_guide.md` with implementation reality:
  - Semantic similarity: $[-1.0, 1.0]$ range, cosine similarity on L2-normalized embeddings, threshold 0.8.
  - LLM-as-a-Judge: $0-10$ raw rubric normalized to $[0.0, 1.0]$.
  - Normalized Exact Match: Whitespace collapse + lowercase conversion (no article stripping).
  - JSON validity: Document raw JSON parsing behavior.
  - Groundedness: Clearly state that groundedness evaluator is not implemented; document roadmap.
- [x] Verify optional dependencies in `pyproject.toml` (`[semantic]`, `[json-schema]`).

### Phase 5: API Security & Reliability
- [x] Implement canonical path validation in `src/llm_eval_lab/api/routes/experiments.py`:
  - `Path.resolve()` against `settings.data_dir.resolve()`.
  - Block path traversal (`../`) and out-of-bounds filesystem access.
- [x] Implement streaming chunked upload validation in `src/llm_eval_lab/api/routes/datasets.py`:
  - Bounded 64KB chunk iteration with 10MB hard ceiling before full memory allocation.
  - Strict extension validation (`.jsonl`).
  - Guaranteed temporary file cleanup in `finally` blocks.

### Phase 6: Frontend Demo Data Integrity
- [ ] Inspect frontend code (`frontend/src/`).
- [ ] Ensure offline fallback data is prominently labelled with "DEMO DATA" / "SIMULATED DATA" badges.
- [ ] Verify frontend build (`npm run build`).

### Phase 7: Test Suite Expansion
- [ ] Add unit & integration tests for:
  - Path traversal attack attempts.
  - Oversized upload rejection with chunked streaming.
  - Non-JSONL extension upload rejection.
  - Latency regression independence from quality decision.
  - Practical significance boundary conditions.
  - Judge parsing fallbacks (malformed JSON regex recovery).
  - Zero baseline and empty array handling.

### Phase 8: Documentation Synchronization
- [ ] Update `README.md` to reflect current verified test counts and capabilities.
- [ ] Synchronize `docs/methodology.md`, `docs/regression_engine.md`, `docs/metrics_guide.md`, `docs/architecture.md`, `docs/api_reference.md`.

### Phase 9: Final Quality & Build Verification
- [ ] Verify `ruff check .` passes with zero warnings.
- [ ] Verify `ruff format --check .` passes.
- [ ] Execute complete `pytest` test suite with 100% pass rate.
- [ ] Run `python -m build` and verify wheel/sdist packages.
- [ ] Run frontend TypeScript compilation and build.
- [ ] Prepare final verification report.
