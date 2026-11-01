"""
Unit tests for the regression decision engine.

Covers all four decision categories, practical significance, inverted metrics,
zero baseline, insufficient data, missing cases, and boundary conditions.
"""

from __future__ import annotations

import pytest

from llm_eval_lab.regression import classify_decision, compare_experiments
from llm_eval_lab.schemas import (
    CaseResult,
    Experiment,
    ExperimentConfig,
    ExperimentStatus,
    MetricDirection,
    MetricResult,
    ProviderConfig,
    RegressionConfig,
    RegressionDecision,
    RegressionThreshold,
)

# ── classify_decision ─────────────────────────────────────────────────────────


class TestClassifyDecision:
    def _call(self, lo, hi, ps=0.0, direction=MetricDirection.HIGHER_IS_BETTER, n=10, min_n=5):
        return classify_decision(lo, hi, ps, direction, n, min_n)

    def test_improved_ci_fully_positive(self):
        decision, _ = self._call(0.05, 0.20)
        assert decision == RegressionDecision.IMPROVED

    def test_regressed_ci_fully_negative(self):
        decision, _ = self._call(-0.20, -0.05)
        assert decision == RegressionDecision.REGRESSED

    def test_inconclusive_ci_crosses_zero(self):
        decision, _ = self._call(-0.05, 0.15)
        assert decision == RegressionDecision.INCONCLUSIVE

    def test_insufficient_data(self):
        decision, notes = self._call(0.1, 0.3, n=3, min_n=5)
        assert decision == RegressionDecision.INSUFFICIENT_DATA
        assert any("3" in n for n in notes)

    def test_practical_significance_prevents_improved(self):
        # CI = [0.01, 0.03] is positive but below threshold=0.05
        decision, _ = self._call(0.01, 0.03, ps=0.05)
        assert decision == RegressionDecision.INCONCLUSIVE

    def test_practical_significance_allows_improved_at_threshold(self):
        # CI = [0.06, 0.10] is fully above threshold=0.05
        decision, _ = self._call(0.06, 0.10, ps=0.05)
        assert decision == RegressionDecision.IMPROVED

    def test_lower_is_better_improved(self):
        # For lower-is-better, a negative diff (candidate is lower) is good.
        # CI [-0.2, -0.05] means candidate is lower → IMPROVED after sign flip.
        decision, _ = self._call(-0.20, -0.05, direction=MetricDirection.LOWER_IS_BETTER)
        assert decision == RegressionDecision.IMPROVED

    def test_lower_is_better_regressed(self):
        # CI [0.05, 0.20] means candidate is higher → REGRESSED for lower-is-better.
        decision, _ = self._call(0.05, 0.20, direction=MetricDirection.LOWER_IS_BETTER)
        assert decision == RegressionDecision.REGRESSED

    def test_exactly_at_zero(self):
        decision, _ = self._call(0.0, 0.0)
        assert decision == RegressionDecision.INCONCLUSIVE

    def test_default_threshold_strictly_requires_non_zero_bound(self):
        # Default ps=0.0: CI lower bound must strictly exceed 0
        dec_improved, _ = self._call(0.0001, 0.05, ps=0.0)
        assert dec_improved == RegressionDecision.IMPROVED

        # Exact zero at lower bound is NOT improved
        dec_zero_low, _ = self._call(0.0, 0.05, ps=0.0)
        assert dec_zero_low == RegressionDecision.INCONCLUSIVE

        # Default ps=0.0: CI upper bound must strictly be below 0
        dec_regressed, _ = self._call(-0.05, -0.0001, ps=0.0)
        assert dec_regressed == RegressionDecision.REGRESSED

        # Exact zero at upper bound is NOT regressed
        dec_zero_high, _ = self._call(-0.05, 0.0, ps=0.0)
        assert dec_zero_high == RegressionDecision.INCONCLUSIVE

    def test_practical_significance_exact_boundary_conditions(self):
        # Boundary: ci_lower == threshold -> INCONCLUSIVE because it requires strictly >
        dec_at_thresh, _ = self._call(0.05, 0.10, ps=0.05)
        assert dec_at_thresh == RegressionDecision.INCONCLUSIVE

        # Above boundary -> IMPROVED
        dec_above, _ = self._call(0.0501, 0.10, ps=0.05)
        assert dec_above == RegressionDecision.IMPROVED

        # Negative boundary: ci_upper == -threshold -> INCONCLUSIVE (requires strictly <)
        dec_neg_thresh, _ = self._call(-0.10, -0.05, ps=0.05)
        assert dec_neg_thresh == RegressionDecision.INCONCLUSIVE

        # Below negative boundary -> REGRESSED
        dec_below, _ = self._call(-0.10, -0.0501, ps=0.05)
        assert dec_below == RegressionDecision.REGRESSED

    def test_lower_is_better_with_nonzero_practical_threshold(self):
        # Lower-is-better: candidate latency drops by 50-100ms. Threshold = 20ms.
        # Difference = cand - base = [-100, -50].
        # Sign-flipped to [50, 100]. Lower bound 50 > 20 -> IMPROVED.
        dec_imp, _ = self._call(-100.0, -50.0, ps=20.0, direction=MetricDirection.LOWER_IS_BETTER)
        assert dec_imp == RegressionDecision.IMPROVED

        # Latency drops by only 5-15ms, which is below practical threshold of 20ms
        dec_small_imp, _ = self._call(
            -15.0, -5.0, ps=20.0, direction=MetricDirection.LOWER_IS_BETTER
        )
        assert dec_small_imp == RegressionDecision.INCONCLUSIVE

        # Latency increases by 50-100ms. Difference = [50, 100].
        # Sign-flipped to [-100, -50]. Upper bound -50 < -20 -> REGRESSED.
        dec_reg, _ = self._call(50.0, 100.0, ps=20.0, direction=MetricDirection.LOWER_IS_BETTER)
        assert dec_reg == RegressionDecision.REGRESSED


