"""Deterministic MPIPS versus ImageJ/Fiji characterization harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from mpips.processing.imagej import ImageJReplicator

FIXTURES = {
    "constant": [7] * 25,
    "two_level": [0, 255] * 12 + [0],
    "ramp": list(range(25)),
    "sparse": [0] * 20 + [17, 17, 200, 255, 255],
    "narrow": [100] * 8 + [101] * 9 + [102] * 8,
    "full": [0, 255, 1, 254, 2, 253, 127, 128] * 3 + [0],
    "impulse": [0] * 12 + [255] + [0] * 12,
    "asymmetric_tail": [10] * 20 + [11, 12, 13, 200, 255],
}
MEDIAN_FIXTURE = [
    9,
    2,
    7,
    4,
    6,
    3,
    8,
    1,
    5,
    0,
    6,
    4,
    9,
    2,
    7,
    5,
    1,
    8,
    3,
    6,
    0,
    7,
    2,
    9,
    4,
]


def scaled(values: list[int], dtype: str) -> np.ndarray:
    if dtype == "uint8":
        return np.asarray(values, dtype=np.uint8).reshape(5, 5)
    return (np.asarray(values, dtype=np.uint16) * 257).reshape(5, 5)


def run_reference(
    java: str,
    classpath: str,
    operation: str,
    dtype: str,
    image: np.ndarray,
    *params: Any,
) -> np.ndarray:
    flat = " ".join(str(int(x)) for x in image.flat) + "\n"
    command = [
        java,
        "-Djava.awt.headless=true",
        "-cp",
        classpath,
        "ReferenceHarness",
        operation,
        dtype,
        str(image.shape[1]),
        str(image.shape[0]),
        *(str(x) for x in params),
    ]
    result = subprocess.run(
        command, input=flat, text=True, capture_output=True, check=False, timeout=30
    )
    if result.returncode:
        raise RuntimeError(f"reference failed: {' '.join(command)}\n{result.stderr}")
    values = np.fromstring(result.stdout, sep=" ", dtype=np.uint64)
    return values.astype(np.uint8 if dtype == "uint8" else np.uint16).reshape(
        image.shape
    )


def compare(
    operation: str,
    fixture: str,
    dtype: str,
    params: dict[str, Any],
    actual: np.ndarray,
    reference: np.ndarray,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    equal = (
        actual.shape == reference.shape
        and actual.dtype == reference.dtype
        and np.array_equal(actual, reference)
    )
    difference = np.abs(actual.astype(np.int64) - reference.astype(np.int64))
    mismatch = (
        np.argwhere(actual != reference)
        if actual.shape == reference.shape
        else np.empty((0, 2), dtype=int)
    )
    first = None
    if mismatch.size:
        y, x = mismatch[0]
        first = {
            "coordinate": [int(y), int(x)],
            "mpips": int(actual[y, x]),
            "reference": int(reference[y, x]),
        }
    return {
        "operation": operation,
        "fixture": fixture,
        "dtype": dtype,
        "shape": list(actual.shape),
        "authoritative": provenance,
        "parameters": params,
        "comparison_mode": "exact",
        "tolerance": None,
        "tolerance_rationale": None,
        "equal": bool(equal),
        "mismatch_count": (
            int(np.count_nonzero(actual != reference))
            if actual.shape == reference.shape
            else -1
        ),
        "mismatch_fraction": (
            float(np.count_nonzero(actual != reference) / actual.size)
            if actual.shape == reference.shape
            else 1.0
        ),
        "max_absolute_difference": int(difference.max()) if difference.size else 0,
        "first_mismatch": first,
        "mpips_sha256": hashlib.sha256(actual.tobytes()).hexdigest(),
        "reference_sha256": hashlib.sha256(reference.tobytes()).hexdigest(),
        "classification": "PARITY CONFIRMED" if equal else "FIDELITY FAILURE",
    }


def reference_error_case(
    operation: str,
    fixture: str,
    dtype: str,
    params: dict[str, Any],
    actual: np.ndarray,
    error: str,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    return {
        "operation": operation,
        "fixture": fixture,
        "dtype": dtype,
        "shape": list(actual.shape),
        "authoritative": provenance,
        "parameters": params,
        "comparison_mode": "exact",
        "tolerance": None,
        "tolerance_rationale": None,
        "equal": False,
        "mismatch_count": None,
        "mismatch_fraction": None,
        "max_absolute_difference": None,
        "first_mismatch": None,
        "mpips_sha256": hashlib.sha256(actual.tobytes()).hexdigest(),
        "reference_sha256": None,
        "reference_error": error,
        "classification": "REFERENCE NOT RESOLVED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-java", required=True)
    parser.add_argument("--reference-classpath", required=True)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--jdk-archive", required=True)
    parser.add_argument("--jdk-sha256", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    cases: list[dict[str, Any]] = []
    provenance: dict[str, Any] = {
        "imagej": {
            "project": "imagej/ImageJ",
            "source": "ij.plugin.ContrastEnhancer and ij.plugin.filter.RankFilters",
            "version": "1.54p",
            "artifact": "ij-1.54p.jar",
            "retrieval": "https://repo1.maven.org/maven2/net/imagej/ij/1.54p/ij-1.54p.jar",  # noqa: E501
            "sha256": "2e1a09961dfb41cee66ddc821b2577a41a072566ce45a49bae69267099741e20",  # noqa: E501
        },
        "clahe": {
            "project": "axtimwalde/mpicbg",
            "source": "mpicbg.ij.clahe.Flat, FastFlat, Util",
            "commit": "0ed8a9d0592b1b679311f798b0b4dac6f44d3ef0",
            "retrieval": "https://github.com/axtimwalde/mpicbg",
            "source_sha256": {
                "Flat.java": "112ba574034acb2c740dfcc5365fb9489305d62e9527df71665cac8971dedee2",  # noqa: E501
                "FastFlat.java": "09fa2048f80d258a2ce02b8940373e2a9e9b8176e5b86e0a4c5ae6710114b3fd",  # noqa: E501
                "Util.java": "4dbe118c08eaa36a5f87c78930169383a602a84f25ca7b975284cb089bdd1689",  # noqa: E501
            },
        },
        "hybrid_median": {
            "project": "ImageJ plugin site",
            "source": "Hybrid_2D_Median_Filter.java by Christopher Philip Mauer",  # noqa: E501
            "retrieval": "https://wsr.imagej.net/ij/plugins/download/Hybrid_2D_Median_Filter.java",  # noqa: E501
            "sha256": "494cc92747ba8e01e9ad19f16d735ffe8faf0b65eba00f02fda691bc5529af03",  # noqa: E501
        },
        "runtime": {
            "system_java_initially_available": False,
            "vendor": "Eclipse Temurin / Eclipse Adoptium",
            "version": "17.0.19+10",
            "build": "17.0.19+10",
            "release_tag": "jdk-17.0.19+10",
            "archive": args.jdk_archive,
            "archive_sha256_expected": args.jdk_sha256,
            "archive_sha256_observed": hashlib.sha256(
                (Path(args.runtime_root) / "downloads" / args.jdk_archive).read_bytes()
            ).hexdigest(),
            "checksum_verified": hashlib.sha256(
                (Path(args.runtime_root) / "downloads" / args.jdk_archive).read_bytes()
            ).hexdigest()
            == args.jdk_sha256,
            "temporary_location": args.runtime_root,
            "system_wide_installation": False,
            "persistent_environment_change": False,
            "mpips_dependencies_changed": False,
        },
    }
    for dtype in ("uint8", "uint16"):
        for name, values in FIXTURES.items():
            image = scaled(values, dtype)
            for saturation in (0.0, 0.35, 5.0):
                actual = ImageJReplicator.enhance_contrast(
                    image, saturated_pixels=saturation
                )
                reference = run_reference(
                    args.reference_java,
                    args.reference_classpath,
                    "stretch",
                    dtype,
                    image,
                    saturation,
                )
                cases.append(
                    compare(
                        "Contrast stretch",
                        name,
                        dtype,
                        {"saturated_pixels": saturation},
                        actual,
                        reference,
                        provenance["imagej"],
                    )
                )
            for classic in (False, True):
                actual = ImageJReplicator.enhance_contrast(
                    image, equalize=True, classic_equalization=classic
                )
                reference = run_reference(
                    args.reference_java,
                    args.reference_classpath,
                    "equalize_classic" if classic else "equalize_weighted",
                    dtype,
                    image,
                )
                cases.append(
                    compare(
                        "Equalize classic" if classic else "Equalize weighted",
                        name,
                        dtype,
                        {"classic": classic},
                        actual,
                        reference,
                        provenance["imagej"],
                    )
                )
        image = scaled(MEDIAN_FIXTURE, dtype)
        for kernel in (3, 5, 7):
            actual = ImageJReplicator.hybrid_median_filter_2d(image, kernel_size=kernel)
            reference = run_reference(
                args.reference_java,
                args.reference_classpath,
                "hybrid",
                dtype,
                image,
                kernel,
            )
            cases.append(
                compare(
                    f"Hybrid Median {kernel}x{kernel}",
                    "median_grid",
                    dtype,
                    {"kernel_size": kernel},
                    actual,
                    reference,
                    provenance["hybrid_median"],
                )
            )
        for radius in (1.0, 2.0, 3.0):
            actual = ImageJReplicator.median_filter_imagej(image, radius=radius)
            reference = run_reference(
                args.reference_java,
                args.reference_classpath,
                "circular",
                dtype,
                image,
                radius,
            )
            cases.append(
                compare(
                    "Circular Median",
                    "median_grid",
                    dtype,
                    {"radius": radius},
                    actual,
                    reference,
                    provenance["imagej"],
                )
            )
        clahe_image = np.arange(128 * 128, dtype=np.uint32).reshape(128, 128) % 64
        clahe_image = (clahe_image * (257 if dtype == "uint16" else 1)).astype(dtype)
        for operation, fast in (
            ("CLAHE Flat / precise", False),
            ("CLAHE FastFlat / fast", True),
        ):
            actual = ImageJReplicator.apply_clahe(
                clahe_image,
                blocksize=127,
                histogram_bins=256,
                max_slope=0.6,
                fast=fast,
                composite=True,
            )
            params = {
                "blocksize": 127,
                "histogram_bins": 256,
                "maximum_slope": 0.6,
                "composite": True,
            }
            try:
                reference = run_reference(
                    args.reference_java,
                    args.reference_classpath,
                    "clahe_fast" if fast else "clahe_flat",
                    dtype,
                    clahe_image,
                    63,
                    256,
                    0.6,
                )
                cases.append(
                    compare(
                        operation,
                        "clahe_128x128_full_bin_ramp",
                        dtype,
                        params,
                        actual,
                        reference,
                        provenance["clahe"],
                    )
                )
            except RuntimeError as error:
                cases.append(
                    reference_error_case(
                        operation,
                        "clahe_128x128_full_bin_ramp",
                        dtype,
                        params,
                        actual,
                        str(error),
                        provenance["clahe"],
                    )
                )

    summary: dict[str, str] = {}
    for operation in sorted({case["operation"] for case in cases}):
        subset = [case for case in cases if case["operation"] == operation]
        summary[operation] = (
            "REFERENCE NOT RESOLVED"
            if any(
                case["classification"] == "REFERENCE NOT RESOLVED" for case in subset
            )
            else (
                "PARITY CONFIRMED"
                if all(case["equal"] for case in subset)
                else "FIDELITY FAILURE"
            )
        )
    summary["Temporal Median"] = "NOT PRODUCTION-REACHABLE"

    java_version = subprocess.run(
        [args.reference_java, "-version"], capture_output=True, text=True, check=False
    )
    javac_version = subprocess.run(
        [str(Path(args.reference_java).with_name("javac")), "-version"],
        capture_output=True,
        text=True,
        check=False,
    )
    provenance["runtime"]["java_version_output"] = (
        java_version.stderr or java_version.stdout
    ).strip()
    provenance["runtime"]["javac_version_output"] = (
        javac_version.stderr or javac_version.stdout
    ).strip()

    output = {
        "task": "I-4A",
        "governing_task_revision": "ae873d1d8ea04cb482a7896ca84088867e5524ec",
        "accepted_implementation_baseline": "dd13fc4dab512bbb59242bde7f5fb7cc6c5c370e",
        "cases": cases,
        "summary": summary,
        "provenance": provenance,
        "reachability": {
            "temporal_median": "NOT PRODUCTION-REACHABLE",
            "rgb_composite": "secondary only; no RGB parity claim",
        },
    }
    args.output_json.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    lines = [
        "# MPIPS ImageJ/Fiji Fidelity Characterization — I-4A",
        "",
        "Governing task: `ae873d1d8ea04cb482a7896ca84088867e5524ec`; accepted implementation baseline: `dd13fc4dab512bbb59242bde7f5fb7cc6c5c370e`.",  # noqa: E501
        "",
        "## Runtime and provenance",
        "",
        "```json",
        json.dumps(provenance, indent=2, sort_keys=True),
        "```",
        "",
        "## Production reachability",
        "",
        "Temporal median is **NOT PRODUCTION-REACHABLE**: no pipeline caller or registered production API path was found. RGB/composite behavior was inspected secondarily; grayscale evidence does not establish RGB parity.",  # noqa: E501
        "",
        "## Fixture matrix",
        "",
        "`constant`, `two_level`, `ramp`, `sparse`, `narrow`, `full`, `impulse`, and `asymmetric_tail` cover uint8/uint16 stretch and equalization. `median_grid` covers hybrid, circular, and CLAHE boundary cases. The CLAHE fixture is a deterministic 128×128 ramp modulo 64 so the authoritative 256-bin implementation has non-full bins.",  # noqa: E501
        "",
        "## Parameter mappings",
        "",
        "MPIPS maps `blocksize=127` to `block_radius=63`; the Fiji call therefore uses `blockRadius=63`, `bins=256`, `slope=0.6`, and `composite=true`. Exact integer array equality is used for every executable case. Fiji Flat/FastFlat raise `ArithmeticException: / by zero` for this slope/data combination; those cases are recorded as `REFERENCE NOT RESOLVED`, not treated as parity.",  # noqa: E501
        "",
        "## Final classification table",
        "",
        "| Operation | Final classification |",
        "|---|---|",
    ]
    required_rows: list[tuple[str, str, str | None]] = [
        ("Contrast stretch uint8", "Contrast stretch", "uint8"),
        ("Contrast stretch uint16", "Contrast stretch", "uint16"),
        ("Equalize weighted uint8", "Equalize weighted", "uint8"),
        ("Equalize weighted uint16", "Equalize weighted", "uint16"),
        ("Equalize classic uint8", "Equalize classic", "uint8"),
        ("Equalize classic uint16", "Equalize classic", "uint16"),
        ("CLAHE Flat / precise", "CLAHE Flat / precise", None),
        ("CLAHE FastFlat / fast", "CLAHE FastFlat / fast", None),
        ("Hybrid Median 3x3", "Hybrid Median 3x3", None),
        ("Hybrid Median 5x5", "Hybrid Median 5x5", None),
        ("Hybrid Median 7x7", "Hybrid Median 7x7", None),
        ("Circular Median", "Circular Median", None),
        ("Temporal Median", "Temporal Median", None),
    ]
    for label, operation, required_dtype in required_rows:
        subset = [
            case
            for case in cases
            if case["operation"] == operation
            and (required_dtype is None or case["dtype"] == required_dtype)
        ]
        if operation == "Temporal Median":
            classification = "NOT PRODUCTION-REACHABLE"
        elif any(case["classification"] == "REFERENCE NOT RESOLVED" for case in subset):
            classification = "REFERENCE NOT RESOLVED"
        else:
            classification = (
                "PARITY CONFIRMED"
                if subset and all(case["equal"] for case in subset)
                else "FIDELITY FAILURE"
            )
        lines.append(f"| {label} | {classification} |")
    lines += [
        "",
        "## Aggregate results",
        "",
        "| Operation | Cases | Mismatches |",
        "|---|---:|---:|",
    ]
    for operation, classification in summary.items():
        subset = [case for case in cases if case["operation"] == operation]
        mismatch_total = (
            sum(
                case["mismatch_count"]
                for case in subset
                if case["mismatch_count"] is not None
            )
            if subset
            else None
        )
        mismatch_text = (
            str(mismatch_total)
            if subset and all(case["mismatch_count"] is not None for case in subset)
            else "n/a"
        )
        lines.append(
            f"| {operation} | {classification} | {len(subset)} | {mismatch_text} |"
            if subset
            else f"| {operation} | {classification} | — | — |"
        )
    lines += [
        "",
        "## Per-case measurements",
        "",
        "| Operation | Fixture | Dtype | Parameters | Classification | Mismatch fraction | Max abs diff |",  # noqa: E501
        "|---|---|---|---|---|---:|---:|",
    ]
    for case in cases:
        lines.append(
            f"| {case['operation']} | {case['fixture']} | {case['dtype']} | `{json.dumps(case['parameters'], sort_keys=True)}` | {case['classification']} | {case['mismatch_fraction'] if case['mismatch_fraction'] is not None else 'n/a'} | {case['max_absolute_difference'] if case['max_absolute_difference'] is not None else 'n/a'} |"  # noqa: E501
        )
    lines += [
        "",
        "## Existing test gaps",
        "",
        "`tests/test_imagej_migration.py` locks accepted MPIPS outputs but does not compare them with executable ImageJ/Fiji references. Its expected arrays and hashes were not modified.",  # noqa: E501
        "",
        "## Representative deviations",
        "",
        "The JSON records mismatch count, mismatch fraction, maximum absolute difference, output/reference SHA256, and the first differing coordinate/value for every case. A mismatch is diagnostic evidence; no production behavior was changed.",  # noqa: E501
        "",
        "## Later remediation ordering",
        "",
        "Use the measured operation families in this order: circular/Hybrid median edge semantics, ContrastEnhancer rounding/statistics, CLAHE Flat versus FastFlat parameter mapping, then any secondary RGB/composite work. This is diagnostic ordering only; remediation is out of scope for I-4A.",  # noqa: E501
        "",
        "## Licensing and unresolved constraints",
        "",
        "ImageJ core is public domain; the Fiji CLAHE implementation is GPL-2-era source and the Hybrid Median source carries its own non-commercial restriction. No third-party source or JAR is committed. Temporal median has an upstream plugin page but is not production-reachable, so no executable comparison was required.",  # noqa: E501
        "",
    ]
    args.output_md.write_text("\n".join(lines))
    print(
        json.dumps(
            {
                "cases": len(cases),
                "summary": summary,
                "json": str(args.output_json),
                "markdown": str(args.output_md),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
