#!/usr/bin/env python3
"""Validate Phase-6 reference-grounding artifacts without source access."""

import csv
import json
from pathlib import Path

TAXONOMY = {
    "EXACT_SAME_ACQUISITION_LOSSLESS",
    "SAME_ACQUISITION_PROVENANCE_INSUFFICIENT",
    "SAME_SUBJECT_DIFFERENT_OR_UNKNOWN_ACQUISITION",
    "DERIVED_PROVENANCE_UNKNOWN",
    "NON-COMPARABLE",
}


def main():
    root = Path(__file__).parents[1] / "artifacts/real-data-regression"
    data = json.loads((root / "bed-threshold-reference-grounding.json").read_text())
    assert data["classification"] == "BED THRESHOLD POLICY UNRESOLVED"
    assert len(data["accepted_cases"]) == 12
    assert data["verification"]["exact_mapping_count"] == 0
    assert all(
        case["accepted_auto_sha256"] and case["accepted_none_sha256"]
        for case in data["accepted_cases"]
    )
    for mapping in data["mappings"]:
        assert mapping["classification"] in TAXONOMY
        assert mapping["positive_provenance_evidence"] is False
    rows = list(
        csv.DictReader(
            (root / "bed-threshold-reference-grounding.csv").open(newline="")
        )
    )
    assert len(rows) == 12
    print("Phase-6 reference-grounding artifacts: valid")


if __name__ == "__main__":
    main()