# ── compare_experiments ───────────────────────────────────────────────────────


def _make_experiment(
    case_scores: dict[str, float | None],
    metric_name: str = "exact_match",
    direction: MetricDirection = MetricDirection.HIGHER_IS_BETTER,
) -> Experiment:
    """Build a minimal Experiment with the given per-case scores."""
    results = []
    for cid, score in case_scores.items():
        mr = MetricResult(
            metric_name=metric_name,
            score=score,
            direction=direction,
        )
        results.append(
            CaseResult(
                case_id=cid,
                input=f"input {cid}",
                metrics=[mr],
            )
        )

    config = ExperimentConfig(
        provider=ProviderConfig(name="mock"),
        dataset_path="test.jsonl",
    )
    return Experiment(
        config=config,
        status=ExperimentStatus.COMPLETED,
        results=results,
    )


def _scores(n: int, value: float) -> dict[str, float]:
    return {f"case-{i}": value for i in range(n)}


class TestCompareExperiments:
    def test_identical_experiments_inconclusive(self):
        scores = _scores(20, 0.5)
        base = _make_experiment(scores)
        cand = _make_experiment(scores)
        report = compare_experiments(base, cand, bootstrap_n=200, bootstrap_seed=42)
        # With identical scores, CI should straddle zero or give INCONCLUSIVE
        mc = report.metric_comparisons[0]
        assert mc.decision in (
            RegressionDecision.INCONCLUSIVE,
            RegressionDecision.INSUFFICIENT_DATA,
        )

    def test_clear_improvement_detected(self):
        base = _make_experiment(_scores(30, 0.3))
        cand = _make_experiment(_scores(30, 0.7))
        report = compare_experiments(base, cand, bootstrap_n=500, bootstrap_seed=42)
        mc = next(m for m in report.metric_comparisons if m.metric_name == "exact_match")
        assert mc.decision == RegressionDecision.IMPROVED
        assert mc.absolute_change == pytest.approx(0.4, abs=1e-5)

    def test_clear_regression_detected(self):
        base = _make_experiment(_scores(30, 0.7))
        cand = _make_experiment(_scores(30, 0.3))
        report = compare_experiments(base, cand, bootstrap_n=500, bootstrap_seed=42)
        mc = next(m for m in report.metric_comparisons if m.metric_name == "exact_match")
        assert mc.decision == RegressionDecision.REGRESSED

    def test_insufficient_data_small_sample(self):
        base = _make_experiment(_scores(2, 0.5))
        cand = _make_experiment(_scores(2, 0.8))
        report = compare_experiments(
            base,
            cand,
            bootstrap_n=100,
            bootstrap_seed=42,
        )
        mc = next(m for m in report.metric_comparisons if m.metric_name == "exact_match")
        assert mc.decision == RegressionDecision.INSUFFICIENT_DATA

    def test_empty_experiments(self):
        base = _make_experiment({})
        cand = _make_experiment({})
        report = compare_experiments(base, cand)
        assert report.overall_decision == RegressionDecision.INSUFFICIENT_DATA

    def test_zero_baseline_score(self):
        base = _make_experiment(_scores(20, 0.0))
        cand = _make_experiment(_scores(20, 0.1))
        report = compare_experiments(base, cand, bootstrap_n=200, bootstrap_seed=42)
        # Relative change should be None (zero baseline)
        mc = next(m for m in report.metric_comparisons if m.metric_name == "exact_match")
        assert mc.relative_change_pct is None

    def test_missing_cases_counted(self):
        base = _make_experiment({"a": 0.5, "b": 0.5, "c": 0.5})
        cand = _make_experiment({"a": 0.6, "c": 0.7})  # missing "b"
        report = compare_experiments(base, cand, bootstrap_n=100, bootstrap_seed=42)
        mc = next(m for m in report.metric_comparisons if m.metric_name == "exact_match")
        assert mc.n_missing_baseline == 0
        assert mc.n_missing_candidate > 0

    def test_failed_cases_not_counted_in_paired(self):
        base = _make_experiment({"a": 0.5, "b": None, "c": 0.5})
        cand = _make_experiment({"a": 0.6, "b": 0.7, "c": 0.6})
        report = compare_experiments(base, cand, bootstrap_n=100, bootstrap_seed=42)
        mc = next(m for m in report.metric_comparisons if m.metric_name == "exact_match")
        assert mc.n_paired == 2  # "b" excluded
        assert mc.n_failed == 1

    def test_deterministic_with_fixed_seed(self):
        base = _make_experiment({f"c{i}": 0.5 + i * 0.01 for i in range(20)})
        cand = _make_experiment({f"c{i}": 0.6 + i * 0.01 for i in range(20)})
        r1 = compare_experiments(base, cand, bootstrap_n=200, bootstrap_seed=99)
        r2 = compare_experiments(base, cand, bootstrap_n=200, bootstrap_seed=99)
        mc1 = r1.metric_comparisons[0]
        mc2 = r2.metric_comparisons[0]
        assert mc1.ci.lower == mc2.ci.lower
        assert mc1.ci.upper == mc2.ci.upper

    def test_overall_decision_regressed_when_any_metric_regresses(self):
        base = _make_experiment(_scores(30, 0.7))
        cand = _make_experiment(_scores(30, 0.3))
        report = compare_experiments(base, cand, bootstrap_n=500, bootstrap_seed=42)
        assert report.overall_decision == RegressionDecision.REGRESSED

    def test_practical_significance_config(self):
        # Small improvement that should be INCONCLUSIVE with threshold=0.3
        base = _make_experiment(_scores(30, 0.5))
        cand = _make_experiment(_scores(30, 0.6))
        cfg = RegressionConfig(
            thresholds=[RegressionThreshold(metric_name="exact_match", practical_significance=0.3)]
        )
        report = compare_experiments(
            base, cand, regression_config=cfg, bootstrap_n=500, bootstrap_seed=42
        )
        mc = next(m for m in report.metric_comparisons if m.metric_name == "exact_match")
        assert mc.decision == RegressionDecision.INCONCLUSIVE

    def test_latency_regression_independent_of_overall_quality_decision(self):
        # Accuracy improves, latency regresses. Overall decision should be IMPROVED.
        base_cases = {
            f"c{i}": [
                MetricResult(
                    metric_name="exact_match", score=0.3, direction=MetricDirection.HIGHER_IS_BETTER
                ),
                MetricResult(
                    metric_name="latency_ms", score=100.0, direction=MetricDirection.LOWER_IS_BETTER
                ),
            ]
            for i in range(25)
        }
        cand_cases = {
            f"c{i}": [
                MetricResult(
                    metric_name="exact_match", score=0.8, direction=MetricDirection.HIGHER_IS_BETTER
                ),
                MetricResult(
                    metric_name="latency_ms", score=400.0, direction=MetricDirection.LOWER_IS_BETTER
                ),
            ]
            for i in range(25)
        }
        base_exp = Experiment(
            config=ExperimentConfig(
                provider=ProviderConfig(name="mock"), dataset_path="test.jsonl"
            ),
            status=ExperimentStatus.COMPLETED,
            results=[
                CaseResult(case_id=cid, input=f"input {cid}", metrics=m)
                for cid, m in base_cases.items()
            ],
        )
        cand_exp = Experiment(
            config=ExperimentConfig(
                provider=ProviderConfig(name="mock"), dataset_path="test.jsonl"
            ),
            status=ExperimentStatus.COMPLETED,
            results=[
                CaseResult(case_id=cid, input=f"input {cid}", metrics=m)
                for cid, m in cand_cases.items()
            ],
        )
        report = compare_experiments(base_exp, cand_exp, bootstrap_n=200, bootstrap_seed=42)

        em_mc = next(m for m in report.metric_comparisons if m.metric_name == "exact_match")
        lat_mc = next(m for m in report.metric_comparisons if m.metric_name == "latency_ms")

        assert em_mc.decision == RegressionDecision.IMPROVED
        assert lat_mc.decision == RegressionDecision.REGRESSED
        # Overall decision follows quality metrics, not informational latency
        assert report.overall_decision == RegressionDecision.IMPROVED
