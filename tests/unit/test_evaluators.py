"""
Unit tests for deterministic evaluators.

Covers: exact match, normalized exact match, token F1, keyword coverage,
latency metric, and edge cases (empty strings, errors, missing references).
"""

from __future__ import annotations

from llm_eval_lab.evaluators.deterministic import (
    ExactMatchEvaluator,
    KeywordCoverageEvaluator,
    LatencyEvaluator,
    NormalizedExactMatchEvaluator,
    TokenOverlapF1Evaluator,
)
from llm_eval_lab.evaluators.judge import JudgeEvaluator
from llm_eval_lab.schemas import MetricDirection, ModelResponse, ProviderConfig, TestCase


def _case(
    input_text: str = "test input",
    reference: str | None = "expected answer",
    keywords: list[str] | None = None,
) -> TestCase:
    return TestCase(
        id="t1",
        input=input_text,
        reference=reference,
        expected_keywords=keywords or [],
    )


def _response(text: str = "expected answer", error: str | None = None) -> ModelResponse:
    return ModelResponse(text=text, latency_ms=100.0, error=error)


# ── ExactMatchEvaluator ───────────────────────────────────────────────────────


class TestExactMatch:
    ev = ExactMatchEvaluator()

    def test_match(self):
        r = self.ev.evaluate(_case(), _response())
        assert r.score == 1.0
        assert r.passed is True

    def test_no_match(self):
        r = self.ev.evaluate(_case(), _response("wrong answer"))
        assert r.score == 0.0
        assert r.passed is False

    def test_no_reference(self):
        r = self.ev.evaluate(_case(reference=None), _response())
        assert r.score is None
        assert r.error is not None

    def test_provider_error(self):
        r = self.ev.evaluate(_case(), _response(error="timeout"))
        assert r.score is None
        assert "failed" in r.error.lower()

    def test_case_sensitive(self):
        r = self.ev.evaluate(_case(reference="Hello"), _response("hello"))
        assert r.score == 0.0


# ── NormalizedExactMatchEvaluator ─────────────────────────────────────────────


class TestNormalizedExactMatch:
    ev = NormalizedExactMatchEvaluator()

    def test_match_exact(self):
        r = self.ev.evaluate(_case(), _response("expected answer"))
        assert r.score == 1.0

    def test_match_case_insensitive(self):
        r = self.ev.evaluate(_case(reference="Hello World"), _response("hello world"))
        assert r.score == 1.0

    def test_match_whitespace_normalized(self):
        r = self.ev.evaluate(_case(reference="  hello   world  "), _response("hello world"))
        assert r.score == 1.0

    def test_no_match(self):
        r = self.ev.evaluate(_case(reference="abc"), _response("xyz"))
        assert r.score == 0.0

    def test_no_reference(self):
        r = self.ev.evaluate(_case(reference=None), _response())
        assert r.score is None

    def test_details_populated(self):
        r = self.ev.evaluate(_case(reference="Hello"), _response("hello"))
        assert "normalized_prediction" in r.details
        assert "normalized_reference" in r.details


# ── TokenOverlapF1Evaluator ───────────────────────────────────────────────────


class TestTokenOverlapF1:
    ev = TokenOverlapF1Evaluator()

    def test_perfect_match(self):
        r = self.ev.evaluate(_case(reference="the cat sat"), _response("the cat sat"))
        assert abs(r.score - 1.0) < 1e-6

    def test_partial_overlap(self):
        r = self.ev.evaluate(_case(reference="the cat sat on mat"), _response("the cat"))
        assert 0.0 < r.score < 1.0

    def test_no_overlap(self):
        r = self.ev.evaluate(_case(reference="dog runs fast"), _response("cat sits slowly"))
        assert r.score == 0.0

    def test_empty_prediction_and_reference(self):
        r = self.ev.evaluate(_case(reference=""), _response(""))
        assert r.score == 1.0

    def test_empty_prediction(self):
        r = self.ev.evaluate(_case(reference="some text"), _response(""))
        assert r.score == 0.0

    def test_no_reference(self):
        r = self.ev.evaluate(_case(reference=None), _response("text"))
        assert r.score is None

    def test_provider_error(self):
        r = self.ev.evaluate(_case(), _response(error="err"))
        assert r.score is None

    def test_f1_is_harmonic_mean(self):
        # pred = "a b", ref = "a b c d"
        # common = {a:1, b:1} = 2
        # precision = 2/2 = 1.0, recall = 2/4 = 0.5, f1 = 0.667
        r = self.ev.evaluate(_case(reference="a b c d"), _response("a b"))
        assert abs(r.score - 2 / 3) < 0.01

    def test_details_contain_precision_recall(self):
        r = self.ev.evaluate(_case(reference="hello world"), _response("hello"))
        assert "precision" in r.details
        assert "recall" in r.details


