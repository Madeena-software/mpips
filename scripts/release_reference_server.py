"""Loopback-only reference server for synthetic MPIPS release distribution."""

from __future__ import annotations

import base64
import json
import os
import re
import tempfile
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from . import runtime_release
else:
    from importlib import import_module

    runtime_release = import_module(
        f"{__package__}.runtime_release" if __package__ else "runtime_release"
    )

CONTROL_LIMIT = 64 * 1024
PACKAGE_LIMIT = 2 * 1024 * 1024 * 1024
ROLES = {"reader", "publisher", "qualifier", "approver", "promoter"}
RELEASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}\Z")
CHANNEL = re.compile(r"[a-z][a-z0-9-]{0,31}\Z")
TARGET = re.compile(r"ubuntu-\d{2}\.\d{2}-[A-Za-z0-9_]+-py\d+\.\d+\Z")


class ReferenceServer(ThreadingHTTPServer):
    """A synthetic, filesystem-backed server that cannot bind off-loopback."""

    daemon_threads = True
    allow_reuse_address = False

    def handle_error(self, _request: Any, _client_address: Any) -> None:
        return

    def __init__(
        self,
        storage: Path,
        public_key: Path,
        tokens: dict[str, str],
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        if host != "127.0.0.1":
            raise ValueError("Reference server must bind to 127.0.0.1")
        if not tokens or any(
            not token or role not in ROLES for token, role in tokens.items()
        ):
            raise ValueError("Valid in-memory role tokens required")
        self.storage = Path(storage).resolve()
        self.public_key = Path(public_key).resolve()
        self.tokens = dict(tokens)
        self.lock = threading.RLock()
        self.storage.mkdir(parents=True, exist_ok=True)
        super().__init__((host, port), _handler())

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}"


