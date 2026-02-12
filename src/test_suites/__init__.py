"""Load test cases from JSON files in the data directory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from src.models import TestCase

DATA_DIR = Path(__file__).parent / "data"


def load_suite(name: str) -> list[TestCase]:
    """Load a test suite by filename (without .json extension)."""
    path = DATA_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Test suite not found: {path}")
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return [TestCase.from_dict(tc) for tc in raw]


def load_all_suites() -> list[TestCase]:
    """Load every .json file in the data directory."""
    cases: list[TestCase] = []
    for path in sorted(DATA_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        cases.extend(TestCase.from_dict(tc) for tc in raw)
    return cases


def list_suites() -> list[str]:
    """Return available suite names."""
    return sorted(p.stem for p in DATA_DIR.glob("*.json"))


def load_suites(names: Sequence[str]) -> list[TestCase]:
    """Load multiple named suites and merge."""
    cases: list[TestCase] = []
    for name in names:
        cases.extend(load_suite(name))
    return cases
