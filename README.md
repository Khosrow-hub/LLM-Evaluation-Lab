# LLM Evaluation Lab

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%20%7C%203.12-blue?style=flat-square&logo=python" alt="Python 3.11 | 3.12" />
  <img src="https://img.shields.io/badge/tests-137%20passed-emerald?style=flat-square&logo=pytest" alt="137 Tests Passed" />
  <img src="https://img.shields.io/badge/fastapi-0.111-009688?style=flat-square&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/react-19%20%2B%20vite-61dafb?style=flat-square&logo=react" alt="React 19 + Vite" />
  <img src="https://img.shields.io/badge/license-MIT-purple?style=flat-square" alt="MIT License" />
</p>

<p align="center">
  <strong>Test your prompts. Measure your models. Trust your evidence.</strong><br>
  A scientific evaluation framework and statistical regression detection platform for AI engineering.
</p>

---

## 🌟 Overview

Most LLM applications are evaluated on "vibes" — changing a system prompt or upgrading a model and manually eye-balling three sample queries.

**LLM Evaluation Lab** replaces subjective guesswork with **rigorous, reproducible AI engineering**:
- **Dataset Validation:** Strict JSONL schema verification with line-by-line syntax diagnostics.
- **Layered Evaluator Pipeline:** Deterministic exact match, normalized exact match, token-level F1, keyword coverage, latency, JSON validity, schema compliance, semantic embedding similarity, and LLM-as-a-judge.
- **Statistical Regression Engine:** **Paired Non-Parametric Bootstrap Resampling** (2,000 resamples by default) computing empirical 95% confidence intervals and practical significance thresholds.
- **Multi-Interface Access:**
  - 🖥️ **CLI (`llm-eval`):** Terminal workflows with rich tables and progress tracking.
  - 🚀 **REST API:** High-throughput FastAPI service with OpenAPI documentation and zero secret leakage.
  - 💻 **Web Application:** Modern React 19 + Vite interface with obsidian dark mode, visual CI error bars, live runners, and dataset inspectors.
  - 🐍 **Python SDK:** Direct importable modules for custom research pipelines.

---

## 🏗️ Architecture

```
                           ┌────────────────────────┐
                           │   JSONL Test Dataset   │
                           └───────────┬────────────┘
                                       │
                                       ▼
┌──────────────────┐       ┌────────────────────────┐       ┌──────────────────────┐
│ Model Provider   │ ◄───► │    Evaluation Runner   │ ───►  │ Evaluator Pipeline   │
│ (Mock / OpenAI)  │       │     (llm_eval_lab)     │       │ (EM, F1, JSON, etc.) │
└──────────────────┘       └───────────┬────────────┘       └──────────────────────┘
                                       │
                                       ▼
                           ┌────────────────────────┐
                           │  SQLite Storage Layer  │
                           │     (eval_lab.db)      │
                           └───────────┬────────────┘
                                       │
             ┌─────────────────────────┴─────────────────────────┐
             ▼                                                   ▼
┌────────────────────────┐                           ┌────────────────────────┐
│ Statistical Comparison │                           │ REST API & Web UI      │
│ (Paired Bootstrap CI)  │                           │ (FastAPI, React 19)    │
└────────────────────────┘                           └────────────────────────┘
```

---

## ⚡ Quickstart in 60 Seconds

### 1. Installation

```bash
# Clone repository
git clone https://github.com/prathamforgelab/LLM-Evaluation-Lab.git
cd LLM-Evaluation-Lab

# Install package in editable mode
pip install -e .

# Or with dev dependencies (pytest, ruff, mypy)
pip install -e ".[dev]"
```

### 2. Validate a Dataset
```bash
llm-eval validate examples/sample_dataset.jsonl
```

### 3. Run an Evaluation Experiment
```bash
# Run with offline mock provider (instant, deterministic)
llm-eval run examples/sample_dataset.jsonl \
  --name "Baseline Run" \
  --provider mock \
  --evaluators exact_match,token_f1,json_validity
```

### 4. Statistically Compare Two Experiments
```bash
llm-eval compare \
  --baseline <baseline-experiment-id> \
  --candidate <candidate-experiment-id>
```

