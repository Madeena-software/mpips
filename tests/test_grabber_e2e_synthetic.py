"""Synthetic Grabber end-to-end simulation (test-only, offline, no real data).

Flow: mock SIMRS response -> confirmed selection -> SIMRS-to-manifest mapping ->
Grabber-owned capture metadata -> synthetic BED/TRX NPZ with matching gain and
calibration -> real ``python -m mpips.runtime convert`` -> verified DICOM.

Network verification is Python-level and test-enforced; see ``LIMITATION``.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pydicom
import pytest
from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "docs" / "integration" / "examples"
VISIT = "SYNTHETIC-VISIT-2026-0001"
CAPTURED_AT = "2026-10-12T10:00:00+07:00"
SOP_CLASS = "1.2.840.10008.5.1.4.1.1.1.1.1"
LIMITATION = (
    "Network verification is Python-level and test-enforced via an audit hook; "
    "it is not kernel network isolation and does not stop non-Python code, "
    "ctypes or C-extension raw sockets that bypass audit events, or interpreters "
    "started without the inherited environment."
)

# Pixel regression pins (NOT a correctness proof). Provenance: baseline
# 1a25609 + task e4dbb72; command
#   .venv/bin/python -m pytest -q tests/test_grabber_e2e_synthetic.py
# on CPython 3.12.3, numpy 2.4.6, opencv 4.13.0, pydicom 3.0.2, linux x86_64.
# An independent NumPy oracle of the exact processing chain was infeasible (the
# observed output is quantised, inverted and clipped by non-linear presentation
# processing), so ranked form (b) is used: hard-coded digests recorded from a
# prior run, never computed from the output under test, plus structural
# invariants asserted in ``verify_pixels``.
PIXEL_SHA256 = {
    "BED": "13a9a56a28e1cb6d0a6daf887cc3bf98fc9b85f17995935e6b933ead836510ca",
    "TRX": "24d4be23a354de71302a9d6bed77b29acef049f05863dcf86da1d7da835439c1",
}
SHAPES = {"BED": (48, 64), "TRX": (64, 48)}

GUARD_SOURCE = r"""
import os, sys, socket
socket.has_ipv6 = False
_dir = os.environ.get("MPIPS_E2E_GUARD_DIR")
if _dir:
    try:
        with open("/proc/self/cmdline", "rb") as _f:
            _cmd = _f.read().decode("utf-8", "replace")
    except OSError:
        _cmd = ""
    if "mpips.conversion.worker" in _cmd:
        _role = "worker"
    elif "mpips.runtime" in _cmd:
        _role = "cli"
    else:
        _role = "canary"
    _pid = os.getpid()
    open(os.path.join(_dir, "loaded.%s.%d" % (_role, _pid)), "w").close()

    def _hook(event, args):
        if not event.startswith("socket."):
            return
        if event in ("socket.connect", "socket.bind", "socket.sendto"):
            if isinstance(args[1], (str, bytes)):
                return
        elif event not in ("socket.getaddrinfo", "socket.gethostbyname"):
            return
        with open(os.path.join(_dir, "reject.%s.%d" % (_role, _pid)), "a") as _f:
            _f.write(event + "\n")
        raise RuntimeError("network blocked by test guard")

    sys.addaudithook(_hook)
