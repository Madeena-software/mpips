"""Build and locally qualify an offline wheelhouse from an immutable Git revision."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from runtime_release import create_metadata, host_compatibility, sha256

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def build(output: Path, commit: str, sequence: int) -> Path:
    if sequence <= 0:
        raise ValueError("Positive candidate sequence required")
    target = host_compatibility()
    if target["python"] != "3.12":
        raise ValueError("Build with Python 3.12")
    revision = subprocess.check_output(
        ["git", "rev-parse", "--verify", f"{commit}^{{commit}}"], cwd=ROOT, text=True
    ).strip()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mpips-build-") as scratch:
        stage = Path(scratch)
        source = stage / "source"
        source.mkdir()
        source_archive = stage / "source.tar.gz"
        with source_archive.open("wb") as stream:
            subprocess.run(
                [
                    "git",
                    "archive",
                    "--format=tar.gz",
                    revision,
                    "mpips",
                    "pyproject.toml",
                    "uv.lock",
                    "THIRD_PARTY_NOTICES.md",
                    "LICENSES",
                    "scripts/grabber_smoke.py",
                ],
                cwd=ROOT,
                stdout=stream,
                check=True,
            )
        with tarfile.open(source_archive) as archive:
            archive.extractall(source, filter="data")
        version = tomllib.loads((source / "pyproject.toml").read_text())["project"][
            "version"
        ]
        identity = (
            f"mpips-{version}-{revision}-{target['os']}{target['os_version']}-"
            f"{target['architecture']}-py312"
        )
        bundle = stage / identity
        bundle.mkdir()
        wheels = bundle / "wheels"
        wheels.mkdir()
        dependencies = bundle / "requirements.txt"
        run(["uv", "lock", "--check"], source)
        run(
            [
                "uv",
                "export",
                "--frozen",
                "--no-dev",
                "--no-emit-project",
                "--format",
                "requirements.txt",
                "--output-file",
                str(dependencies),
            ],
            source,
        )
        run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--require-hashes",
                "--only-binary=:all:",
                "--dest",
                str(wheels),
                "-r",
                str(dependencies),
            ],
            source,
        )
        run(
            [
                "uv",
                "build",
                "--wheel",
                "--python",
                sys.executable,
                "--out-dir",
                str(wheels),
                str(source),
            ],
            source,
        )
        (project_wheel,) = wheels.glob("mpips-*.whl")
        with dependencies.open("a") as stream:
            stream.write(f"\nmpips=={version} --hash=sha256:{sha256(project_wheel)}\n")
        (bundle / "source.tar.gz").write_bytes(source_archive.read_bytes())
        (bundle / "THIRD_PARTY_NOTICES.md").write_bytes(
            (source / "THIRD_PARTY_NOTICES.md").read_bytes()
        )
        (bundle / "LICENSES").mkdir()
        for license_file in (source / "LICENSES").iterdir():
            if license_file.is_file():
                (bundle / "LICENSES" / license_file.name).write_bytes(
                    license_file.read_bytes()
                )
        (bundle / "build.json").write_text(
            json.dumps(
                {
                    "commit_sha": revision,
                    "runtime_version": version,
                    "interface_version": "1",
                    "compatibility": target,
                    "qualification": "synthetic-only",
                },
                indent=2,
            )
            + "\n"
        )
        (bundle / "INSTALL.txt").write_text(
            "Candidate only: licensing/infrastructure/clinical approvals required.\n"
            "Verify signed release metadata and tar hash/size before extraction.\n"
            "Preinstall Python 3.12 with venv/ensurepip through an approved "
            "OS channel.\n"
            "python3.12 -m venv /absolute/path/to/new-version/runtime\n"
            "/absolute/path/to/new-version/runtime/bin/python -m pip install "
            "--no-index --only-binary=:all: --require-hashes "
            "--find-links /absolute/path/to/bundle/wheels "
            "-r /absolute/path/to/bundle/requirements.txt\n"
            "Keep data, calibration and configuration outside this version directory.\n"
        )
        package = output / f"{identity}.tar.gz"
        metadata = output / f"{identity}.release.json"
        if package.exists() or metadata.exists():
            raise FileExistsError("Immutable candidate already exists")
        # Qualify the actual installed wheels without source-tree imports or indexes.
        env_dir = stage / "verify-runtime"
        run([sys.executable, "-m", "venv", str(env_dir)], stage)
        python = env_dir / "bin" / "python"
        run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--only-binary=:all:",
                "--require-hashes",
                "--find-links",
                str(wheels),
                "-r",
                str(dependencies),
            ],
            stage,
        )
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        subprocess.run(
            [
                str(python),
                str(source / "scripts/grabber_smoke.py"),
                "--runtime",
                str(env_dir / "bin/mpips-runtime"),
            ],
            cwd=stage,
            env=env,
            check=True,
        )
        with tempfile.NamedTemporaryFile(
            dir=output, prefix=".candidate-", delete=False
        ) as stream:
            temporary = Path(stream.name)
        try:
            with tarfile.open(temporary, "w:gz") as archive:
                archive.add(bundle, arcname=identity)
            os.link(temporary, package)
        finally:
            temporary.unlink()
        create_metadata(
            package,
            metadata,
            version,
            revision,
            sequence,
            target,
            datetime.now(timezone.utc) + timedelta(days=7),
        )
        print(
            json.dumps(
                {
                    "package": str(package),
                    "metadata": str(metadata),
                    "commit_sha": revision,
                    "qualification": "synthetic-only",
                }
            )
        )
        return package


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", default="HEAD")
    parser.add_argument(
        "--sequence",
        type=int,
        required=True,
        help="Candidate sequence; release owner assigns production sequences",
    )
    args = parser.parse_args()
    build(args.output, args.commit, args.sequence)


if __name__ == "__main__":
    main()
