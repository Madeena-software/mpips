from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import audit_infrastructure_readonly as audit

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/audit-infrastructure-readonly.yml"


def test_capacity_category_boundaries() -> None:
    assert audit.category(7.99, (8, 16, 32)) == "below 8 GiB"
    assert audit.category(8, (8, 16, 32)) == "8–16 GiB"
    assert audit.category(16, (8, 16, 32)) == "16–32 GiB"
    assert audit.category(32, (8, 16, 32)) == "16–32 GiB"
    assert audit.category(32.01, (8, 16, 32)) == "above 32 GiB"


def test_disk_category_boundaries() -> None:
    for free_gib, expected in (
        (9, ("low", True)),
        (10, ("moderate", False)),
        (50, ("moderate", False)),
        (51, ("sufficient", False)),
    ):
        usage = SimpleNamespace(total=100 * 1024**3, free=free_gib * 1024**3)
        with patch.object(shutil, "disk_usage", return_value=usage):
            assert audit.disk("/unused") == expected


def completed(args: list[str], output: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, 0, output, "sensitive stderr")


def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    assert kwargs["capture_output"] is True
    timeout = kwargs["timeout"]
    assert isinstance(timeout, int) and timeout <= 3
    assert kwargs["env"] == {
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "HOME": "/nonexistent",
        "DOCKER_CONFIG": "/nonexistent",
        "LC_ALL": "C",
    }
    if args[:2] == ["docker", "info"]:
        return completed(args, "daemon-version-sensitive")
    if args[:3] == ["docker", "compose", "version"]:
        return completed(args, "compose-version-sensitive")
    if args == ["docker", "ps", "-q"]:
        return completed(args, "container-id-sensitive\n")
    if args[:3] == ["docker", "ps", "-q"]:
        return completed(args, "container-id-sensitive\n")
    if args[:3] == ["docker", "network", "ls"]:
        return completed(args, "mpips-internal-beta-v1\nprivate-network-sensitive\n")
    if "com.docker.compose.service" in " ".join(args):
        return completed(args, "mpips-api\nredis\n")
    if args[:2] == ["docker", "inspect"]:
        return completed(args, "healthy\n")
    if args[:2] == ["ss", "-H"]:
        return completed(
            args,
            "LISTEN 0 10 127.0.0.1:8014 0.0.0.0:*\n"
            "LISTEN 0 10 10.10.20.30:443 0.0.0.0:*\n",
        )
    raise AssertionError(f"Unexpected inspection command: {args[0]}")


def test_collector_emits_only_sanitized_categories() -> None:
    with patch.object(subprocess, "run", side_effect=fake_run):
        output = "\n".join(f"{label}: {value}" for label, value in audit.collect())

    assert "Running containers: 1–5" in output
    assert "MPIPS expected services: present" in output
    assert "Port 8014 bound to loopback: yes" in output
    assert "Port 443 occupied: yes" in output
    assert "Candidate network conflict: unknown" in output
    assert "Approved HTTPS ingress identifiable: unknown" in output
    for sensitive in (
        "daemon-version-sensitive",
        "compose-version-sensitive",
        "container-id-sensitive",
        "private-network-sensitive",
        "10.10.20.30",
        "sensitive stderr",
    ):
        assert sensitive not in output


def test_missing_inspection_commands_fail_closed() -> None:
    with patch.object(subprocess, "run", side_effect=FileNotFoundError):
        output = dict(audit.collect())

    assert output["Docker daemon"] == "unknown"
    assert output["Docker Compose"] == "unknown"
    assert output["Running containers"] == "unknown"
    assert output["MPIPS expected services"] == "unknown"
    assert output["Expected Docker networks"] == "unknown"
    assert output["Port 8014 occupied"] == "unknown"


def test_missing_os_measurements_fail_closed() -> None:
    with (
        patch.object(audit, "memory_gib", return_value=None),
        patch.object(audit, "os_classification", return_value="unknown"),
        patch.object(audit, "disk", return_value=("unknown", None)),
        patch.object(os, "cpu_count", return_value=None),
        patch.object(os, "getloadavg", side_effect=OSError),
        patch.object(audit, "command", return_value=None),
    ):
        output = dict(audit.collect())

    assert output["OS compatibility"] == "unknown"
    assert output["CPU capacity"] == "unknown"
    assert output["RAM total"] == "unknown"
    assert output["Root disk available"] == "unknown"
    assert output["Current CPU/load"] == "unknown"


def test_workflow_is_manual_main_only_and_non_canceling() -> None:
    workflow = WORKFLOW.read_text()
    assert workflow.startswith("name:")
    assert "on:\n  workflow_dispatch:\n" in workflow
    assert "if: github.ref == 'refs/heads/main'" in workflow
    assert "runs-on: [self-hosted, production]" in workflow
    assert "timeout-minutes: 5" in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "group: mpips-infrastructure-audit" in workflow
    assert "queue: max" in workflow
    assert "cancel-in-progress" not in workflow
    assert "persist-credentials: false" in workflow
    assert workflow.count("uses:") == 1
    assert "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683" in workflow
    assert "secrets." not in workflow
    assert "upload-artifact" not in workflow
    assert "workflow_run:" not in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow


def test_inspector_has_no_mutation_or_external_probe_commands() -> None:
    source = (ROOT / "scripts/audit_infrastructure_readonly.py").read_text()
    assert "set -x" not in source
    for forbidden in (
        '"docker", "exec"',
        '"docker", "rm"',
        '"docker", "compose", "up"',
        '"docker", "compose", "down"',
        '"docker", "network", "create"',
        '"curl"',
        '"wget"',
        '"pip", "install"',
        '"apt", "install"',
    ):
        assert forbidden not in source
    assert ".env" not in source
    assert "DOCKER_HOST" not in source
