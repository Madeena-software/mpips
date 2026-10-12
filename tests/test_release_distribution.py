"""Integration tests for the local-only release distribution reference."""

from __future__ import annotations

import base64
import http.client
import json
import subprocess
import threading
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest


def request(
    base: str,
    path: str,
    token: str,
    method: str = "GET",
    body: bytes | None = None,
) -> tuple[int, bytes]:
    req = urllib.request.Request(
        base + path,
        data=body,
        headers={"Authorization": f"Bearer {token}"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def signed_metadata(
    distribution: Any, tmp_path: Path, value: dict[str, Any]
) -> tuple[bytes, bytes]:
    metadata = tmp_path / "variant.json"
    signature = tmp_path / "variant.sig"
    metadata.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    subprocess.run(
        [
            "openssl",
            "pkeyutl",
            "-sign",
            "-rawin",
            "-inkey",
            str(distribution["private_key"]),
            "-in",
            str(metadata),
            "-out",
            str(signature),
        ],
        check=True,
        capture_output=True,
    )
    return metadata.read_bytes(), signature.read_bytes()


def stage_release(
    distribution: Any, release_id: str, metadata: bytes, signature: bytes
) -> str:
    path = f"/v1/staging/{release_id}/1"
    for component, data in (
        ("metadata", metadata),
        ("signature", signature),
        ("package", distribution["package"]),
    ):
        assert (
            request(
                distribution["base"],
                f"{path}/{component}",
                "publisher-token",
                "PUT",
                data,
            )[0]
            == 201
        )
    return path


@pytest.fixture
def distribution(tmp_path: Path) -> Any:
    from scripts.release_reference_server import ReferenceServer
    from scripts.runtime_release import create_metadata, host_compatibility

    package = tmp_path / "runtime.tar.gz"
    package.write_bytes(b"synthetic signed software artifact")
    metadata = tmp_path / "release.json"
    create_metadata(
        package,
        metadata,
        "0.1.0",
        "a" * 40,
        1,
        host_compatibility(),
        datetime.now(timezone.utc) + timedelta(days=1),
    )
    private_key, public_key = tmp_path / "private.pem", tmp_path / "public.pem"
    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "Ed25519", "-out", str(private_key)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "openssl",
            "pkey",
            "-in",
            str(private_key),
            "-pubout",
            "-out",
            str(public_key),
        ],
        check=True,
        capture_output=True,
    )
    signature = tmp_path / "release.sig"
    subprocess.run(
        [
            "openssl",
            "pkeyutl",
            "-sign",
            "-rawin",
            "-inkey",
            str(private_key),
            "-in",
            str(metadata),
            "-out",
            str(signature),
        ],
        check=True,
        capture_output=True,
    )
    server = ReferenceServer(
        tmp_path / "server",
        public_key,
        {
            "reader-token": "reader",
            "publisher-token": "publisher",
            "qualifier-token": "qualifier",
            "approver-token": "approver",
            "promoter-token": "promoter",
        },
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield {
        "base": server.base_url,
        "server": server,
        "thread": thread,
        "package": package.read_bytes(),
        "metadata": metadata.read_bytes(),
        "signature": signature.read_bytes(),
        "package_path": package,
        "metadata_path": metadata,
        "signature_path": signature,
        "private_key": private_key,
        "public_key": public_key,
    }
    server.shutdown()
    thread.join(timeout=3)
    server.server_close()


def test_signed_release_lifecycle_and_exact_channel_snapshot(distribution: Any) -> None:
    base = distribution["base"]
    metadata_value = json.loads(distribution["metadata"])
    release_id = metadata_value["release_id"]
    target_data = metadata_value["compatibility"]
    target = (
        f"ubuntu-{target_data['os_version']}-{target_data['architecture']}"
        f"-py{target_data['python']}"
    )
    path = f"/v1/staging/{release_id}/1"
    for component, data in (
        ("metadata", distribution["metadata"]),
        ("signature", distribution["signature"]),
        ("package", distribution["package"]),
    ):
        status, _ = request(base, f"{path}/{component}", "publisher-token", "PUT", data)
        assert status == 201
    status, body = request(base, f"{path}/qualify", "qualifier-token", "POST")
    assert status == 200
    assert json.loads(body)["state"] == "qualified"
    status, _ = request(base, f"{path}/approve", "approver-token", "POST")
    assert status == 200
    status, _ = request(base, f"{path}/publish", "publisher-token", "POST")
    assert status == 200
    status, body = request(
        base,
        f"/v1/channels/stable/{target}/promote",
        "promoter-token",
        "POST",
        b'{"expected_current_sequence":0}',
    )
    assert status == 200
    assert json.loads(body)["state"] == "promoted"
    status, body = request(base, f"/v1/channels/stable/{target}", "reader-token")
    assert status == 200
    snapshot = json.loads(body)
    assert snapshot["state"] == "promoted"
    assert base64.b64decode(snapshot["metadata_b64"]) == distribution["metadata"]
    assert base64.b64decode(snapshot["signature_b64"]) == distribution["signature"]
    status, body = request(base, f"/v1/releases/{release_id}/1", "reader-token")
    assert status == 200
    assert json.loads(body)["state"] == "promoted"
    status, body = request(
        base,
        f"/v1/channels/stable/{target}/history",
        "reader-token",
    )
    assert status == 200
    assert len(json.loads(body)["history"]) == 1
    status, body = request(
        base,
        f"/v1/releases/{release_id}/1/package",
        "reader-token",
    )
    assert status == 200
    assert body == distribution["package"]


def test_role_boundaries_immutable_upload_and_compare_and_swap(
    distribution: Any,
) -> None:
    base = distribution["base"]
    release_id = json.loads(distribution["metadata"])["release_id"]
    path = f"/v1/staging/{release_id}/1/metadata"
    assert request(base, path, "reader-token", "PUT", b"x")[0] == 403
    assert request(base, path, "publisher-token", "PUT", b"first")[0] == 201
    status, body = request(base, path, "publisher-token", "PUT", b"second")
    assert status == 409
    assert b"second" not in body
    status, body = request(
        base,
        "/v1/channels/stable/ubuntu-26.04-x86_64-py3.12/promote",
        "promoter-token",
        "POST",
        b'{"expected_current_sequence":9}',
    )
    assert status == 409
    assert request(base, path, "bad-secret", "PUT", b"x")[0] == 401


def test_partial_release_cannot_be_discovered_or_qualified(distribution: Any) -> None:
    base = distribution["base"]
    metadata = json.loads(distribution["metadata"])
    path = f"/v1/staging/{metadata['release_id']}/1"
    assert (
        request(
            base, f"{path}/metadata", "publisher-token", "PUT", distribution["metadata"]
        )[0]
        == 201
    )
    assert request(base, f"{path}/qualify", "qualifier-token", "POST")[0] == 409
    assert (
        request(
            base,
            f"/v1/releases/{metadata['release_id']}/1",
            "reader-token",
        )[0]
        == 404
    )


def test_tampered_metadata_fails_qualification_with_sanitized_error(
    distribution: Any,
) -> None:
    base = distribution["base"]
    metadata = json.loads(distribution["metadata"])
    path = f"/v1/staging/{metadata['release_id']}/1"
    changed = distribution["metadata"].replace(b'"sequence":1', b'"sequence":2')
    for component, data in (
        ("metadata", changed),
        ("signature", distribution["signature"]),
        ("package", distribution["package"]),
    ):
        assert (
            request(base, f"{path}/{component}", "publisher-token", "PUT", data)[0]
            == 201
        )
    status, body = request(base, f"{path}/qualify", "qualifier-token", "POST")
    assert status == 422
    assert b"aaaaaaaa" not in body
    assert b"test-private" not in body


def test_tampered_package_fails_signed_integrity_check(distribution: Any) -> None:
    value = json.loads(distribution["metadata"])
    path = f"/v1/staging/{value['release_id']}/1"
    for component, data in (
        ("metadata", distribution["metadata"]),
        ("signature", distribution["signature"]),
        ("package", b"tampered package"),
    ):
        assert (
            request(
                distribution["base"],
                f"{path}/{component}",
                "publisher-token",
                "PUT",
                data,
            )[0]
            == 201
        )
    assert (
        request(distribution["base"], f"{path}/qualify", "qualifier-token", "POST")[0]
        == 422
    )


def test_server_qualifies_cross_target_but_client_enforces_host(
    distribution: Any, tmp_path: Path
) -> None:
    from scripts.runtime_release import host_compatibility, verify

    compatibility = host_compatibility()
    compatibility["os_version"] = (
        "26.04" if compatibility["os_version"] != "26.04" else "24.04"
    )
    value = json.loads(distribution["metadata"])
    value["compatibility"] = compatibility
    value["release_id"] = (
        f"{value['runtime_version']}-{value['commit_sha']}-ubuntu"
        f"{compatibility['os_version']}-{compatibility['architecture']}"
        f"-py{compatibility['python']}"
    )
    metadata, signature = signed_metadata(distribution, tmp_path, value)
    path = stage_release(distribution, value["release_id"], metadata, signature)
    base = distribution["base"]
    assert request(base, f"{path}/qualify", "qualifier-token", "POST")[0] == 200
    assert request(base, f"{path}/approve", "approver-token", "POST")[0] == 200
    assert request(base, f"{path}/publish", "publisher-token", "POST")[0] == 200
    target = (
        f"ubuntu-{compatibility['os_version']}-{compatibility['architecture']}"
        f"-py{compatibility['python']}"
    )
    wrong_target = (
        f"ubuntu-{host_compatibility()['os_version']}-"
        f"{compatibility['architecture']}-py{compatibility['python']}"
    )
    assert (
        request(
            base,
            f"/v1/channels/stable/{wrong_target}/promote",
            "promoter-token",
            "POST",
            b'{"expected_current_sequence":0}',
        )[0]
        == 404
    )
    assert (
        request(
            base,
            f"/v1/channels/stable/{target}/promote",
            "promoter-token",
            "POST",
            b'{"expected_current_sequence":0}',
        )[0]
        == 200
    )
    local_package = tmp_path / "runtime.tar.gz"
    local_package.write_bytes(distribution["package"])
    with pytest.raises(ValueError, match="Incompatible runtime target"):
        verify(
            tmp_path / "variant.json",
            tmp_path / "variant.sig",
            distribution["public_key"],
            local_package,
            1,
        )


@pytest.mark.parametrize("change", ["malformed_target", "expired"])
def test_signed_invalid_compatibility_or_expiry_is_rejected(
    distribution: Any, tmp_path: Path, change: str
) -> None:
    value = json.loads(distribution["metadata"])
    if change == "malformed_target":
        value["compatibility"]["os_version"] = "../../24.04"
        value["release_id"] = "invalid-target"
    else:
        value["expires_at"] = (
            datetime.now(timezone.utc) - timedelta(days=1)
        ).isoformat()
    metadata, signature = signed_metadata(distribution, tmp_path, value)
    path = stage_release(distribution, value["release_id"], metadata, signature)
    assert (
        request(distribution["base"], f"{path}/qualify", "qualifier-token", "POST")[0]
        == 422
    )


def test_declared_oversize_and_traversal_are_rejected(
    distribution: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import release_reference_server

    monkeypatch.setattr(release_reference_server, "PACKAGE_LIMIT", 8)
    base = distribution["base"]
    metadata = json.loads(distribution["metadata"])
    path = f"/v1/staging/{metadata['release_id']}/1"
    assert (
        request(base, f"{path}/package", "publisher-token", "PUT", b"x" * 9)[0] == 413
    )


def test_unknown_channel_history_and_unsupported_method_use_error_envelopes(
    distribution: Any,
) -> None:
    base = distribution["base"]
    status, body = request(
        base,
        "/v1/channels/stable/ubuntu-24.04-x86_64-py3.12/history",
        "reader-token",
    )
    assert status == 404
    assert json.loads(body)["error"]["code"] == "not_found"
    status, body = request(base, "/v1/staging/x/1/metadata", "publisher-token", "PATCH")
    assert status == 404
    assert json.loads(body)["error"]["code"] == "not_found"
    assert (
        request(
            base,
            "/v1/staging/../1/metadata",
            "publisher-token",
            "PUT",
            b"x",
        )[0]
        == 400
    )


def test_replayed_promotion_is_rejected(distribution: Any) -> None:
    base = distribution["base"]
    metadata = json.loads(distribution["metadata"])
    compatibility = metadata["compatibility"]
    target = (
        f"ubuntu-{compatibility['os_version']}-{compatibility['architecture']}"
        f"-py{compatibility['python']}"
    )
    path = f"/v1/staging/{metadata['release_id']}/1"
    for component, data in (
        ("metadata", distribution["metadata"]),
        ("signature", distribution["signature"]),
        ("package", distribution["package"]),
    ):
        request(base, f"{path}/{component}", "publisher-token", "PUT", data)
    request(base, f"{path}/qualify", "qualifier-token", "POST")
    request(base, f"{path}/approve", "approver-token", "POST")
    request(base, f"{path}/publish", "publisher-token", "POST")
    promote = f"/v1/channels/stable/{target}/promote"
    assert (
        request(
            base, promote, "promoter-token", "POST", b'{"expected_current_sequence":0}'
        )[0]
        == 200
    )
    assert (
        request(
            base, promote, "promoter-token", "POST", b'{"expected_current_sequence":0}'
        )[0]
        == 409
    )


def test_concurrent_compare_and_swap_allows_only_one_promotion(
    distribution: Any, tmp_path: Path
) -> None:
    base = distribution["base"]
    metadata = json.loads(distribution["metadata"])
    second_metadata = tmp_path / "release-2.json"
    second_signature = tmp_path / "release-2.sig"
    second_metadata.write_bytes(
        distribution["metadata"].replace(b'"sequence":1', b'"sequence":2')
    )
    subprocess.run(
        [
            "openssl",
            "pkeyutl",
            "-sign",
            "-rawin",
            "-inkey",
            str(distribution["private_key"]),
            "-in",
            str(second_metadata),
            "-out",
            str(second_signature),
        ],
        check=True,
        capture_output=True,
    )
    for sequence, metadata_bytes, signature_bytes in (
        (1, distribution["metadata"], distribution["signature"]),
        (2, second_metadata.read_bytes(), second_signature.read_bytes()),
    ):
        path = f"/v1/staging/{metadata['release_id']}/{sequence}"
        for component, data in (
            ("metadata", metadata_bytes),
            ("signature", signature_bytes),
            ("package", distribution["package"]),
        ):
            assert (
                request(base, f"{path}/{component}", "publisher-token", "PUT", data)[0]
                == 201
            )
        assert request(base, f"{path}/qualify", "qualifier-token", "POST")[0] == 200
        assert request(base, f"{path}/approve", "approver-token", "POST")[0] == 200
        assert request(base, f"{path}/publish", "publisher-token", "POST")[0] == 200
    compatibility = metadata["compatibility"]
    target = (
        f"ubuntu-{compatibility['os_version']}-{compatibility['architecture']}"
        f"-py{compatibility['python']}"
    )
    path = f"/v1/channels/stable/{target}/promote"
    barrier = threading.Barrier(3)
    statuses: list[int] = []

    def promote() -> None:
        barrier.wait()
        statuses.append(
            request(
                base,
                path,
                "promoter-token",
                "POST",
                b'{"expected_current_sequence":0}',
            )[0]
        )

    workers = [threading.Thread(target=promote) for _ in range(2)]
    for worker in workers:
        worker.start()
    barrier.wait()
    for worker in workers:
        worker.join(timeout=5)
    assert sorted(statuses) == [200, 409]
    status, body = request(
        base, f"/v1/channels/stable/{target}/history", "reader-token"
    )
    assert status == 200
    assert len(json.loads(body)["history"]) == 1


def test_dry_run_validates_without_opening_a_connection(
    distribution: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import publish_runtime

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("dry-run attempted a network connection")

    monkeypatch.setattr(http.client, "HTTPConnection", forbidden)
    result = publish_runtime.main(
        [
            "dry-run",
            "--package",
            str(distribution["package_path"]),
            "--metadata",
            str(distribution["metadata_path"]),
            "--signature",
            str(distribution["signature_path"]),
            "--key",
            str(distribution["public_key"]),
        ]
    )
    assert result == 0


def test_publisher_stages_only_to_explicit_loopback(
    distribution: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import publish_runtime

    monkeypatch.setenv("MPIPS_REFERENCE_PUBLISHER_TOKEN", "publisher-token")
    result = publish_runtime.main(
        [
            "stage",
            "--package",
            str(distribution["package_path"]),
            "--metadata",
            str(distribution["metadata_path"]),
            "--signature",
            str(distribution["signature_path"]),
            "--key",
            str(distribution["public_key"]),
            "--server",
            distribution["base"],
        ]
    )
    assert result == 0
    value = json.loads(distribution["metadata"])
    staged = distribution["server"].storage / "staging" / value["release_id"] / "1"
    assert {path.name for path in staged.iterdir()} == {
        "metadata",
        "signature",
        "package",
    }


def test_publisher_rejects_non_loopback_endpoint() -> None:
    from scripts.publish_runtime import _loopback

    with pytest.raises(ValueError):
        _loopback("http://localhost:1234")
