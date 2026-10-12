"""Local release metadata/signature verification; no network or publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ED25519_SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def host_compatibility() -> dict[str, str]:
    release = platform.freedesktop_os_release()
    libc, version = platform.libc_ver()
    if release["ID"] != "ubuntu" or libc != "glibc":
        raise ValueError("Ubuntu/glibc required for this candidate builder")
    return {
        "os": "ubuntu",
        "os_version": release["VERSION_ID"],
        "architecture": platform.machine(),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "glibc_min": version,
    }


def validate_compatibility(target: dict[str, str]) -> None:
    host = host_compatibility()
    for key in ("os", "os_version", "architecture", "python"):
        if target[key] != host[key]:
            raise ValueError("Incompatible runtime target")
    minimum = tuple(int(v) for v in target["glibc_min"].split("."))
    available = tuple(int(v) for v in host["glibc_min"].split("."))
    if not minimum or minimum > available:
        raise ValueError("Incompatible glibc")


def write_json(path: Path, value: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def create_metadata(
    package: Path,
    output: Path,
    version: str,
    commit: str,
    sequence: int,
    compatibility: dict[str, str],
    expires: datetime,
) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or sequence <= 0:
        raise ValueError("Full commit SHA and positive release sequence required")
    if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
        raise ValueError("Future timezone-aware metadata expiry required")
    write_json(
        output,
        {
            "schema_version": 1,
            "runtime_version": version,
            "release_id": f"{version}-{commit}",
            "commit_sha": commit,
            "sequence": sequence,
            "expires_at": expires.isoformat(),
            "interface_version": "1",
            "manifest_version": "1.0",
            "package": {
                "filename": package.name,
                "sha256": sha256(package),
                "size": package.stat().st_size,
                "format": "offline-wheelhouse-tar-gzip",
            },
            "compatibility": compatibility,
            "qualification": "synthetic-only",
            "release_status": "candidate-not-approved-for-distribution",
        },
    )


def openssl(*args: str) -> bytes:
    result = subprocess.run(["openssl", *args], capture_output=True)
    if result.returncode:
        raise ValueError("Signature operation failed")
    return result.stdout


def check_key(key: Path, public: bool) -> None:
    flags = ["-pubin"] if public else []
    der = openssl("pkey", *flags, "-in", str(key), "-pubout", "-outform", "DER")
    if len(der) != 44 or not der.startswith(ED25519_SPKI_PREFIX):
        raise ValueError("Ed25519 key required")


def sign(metadata: Path, signature: Path, key: Path) -> None:
    check_key(key, public=False)
    with tempfile.TemporaryDirectory(prefix="mpips-sign-") as scratch:
        staged = Path(scratch) / "signature"
        openssl(
            "pkeyutl",
            "-sign",
            "-rawin",
            "-inkey",
            str(key),
            "-in",
            str(metadata),
            "-out",
            str(staged),
        )
        with signature.open("xb") as stream:
            stream.write(staged.read_bytes())


def verify(
    metadata: Path,
    signature: Path,
    key: Path,
    package: Path,
    minimum_sequence: int,
) -> dict[str, Any]:
    check_key(key, public=True)
    # Parse the same snapshot we authenticated, even if the caller replaces files.
    raw = metadata.read_bytes()
    with tempfile.TemporaryDirectory(prefix="mpips-verify-") as scratch:
        snapshot = Path(scratch) / "metadata"
        snapshot.write_bytes(raw)
        openssl(
            "pkeyutl",
            "-verify",
            "-rawin",
            "-pubin",
            "-inkey",
            str(key),
            "-in",
            str(snapshot),
            "-sigfile",
            str(signature),
        )
    value: dict[str, Any] = json.loads(raw)
    if value["schema_version"] != 1 or value["interface_version"] != "1":
        raise ValueError("Unsupported release interface")
    if value["manifest_version"] != "1.0":
        raise ValueError("Unsupported manifest interface")
    if type(value["sequence"]) is not int or value["sequence"] < max(
        1, minimum_sequence
    ):
        raise ValueError("Release sequence rejected")
    expiry = datetime.fromisoformat(value["expires_at"])
    if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
        raise ValueError("Metadata expired")
    if not re.fullmatch(r"[0-9a-f]{40}", value["commit_sha"]):
        raise ValueError("Invalid commit identity")
    validate_compatibility(value["compatibility"])
    descriptor = value["package"]
    if descriptor["format"] != "offline-wheelhouse-tar-gzip":
        raise ValueError("Unsupported package format")
    if descriptor["filename"] != package.name:
        raise ValueError("Package identity mismatch")
    if descriptor["size"] != package.stat().st_size or descriptor["sha256"] != sha256(
        package
    ):
        raise ValueError("Package integrity mismatch")
    return value


def publication_plan(
    value: dict[str, Any],
    endpoint: str,
    licensing: str,
    infrastructure: str,
) -> dict[str, Any]:
    url = urlsplit(endpoint)
    if (
        url.scheme != "https"
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise ValueError("Approved HTTPS publication base required")
    if not licensing.strip() or not infrastructure.strip():
        raise ValueError("Owner approval references required")
    return {
        "status": "preparation-only-no-network-action",
        "licensing_approval_reference": licensing,
        "infrastructure_approval_reference": infrastructure,
        "immutable_prefix": endpoint.rstrip("/") + "/releases/" + value["release_id"],
        "authentication": "owner-provisioned short-lived HTTPS bearer token",
        "files": [value["package"]["filename"], "release.json", "release.sig"],
        "promotion": "separate approved server-side atomic channel-pointer change",
        "release_status": value["release_status"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    meta = commands.add_parser("metadata")
    meta.add_argument("--package", required=True, type=Path)
    meta.add_argument("--output", required=True, type=Path)
    meta.add_argument("--version", required=True)
    meta.add_argument("--commit", required=True)
    meta.add_argument("--sequence", required=True, type=int)
    for command in ("sign", "verify", "publication-plan"):
        sub = commands.add_parser(command)
        for name in ("metadata", "signature", "key"):
            sub.add_argument(f"--{name}", required=True, type=Path)
        if command != "sign":
            sub.add_argument("--package", required=True, type=Path)
            sub.add_argument("--minimum-sequence", required=True, type=int)
        if command == "publication-plan":
            for name in ("endpoint", "licensing-approval", "infrastructure-approval"):
                sub.add_argument(f"--{name}", required=True)
            sub.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "metadata":
            create_metadata(
                args.package,
                args.output,
                args.version,
                args.commit,
                args.sequence,
                host_compatibility(),
                datetime.now(timezone.utc) + timedelta(days=7),
            )
        elif args.command == "sign":
            sign(args.metadata, args.signature, args.key)
        else:
            value = verify(
                args.metadata,
                args.signature,
                args.key,
                args.package,
                args.minimum_sequence,
            )
            if args.command == "publication-plan":
                write_json(
                    args.output,
                    publication_plan(
                        value,
                        args.endpoint,
                        args.licensing_approval,
                        args.infrastructure_approval,
                    ),
                )
            else:
                print(
                    json.dumps(
                        {
                            "status": "verified",
                            "release_id": value["release_id"],
                            "release_status": value["release_status"],
                        }
                    )
                )
        return 0
    except (ValueError, OSError, KeyError, TypeError):
        print("Release operation rejected; no publication performed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
