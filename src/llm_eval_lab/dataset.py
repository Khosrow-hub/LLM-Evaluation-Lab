"""
JSONL dataset loading and validation.

Design decisions
----------------
* Invalid records are never silently discarded.  The caller receives both valid
  cases and a list of parse errors with line numbers.
* UTF-8 is required.  Files with a BOM are accepted but the BOM is stripped.
* Duplicate IDs are treated as a validation error on the second occurrence.
* Dataset size is bounded by Settings.max_cases.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

from pydantic import ValidationError

from llm_eval_lab.config import settings
from llm_eval_lab.schemas import DatasetInfo, TestCase


class DatasetParseError(Exception):
    """Raised when a dataset file cannot be opened or parsed at all."""


class ParseResult:
    """Result of loading one JSONL dataset."""

    def __init__(self) -> None:
        self.cases: list[TestCase] = []
        self.errors: list[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def info(self, path: str) -> DatasetInfo:
        categories: list[str] = []
        for c in self.cases:
            cat = c.metadata.get("category", "")
            if cat and cat not in categories:
                categories.append(cat)
        return DatasetInfo(
            path=path,
            total_cases=len(self.cases) + len(self.errors),
            valid_cases=len(self.cases),
            invalid_cases=len(self.errors),
            parse_errors=self.errors,
            categories=sorted(categories),
        )


def iter_jsonl(path: Path) -> Iterator[tuple[int, dict]]:
    """Yield (line_number, parsed_dict) for each non-blank line in a JSONL file.

    Raises DatasetParseError if the file cannot be opened.
    """
    try:
        with path.open(encoding="utf-8-sig") as fh:
            for lineno, raw in enumerate(fh, start=1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                    if not isinstance(parsed, dict):
                      actual_type = (
                        "null" if parsed is None
                        else "array" if isinstance(parsed, list)
                        else type(parsed).__name__
                      )
                      yield lineno, {
                        "__parse_error_": f"Expected a JSON object, got {actual_type}"
                      }
                    else:
                      yield lineno, parsed

                except json.JSONDecodeError as exc:
                  yield lineno, {"__parse_error__": str(exc)}
                    
    except OSError as exc:
        raise DatasetParseError(f"Cannot open dataset file '{path}': {exc}") from exc


def load_dataset(path: str | Path, max_cases: int | None = None) -> ParseResult:
    """Load a JSONL evaluation dataset.

    Parameters
    ----------
    path:
        Path to the JSONL file.
    max_cases:
        Maximum number of valid test cases to accept.  Defaults to
        ``settings.max_cases``.

    Returns
    -------
    ParseResult
        Contains the list of valid :class:`TestCase` objects and any parse
        errors encountered.  Callers should inspect ``result.errors`` before
        using the cases.
    """
    if max_cases is None:
        max_cases = settings.max_cases

    p = Path(path)
    result = ParseResult()
    seen_ids: set[str] = set()

    for lineno, raw in iter_jsonl(p):
        if "__parse_error__" in raw:
            result.errors.append(f"Line {lineno}: JSON parse error — {raw['__parse_error__']}")
            continue

        try:
            case = TestCase.model_validate(raw)
        except ValidationError as exc:
            msgs = "; ".join(
                f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()
            )
            result.errors.append(f"Line {lineno}: Validation error — {msgs}")
            continue

        if case.id in seen_ids:
            result.errors.append(f"Line {lineno}: Duplicate test-case id '{case.id}' — skipping.")
            continue

        seen_ids.add(case.id)
        result.cases.append(case)

        if len(result.cases) >= max_cases:
            result.errors.append(f"Dataset truncated: max_cases limit of {max_cases} reached.")
            break

    return result


def validate_dataset(path: str | Path) -> tuple[bool, list[str]]:
    """Validate a dataset file and return (is_valid, list_of_errors).

    Convenience wrapper around :func:`load_dataset`.
    """
    try:
        result = load_dataset(path)
    except DatasetParseError as exc:
        return False, [str(exc)]
    return result.is_valid, result.errors
