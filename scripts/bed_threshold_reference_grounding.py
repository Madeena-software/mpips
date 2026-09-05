#!/usr/bin/env python3
# flake8: noqa: E501
"""Build and validate Phase-6 BED reference-grounding evidence."""

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

TAXONOMY = (
    "EXACT_SAME_ACQUISITION_LOSSLESS",
    "SAME_ACQUISITION_PROVENANCE_INSUFFICIENT",
    "SAME_SUBJECT_DIFFERENT_OR_UNKNOWN_ACQUISITION",
    "DERIVED_PROVENANCE_UNKNOWN",
    "NON-COMPARABLE",
)
ROOT = Path(__file__).parents[1] / "artifacts/real-data-regression"
PHASE5 = ROOT / "bed-threshold-policy-characterization.json"
JSON_OUT = ROOT / "bed-threshold-reference-grounding.json"
CSV_OUT = ROOT / "bed-threshold-reference-grounding.csv"
MD_OUT = ROOT / "bed-threshold-reference-grounding.md"


def number(text):
    match = re.search(r"\d{10,}", text or "")
    return match.group(0) if match else None


def subject_key(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def canonical_inventory(records):
    fields = (
        "drive_file_id",
        "path",
        "filename",
        "file_type",
        "size_bytes",
        "sha256",
        "dimensions",
        "dtype",
        "acquisition_identifier",
        "session",
        "subject",
        "orientation",
        "derivation_provenance",
    )
    normalized = [{field: record.get(field) for field in fields} for record in records]
    return sorted(normalized, key=lambda record: record["path"])


def inventory_digest(records):
    payload = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def build_mappings(cases, inventory):
    mappings = []
    for case in cases:
        source_id = number(case["accepted_source_filename"])
        candidates = [
            record
            for record in inventory
            if record["session"] == case["session"]
            and subject_key(record["subject"]) == subject_key(case["subject"])
        ]
        for reference in candidates:
            same_acquisition = reference["acquisition_identifier"] == source_id
            classification = (
                "SAME_ACQUISITION_PROVENANCE_INSUFFICIENT"
                if same_acquisition
                else "SAME_SUBJECT_DIFFERENT_OR_UNKNOWN_ACQUISITION"
            )
            mappings.append(
                {
                    "case": case["case"],
                    "case_id": case["id"],
                    "reference_drive_file_id": reference["drive_file_id"],
                    "reference_path": reference["path"],
                    "reference_sha256": reference["sha256"],
                    "dimensions": reference["dimensions"],
                    "orientation": reference["orientation"],
                    "geometry_reconciliation": None,
                    "lossless": False,
                    "classification": classification,
                    "positive_provenance_evidence": False,
                    "relationship_evidence": (
                        "Filename-level acquisition number only; no derivation log or "
                        "metadata establishes provenance."
                        if same_acquisition
                        else (
                            "Same session/subject folder only; acquisition identity is not "
                            "established."
                        )
                    ),
                }
            )
    return sorted(mappings, key=lambda item: (item["case"], item["reference_path"]))


def counts(mappings):
    return {
        name: sum(item["classification"] == name for item in mappings)
        for name in TAXONOMY
    }


def write_markdown(data):
    summary = data["inventory_summary"]
    repro = data["inventory_reproducibility"]
    totals = data["verification"]["taxonomy_counts"]
    match = "" if repro["matches_provisional"] else "does not "
    text = f"""# BED Threshold Policy Reference Grounding

Classification: **{data['classification']}**

Phase-5 evidence: `{data['accepted_phase5_evidence']}`. The accepted 12-case Phase-5
cohort was used unchanged; no new cohort was selected.

## Inventory

The read-only Drive inventory found **{summary['processed_reference_tiff']} processed/reference
TIFFs** across six sessions and their subject folders. Historical Phase-5 inventory records
{summary['acquisition_npz']} acquisition NPZ candidates, {summary['gain_npz']} gain NPZ
files, {summary['calibration_or_processed_npz']} calibration/processed NPZ files, and no
generated outputs in scope. TIFF bytes were not materialized, so reference hashes and image
dimensions/dtypes are unavailable.

The refreshed normalized inventory digest is `{repro['refreshed_normalized_sha256']}`. It has
{repro['additions']} additions, {repro['removals']} removals, and {repro['changed_metadata']}
changed metadata records versus the provisional inventory; it {match}matches the provisional
inventory.

## Relationship results

All {len(data['mappings'])} same-session/subject reference candidates were classified
without treating folder proximity as proof. **{totals['EXACT_SAME_ACQUISITION_LOSSLESS']}**
were exact lossless matches, **{totals['SAME_ACQUISITION_PROVENANCE_INSUFFICIENT']}** had
filename-level acquisition-number matches but insufficient provenance, and
**{totals['SAME_SUBJECT_DIFFERENT_OR_UNKNOWN_ACQUISITION']}** were same-subject/different-
or-unknown-acquisition candidates. No derived-unknown or non-comparable mappings were created.

Filename-level matches cannot be promoted to exact identity without a derivation log or
metadata. No allowed geometry transform was applied; no mapping is lossless-comparable.

## Short-circuit

Because no accepted Phase-5 case has an `EXACT_SAME_ACQUISITION_LOSSLESS` reference,
Phase 6 short-circuited. AUTO/NONE arrays were not regenerated, and reference-vs-AUTO/NONE
measurements were not run.

The result is engineering provenance evidence only, not clinical ground truth or a runtime-policy decision.
"""
    MD_OUT.write_text(text)


def validate(data):
    assert data["classification"] == "BED THRESHOLD POLICY UNRESOLVED"
    assert len(data["accepted_cases"]) == 12
    assert data["verification"]["exact_mapping_count"] == 0
    assert all(
        case["accepted_auto_sha256"] and case["accepted_none_sha256"]
        for case in data["accepted_cases"]
    )
    assert all(mapping["classification"] in TAXONOMY for mapping in data["mappings"])
    rows = list(csv.DictReader(CSV_OUT.open(newline="")))
    assert len(rows) == len(data["accepted_cases"])
    assert MD_OUT.exists()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    args = parser.parse_args()
    phase5 = json.loads(PHASE5.read_text())
    source = json.loads(args.inventory.read_text())
    inventory = canonical_inventory(source["processed_reference_inventory"])
    previous = json.loads(JSON_OUT.read_text()) if JSON_OUT.exists() else {}
    previous_inventory = canonical_inventory(
        previous.get("processed_reference_inventory", [])
    )
    old = {item["drive_file_id"]: item for item in previous_inventory}
    new = {item["drive_file_id"]: item for item in inventory}
    changed = sum(
        file_id in old and old[file_id] != record for file_id, record in new.items()
    )
    accepted_cases = []
    for selected, original in zip(phase5["selected_candidates"], phase5["cases"]):
        accepted_cases.append(
            {
                "case": original["case"],
                "id": original["id"],
                "session": selected["session"],
                "subject": selected["subject"],
                "source_sha256": original["source_sha256"],
                "accepted_source_filename": selected["title"],
                "accepted_auto_sha256": original["auto_final"]["sha256"],
                "accepted_none_sha256": original["none_final"]["sha256"],
            }
        )
    mappings = build_mappings(accepted_cases, inventory)
    taxonomy_counts = counts(mappings)
    for case in accepted_cases:
        case["classification_counts"] = {
            name: sum(
                item["case"] == case["case"] and item["classification"] == name
                for item in mappings
            )
            for name in TAXONOMY
        }
    categories = source["inventory_categories"]
    data = {
        "phase": "PHASE 6 — BED THRESHOLD POLICY REFERENCE GROUNDING",
        "governing_task_revision": "084aa1c1d5bf5a4dd60a68d2ac7e83c2c18c991a",
        "accepted_phase5_evidence": "80d815c191766798bf0a6977f7abcbe24977cfbd",
        "source_folder": source["source_folder"],
        "source_access": source["source_access"],
        "target_rule": (
            "Exact accepted 12-case Phase-5 target set; no new cohort selected."
        ),
        "inventory_summary": {"processed_reference_tiff": len(inventory), **categories},
        "processed_reference_inventory": inventory,
        "inventory_reproducibility": {
            "refreshed_item_count": len(inventory),
            "refreshed_normalized_sha256": inventory_digest(inventory),
            "provisional_item_count": len(previous_inventory),
            "provisional_normalized_sha256": (
                inventory_digest(previous_inventory) if previous_inventory else None
            ),
            "additions": len(set(new) - set(old)),
            "removals": len(set(old) - set(new)),
            "changed_metadata": changed,
            "matches_provisional": inventory == previous_inventory,
        },
        "accepted_cases": accepted_cases,
        "mappings": mappings,
        "geometry_boundary": {
            "allowed": [
                "known orientation transform",
                "crop",
                "pad",
                "integer translation",
                "valid-mask intersection",
            ],
            "forbidden": [
                "resize",
                "interpolation",
                "resampling",
                "warp",
                "non-rigid registration",
            ],
        },
        "regeneration": {
            "short_circuited": True,
            "auto_none_regenerated": False,
            "reason": "No exact lossless reference mapping.",
        },
        "measurements": {
            "reference_vs_auto": "NOT_RUN",
            "reference_vs_none": "NOT_RUN",
        },
        "classification": "BED THRESHOLD POLICY UNRESOLVED",
        "limitations": [
            "Drive metadata did not provide reference bytes, derivation logs, or image "
            "metadata.",
            "Filename and folder similarity are not proof of acquisition provenance.",
        ],
        "verification": {
            "exact_mapping_count": taxonomy_counts["EXACT_SAME_ACQUISITION_LOSSLESS"],
            "taxonomy_counts": taxonomy_counts,
        },
    }
    JSON_OUT.write_text(json.dumps(data, indent=2) + "\n")
    fields = [
        "case",
        "case_id",
        "session",
        "subject",
        "accepted_source_sha256",
        "accepted_auto_sha256",
        "accepted_none_sha256",
        "possible_reference_count",
        *TAXONOMY,
        "reference_vs_auto",
        "reference_vs_none",
    ]
    with CSV_OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for case in accepted_cases:
            writer.writerow(
                {
                    "case": case["case"],
                    "case_id": case["id"],
                    "session": case["session"],
                    "subject": case["subject"],
                    "accepted_source_sha256": case["source_sha256"],
                    "accepted_auto_sha256": case["accepted_auto_sha256"],
                    "accepted_none_sha256": case["accepted_none_sha256"],
                    "possible_reference_count": sum(
                        case["classification_counts"].values()
                    ),
                    **case["classification_counts"],
                    "reference_vs_auto": "NOT_RUN",
                    "reference_vs_none": "NOT_RUN",
                }
            )
    write_markdown(data)
    validate(data)
    print("Phase-6 reference-grounding artifacts: rebuilt and valid")


if __name__ == "__main__":
    main()
