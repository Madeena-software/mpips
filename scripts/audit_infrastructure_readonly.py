"""Emit coarse, allowlisted production host inventory classifications."""

from __future__ import annotations

import ipaddress
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Sequence


def command(args: Sequence[str]) -> str | None:
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            check=False,
            text=True,
            timeout=3,
            env={
                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "HOME": "/nonexistent",
                "DOCKER_CONFIG": "/nonexistent",
                "LC_ALL": "C",
            },
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return None
    return result.stdout if result.returncode == 0 else None


def category(value: float | None, thresholds: tuple[float, ...]) -> str:
    if value is None:
        return "unknown"
    labels = ("below 8 GiB", "8–16 GiB", "16–32 GiB", "above 32 GiB")
    if value < thresholds[0]:
        return labels[0]
    if value < thresholds[1]:
        return labels[1]
    if value <= thresholds[2]:
        return labels[2]
    return labels[3]


def memory_gib(field: str) -> float | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith(f"{field}:"):
                return int(line.split()[1]) / 1024 / 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def os_classification() -> str:
    try:
        release = platform.freedesktop_os_release()
        family = release.get("ID", "").lower()
        version = tuple(
            int(part) for part in release.get("VERSION_ID", "").split(".")[:2]
        )
    except (OSError, ValueError):
        return "unknown"
    if family == "ubuntu":
        return "Ubuntu 24.04+" if version >= (24, 4) else "Ubuntu earlier than 24.04"
    if family == "debian":
        return "Debian"
    return "other Linux" if platform.system() == "Linux" else "other OS"


def architecture_classification() -> str:
    architecture = platform.machine().lower()
    if architecture in {"x86_64", "amd64"}:
        return "x86_64"
    if architecture in {"aarch64", "arm64"}:
        return "arm64"
    return "other" if architecture else "unknown"


def disk(path: str) -> tuple[str, bool | None]:
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return "unknown", None
    if usage.total <= 0:
        return "unknown", None
    free_gib = usage.free / 1024**3
    label = "low" if free_gib < 10 else "moderate" if free_gib <= 50 else "sufficient"
    return label, free_gib < 10 or usage.free / usage.total < 0.10


def port_state(output: str | None, port: int) -> tuple[bool | None, bool | None]:
    if output is None:
        return None, None
    occupied = False
    listeners: list[bool] = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 4:
            return None, None
        endpoint = fields[3]
        if endpoint.startswith("["):
            address, separator, raw_port = endpoint[1:].partition("]:")
            if not separator:
                return None, None
        else:
            address, separator, raw_port = endpoint.rpartition(":")
            if not separator or ":" in address:
                return None, None
        if not raw_port.isdigit():
            return None, None
        if int(raw_port) != port:
            continue
        if len(fields) != 5 or fields[0] != "LISTEN" or not address:
            return None, None
        if not fields[1].isdigit() or not fields[2].isdigit():
            return None, None
        try:
            ip = None if address == "*" else ipaddress.ip_address(address)
        except ValueError:
            return None, None
        if int(raw_port) > 65535:
            return None, None
        occupied = True
        listeners.append(ip is not None and ip.is_loopback)
    return occupied, bool(listeners) and all(listeners)


SERVICES = ("mpips-api", "redis")
DOCKER_STATES = {"running", "created", "restarting", "paused", "exited", "dead"}


def service_inventory(output: str | None) -> tuple[dict[str, tuple[str, str]], str]:
    if output is None:
        return {}, "unknown"
    services: dict[str, list[tuple[str, str]]] = {name: [] for name in SERVICES}
    for line in output.splitlines():
        fields = line.split("|")
        if (
            len(fields) != 3
            or re.fullmatch(r"[0-9a-fA-F]{12,64}", fields[0]) is None
            or re.fullmatch(r"[A-Za-z0-9_.-]+", fields[1]) is None
            or fields[2] not in DOCKER_STATES
        ):
            return {}, "unknown"
        if fields[1] in services:
            services[fields[1]].append((fields[0], fields[2]))
    if any(len(services[name]) > 1 for name in SERVICES):
        return {}, "unknown"
    complete = "yes" if all(services[name] for name in SERVICES) else "no"
    identified = {name: entries[0] for name, entries in services.items() if entries}
    return identified, complete


def service_state(entry: tuple[str, str] | None, inventory: str) -> str:
    if inventory == "unknown":
        return "unknown"
    if entry is None:
        return "not_found"
    if entry[1] == "running":
        return "running"
    return "stopped"


def service_health(state: str, output: str | None) -> str:
    if state in {"not_found", "stopped"}:
        return "unavailable"
    if state == "unknown" or output is None:
        return "unknown"
    health = output.strip()
    if health in {"healthy", "unhealthy", "unavailable"}:
        return health
    return "unknown"


