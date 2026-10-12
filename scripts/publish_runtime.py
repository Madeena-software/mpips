"""Validate local runtime releases and stage them to the loopback reference."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from . import runtime_release
else:
    from importlib import import_module

    runtime_release = import_module(
        f"{__package__}.runtime_release" if __package__ else "runtime_release"
    )


def _loopback(endpoint: str) -> tuple[str, int]:
    url = urlsplit(endpoint)
    if (
        url.scheme != "http"
        or url.hostname != "127.0.0.1"
        or url.port is None
        or url.username
        or url.password
        or url.path not in ("", "/")
        or url.query
        or url.fragment
    ):
        raise ValueError("Only an explicit 127.0.0.1 reference server is supported")
    return url.hostname, url.port


def _request(
    endpoint: str, path: str, method: str, token: str, body: bytes | None = None
) -> None:
    host, port = _loopback(endpoint)
    connection = http.client.HTTPConnection(host, port, timeout=5)
    try:
        connection.request(
            method,
            path,
            body=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": (
                    "application/json"
                    if body is not None
                    else "application/octet-stream"
                ),
            },
        )
        response = connection.getresponse()
        response.read()
        if response.status not in (200, 201):
            raise ValueError("Reference server rejected the operation")
    finally:
        connection.close()


def _upload(endpoint: str, path: str, token: str, filename: Path) -> None:
    host, port = _loopback(endpoint)
    connection = http.client.HTTPConnection(host, port, timeout=5)
    try:
        connection.putrequest("PUT", path)
        connection.putheader("Authorization", f"Bearer {token}")
        connection.putheader("Content-Length", str(filename.stat().st_size))
        connection.putheader("Content-Type", "application/octet-stream")
        connection.endheaders()
        with filename.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                connection.send(chunk)
        response = connection.getresponse()
        response.read()
        if response.status != 201:
            raise ValueError("Reference server rejected the upload")
    finally:
        connection.close()


def _release_args(args: argparse.Namespace) -> dict[str, Any]:
    return runtime_release.verify(
        args.metadata, args.signature, args.key, args.package, 1
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("dry-run", "stage"):
        sub = commands.add_parser(command)
        sub.add_argument("--package", type=Path, required=True)
        sub.add_argument("--metadata", type=Path, required=True)
        sub.add_argument("--signature", type=Path, required=True)
        sub.add_argument("--key", type=Path, required=True)
        if command == "stage":
            sub.add_argument("--server", required=True)
    promote = commands.add_parser("promote")
    promote.add_argument("--server", required=True)
    promote.add_argument("--channel", required=True)
    promote.add_argument("--target", required=True)
    promote.add_argument("--expected-current-sequence", required=True, type=int)
    args = parser.parse_args(argv)
    try:
        if args.command in {"dry-run", "stage"}:
            value = _release_args(args)
            if args.command == "dry-run":
                print(
                    json.dumps(
                        {
                            "status": "validated-no-network-action",
                            "mode": "local-reference-only",
                            "release_id": value["release_id"],
                            "sequence": value["sequence"],
                        },
                        sort_keys=True,
                    )
                )
                return 0
            endpoint = args.server
            _loopback(endpoint)
            token = os.environ.get("MPIPS_REFERENCE_PUBLISHER_TOKEN", "")
            if not token:
                raise ValueError("Local publisher test token required")
            release_id = value["release_id"]
            sequence = value["sequence"]
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}", release_id):
                raise ValueError("Release identity rejected")
            prefix = f"/v1/staging/{release_id}/{sequence}"
            for component, file in (
                ("metadata", args.metadata),
                ("signature", args.signature),
                ("package", args.package),
            ):
                _upload(endpoint, f"{prefix}/{component}", token, file)
            print(json.dumps({"status": "staged", "mode": "local-reference-only"}))
            return 0
        if args.expected_current_sequence < 0:
            raise ValueError("Expected sequence must be nonnegative")
        endpoint = args.server
        _loopback(endpoint)
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", args.channel):
            raise ValueError("Channel rejected")
        if not re.fullmatch(
            r"ubuntu-\d{2}\.\d{2}-[A-Za-z0-9_]+-py\d+\.\d+", args.target
        ):
            raise ValueError("Target rejected")
        token = os.environ.get("MPIPS_REFERENCE_PROMOTER_TOKEN", "")
        if not token:
            raise ValueError("Local promoter test token required")
        body = json.dumps(
            {"expected_current_sequence": args.expected_current_sequence}
        ).encode()
        _request(
            endpoint,
            f"/v1/channels/{args.channel}/{args.target}/promote",
            "POST",
            token,
            body,
        )
        print(json.dumps({"status": "promoted", "mode": "local-reference-only"}))
        return 0
    except (ValueError, OSError, KeyError, TypeError, http.client.HTTPException):
        print(
            "Reference release operation rejected; no remote publication is available",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