def _handler() -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server: ReferenceServer

        def send_error(
            self,
            code: int,
            _message: str | None = None,
            _explain: str | None = None,
        ) -> None:
            if code == 501:
                self._error(404, "not_found", "Reference route not found")
            else:
                self._error(400, "bad_request", "Malformed HTTP request")

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, _format: str, *_args: object) -> None:
            return

        def _send(self, status: int, value: dict[str, Any] | bytes) -> None:
            if isinstance(value, bytes):
                body = value
                content_type = "application/octet-stream"
            else:
                body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
                content_type = "application/json"
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _stream_file(self, path: Path) -> None:
            size = path.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    self.wfile.write(chunk)

        def _error(self, status: int, code: str, message: str) -> None:
            self._send(
                status,
                {"schema_version": 1, "error": {"code": code, "message": message}},
            )

        def _authorized(self, roles: set[str]) -> bool:
            header = self.headers.get("Authorization", "")
            token = header[7:] if header.startswith("Bearer ") else ""
            role = self.server.tokens.get(token)
            if role is None:
                self._error(401, "unauthorized", "Valid reference token required")
                return False
            if role not in roles:
                self._error(403, "forbidden", "Reference role not permitted")
                return False
            return True

        def _length(self, limit: int, exact: int | None = None) -> int | None:
            if self.headers.get("Transfer-Encoding"):
                self._error(400, "bad_request", "Unsupported transfer encoding")
                return None
            raw = self.headers.get("Content-Length")
            if raw is None or not raw.isdecimal():
                self._error(400, "bad_request", "Content-Length required")
                return None
            length = int(raw)
            if length > limit:
                self._error(413, "too_large", "Request body exceeds reference limit")
                return None
            if exact is not None and length != exact:
                self._error(400, "bad_request", "Invalid request body length")
                return None
            return length

        def _read_body(self, limit: int, exact: int | None = None) -> bytes | None:
            length = self._length(limit, exact)
            if length is None:
                return None
            data = self.rfile.read(length)
            if len(data) != length:
                self._error(400, "bad_request", "Incomplete request body")
                return None
            return data

        def _write_component(self, directory: Path, name: str, limit: int) -> None:
            length = self._length(limit, 64 if name == "signature" else None)
            if length is None:
                return
            directory.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=".upload-", dir=directory)
            total = 0
            try:
                with os.fdopen(fd, "wb") as stream:
                    while total < length:
                        chunk = self.rfile.read(min(1024 * 1024, length - total))
                        if not chunk:
                            self._error(400, "bad_request", "Incomplete request body")
                            return
                        total += len(chunk)
                        stream.write(chunk)
                    stream.flush()
                    os.fsync(stream.fileno())
                with self.server.lock:
                    target = directory / name
                    try:
                        os.link(temporary, target)
                    except FileExistsError:
                        self._error(
                            409, "conflict", "Immutable release component exists"
                        )
                        return
                Path(temporary).unlink(missing_ok=True)
                self._send(201, {"schema_version": 1, "mode": "local-reference-only"})
            finally:
                Path(temporary).unlink(missing_ok=True)

        def _json_body(self) -> dict[str, Any] | None:
            body = self._read_body(CONTROL_LIMIT)
            if body is None:
                return None
            try:
                value = json.loads(body)
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._error(400, "bad_request", "Invalid JSON request")
                return None
            if not isinstance(value, dict):
                self._error(400, "bad_request", "Invalid JSON request")
                return None
            return value

        def _parts(self) -> list[str] | None:
            parsed = urlsplit(self.path)
            if parsed.query or parsed.fragment or "%" in parsed.path:
                self._error(400, "bad_request", "Invalid reference path")
                return None
            parts = parsed.path.split("/")[1:]
            if not parts or any(part in ("", ".", "..") for part in parts):
                self._error(400, "bad_request", "Invalid reference path")
                return None
            return parts

        def _snapshot(self, release: Path, state: str) -> dict[str, Any]:
            metadata = (release / "metadata").read_bytes()
            signature = (release / "signature").read_bytes()
            value = json.loads(metadata)
            if state == "published" and self._was_promoted(
                value["release_id"], value["sequence"]
            ):
                state = "promoted"
            return {
                "schema_version": 1,
                "mode": "local-reference-only",
                "release_id": value["release_id"],
                "sequence": value["sequence"],
                "state": state,
                "metadata_b64": base64.b64encode(metadata).decode("ascii"),
                "signature_b64": base64.b64encode(signature).decode("ascii"),
            }

        def _was_promoted(self, release_id: str, sequence: int) -> bool:
            for pointer in (self.server.storage / "channels").rglob("pointer.json"):
                try:
                    history = json.loads(pointer.read_text())["history"]
                except (OSError, KeyError, TypeError, json.JSONDecodeError):
                    continue
                if any(
                    item.get("release_id") == release_id
                    and item.get("sequence") == sequence
                    for item in history
                ):
                    return True
            return False

        def _verify(
            self, directory: Path, requested_target: str | None = None
        ) -> dict[str, Any]:
            metadata_path = directory / "metadata"
            signature_path = directory / "signature"
            package_path = directory / "package"
            raw = metadata_path.read_bytes()
            metadata = json.loads(raw)
            filename = metadata["package"]["filename"]
            if (
                not isinstance(filename, str)
                or Path(filename).name != filename
                or not re.fullmatch(r"[A-Za-z0-9._-]{1,255}", filename)
            ):
                raise ValueError("Package filename rejected")
            with tempfile.TemporaryDirectory(
                prefix="mpips-reference-verify-"
            ) as scratch:
                candidate = Path(scratch) / filename
                os.link(package_path, candidate)
                value = runtime_release.verify(
                    metadata_path,
                    signature_path,
                    self.server.public_key,
                    candidate,
                    metadata["sequence"],
                    enforce_host_compatibility=False,
                )
            if value["release_id"] != directory.parent.name or value["sequence"] != int(
                directory.name
            ):
                raise ValueError("Release identity mismatch")
            compatibility = value["compatibility"]
            expected_target = (
                f"ubuntu-{compatibility['os_version']}-{compatibility['architecture']}"
                f"-py{compatibility['python']}"
            )
            if compatibility["os"] != "ubuntu" or not TARGET.fullmatch(expected_target):
                raise ValueError("Release target rejected")
            if requested_target is not None and expected_target != requested_target:
                raise ValueError("Release target mismatch")
            return value

        def _record_path(
            self, release_id: str, sequence: str, published: bool = False
        ) -> Path:
            if not RELEASE_ID.fullmatch(release_id) or not re.fullmatch(
                r"[1-9][0-9]*", sequence
            ):
                raise ValueError("Invalid identity")
            return (
                self.server.storage
                / ("releases" if published else "staging")
                / release_id
                / sequence
            )

        def _state(self, path: Path) -> dict[str, Any]:
            state_file = path / "state.json"
            if not state_file.exists():
                return {"state": "candidate", "simulated": False}
            return cast(dict[str, Any], json.loads(state_file.read_text()))

        def _set_state(self, path: Path, value: dict[str, Any]) -> None:
            fd, temporary = tempfile.mkstemp(prefix=".state-", dir=path)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    json.dump(value, stream, sort_keys=True, separators=(",", ":"))
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path / "state.json")
            finally:
                Path(temporary).unlink(missing_ok=True)

        def _control_transition(self, parts: list[str]) -> None:
            if len(parts) != 5 or parts[0] != "v1" or parts[1] != "staging":
                self._error(404, "not_found", "Reference route not found")
                return
            release_id, sequence, action = parts[2:]
            roles = {
                "qualify": "qualifier",
                "approve": "approver",
                "publish": "publisher",
            }
            role = roles.get(action)
            if role is None:
                self._error(404, "not_found", "Reference route not found")
                return
            if not self._authorized({role}):
                return
            body = self._read_body(CONTROL_LIMIT, 0)
            if body is None:
                return
            try:
                path = self._record_path(release_id, sequence)
            except ValueError:
                self._error(400, "bad_request", "Invalid release identity")
                return
            with self.server.lock:
                try:
                    state = self._state(path)
                    if action == "qualify" and state["state"] == "candidate":
                        self._verify(path)
                        state = {"state": "qualified", "simulated": True}
                        self._set_state(path, state)
                    elif action == "approve" and state["state"] == "qualified":
                        state = {
                            **state,
                            "state": "approved",
                            "simulated_approval": True,
                        }
                        self._set_state(path, state)
                    elif action == "publish" and state["state"] in (
                        "approved",
                        "published",
                    ):
                        value = self._verify(path)
                        if value["release_id"] != release_id or value[
                            "sequence"
                        ] != int(sequence):
                            raise ValueError("Release identity mismatch")
                        destination = self._record_path(release_id, sequence, True)
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        if destination.exists():
                            self._error(
                                409, "conflict", "Immutable release already published"
                            )
                            return
                        state = {**state, "state": "published"}
                        self._set_state(path, state)
                        try:
                            os.rename(path, destination)
                        except FileExistsError:
                            self._set_state(path, {**state, "state": "approved"})
                            self._error(
                                409, "conflict", "Immutable release already published"
                            )
                            return
                        except OSError:
                            self._set_state(path, {**state, "state": "approved"})
                            raise
                    else:
                        self._error(
                            409, "conflict", "Invalid reference lifecycle transition"
                        )
                        return
                except FileNotFoundError:
                    self._error(409, "conflict", "Complete staged release required")
                    return
                except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError):
                    self._error(
                        422, "invalid_release", "Signed release verification failed"
                    )
                    return
            self._send(
                200, {"schema_version": 1, "mode": "local-reference-only", **state}
            )

        def _promote(self, parts: list[str]) -> None:
            if (
                len(parts) != 5
                or parts[0:2] != ["v1", "channels"]
                or parts[4] != "promote"
            ):
                self._error(404, "not_found", "Reference route not found")
                return
            channel, target = parts[2:4]
            if not CHANNEL.fullmatch(channel) or not TARGET.fullmatch(target):
                self._error(400, "bad_request", "Invalid channel target")
                return
            if not self._authorized({"promoter"}):
                return
            body = self._json_body()
            if body is None:
                return
            if set(body) != {"expected_current_sequence"}:
                self._error(400, "bad_request", "Invalid promotion request")
                return
            expected = body.get("expected_current_sequence")
            if type(expected) is not int or expected < 0:
                self._error(400, "bad_request", "Invalid expected sequence")
                return
            with self.server.lock:
                channel_path = self.server.storage / "channels" / channel / target
                pointer = channel_path / "pointer.json"
                current = json.loads(pointer.read_text()) if pointer.exists() else None
                current_entry = current["current"] if current else None
                current_sequence = current_entry["sequence"] if current_entry else 0
                if expected != current_sequence:
                    self._error(409, "conflict", "Channel sequence changed")
                    return
                eligible: list[tuple[int, str, Path]] = []
                releases = self.server.storage / "releases"
                for release_id_dir in releases.iterdir() if releases.exists() else ():
                    for sequence_dir in release_id_dir.iterdir():
                        try:
                            state = self._state(sequence_dir)
                            metadata = json.loads(
                                (sequence_dir / "metadata").read_bytes()
                            )
                            compatibility = metadata["compatibility"]
                            matches_target = (
                                f"ubuntu-{compatibility['os_version']}-"
                                f"{compatibility['architecture']}-py"
                                f"{compatibility['python']}" == target
                            )
                            if (
                                state["state"] == "published"
                                and type(metadata["sequence"]) is int
                                and metadata["sequence"] > current_sequence
                                and matches_target
                            ):
                                eligible.append(
                                    (
                                        metadata["sequence"],
                                        metadata["release_id"],
                                        sequence_dir,
                                    )
                                )
                        except (
                            OSError,
                            ValueError,
                            KeyError,
                            TypeError,
                            json.JSONDecodeError,
                        ):
                            continue
                if not eligible:
                    self._error(
                        404, "not_found", "No approved release available for target"
                    )
                    return
                sequence, release_id, directory = min(eligible)
                try:
                    value = self._verify(directory, target)
                except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                    self._error(
                        422, "invalid_release", "Signed release verification failed"
                    )
                    return
                if value["release_id"] != release_id or value["sequence"] != sequence:
                    self._error(
                        422, "invalid_release", "Signed release verification failed"
                    )
                    return
                now = datetime.now(timezone.utc).isoformat()
                entry = {
                    "release_id": release_id,
                    "sequence": sequence,
                    "previous_sequence": current_sequence,
                    "promoted_at": now,
                }
                history = current["history"] if current else []
                next_value = {"current": entry, "history": [*history, entry]}
                channel_path.mkdir(parents=True, exist_ok=True)
                fd, temporary = tempfile.mkstemp(prefix=".pointer-", dir=channel_path)
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as stream:
                        json.dump(
                            next_value, stream, sort_keys=True, separators=(",", ":")
                        )
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary, pointer)
                finally:
                    Path(temporary).unlink(missing_ok=True)
            self._send(
                200,
                {
                    "schema_version": 1,
                    "mode": "local-reference-only",
                    "state": "promoted",
                    **entry,
                },
            )

        def do_PUT(self) -> None:
            parts = self._parts()
            if parts is None:
                return
            if len(parts) != 5 or parts[0:2] != ["v1", "staging"]:
                self._error(404, "not_found", "Reference route not found")
                return
            if not self._authorized({"publisher"}):
                return
            release_id, sequence, component = parts[2:]
            if component not in {"metadata", "signature", "package"}:
                self._error(404, "not_found", "Reference route not found")
                return
            try:
                directory = self._record_path(release_id, sequence)
            except ValueError:
                self._error(400, "bad_request", "Invalid release identity")
                return
            published = self._record_path(release_id, sequence, True)
            if published.exists():
                self._error(409, "conflict", "Published release is immutable")
                return
            self._write_component(
                directory,
                component,
                PACKAGE_LIMIT if component == "package" else CONTROL_LIMIT,
            )

        def do_POST(self) -> None:
            parts = self._parts()
            if parts is None:
                return
            if parts[0:2] == ["v1", "staging"]:
                self._control_transition(parts)
            elif len(parts) == 5 and parts[1] == "channels" and parts[4] == "promote":
                self._promote(parts)
            else:
                self._error(404, "not_found", "Reference route not found")

        def do_GET(self) -> None:
            parts = self._parts()
            if parts is None:
                return
            if parts[:1] != ["v1"]:
                self._error(404, "not_found", "Reference route not found")
                return
            if len(parts) == 4 and parts[1] == "releases":
                if not self._authorized({"reader"}):
                    return
                try:
                    directory = self._record_path(parts[2], parts[3], True)
                    state = self._state(directory)
                    self._send(200, self._snapshot(directory, state["state"]))
                except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                    self._error(404, "not_found", "Published release not found")
                return
            if len(parts) == 5 and parts[1] == "releases" and parts[4] == "package":
                if not self._authorized({"reader"}):
                    return
                try:
                    directory = self._record_path(parts[2], parts[3], True)
                    self._verify(directory)
                    self._stream_file(directory / "package")
                except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                    self._error(404, "not_found", "Published package not found")
                return
            if len(parts) == 4 and parts[1] == "channels":
                channel, target = parts[2:]
                if not CHANNEL.fullmatch(channel) or not TARGET.fullmatch(target):
                    self._error(400, "bad_request", "Invalid channel target")
                    return
                if not self._authorized({"reader"}):
                    return
                pointer = (
                    self.server.storage / "channels" / channel / target / "pointer.json"
                )
                try:
                    value = json.loads(pointer.read_text())["current"]
                    directory = self._record_path(
                        value["release_id"], str(value["sequence"]), True
                    )
                    self._send(200, self._snapshot(directory, "promoted"))
                except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                    self._error(404, "not_found", "Channel release not found")
                return
            if len(parts) == 5 and parts[1] == "channels" and parts[4] == "history":
                channel, target = parts[2:4]
                if not CHANNEL.fullmatch(channel) or not TARGET.fullmatch(target):
                    self._error(400, "bad_request", "Invalid channel target")
                    return
                if not self._authorized({"reader"}):
                    return
                history = (
                    self.server.storage / "channels" / channel / target / "pointer.json"
                )
                try:
                    entries = json.loads(history.read_text())["history"]
                except FileNotFoundError:
                    self._error(404, "not_found", "Channel history not found")
                    return
                self._send(
                    200,
                    {
                        "schema_version": 1,
                        "mode": "local-reference-only",
                        "history": entries,
                    },
                )
                return
            self._error(404, "not_found", "Reference route not found")

    return Handler


def main() -> int:
    raise SystemExit(
        "The reference server is test-only and is started by local fixtures"
    )


if __name__ == "__main__":
    main()
