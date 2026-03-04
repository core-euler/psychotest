import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestData:
    base: dict


def load_test_data() -> TestData:
    root = Path(__file__).resolve().parents[1]
    with (root / "data" / "test.json").open("r", encoding="utf-8") as f:
        base = json.load(f)
    return TestData(base=base)
