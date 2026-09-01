"""Fail CI when a candidate introduces or increases mypy diagnostics."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Iterable

Diagnostic = tuple[str, str, str]
_ERROR = re.compile(
    r"^(?P<path>.+?):\d+(?::\d+)?: error: (?P<message>.+?) \[(?P<code>[\w-]+)\]$"
)


def parse_mypy_output(
    stdout: str,
    stderr: str,
    root: str | Path = "",
    *,
    returncode: int = 0,
) -> Counter[Diagnostic]:
    if returncode not in (0, 1):
        raise RuntimeError(
            f"mypy execution failed with exit code {returncode}: {stderr}"
        )

    base = Path(root).resolve() if root else None
    diagnostics: Counter[Diagnostic] = Counter()
    for line in (stdout + "\n" + stderr).splitlines():
        if ": error:" not in line:
            continue
        match = _ERROR.match(line.strip())
        if match is None:
            raise ValueError(f"Unparseable mypy error: {line}")
        path = Path(match.group("path"))
        if base is not None and path.is_absolute():
            try:
                path = path.relative_to(base)
            except ValueError:
                pass
        message = re.sub(r"\s+", " ", match.group("message")).strip()
        diagnostics[(path.as_posix(), match.group("code"), message)] += 1
    if returncode == 1 and not diagnostics:
        raise RuntimeError(
            "mypy execution failed: exit code 1 without parseable errors"
        )
    return diagnostics


def compare_diagnostics(
    base: Counter[Diagnostic], candidate: Counter[Diagnostic]
) -> Counter[Diagnostic]:
    return candidate - base


def _run_mypy(cwd: Path) -> Counter[Diagnostic]:
    command = shlex.split(os.environ.get("MYPY_COMMAND", "uv run mypy mpips tests"))
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    return parse_mypy_output(
        result.stdout, result.stderr, cwd, returncode=result.returncode
    )


def _git(*args: str, cwd: Path) -> None:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--candidate-ref", default="HEAD")
    args = parser.parse_args(list(argv) if argv is not None else None)
    repo = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="mpips-mypy-base-") as raw_temp:
        base_worktree = Path(raw_temp) / "base"
        _git("worktree", "add", "--detach", str(base_worktree), args.base_ref, cwd=repo)
        try:
            base = _run_mypy(base_worktree)
            candidate = _run_mypy(repo)
        finally:
            _git("worktree", "remove", "--force", str(base_worktree), cwd=repo)

    excess = compare_diagnostics(base, candidate)
    reduced = sum((base - candidate).values())
    print(f"BASE_MYPY_ERRORS={sum(base.values())}")
    print(f"CANDIDATE_MYPY_ERRORS={sum(candidate.values())}")
    print(f"NEW_MYPY_ERRORS={sum(excess.values())}")
    print(f"REDUCED_MYPY_ERRORS={reduced}")
    if excess:
        print("New or increased mypy diagnostics:")
        for diagnostic, count in sorted(excess.items()):
            print(f"{count}x {diagnostic[0]}: error: {diagnostic[2]} [{diagnostic[1]}]")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
