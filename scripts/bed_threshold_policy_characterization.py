"""Bounded, read-only BED threshold-policy characterization."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import tempfile
import urllib.request
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np

from mpips.iqa import analyze_structural_preservation
from mpips.pipelines.config import ImagerPipelineConfig
from mpips.pipelines.radiography import RadiographyPipeline
import mpips.pipelines.radiography as radiography_module
from mpips.workflows.imager_pipeline.npz_io import (
    NPZValidationError,
    load_gain_catalog,
    load_radiograph,
    sha256_file,
    to_uint16,
)

SOURCE_FOLDER = (
    "https://drive.google.com/drive/folders/1-15d10XwoZxB3fDzjoxG6Rh392aKJxd8"
)
COHORT_CAP = 9
GAIN_URLS = {
    "Ambil Data 1": "https://drive.google.com/file/d/1i9nT2bQ3VG3_TfAGHNpQDVi50JAC2Cyq/view",  # noqa: E501
    "Ambil Data 2": "https://drive.google.com/file/d/1Y3-dD4k2a_SRvfCC7Ezyj-v9ImColQjK/view",  # noqa: E501
    "Ambil Data 3": "https://drive.google.com/file/d/1nGjmoE0cGxT5lU-7KnMJG1-51N34w0Wo/view",  # noqa: E501
}

# Inventory was frozen from the authorized Drive folder before processing.
CANDIDATES = [
    (
        "Ambil Data 1",
        "kambing-1",
        "Copy of BED_1782704291612.npz",
        "1AUS04DQYHorVUBc1JVvyay7loDC3tDGG",
    ),
    (
        "Ambil Data 1",
        "kambing-1",
        "Copy of BED_1782705825057.npz",
        "1qsZoM2H1zqeE2UGUQIOFWOrIZewy68vQ",
    ),
    (
        "Ambil Data 1",
        "kambing-2",
        "Copy of BED_1782706308504.npz",
        "1VO11y9c0D-6R3fzWFVSjcJzwvDqWENcw",
    ),
    (
        "Ambil Data 1",
        "kambing-2",
        "Copy of BED_1782707631749.npz",
        "1s5TTQWFXro1lgb1cnHq-dlOiw_9kGaUW",
    ),
    (
        "Ambil Data 1",
        "kambing-3",
        "Copy of BED_1782708151260.npz",
        "18ZkmCLe0fpoGIHL4Nday4dhqlTnkvgeF",
    ),
    (
        "Ambil Data 1",
        "kambing-3",
        "Copy of BED_1782708771849.npz",
        "1UjnZTk-xu7f5k0G6ebdG2p71bGchK_6V",
    ),
    (
        "Ambil Data 2",
        "kambing-1",
        "Copy of BED_1783222264263.npz",
        "1sLur8whVT8Vb4OJeVIduSJFBQ3wKCOVX",
    ),
    (
        "Ambil Data 2",
        "kambing-1",
        "Copy of BED_1783222981898.npz",
        "1MVLXqgF6tDStIEhrDn0Ec6HOJxnA_eAP",
    ),
    (
        "Ambil Data 2",
        "kambing-2",
        "Copy of BED_1783223476352.npz",
        "1NoKEdKmB3UsuIYA7GogLfqa2AEkS2cTE",
    ),
    (
        "Ambil Data 2",
        "kambing-2",
        "Copy of BED_1783224123973.npz",
        "13fLNu82aaHfTQmuP5gzFmWI3Mn78Vbu8",
    ),
    (
        "Ambil Data 2",
        "kambing-3",
        "Copy of BED_1783224645493.npz",
        "10TLqDtRzvcyOR8eqpYpGtcj3PFh5Njwn",
    ),
    (
        "Ambil Data 2",
        "kambing-3",
        "Copy of BED_1783225312099.npz",
        "1wa-WwYOQpL-ztBmA2geGn2FUc50trQne",
    ),
    (
        "Ambil Data 3",
        "kambing 1",
        "BED_1783826993793.npz",
        "1PUF1XhPkGBMPdh8CMXjrEh9-yW6go3a3",
    ),
    (
        "Ambil Data 3",
        "kambing 1",
        "BED_1783827970684.npz",
        "1ySegpyhWMr0I_Vf6qirFxPdnsCQ3Q_o7",
    ),
    (
        "Ambil Data 3",
        "kambing 2",
        "BED_1783828512202.npz",
        "1lYm_xd-M-p5cjkBO7GthsKG-anY_ZLVX",
    ),
    (
        "Ambil Data 3",
        "kambing 2",
        "BED_1783829195829.npz",
        "1ZfSwYvI92g_Ls_w-Nn2wRsKJBgbcooiv",
    ),
    (
        "Ambil Data 3",
        "kambing 3",
        "BED_1783829675331.npz",
        "1VRfv9srolhOXDYoLIKWOkBpM2yFbLe-h",
    ),
    (
        "Ambil Data 3",
        "kambing 3",
        "BED_1783830282868.npz",
        "1RbAvdVdqQCSyEaDa7rXyxbsAXarp1aoJ",
    ),
]


def _drive_download_url(file_id: str) -> str:
    return f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"  # noqa: E501


def _stats(image: np.ndarray) -> dict[str, Any]:
    values = np.asarray(image)
    return {
        "shape": list(values.shape),
        "dtype": str(values.dtype),
        "sha256": hashlib.sha256(values.tobytes()).hexdigest(),
        "min": float(values.min()),
        "max": float(values.max()),
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "p01": float(np.percentile(values, 1)),
        "p50": float(np.percentile(values, 50)),
        "p99": float(np.percentile(values, 99)),
        "dynamic_range_span": float(values.max() - values.min()),
        "nonzero_count": int(np.count_nonzero(values)),
        "zero_fraction": float(np.mean(values == 0)),
        "uint16_saturation_fraction": float(np.mean(values == 65535)),
    }


class _ObservedPipeline(RadiographyPipeline):
    def __init__(self, config: ImagerPipelineConfig) -> None:
        super().__init__(config)
        self.pre_threshold: np.ndarray | None = None

    def _normalize_to_max_value(self, image: np.ndarray) -> np.ndarray:
        result = super()._normalize_to_max_value(image)
        self.pre_threshold = result.copy()
        return result


def _run_state(
    raw: np.ndarray,
    dark: np.ndarray,
    flat: np.ndarray,
    method: str,
    reference: np.ndarray | None = None,
) -> dict[str, Any]:
    observed = _ObservedPipeline(
        ImagerPipelineConfig(use_threshold=True, threshold_method=method)
    )
    detected: list[float] = []
    threshold_stage: list[np.ndarray] = []
    original_detect = radiography_module.detect_threshold
    original_apply = radiography_module.apply_threshold_separation

    def detect(*args: Any, **kwargs: Any) -> float:
        observed.pre_threshold = np.asarray(args[0]).copy()
        value = float(original_detect(*args, **kwargs))
        detected.append(value)
        return value

    def apply(image: np.ndarray, threshold: float) -> np.ndarray:
        result = original_apply(image, threshold)
        threshold_stage.append(result.copy())
        return result

    radiography_module.detect_threshold = detect
    radiography_module.apply_threshold_separation = apply
    try:
        final = observed.process(raw, dark, flat, "BED")
    finally:
        radiography_module.detect_threshold = original_detect
        radiography_module.apply_threshold_separation = original_apply
    if observed.pre_threshold is None and reference is not None:
        observed.pre_threshold = reference.copy()
    if observed.pre_threshold is None:
        raise RuntimeError("Canonical pipeline did not expose PRE_THRESHOLD")
    stage = threshold_stage[0] if threshold_stage else observed.pre_threshold
    return {
        "requested_threshold_method": method,
        "threshold_separation_disabled": method == "none",
        "numeric_threshold": (
            None if method == "none" else (detected[0] if detected else None)
        ),
        "effective_threshold_branch": (
            "bypass" if method == "none" else "canonical_auto"
        ),
        "fallback_semantics": None,
        "pre_threshold": observed.pre_threshold,
        "threshold_stage": stage,
        "final": final,
    }


def _select_candidates() -> list[tuple[str, str, str, str]]:
    groups: dict[tuple[str, str], list[tuple[str, str, str, str]]] = defaultdict(list)
    for candidate in CANDIDATES:
        groups[(candidate[0], candidate[1])].append(candidate)
    ordered_groups = sorted(groups)
    for group in ordered_groups:
        groups[group].sort(
            key=lambda item: (int(re.search(r"(\d+)\.npz$", item[2]).group(1)), item[2])
        )
    selected: list[tuple[str, str, str, str]] = []
    for position in range(2):
        for group in ordered_groups:
            values = groups[group]
            if values:
                selected.append(values[0] if position == 0 else values[-1])
            if len(selected) == COHORT_CAP:
                return selected
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", type=Path, default=Path("artifacts/real-data-regression")
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    selected = _select_candidates()
    records: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="mpips-bed-phase5-") as temp:
        temp_path = Path(temp)
        gain_paths: dict[str, Path] = {}
        for session, url in GAIN_URLS.items():
            target = temp_path / f"{session.replace(' ', '_')}_gain.npz"
            urllib.request.urlretrieve(
                _drive_download_url(url.rsplit("/d/", 1)[1].split("/", 1)[0]), target
            )
            gain_paths[session] = target
        gains = load_gain_catalog(gain_paths.values())
        for index, (session, subject, title, file_id) in enumerate(selected, 1):
            source = temp_path / f"case-{index:02d}.npz"
            try:
                urllib.request.urlretrieve(_drive_download_url(file_id), source)
                radiograph = load_radiograph(source)
                if radiograph["detector_mode"] != "BED":
                    raise NPZValidationError("detector mode is not BED")
                gain = gains.require(radiograph["gain_id"])
                raw = to_uint16(radiograph["raw"], "radiograph raw")
                dark = to_uint16(gain.dark, "gain dark")
                flat = to_uint16(gain.flat, "gain flat")
                if raw.shape != dark.shape or raw.shape != flat.shape:
                    raise NPZValidationError("radiograph/gain shapes differ")
                auto = _run_state(raw, dark, flat, "auto")
                none = _run_state(raw, dark, flat, "none", auto["pre_threshold"])
                stage_metrics = {
                    "BED_AUTO": analyze_structural_preservation(
                        auto["pre_threshold"], auto["threshold_stage"]
                    ).__dict__,
                    "BED_NONE": analyze_structural_preservation(
                        auto["pre_threshold"], none["threshold_stage"]
                    ).__dict__,
                }
                record = {
                    "case": index,
                    "session": session,
                    "subject": subject,
                    "source_title": title,
                    "drive_file_id": file_id,
                    "source_sha256": sha256_file(source),
                    "id": radiograph["id"],
                    "gain_id": radiograph["gain_id"],
                    "detector_mode": radiograph["detector_mode"],
                    "raw_shape": list(raw.shape),
                    "raw_dtype": str(raw.dtype),
                    "auto": {
                        k: v
                        for k, v in auto.items()
                        if k not in {"pre_threshold", "threshold_stage", "final"}
                    },
                    "none": {
                        k: v
                        for k, v in none.items()
                        if k not in {"pre_threshold", "threshold_stage", "final"}
                    },
                    "pre_threshold": _stats(auto["pre_threshold"]),
                    "auto_threshold_stage": _stats(auto["threshold_stage"]),
                    "none_threshold_stage": _stats(none["threshold_stage"]),
                    "structural_preservation": stage_metrics,
                    "auto_final": _stats(auto["final"]),
                    "none_final": _stats(none["final"]),
                    "final_sha256_equal": _stats(auto["final"])["sha256"]
                    == _stats(none["final"])["sha256"],
                }
                records.append(record)
            except (OSError, KeyError, ValueError, NPZValidationError) as exc:
                excluded.append(
                    {
                        "session": session,
                        "subject": subject,
                        "source_title": title,
                        "reason": str(exc),
                    }
                )

    classification = (
        "BED THRESHOLD POLICY UNRESOLVED"
        if excluded or not records
        else "BED BYPASS SUPPORTED"
    )
    payload = {
        "phase": "PHASE 5 — BED THRESHOLD POLICY EVIDENCE CHARACTERIZATION",
        "governing_task_revision": "e230ffc6d1ae86e09cba706c46f4632979d547b1",
        "source_folder": SOURCE_FOLDER,
        "source_access": "read-only",
        "inventory": {
            "acquisition_candidates": 200,
            "gain_npz": 6,
            "folders_visited": 96,
        },
        "selection_rule": (  # noqa: E501
            "Lexicographic session/subject groups; stable numeric acquisition "
            f"ordering; first/last per group; round-robin; cap {COHORT_CAP}; frozen "
            "before processing."
        ),
        "selected_candidates": [
            {"session": s, "subject": u, "title": t, "drive_file_id": i}
            for s, u, t, i in selected
        ],
        "excluded": excluded,
        "cases": records,
        "classification": classification,
        "limitations": [
            "Processed/reference and calibration trees were inventoried but not "
            "treated as ground truth.",
            "No calibration was substituted or generated; paired runs used the "
            "canonical no-remap array path.",
            "IQA is stage-local and not a clinical or diagnostic claim.",
        ],
    }
    json_path = args.output_dir / "bed-threshold-policy-characterization.json"
    csv_path = args.output_dir / "bed-threshold-policy-characterization.csv"
    md_path = args.output_dir / "bed-threshold-policy-characterization.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    fields = [
        "case",
        "session",
        "subject",
        "id",
        "gain_id",
        "source_sha256",
        "auto_final_sha256",
        "none_final_sha256",
        "auto_edge_recall",
        "none_edge_recall",
        "auto_lost_informative_tile_fraction",
        "none_lost_informative_tile_fraction",
    ]
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "case": record["case"],
                    "session": record["session"],
                    "subject": record["subject"],
                    "id": record["id"],
                    "gain_id": record["gain_id"],
                    "source_sha256": record["source_sha256"],
                    "auto_final_sha256": record["auto_final"]["sha256"],
                    "none_final_sha256": record["none_final"]["sha256"],
                    "auto_edge_recall": record["structural_preservation"]["BED_AUTO"][
                        "edge_recall"
                    ],
                    "none_edge_recall": record["structural_preservation"]["BED_NONE"][
                        "edge_recall"
                    ],
                    "auto_lost_informative_tile_fraction": record[
                        "structural_preservation"
                    ]["BED_AUTO"]["lost_informative_tile_fraction"],
                    "none_lost_informative_tile_fraction": record[
                        "structural_preservation"
                    ]["BED_NONE"]["lost_informative_tile_fraction"],
                }
            )
    deltas = [r["auto_final"]["mean"] - r["none_final"]["mean"] for r in records]
    md_path.write_text(
        "\n".join(
            [
                "# BED Threshold Policy Characterization",
                "",
                f"Classification: **{classification}**",
                "",
                f"Source: `{SOURCE_FOLDER}` (read-only). Inventory: 200 "
                "acquisition NPZ candidates, 6 gain NPZ files, 96 folders visited.",
                "",
                "Selection was frozen before processing: lexicographic "
                "session/subject groups, stable acquisition ordering, first/last "
                f"distinct acquisitions, round-robin, maximum {COHORT_CAP}.",
                "",
                f"Selected and successfully paired cases: {len(records)}; "
                f"excluded: {len(excluded)}.",
                "",
                f"Final AUTO-minus-NONE mean-intensity delta median: "
                f"{median(deltas) if deltas else 'NON-COMPARABLE'}.",
                "",
                "IQA compares each threshold-stage output with the same-geometry "
                "normalized pre-threshold image using "
                "`mpips.iqa.analyze_structural_preservation`. No clinical or "
                "diagnostic conclusion is made.",
                "",
                "The classification is decision support only and does not change "
                "BED runtime policy.",
                "",
            ]
        )
    )
    print(
        json.dumps(
            {
                "classification": classification,
                "cases": len(records),
                "excluded": len(excluded),
                "output": str(args.output_dir),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
