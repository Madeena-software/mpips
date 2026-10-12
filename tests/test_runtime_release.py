import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


def release(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/runtime_release.py", *args],
        text=True,
        capture_output=True,
    )


@pytest.fixture
def signed_release(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    from scripts.runtime_release import create_metadata, host_compatibility

    package = tmp_path / "mpips-test.tar.gz"
    package.write_bytes(b"test artifact")
    metadata = tmp_path / "release.json"
    create_metadata(
        package,
        metadata,
        "0.1.0",
        "a" * 40,
        42,
        host_compatibility(),
        datetime.now(timezone.utc) + timedelta(days=1),
    )
    key, public = tmp_path / "test-private.pem", tmp_path / "test-public.pem"
    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "Ed25519", "-out", str(key)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["openssl", "pkey", "-in", str(key), "-pubout", "-out", str(public)],
        check=True,
        capture_output=True,
    )
    signature = tmp_path / "release.sig"
    result = release(
        "sign",
        "--metadata",
        str(metadata),
        "--signature",
        str(signature),
        "--key",
        str(key),
    )
    assert result.returncode == 0, result.stderr
    return package, metadata, signature, public


def test_signature_and_package_verification(signed_release: tuple[Path, ...]) -> None:
    package, metadata, signature, public = signed_release
    result = release(
        "verify",
        "--package",
        str(package),
        "--metadata",
        str(metadata),
        "--signature",
        str(signature),
        "--key",
        str(public),
        "--minimum-sequence",
        "42",
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "verified"


@pytest.mark.parametrize(
    "change", ["metadata", "package", "signature", "key", "replay"]
)
def test_tampering_fails_closed(
    signed_release: tuple[Path, ...], change: str, tmp_path: Path
) -> None:
    package, metadata, signature, public = signed_release
    if change == "metadata":
        metadata.write_bytes(
            metadata.read_bytes().replace(b'"sequence":42', b'"sequence":43')
        )
    elif change == "package":
        package.write_bytes(b"substituted artifact")
    elif change == "signature":
        signature.write_bytes(b"invalid")
    elif change == "key":
        subprocess.run(
            [
                "openssl",
                "genpkey",
                "-algorithm",
                "Ed25519",
                "-out",
                str(tmp_path / "other"),
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "openssl",
                "pkey",
                "-in",
                str(tmp_path / "other"),
                "-pubout",
                "-out",
                str(public),
            ],
            check=True,
            capture_output=True,
        )
    result = release(
        "verify",
        "--package",
        str(package),
        "--metadata",
        str(metadata),
        "--signature",
        str(signature),
        "--key",
        str(public),
        "--minimum-sequence",
        "43" if change == "replay" else "42",
    )
    assert result.returncode != 0
    assert "test-private" not in result.stdout + result.stderr


@pytest.mark.parametrize(
    "field,value",
    [
        ("architecture", "aarch64"),
        ("python", "3.99"),
        ("glibc_min", "99.0"),
        ("os_version", "0"),
    ],
)
def test_incompatible_target_rejected(field: str, value: str) -> None:
    from scripts.runtime_release import host_compatibility, validate_compatibility

    target = host_compatibility()
    target[field] = value
    with pytest.raises(ValueError):
        validate_compatibility(target)


def test_metadata_is_immutable(signed_release: tuple[Path, ...]) -> None:
    from scripts.runtime_release import create_metadata, host_compatibility

    package, metadata, _, _ = signed_release
    with pytest.raises(FileExistsError):
        create_metadata(
            package,
            metadata,
            "0.1.0",
            "a" * 40,
            42,
            host_compatibility(),
            datetime.now(timezone.utc) + timedelta(days=1),
        )


@pytest.mark.parametrize("change", ["expired", "interface", "manifest", "target"])
def test_authenticated_but_unusable_metadata_rejected(
    signed_release: tuple[Path, ...], change: str, tmp_path: Path
) -> None:
    from scripts.runtime_release import sign, verify

    package, metadata, signature, public = signed_release
    value = json.loads(metadata.read_text())
    if change == "expired":
        value["expires_at"] = "2000-01-01T00:00:00+00:00"
    elif change == "interface":
        value["interface_version"] = "999"
    elif change == "manifest":
        value["manifest_version"] = "999"
    else:
        value["compatibility"]["architecture"] = "unsupported-cpu"
    metadata.write_text(json.dumps(value))
    signature.unlink()
    sign(metadata, signature, tmp_path / "test-private.pem")
    with pytest.raises(ValueError):
        verify(metadata, signature, public, package, 42)


def test_publication_plan_is_local_and_requires_approval_references(
    signed_release: tuple[Path, ...],
) -> None:
    from scripts.runtime_release import publication_plan, verify

    package, metadata, signature, public = signed_release
    value = verify(metadata, signature, public, package, 42)
    plan = publication_plan(
        value, "https://release.example.invalid/mpips", "LEGAL-EXAMPLE", "INFRA-EXAMPLE"
    )
    assert plan["status"] == "preparation-only-no-network-action"
    assert len(plan["files"]) == 3
    for endpoint in (
        "http://example.invalid",
        "https://user:password@example.invalid",
        "https://example.invalid/?token=secret",
    ):
        with pytest.raises(ValueError):
            publication_plan(value, endpoint, "LEGAL-EXAMPLE", "INFRA-EXAMPLE")
    with pytest.raises(ValueError):
        publication_plan(value, "https://example.invalid", "", "INFRA-EXAMPLE")


def test_only_authenticated_snapshot_is_parsed(
    signed_release: tuple[Path, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    from scripts import runtime_release

    package, metadata, signature, public = signed_release
    real_openssl = runtime_release.openssl

    def mutate_after_verification(*args: str) -> bytes:
        result = real_openssl(*args)
        if "-verify" in args:
            value = json.loads(metadata.read_text())
            value["sequence"] = 99
            metadata.write_text(json.dumps(value))
        return result

    monkeypatch.setattr(runtime_release, "openssl", mutate_after_verification)
    value = runtime_release.verify(metadata, signature, public, package, 42)
    assert value["sequence"] == 42