# ── KeywordCoverageEvaluator ──────────────────────────────────────────────────


class TestKeywordCoverage:
    ev = KeywordCoverageEvaluator()

    def test_all_keywords_found(self):
        case = _case(keywords=["python", "language"])
        resp = _response("Python is a programming language.")
        r = self.ev.evaluate(case, resp)
        assert r.score == 1.0
        assert r.passed is True

    def test_partial_keywords(self):
        case = _case(keywords=["python", "ruby", "java"])
        resp = _response("Python is great.")
        r = self.ev.evaluate(case, resp)
        assert abs(r.score - 1 / 3) < 0.01

    def test_no_keywords_configured(self):
        r = self.ev.evaluate(_case(keywords=[]), _response("anything"))
        assert r.score is None
        assert r.error is not None

    def test_case_insensitive_match(self):
        case = _case(keywords=["Python"])
        resp = _response("python programming")
        r = self.ev.evaluate(case, resp)
        assert r.score == 1.0

    def test_provider_error(self):
        case = _case(keywords=["kw"])
        r = self.ev.evaluate(case, _response(error="err"))
        assert r.score is None

    def test_missing_keywords_in_details(self):
        case = _case(keywords=["found", "nothere"])
        resp = _response("word found here")
        r = self.ev.evaluate(case, resp)
        assert "nothere" in r.details["missing"]


# ── LatencyEvaluator ──────────────────────────────────────────────────────────


class TestLatencyEvaluator:
    ev = LatencyEvaluator()

    def test_records_latency(self):
        r = self.ev.evaluate(_case(), ModelResponse(text="x", latency_ms=250.0))
        assert r.score == 250.0

    def test_direction_lower_is_better(self):
        assert self.ev.direction == MetricDirection.LOWER_IS_BETTER

    def test_no_reference_needed(self):
        r = self.ev.evaluate(_case(reference=None), ModelResponse(text="x", latency_ms=0.0))
        assert r.score == 0.0


# ── JudgeEvaluator Parsing ───────────────────────────────────────────────────


class TestJudgeEvaluatorParsing:
    ev = JudgeEvaluator(
        judge_config=ProviderConfig(name="mock"),
        score_min=0.0,
        score_max=10.0,
    )

    def test_parse_valid_json(self):
        score, err = self.ev._parse_score('{"score": 8, "reasoning": "Well formulated."}')
        assert score == 8.0
        assert err == ""

    def test_parse_json_code_fence(self):
        payload = '```json\n{\n  "score": 9,\n  "reasoning": "Excellent"\n}\n```'
        score, err = self.ev._parse_score(payload)
        assert score == 9.0
        assert err == ""

    def test_parse_extra_numbers_before_score(self):
        # Must not falsely grab "3" or "2"
        text = "Evaluated 3 criteria across 2 dimensions. score: 7"
        score, _ = self.ev._parse_score(text)
        assert score == 7.0

    def test_parse_malformed_json_with_explicit_label(self):
        text = "Rating = 8.5\nThe model answered accurately."
        score, _ = self.ev._parse_score(text)
        assert score == 8.5

    def test_reject_non_object_json(self):
        score, err = self.ev._parse_score("[1, 2, 3]")
        assert score is None
        assert "not a JSON object" in err

    def test_reject_missing_score_key(self):
        score, err = self.ev._parse_score('{"reasoning": "Missing score field"}')
        assert score is None
        assert "missing required 'score' key" in err

    def test_reject_non_numeric_score(self):
        score, err = self.ev._parse_score('{"score": "excellent", "reasoning": "good"}')
        assert score is None
        assert "not a valid number" in err

    def test_reject_out_of_range_high_no_silent_clamping(self):
        # Must not silently clamp 15 to 10
        score, err = self.ev._parse_score('{"score": 15}')
        assert score is None
        assert "outside allowed range" in err

    def test_reject_out_of_range_negative(self):
        score, err = self.ev._parse_score('{"score": -2}')
        assert score is None
        assert "outside allowed range" in err

    def test_reject_arbitrary_text_with_numbers(self):
        # Random numbers without score label must be rejected
        text = "There are 5 apples and 10 oranges in the basket."
        score, err = self.ev._parse_score(text)
        assert score is None
        assert "Could not safely parse" in err
