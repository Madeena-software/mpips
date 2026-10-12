from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timezone
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


def inspection(
    state: str = "exited",
    exit_code: str = "137",
    oom: str = "true",
    restarts: str = "6",
    finished: str = "2026-10-12T11:00:00Z",
    policy: str = "unless-stopped",
    image: str = "mpips-api:" + "a" * 40,
    network: str = "yes",
) -> str:
    return "|".join((state, exit_code, oom, restarts, finished, policy, image, network))


@pytest.mark.parametrize(
    ("output", "version", "expected"),
    (
        (
            inspection(),
            "a" * 40,
            audit.ContainerDiagnostics(
                "nonzero", "yes", "many", "recent", "unless-stopped", "yes", "yes"
            ),
        ),
        (
            inspection(
                exit_code="0",
                oom="false",
                restarts="5",
                finished="2026-10-11T12:00:00Z",
                policy="always",
                image="mpips-api:" + "b" * 40,
                network="no",
            ),
            "a" * 40,
            audit.ContainerDiagnostics(
                "zero", "no", "few", "historical", "other", "no", "no"
            ),
        ),
        (
            inspection(state="running", exit_code="0", oom="false", restarts="0"),
            "a" * 40,
            audit.ContainerDiagnostics(
                "not_applicable",
                "no",
                "none",
                "not_applicable",
                "unless-stopped",
                "yes",
                "yes",
            ),
        ),
        (None, "a" * 40, audit.UNKNOWN_DIAGNOSTICS),
        ("malformed", "a" * 40, audit.UNKNOWN_DIAGNOSTICS),
        (
            inspection(exit_code="bad"),
            "a" * 40,
            audit.ContainerDiagnostics(
                "unknown",
                "yes",
                "many",
                "recent",
                "unless-stopped",
                "yes",
                "yes",
            ),
        ),
        (
            inspection(exit_code="999"),
            "a" * 40,
            audit.ContainerDiagnostics(
                "unknown",
                "yes",
                "many",
                "recent",
                "unless-stopped",
                "yes",
                "yes",
            ),
        ),
        (
            inspection(oom="maybe"),
            "a" * 40,
            audit.ContainerDiagnostics(
                "nonzero",
                "unknown",
                "many",
                "recent",
                "unless-stopped",
                "yes",
                "yes",
            ),
        ),
        (
            inspection(restarts="bad"),
            "a" * 40,
            audit.ContainerDiagnostics(
                "nonzero",
                "yes",
                "unknown",
                "recent",
                "unless-stopped",
                "yes",
                "yes",
            ),
        ),
        (
            inspection(finished="invalid"),
            "a" * 40,
            audit.ContainerDiagnostics(
                "nonzero",
                "yes",
                "many",
                "unknown",
                "unless-stopped",
                "yes",
                "yes",
            ),
        ),
        (
            inspection(),
            None,
            audit.ContainerDiagnostics(
                "nonzero",
                "yes",
                "many",
                "recent",
                "unless-stopped",
                "unknown",
                "yes",
            ),
        ),
    ),
    ids=(
        "stopped-oom-restarted-recent-match",
        "zero-exit-historical-mismatch",
        "running-not-applicable",
        "missing-inspection",
        "malformed-inspection",
        "malformed-exit",
        "out-of-range-exit",
        "malformed-oom",
        "malformed-restart-count",
        "malformed-finish-time",
        "missing-deployment-marker",
    ),
)
def test_container_diagnostics_are_fixed_categories(
    output: str | None,
    version: str | None,
    expected: audit.ContainerDiagnostics,
) -> None:
    now = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)
    assert (
        audit.container_diagnostics(output, "mpips-api", version, now=now) == expected
    )


def test_container_diagnostics_fail_closed_on_state_race() -> None:
    assert audit.container_diagnostics(
        inspection(state="running"), "mpips-api", "a" * 40, "stopped"
    ) == audit.UNKNOWN_DIAGNOSTICS


def test_deployment_version_marker_is_validated_and_private(tmp_path: Path) -> None:
    marker = tmp_path / "marker"
    marker.write_text("a" * 40 + "\n")
    assert audit.deployment_version(marker) == "a" * 40
    marker.write_text("not-a-version")
    assert audit.deployment_version(marker) is None
    assert audit.deployment_version(tmp_path / "missing") is None


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
        if args[2:4] == ["--format", audit.INSPECT_FORMAT]:
            return completed(
                args,
                inspection(
                    state="running",
                    exit_code="0",
                    oom="false",
                    restarts="0",
                    finished="0001-01-01T00:00:00Z",
                    image=(
                        "mpips-api:" + "a" * 40
                        if args[-1] == "aaaaaaaaaaaa"
                        else "redis:7.4.10"
                    ),
                ),
            )
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
    with (
        patch.object(subprocess, "run", side_effect=fake_run),
        patch.object(audit, "deployment_version", return_value="a" * 40),
    ):
        output = "\n".join(f"{label}: {value}" for label, value in audit.collect())

    assert "Running containers: 1–5" in output
    assert "MPIPS API container: running" in output
    assert "MPIPS API health: unhealthy" in output
    assert "MPIPS API exit code: not_applicable" in output
    assert "MPIPS API restart policy: unless-stopped" in output
    assert "MPIPS API image matches deployment marker: yes" in output
    assert "API and Redis share expected network: yes" in output
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
        "mpips-api:" + "a" * 40,
        "redis:7.4.10",
    ):
        assert sensitive not in output


def test_stopped_api_diagnostics_remain_independent_from_healthy_redis() -> None:
    finished = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    finished = finished.replace("+00:00", "Z")

    def stopped_api_run(
        args: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if "com.docker.compose.service" in " ".join(args):
            return completed(
                args,
                "aaaaaaaaaaaa|mpips-api|exited\nbbbbbbbbbbbb|redis|running\n",
            )
        if args[:2] == ["docker", "inspect"] and args[2:4] == [
            "--format",
            audit.INSPECT_FORMAT,
        ]:
            return completed(
                args,
                inspection(
                    state="exited" if args[-1] == "aaaaaaaaaaaa" else "running",
                    exit_code="137",
                    oom="true" if args[-1] == "aaaaaaaaaaaa" else "false",
                    restarts="6" if args[-1] == "aaaaaaaaaaaa" else "0",
                    finished=finished,
                    image="mpips-api:" + "a" * 40,
                ),
            )
        if args[:2] == ["docker", "inspect"]:
            return completed(args, "healthy\n")
        return fake_run(args, **kwargs)

    with (
        patch.object(subprocess, "run", side_effect=stopped_api_run),
        patch.object(audit, "deployment_version", return_value="a" * 40),
    ):
        output = dict(audit.collect())

    assert output["MPIPS API container"] == "stopped"
    assert output["MPIPS API health"] == "unavailable"
    assert output["MPIPS API exit code"] == "nonzero"
    assert output["MPIPS API OOM-killed"] == "yes"
    assert output["MPIPS API restart count"] == "many"
    assert output["MPIPS API stop age"] == "recent"
    assert output["MPIPS API restart policy"] == "unless-stopped"
    assert output["MPIPS API image matches deployment marker"] == "yes"
    assert output["Redis container"] == "running"
    assert output["Redis health"] == "healthy"
    assert output["API and Redis share expected network"] == "yes"
    assert "137" not in output.values()
    assert "mpips-api:" + "a" * 40 not in output.values()


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
    assert (
        QUALIFICATION.read_text().count("scripts/audit_infrastructure_readonly.py") == 2
    )


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