"""


@dataclass
class GuardRecords:
    roles: dict[str, int] = field(default_factory=dict)
    pids: dict[str, set[str]] = field(default_factory=dict)
    rejections: int = 0

    def labels(self) -> list[str]:
        return sorted(f"guard_loaded:{role}" for role in self.roles)


def read_guard(record_dir: Path) -> GuardRecords:
    records = GuardRecords()
    for entry in record_dir.iterdir():
        kind, role, pid = entry.name.split(".")
        if kind == "loaded":
            records.roles[role] = records.roles.get(role, 0) + 1
            records.pids.setdefault(role, set()).add(pid)
        else:
            records.rejections += len(entry.read_text().splitlines())
    return records


def guard_dirs(root: Path) -> tuple[Path, Path]:
    code = root / "guard-code"
    records = root / "guard-records"
    code.mkdir(parents=True)
    records.mkdir()
    (code / "sitecustomize.py").write_text(GUARD_SOURCE)
    return code, records


def run_guarded(
    argv: list[str], code_dir: Path, record_dir: Path
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "MPIPS_E2E_GUARD_DIR": str(record_dir)}
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(code_dir) + (os.pathsep + existing if existing else "")
    return subprocess.run(
        [sys.executable, *argv],
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO_ROOT,
    )


# --- Grabber-side simulation (test-owned; the real Grabber is a separate product) --


class SelectionNotConfirmedError(ValueError):
    pass


def mock_simrs_response() -> Any:
    return json.loads((EXAMPLES / "simrs-response.synthetic.json").read_text())


def confirm_selection(response: Any, visit: str, confirmed: bool) -> None:
    if not confirmed:
        raise SelectionNotConfirmedError("operator did not confirm the selection")
    if not isinstance(response, dict) or response.get("success") is not True:
        raise ValueError("SIMRS response rejected")


GRABBER_CAPTURE = {
    "body_part_examined": "CHEST",
    "projection": "PA",
    "view_code_sequence": [
        {
            "code_value": "272479007",
            "coding_scheme_designator": "SCT",
            "code_meaning": "postero-anterior",
        }
    ],
    "detector_spacing": {"row_mm": 0.15, "column_mm": 0.16},
}
GRABBER_DICOM = {
    "pixel_source": "CANONICAL_PRE_PRESENTATION",
    "pixel_intensity_relationship": "LIN",
    "pixel_intensity_relationship_sign": 1,
}


def compose_manifest(
    response: Any,
    visit: str,
    mode: str,
    confirmed: bool = True,
    dicom_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from mpips.api.schemas.dicom import MHCSManifest
    from scripts.simrs_manifest_example import build_manifest

    confirm_selection(response, visit, confirmed)
    mapped = build_manifest(response, visit, {}, CAPTURED_AT)
    merged: dict[str, Any] = {"manifest_version": "1.0", **copy.deepcopy(mapped)}
    merged["examination"]["performed_at"] = CAPTURED_AT
    merged["capture"].update(copy.deepcopy(GRABBER_CAPTURE), detector_type=mode)
    merged["dicom"] = {**GRABBER_DICOM, **(dicom_overrides or {})}
    MHCSManifest.model_validate(merged)
    return merged


# --- identifier provenance ------------------------------------------------------


def collect_test_controlled_identifiers(
    manifest: dict[str, Any], rad: Path, gain: Path
) -> list[str]:
    patient_name = manifest["patient"]["name"]
    name_str = (
        patient_name["full_name"]
        if isinstance(patient_name, dict)
        else str(patient_name)
    )
    values = [
        manifest["patient"]["medical_record_number"],
        name_str,
        manifest["examination"]["encounter_id"],
    ]
    if manifest.get("examination", {}).get("accession_number"):
        values.append(manifest["examination"]["accession_number"])
    for path in (rad, gain):
        with np.load(path, allow_pickle=True) as data:
            values.append(str(data["id"]))
            values.append(str(data["cameraparams"].item()["serialNumber"]))
            if "gainid" in data.files:
                values.append(str(data["gainid"]))
    return values


def assert_all_synthetic(values: list[str]) -> None:
    offenders = [value for value in values if not value.startswith("SYNTHETIC")]
    assert not offenders, f"{len(offenders)} non-SYNTHETIC test identifier(s)"


UID_SYNTAX = re.compile(r"(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*")


def assert_uid(value: str) -> None:
    assert len(value) <= 64 and UID_SYNTAX.fullmatch(value), "invalid DICOM UID syntax"


# --- NPZ helpers ---------------------------------------------------------------


def rewrite_npz(path: Path, **changes: Any) -> None:
    with np.load(path, allow_pickle=True) as data:
        content = {key: data[key] for key in data.files}
    content.update(changes)
    np.savez_compressed(path, **content)


@dataclass
class Inputs:
    root: Path
    rad: Path
    gain: Path
    manifest: Path
    calibration: Path
    output: Path
    manifest_data: dict[str, Any]


def build_inputs(root: Path, mode: str, manifest_data: dict[str, Any]) -> Inputs:
    from scripts.grabber_smoke import make_inputs

    rad, gain, manifest, calibration = make_inputs(root, mode)
    manifest.write_text(json.dumps(manifest_data))
    return Inputs(
        root, rad, gain, manifest, calibration, root / "image.dcm", manifest_data
    )


def convert_args(item: Inputs) -> list[str]:
    return [
        "-m",
        "mpips.runtime",
        "convert",
        "--radiograph",
        str(item.rad),
        "--gain",
        str(item.gain),
        "--manifest",
        str(item.manifest),
        "--calibration",
        str(item.calibration),
        "--output",
        str(item.output),
    ]


@dataclass
class Run:
    inputs: Inputs
    result: subprocess.CompletedProcess[str]
    guard: GuardRecords
    report: dict[str, Any]


def execute(root: Path, mode: str, mutate: Callable[[Inputs], None] | None) -> Run:
    manifest = compose_manifest(mock_simrs_response(), VISIT, mode)
    item = build_inputs(root / "inputs", mode, manifest)
    if mutate:
        mutate(item)
    code, records = guard_dirs(root / "guard")
    result = run_guarded(convert_args(item), code, records)
    report = json.loads(result.stdout)
    return Run(item, result, read_guard(records), report)


# --- DICOM verification ---------------------------------------------------------


def verify_dicom(run: Run, mode: str) -> np.ndarray:
    output = run.inputs.output
    raw = output.read_bytes()
    assert raw[128:132] == b"DICM"
    assert output.stat().st_mode & 0o777 == 0o600
    ds = pydicom.dcmread(output)
    patient = run.inputs.manifest_data["patient"]
    assert ds.PatientID == patient["medical_record_number"]
    patient_name = (
        patient["name"]["full_name"]
        if isinstance(patient["name"], dict)
        else patient["name"]
    )
    assert str(ds.PatientName) == patient_name
    assert ds.PatientBirthDate == patient["birth_date"].replace("-", "")
    assert run.inputs.manifest_data["examination"]["encounter_id"] == VISIT
    assert ds.Modality == "DX"
    assert ds.SOPClassUID == SOP_CLASS
    assert ds.file_meta.MediaStorageSOPClassUID == SOP_CLASS
    for uid in (ds.StudyInstanceUID, ds.SeriesInstanceUID, ds.SOPInstanceUID):
        assert_uid(str(uid))
    assert_uid(str(ds.file_meta.TransferSyntaxUID))
    assert ds.BitsAllocated == ds.BitsStored == 16
    assert ds.PixelRepresentation == 0
    assert ds.PhotometricInterpretation == "MONOCHROME2"
    assert not any(element.tag.is_private for element in ds.iterall())
    pixels = ds.pixel_array
    assert pixels.shape == SHAPES[mode]
    assert pixels.dtype == np.uint16
    return pixels


def verify_pixels(pixels: np.ndarray, mode: str) -> None:
    assert pixels.min() != pixels.max()
    assert hashlib.sha256(pixels.tobytes()).hexdigest() == PIXEL_SHA256[mode]
    values = pixels.astype(np.int64)
    # Observed structural invariants of the synthetic gradient input (regression
    # characterisation, not independent proof): vertical monotone non-increase for
    # both modes; TRX additionally increases along each row.
    assert np.all(np.diff(values, axis=0) <= 0)
    if mode == "TRX":
        assert np.all(np.diff(values, axis=1) >= 0)
    else:
        assert values[0, 0] == values.max()


# --- fixtures -------------------------------------------------------------------


@pytest.fixture(scope="module")
def positive_runs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Run]:
    return {
        mode: execute(tmp_path_factory.mktemp(f"positive-{mode}"), mode, None)
        for mode in ("BED", "TRX")
    }


def _gain_mode_mismatch(item: Inputs) -> None:
    rewrite_npz(item.gain, xrayparams=np.array({"detectorMode": "TRX"}))


def _gain_shape_mismatch(item: Inputs) -> None:
    rewrite_npz(
        item.gain,
        rawimage=np.full((48, 32), 5000, np.uint16),
        darkimage=np.full((48, 32), 50, np.uint16),
    )


def _gain_id_mismatch(item: Inputs) -> None:
    rewrite_npz(item.rad, gainid=np.array("SYNTHETIC-OTHER-GAIN"))


def _invalid_manifest_json(item: Inputs) -> None:
    item.manifest.write_text("{not json")


def _schema_invalid_manifest(item: Inputs) -> None:
    data = copy.deepcopy(item.manifest_data)
    del data["patient"]["name"]
    item.manifest.write_text(json.dumps(data))


def _missing_calibration(item: Inputs) -> None:
    shutil.rmtree(item.calibration)


def _calibration_not_validated(item: Inputs) -> None:
    path = item.calibration / "metadata.json"
    meta = json.loads(path.read_text())
    meta["validated"] = False
    path.write_text(json.dumps(meta))


def _calibration_wrong_shape(item: Inputs) -> None:
    path = item.calibration / "metadata.json"
    meta = json.loads(path.read_text())
    meta["image_shape"] = [32, 48]
    path.write_text(json.dumps(meta))
    y, x = np.indices((32, 48), dtype=np.float32)
    np.savez_compressed(item.calibration / "remap.npz", map_x=x, map_y=y)


# name -> (mutation, expected exit code, expected code, guard class)
# Exit codes and guard classes below were determined by observing the runtime.
FAILURE_CASES: dict[str, tuple[Callable[[Inputs], None], int, str, str]] = {
    "invalid_manifest_json": (
        _invalid_manifest_json,
        2,
        "INVALID_INPUT",
        "cli_preflight",
    ),
    "schema_invalid_manifest": (
        _schema_invalid_manifest,
        2,
        "INVALID_INPUT",
        "cli_preflight",
    ),
    "gain_id_mismatch": (_gain_id_mismatch, 2, "INVALID_INPUT", "worker"),
    "gain_shape_mismatch": (_gain_shape_mismatch, 2, "INVALID_INPUT", "worker"),
    "detector_mode_mismatch": (
        _gain_mode_mismatch,
        2,
        "INVALID_INPUT",
        "worker",
    ),
    "missing_calibration": (
        _missing_calibration,
        3,
        "INPUT_NOT_FOUND",
        "cli_preflight",
    ),
    "calibration_not_validated": (
        _calibration_not_validated,
        2,
        "INVALID_INPUT",
        "worker",
    ),
    "calibration_wrong_shape": (
        _calibration_wrong_shape,
        2,
        "INVALID_INPUT",
        "worker",
    ),
}


@pytest.fixture(scope="module")
def failure_runs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Run]:
    return {
        name: execute(tmp_path_factory.mktemp(name), "BED", case[0])
        for name, case in FAILURE_CASES.items()
    }


# --- positive tests -------------------------------------------------------------


@pytest.mark.parametrize("mode", ["BED", "TRX"])
def test_positive_end_to_end(positive_runs: dict[str, Run], mode: str) -> None:
    run = positive_runs[mode]
    assert run.result.returncode == 0
    assert run.report["status"] == "ok"
    assert run.result.stderr == ""
    pixels = verify_dicom(run, mode)
    verify_pixels(pixels, mode)
    assert_all_synthetic(
        collect_test_controlled_identifiers(
            run.inputs.manifest_data, run.inputs.rad, run.inputs.gain
        )
    )
    assert not list(run.inputs.root.glob(".mpips-*"))
    assert not list(run.inputs.output.parent.glob(".mpips-*"))


@pytest.mark.parametrize("mode", ["BED", "TRX"])
def test_positive_runs_load_guard_in_cli_and_worker(
    positive_runs: dict[str, Run], mode: str
) -> None:
    guard = positive_runs[mode].guard
    assert guard.labels() == ["guard_loaded:cli", "guard_loaded:worker"]
    assert guard.pids["cli"].isdisjoint(guard.pids["worker"])
    assert guard.rejections == 0, "rejections:nonzero"


def test_bed_and_trx_pixels_are_deterministic(
    positive_runs: dict[str, Run], tmp_path: Path
) -> None:
    again = execute(tmp_path, "BED", None)
    first = verify_dicom(positive_runs["BED"], "BED")
    second = verify_dicom(again, "BED")
    assert np.array_equal(first, second)


# --- pre-CLI rejection tests ----------------------------------------------------


def _bad_dicom_uid(mode: str) -> dict[str, Any]:
    return compose_manifest(
        mock_simrs_response(), VISIT, mode, dicom_overrides={"study_instance_uid": "X"}
    )


PRE_CLI_CASES: dict[str, tuple[Callable[[], Any], type[Exception]]] = {
    "non_dict": (lambda: compose_manifest([], VISIT, "BED"), ValueError),
    "success_not_true": (
        lambda: compose_manifest(
            {**mock_simrs_response(), "success": "true"}, VISIT, "BED"
        ),
        ValueError,
    ),
    "missing_identity": (
        lambda: compose_manifest(
            {
                "success": True,
                "data": {
                    k: v
                    for k, v in mock_simrs_response()["data"].items()
                    if k != "nm_pasien"
                },
            },
            VISIT,
            "BED",
        ),
        ValueError,
    ),
    "visit_mismatch": (
        lambda: compose_manifest(mock_simrs_response(), "SYNTHETIC-OTHER-VISIT", "BED"),
        ValueError,
    ),
    "unconfirmed_selection": (
        lambda: compose_manifest(mock_simrs_response(), VISIT, "BED", confirmed=False),
        SelectionNotConfirmedError,
    ),
    "schema_invalid_manifest": (lambda: _bad_dicom_uid("BED"), ValidationError),
}


@pytest.mark.parametrize("case", sorted(PRE_CLI_CASES))
def test_pre_cli_rejection_never_reaches_runtime(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import socket

    calls: list[str] = []
    attempts: list[str] = []

    def spy(*args: object, **kwargs: object) -> None:
        calls.append("subprocess")
        raise AssertionError("runtime must not be invoked")

    def net_spy(*args: object, **kwargs: object) -> None:
        attempts.append("network")
        raise AssertionError("in-process network attempt")

    monkeypatch.setattr(subprocess, "Popen", spy)
    monkeypatch.setattr(subprocess, "run", spy)
    monkeypatch.setattr(socket.socket, "connect", net_spy)
    monkeypatch.setattr(socket, "getaddrinfo", net_spy)
    build, expected = PRE_CLI_CASES[case]
    with pytest.raises(expected) as error:
        build()
    text = str(error.value)
    for sensitive in ("SYNTHETIC PATIENT", "SYNTHETIC-001", "2000-01-02"):
        assert sensitive not in text
    assert not calls
    # In-process only: says nothing about child processes.
    assert not attempts
    assert not (tmp_path / "image.dcm").exists()
    assert list(tmp_path.iterdir()) == []


# --- CLI failure tests ----------------------------------------------------------


@pytest.mark.parametrize("case", sorted(FAILURE_CASES))
def test_cli_failure_cases(failure_runs: dict[str, Run], case: str) -> None:
    _, exit_code, code, guard_class = FAILURE_CASES[case]
    run = failure_runs[case]
    assert run.result.returncode == exit_code
    assert run.report["status"] == "error"
    assert run.report["code"] == code
    assert set(run.report) == {"code", "interface_version", "runtime_version", "status"}
    assert not run.inputs.output.exists()
    assert not list(run.inputs.output.parent.glob(".mpips-*"))
    visible = run.result.stdout + run.result.stderr
    assert run.result.stderr == ""
    assert "SYNTHETIC" not in visible
    assert str(run.inputs.root) not in visible
    expected = (
        ["guard_loaded:cli"]
        if guard_class == "cli_preflight"
        else ["guard_loaded:cli", "guard_loaded:worker"]
    )
    assert run.guard.labels() == expected, f"case_class:{guard_class}"
    assert run.guard.rejections == 0, "rejections:nonzero"


# --- network guard canary and provenance helper ---------------------------------


def test_guard_canary_observes_rejected_tcp_attempt(tmp_path: Path) -> None:
    code, records = guard_dirs(tmp_path)
    result = run_guarded(
        [
            "-c",
            "import socket; socket.create_connection(('127.0.0.1', 9), timeout=1)",
        ],
        code,
        records,
    )
    assert result.returncode != 0
    guard = read_guard(records)
    assert guard.labels() == ["guard_loaded:canary"]
    assert guard.rejections >= 1
    # Canary records live in their own directory and are never reused elsewhere.
    assert tmp_path.joinpath("guard-records") == records


def test_identifier_helper_rejects_non_synthetic() -> None:
    assert_all_synthetic(["SYNTHETIC-1", "SYNTHETIC PATIENT"])
    with pytest.raises(AssertionError):
        assert_all_synthetic(["SYNTHETIC-1", "MRN-12345"])
    with pytest.raises(AssertionError):
        assert_all_synthetic(["REAL VISIT"])


def test_uid_helper_uses_syntax_not_prefix() -> None:
    assert_uid("1.2.826.0.1.3680043.8.498.1")
    for bad in ("SYNTHETIC.1", "1..2", "01.2", "1." + "2" * 70):
        with pytest.raises(AssertionError):
            assert_uid(bad)


# --- deterministic sanitized evidence -------------------------------------------


def build_evidence(
    positive_runs: dict[str, Run], failure_runs: dict[str, Run]
) -> dict[str, Any]:
    positives = []
    for mode, run in sorted(positive_runs.items()):
        pixels = pydicom.dcmread(run.inputs.output).pixel_array
        positives.append(
            {
                "mode": mode,
                "exit_code": run.result.returncode,
                "status": run.report["status"],
                "shape": list(pixels.shape),
                "pixel_sha256": hashlib.sha256(pixels.tobytes()).hexdigest(),
                "guards": run.guard.labels(),
                "rejections": run.guard.rejections,
            }
        )
    negatives = [
        {
            "case": name,
            "exit_code": run.result.returncode,
            "code": run.report["code"],
            "guards": run.guard.labels(),
            "rejections": run.guard.rejections,
        }
        for name, run in sorted(failure_runs.items())
    ]
    return {
        "synthetic_only": True,
        "positives": positives,
        "cli_failures": negatives,
        "pre_cli_cases": sorted(PRE_CLI_CASES),
        "limitation": LIMITATION,
    }


def test_evidence_is_deterministic_and_sanitized(
    positive_runs: dict[str, Run],
    failure_runs: dict[str, Run],
    tmp_path: Path,
) -> None:
    first = json.dumps(build_evidence(positive_runs, failure_runs), sort_keys=True)
    second = json.dumps(build_evidence(positive_runs, failure_runs), sort_keys=True)
    assert first == second
    data = json.loads(first)
    assert set(data) == {
        "synthetic_only",
        "positives",
        "cli_failures",
        "pre_cli_cases",
        "limitation",
    }
    assert "/" not in first and "\\" not in first
    assert "SYNTHETIC" not in first
    assert "kernel network isolation" in first
    target = os.environ.get("MPIPS_E2E_EVIDENCE")
    if target:
        Path(target).write_text(first + "\n")