def yn(value: bool | None) -> str:
    return "unknown" if value is None else "yes" if value else "no"


def collect() -> list[tuple[str, str]]:
    cores = os.cpu_count()
    total_ram = memory_gib("MemTotal")
    available_ram = memory_gib("MemAvailable")
    try:
        load = os.getloadavg()[0] / cores if cores else None
    except (AttributeError, OSError):
        load = None
    load_category = (
        "unknown"
        if load is None
        else "low" if load < 0.7 else "moderate" if load < 1.5 else "high"
    )
    root_disk, root_near = disk("/")
    runtime_disk, runtime_near = disk("/var/www/mpips-runtime")

    docker_info = command(["docker", "info", "--format", "{{.ServerVersion}}"])
    docker = docker_info is not None and bool(docker_info.strip())
    compose = command(["docker", "compose", "version", "--short"])
    count = command(["docker", "ps", "-q"])
    network_names = command(["docker", "network", "ls", "--format", "{{.Name}}"])
    stack = command(
        [
            "docker",
            "ps",
            "--all",
            "--filter",
            "label=com.docker.compose.project=mpips-internal-beta",
            "--format",
            '{{.ID}}|{{.Label "com.docker.compose.service"}}|{{.State}}',
        ]
    )
    service_entries, project_complete = service_inventory(stack)
    port_8014, exclusive_loopback_8014 = port_state(
        command(["ss", "-H", "-ltn", "sport = :8014"]), 8014
    )
    port_80, _ = port_state(command(["ss", "-H", "-ltn", "sport = :80"]), 80)
    port_443, _ = port_state(command(["ss", "-H", "-ltn", "sport = :443"]), 443)
    compose_available = (
        "unknown"
        if compose is None and docker_info is None
        else "no" if compose is None else "yes"
    )

    if not docker:
        container_count = "unknown"
        project_complete = "unknown"
        networks = "unknown"
        service_entries = {}
    else:
        if count is None:
            container_count = "unknown"
        else:
            running_count = len(count.splitlines())
            container_count = (
                "none"
                if running_count == 0
                else (
                    "1–5"
                    if running_count <= 5
                    else "6–15" if running_count <= 15 else "above 15"
                )
            )
        names = set(network_names.splitlines()) if network_names is not None else set()
        networks = (
            "unknown"
            if network_names is None
            else (
                "present"
                if {"mpips-internal-beta-v1", "mhcs-mpips-integration-v1"} <= names
                else "missing"
            )
        )

    states = {
        name: service_state(service_entries.get(name), project_complete)
        for name in SERVICES
    }
    healths: dict[str, str] = {}
    for name in SERVICES:
        entry = service_entries.get(name)
        result = (
            command(
                [
                    "docker",
                    "inspect",
                    "--format",
                    (
                        "{{if .State.Health}}{{.State.Health.Status}}"
                        "{{else}}unavailable{{end}}"
                    ),
                    entry[0],
                ]
            )
            if entry is not None and states[name] == "running"
            else None
        )
        healths[name] = service_health(states[name], result)

    rows = [
        ("OS compatibility", os_classification()),
        ("CPU architecture", architecture_classification()),
        (
            "CPU capacity",
            (
                "unknown"
                if cores is None
                else "small" if cores <= 2 else "medium" if cores <= 8 else "large"
            ),
        ),
        ("RAM total", category(total_ram, (8, 16, 32))),
        ("RAM available", category(available_ram, (8, 16, 32))),
        ("Root disk available", root_disk),
        ("Runtime disk available", runtime_disk),
        (
            "Filesystem approaching capacity",
            yn(
                None
                if root_near is None or runtime_near is None
                else root_near or runtime_near
            ),
        ),
        ("Current CPU/load", load_category),
        (
            "Docker daemon",
            "yes" if docker else "no" if docker_info is not None else "unknown",
        ),
        ("Docker Compose", compose_available),
        ("Running containers", container_count),
        ("MPIPS API container", states["mpips-api"]),
        ("MPIPS API health", healths["mpips-api"]),
        ("Redis container", states["redis"]),
        ("Redis health", healths["redis"]),
        ("Expected Compose project complete", project_complete),
        ("Expected Docker networks", networks),
        ("Candidate network conflict", "unknown"),
        ("Port 8014 occupied", yn(port_8014)),
        ("Port 8014 exclusively loopback-bound", yn(exclusive_loopback_8014)),
        ("Port 80 occupied", yn(port_80)),
        ("Port 443 occupied", yn(port_443)),
        ("Approved HTTPS ingress identifiable", "unknown"),
    ]
    return rows


if __name__ == "__main__":
    for label, value in collect():
        print(f"{label}: {value}")
