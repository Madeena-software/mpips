#!/usr/bin/env python3
"""Probe MPIPS host launcher socket for conversion readiness and worker image match."""

from __future__ import annotations

import json
import socket
import sys


def main() -> None:
    if len(sys.argv) != 3:
        sys.stderr.write("Usage: probe_launcher.py <socket_path> <expected_worker_image>\n")
        sys.exit(2)

    sock_path = sys.argv[1]
    expected_image = sys.argv[2]

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(5.0)
            sock.connect(sock_path)
            payload = json.dumps({"action": "ping"}).encode("utf-8") + b"\n"
            sock.sendall(payload)
            sock.shutdown(socket.SHUT_WR)

            resp_bytes = bytearray()
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                resp_bytes.extend(chunk)

        if not resp_bytes:
            sys.stderr.write("Error: Empty response from launcher socket\n")
            sys.exit(1)

        data = json.loads(resp_bytes.decode("utf-8"))
        if data.get("status") == "success" and data.get("action") == "pong":
            actual_image = data.get("worker_image")
            if actual_image != expected_image:
                sys.stderr.write(
                    f"Error: Worker image mismatch: expected '{expected_image}', got '{actual_image}'\n"
                )
                sys.exit(1)
            print(f"Launcher probe ready: worker_image={actual_image}")
            sys.exit(0)

        sys.stderr.write(f"Error: Unexpected launcher response: {data}\n")
        sys.exit(1)
    except Exception as exc:
        sys.stderr.write(f"Error connecting to launcher socket {sock_path}: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