### 5. Launch the REST API & Web Dashboard
```bash
# Start FastAPI backend (http://127.0.0.1:8000)
llm-eval serve --host 127.0.0.1 --port 8000

# In another terminal, start the React frontend
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

---

## 📊 Statistical Regression Engine

Comparing two prompts by subtracting their average accuracy ($\bar{x}_B - \bar{x}_A = +0.023$ or $+2.3$ percentage points) is misleading on small or noisy datasets.

**LLM Evaluation Lab** pairs each test case:
$$d_i = \text{score}(C_i) - \text{score}(B_i)$$
and resamples differences with replacement over $B = 2,000$ iterations:

$$\text{CI}_{95\%} = [\text{percentile}_{2.5\%}, \text{percentile}_{97.5\%}]$$

### Statistical vs. Practical Significance & Units
- **Absolute Change ($\Delta$):** $\Delta = \bar{x}_C - \bar{x}_B$ expressed in the metric's natural units (e.g., $+0.05$ on a $[0, 1]$ accuracy scale represents $+5$ percentage points).
- **Relative Change ($\Delta\%$):** $\Delta\% = \frac{\Delta}{|\bar{x}_B|} \times 100\%$ (undefined when baseline mean is zero).
- **Practical Significance Threshold ($\tau$):** An optional minimum effect magnitude in **absolute metric units** (default $\tau = 0.0$, evaluating pure statistical significance).

### Decision State Matrix:
- `IMPROVED`: Lower bound of 95% CI $> \tau$ (for higher-is-better metrics; candidate improvement is statistically verifiable and clears practical threshold).
- `REGRESSED`: Upper bound of 95% CI $< -\tau$ (for higher-is-better metrics; candidate regression is statistically verifiable and exceeds practical threshold).
- `INCONCLUSIVE`: Confidence interval spans zero or fails to clear the practical threshold $\tau$.
- `INSUFFICIENT_DATA`: Fewer than 5 paired samples available between baseline and candidate.

*Note: For lower-is-better metrics (such as `latency_ms`), signs are inverted. Quality metrics drive the overall experiment release verdict, while latency is tracked as an informational metric.*

---

## 🐍 Python SDK Usage

```python
from pathlib import Path
from llm_eval_lab.runner import run_experiment
from llm_eval_lab.regression import compare_experiments
from llm_eval_lab.schemas import (
    EvaluatorConfig,
    ExperimentConfig,
    ProviderConfig,
    PromptTemplate,
)

# 1. Run baseline experiment
baseline = run_experiment(
    ExperimentConfig(
        name="Baseline",
        dataset_path="examples/sample_dataset.jsonl",
        provider=ProviderConfig(name="mock", model="mock-default"),
        prompt=PromptTemplate(system_prompt="Answer concisely."),
        evaluators=EvaluatorConfig(exact_match=True, token_overlap_f1=True),
    )
)

# 2. Run candidate experiment (e.g. modified prompt)
candidate = run_experiment(
    ExperimentConfig(
        name="Candidate",
        dataset_path="examples/sample_dataset.jsonl",
        provider=ProviderConfig(name="mock", model="mock-default"),
        prompt=PromptTemplate(system_prompt="You are an expert AI. Think step-by-step."),
        evaluators=EvaluatorConfig(exact_match=True, token_overlap_f1=True),
    )
)

# 3. Statistical comparison with 95% bootstrap CI
report = compare_experiments(baseline, candidate, bootstrap_n=2000, confidence_level=0.95)

print(f"Overall Decision: {report.overall_decision.value}")
for m in report.metric_comparisons:
    print(
        f"{m.metric_name}: Diff={m.absolute_change:+.4f}, CI=[{m.ci.lower:.4f}, {m.ci.upper:.4f}] -> {m.decision.value}"
    )
```

---

## 📁 Repository Structure

```
LLM-Evaluation-Lab/
├── .github/workflows/          # CI/CD pipelines
│   └── ci.yml                  # Matrix test runs (Python 3.11/3.12 on Linux & Windows)
├── docs/                       # Technical & scientific documentation
│   ├── architecture.md         # Component diagrams & storage models
│   ├── methodology.md          # Statistical mathematics & bootstrap theory
│   ├── metrics_guide.md        # Evaluator algorithms & formulas
│   ├── regression_engine.md    # State machine & CI gating
│   └── api_reference.md        # REST API endpoint reference
├── examples/                   # Datasets and Python examples
│   ├── sample_dataset.jsonl    # Multi-domain benchmark dataset
│   ├── run_offline_eval.py     # Programmatic evaluation script
│   └── compare_models.py       # Programmatic comparison script
├── frontend/                   # React 19 + TypeScript + Vite web app
│   ├── src/                    # Components (Dashboard, Evaluator, Comparison, Datasets)
│   └── package.json            # Frontend dependencies
├── src/llm_eval_lab/           # Core Python package
│   ├── api/                    # FastAPI app and route handlers
│   ├── evaluators/             # Deterministic, schema, and semantic evaluators
│   ├── providers/              # Mock and OpenAI-compatible providers
│   ├── cli.py                  # Typer CLI application
│   ├── config.py               # Environment configuration
│   ├── dataset.py              # JSONL parsing and validation
│   ├── metrics.py              # Statistical aggregations
│   ├── regression.py           # Comparison & regression decision engine
│   ├── reporting.py            # Markdown, JSON, and CSV exports
│   ├── runner.py               # Evaluation execution loop
│   ├── schemas.py              # Pydantic v2 domain models
│   ├── statistics.py           # Paired bootstrap resampling engine
│   └── storage.py              # SQLite persistence layer
├── tests/                      # Comprehensive test suite (137 tests)
│   ├── unit/                   # Evaluators, dataset, statistics, storage, CLI
│   └── integration/            # Workflow tests and FastAPI route tests
├── pyproject.toml              # Build configuration & dependencies
└── README.md                   # Project documentation
```

---

## 🧪 Testing & Quality Assurance

Run the test suite:
```bash
pytest
```
* **137 unit and integration tests passing** covering every evaluator, statistical function, edge case, and API route.
* Zero network dependencies required during test execution (utilizes offline `MockProvider`).

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.  
Copyright &copy; 2026 **Pratham Gupta**.
