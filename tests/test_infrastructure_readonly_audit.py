from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from scripts import audit_infrastructure_readonly as audit

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/audit-infrastructure-readonly.yml"
QUALIFICATION = ROOT / ".github/workflows/qualify-ubuntu-runtime.yml"


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


@pytest.mark.parametrize(
    ("output", "expected"),
    (
        ("LISTEN 0 10 127.0.0.1:8014 0.0.0.0:*", (True, True)),
        ("LISTEN 0 10 [::1]:8014 [::]:*", (True, True)),
        (
            "LISTEN 0 10 127.0.0.1:8014 0.0.0.0:*\n" "LISTEN 0 10 [::1]:8014 [::]:*",
            (True, True),
        ),
        (
            "LISTEN 0 10 127.0.0.1:8014 0.0.0.0:*\n"
            "LISTEN 0 10 0.0.0.0:8014 0.0.0.0:*",
            (True, False),
        ),
        (
            "LISTEN 0 10 127.0.0.1:8014 0.0.0.0:*\nBROKEN 0 0 *:443",
            (True, True),
        ),
        ("LISTEN 0 10 10.10.20.30:8014 0.0.0.0:*", (True, False)),
        ("LISTEN 0 10 *:8014 *:*", (True, False)),
        ("LISTEN 0 10 [::]:8014 [::]:*", (True, False)),
        ("", (False, False)),
        ("LISTEN 0 10 127.0.0.1:80 0.0.0.0:*", (False, False)),
        (None, (None, None)),
        ("not an ss listener row", (None, None)),
        ("LISTEN 0 10 not-an-address:8014 *:*", (None, None)),
    ),
    ids=(
        "ipv4-loopback-only",
        "ipv6-loopback-only",
        "dual-stack-loopback-only",
        "loopback-plus-ipv4-wildcard",
        "malformed-unrelated-port-is-ignored",
        "non-loopback-only",
        "wildcard-only",
        "ipv6-wildcard-only",
        "empty-output-no-match",
        "no-matching-listener",
        "missing-output",
        "malformed-output",
        "malformed-address",
    ),
)
def test_port_state_requires_exclusive_recognized_loopback(
    output: str | None, expected: tuple[bool | None, bool | None]
) -> None:
    assert audit.port_state(output, 8014) == expected


@pytest.mark.parametrize(
    ("output", "expected"),
    (
        ("", (False, False)),
        ("LISTEN 0 10 *:80 *:*", (True, False)),
        ("LISTEN 0 10 [::]:80 [::]:*", (True, False)),
        ("not interpretable", (None, None)),
        (None, (None, None)),
    ),
)
def test_target_port_listener_presence(
    output: str | None, expected: tuple[bool | None, bool | None]
) -> None:
    assert audit.port_state(output, 80) == expected


@pytest.mark.parametrize(
    ("output", "expected", "complete"),
    (
        (None, {}, "unknown"),
        ("", {}, "no"),
        (
            "a" * 12 + "|mpips-api|running",
            {"mpips-api": ("a" * 12, "running")},
            "no",
        ),
        (
            "a" * 12 + "|mpips-api|running\n" + "b" * 12 + "|redis|exited",
            {"mpips-api": ("a" * 12, "running"), "redis": ("b" * 12, "exited")},
            "yes",
        ),
        ("malformed inventory", {}, "unknown"),
        (
            "a" * 12 + "|mpips-api|running\n" + "b" * 12 + "|mpips-api|exited",
            {},
            "unknown",
        ),
    ),
    ids=(
        "inspection-error",
        "empty-valid-stack",
        "partial-stack",
        "complete-stack",
        "malformed",
        "duplicate-service",
    ),
)
def test_service_inventory_is_complete_and_fail_closed(
    output: str | None, expected: dict[str, tuple[str, str]], complete: str
) -> None:
    assert audit.service_inventory(output) == (expected, complete)


@pytest.mark.parametrize(
    ("entry", "inventory", "expected"),
    (
        (None, "unknown", "unknown"),
        (None, "no", "not_found"),
        (("a" * 12, "running"), "yes", "running"),
        (("a" * 12, "exited"), "yes", "stopped"),
    ),
)
def test_service_state_classifications(
    entry: tuple[str, str] | None, inventory: str, expected: str
) -> None:
    assert audit.service_state(entry, inventory) == expected


@pytest.mark.parametrize(
    ("state", "output", "expected"),
    (
        ("running", "healthy\n", "healthy"),
        ("running", "unhealthy\n", "unhealthy"),
        ("running", "unavailable\n", "unavailable"),
        ("running", "starting\n", "unknown"),
        ("running", None, "unknown"),
        ("stopped", None, "unavailable"),
        ("not_found", None, "unavailable"),
        ("unknown", None, "unknown"),
    ),
)
def test_service_health_classifications(
    state: str, output: str | None, expected: str
) -> None:
    assert audit.service_health(state, output) == expected


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
    if args[:3] == ["docker", "network", "ls"]:
        return completed(args, "mpips-internal-beta-v1\nprivate-network-sensitive\n")
    if "com.docker.compose.service" in " ".join(args):
        return completed(
            args,
            "aaaaaaaaaaaa|mpips-api|running\nbbbbbbbbbbbb|redis|running\n",
        )
    if args[:2] == ["docker", "inspect"]:
        return completed(
            args,
            "unhealthy\n" if args[-1] == "aaaaaaaaaaaa" else "healthy\n",
        )
    if args[:3] == ["ss", "-H", "-ltn"]:
        return completed(
            args,
            {
                "sport = :8014": (
                    "LISTEN 0 10 127.0.0.1:8014 0.0.0.0:*\n"
                    "LISTEN 0 10 [::1]:8014 [::]:*\n"
                ),
                "sport = :80": "",
                "sport = :443": "LISTEN 0 10 10.10.20.30:443 0.0.0.0:*\n",
            }[args[-1]],
        )
    raise AssertionError(f"Unexpected inspection command: {args[0]}")


def test_collector_emits_only_sanitized_categories() -> None:
    with patch.object(subprocess, "run", side_effect=fake_run):
        output = "\n".join(f"{label}: {value}" for label, value in audit.collect())

    assert "Running containers: 1–5" in output
    assert "MPIPS API container: running" in output
    assert "MPIPS API health: unhealthy" in output
    assert "Redis health: healthy" in output
    assert "Expected Compose project complete: yes" in output
    assert "Aggregate MPIPS health" not in output
    assert "Port 8014 exclusively loopback-bound: yes" in output
    assert "Port 443 occupied: yes" in output
    assert "Candidate network conflict: unknown" in output
    assert "Approved HTTPS ingress identifiable: unknown" in output
    for sensitive in (
        "daemon-version-sensitive",
        "compose-version-sensitive",
        "container-id-sensitive",
        "aaaaaaaaaaaa",
        "bbbbbbbbbbbb",
        "private-network-sensitive",
        "127.0.0.1",
        "[::1]",
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
    assert output["MPIPS API container"] == "unknown"
    assert output["Redis container"] == "unknown"
    assert output["Expected Compose project complete"] == "unknown"
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
    assert QUALIFICATION.read_text().count("scripts/audit_infrastructure_readonly.py") == 2


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
