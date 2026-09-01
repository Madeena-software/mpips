from collections import Counter

import pytest

from scripts.check_mypy_regressions import compare_diagnostics, parse_mypy_output


def diagnostic(
    path: str = "mpips/example.py",
    line: int = 1,
    message: str = "bad",
    code: str = "arg-type",
) -> str:
    return f"{path}:{line}: error: {message} [{code}]"


def test_identical_and_moved_diagnostics_pass() -> None:
    base = parse_mypy_output(diagnostic(line=10), "")
    candidate = parse_mypy_output(diagnostic(line=99), "")
    assert compare_diagnostics(base, candidate) == Counter()


def test_removed_diagnostic_passes() -> None:
    base = parse_mypy_output(diagnostic(), "")
    candidate = parse_mypy_output("", "")
    assert compare_diagnostics(base, candidate) == Counter()


def test_new_diagnostic_fails() -> None:
    base = parse_mypy_output("", "")
    candidate = parse_mypy_output(diagnostic(), "")
    assert compare_diagnostics(base, candidate) == Counter(
        {("mpips/example.py", "arg-type", "bad"): 1}
    )


def test_increased_duplicate_count_fails() -> None:
    base = parse_mypy_output(diagnostic(), "")
    candidate = parse_mypy_output(diagnostic() + "\n" + diagnostic(line=2), "")
    assert (
        compare_diagnostics(base, candidate)[("mpips/example.py", "arg-type", "bad")]
        == 1
    )


@pytest.mark.parametrize(
    "candidate",
    [
        diagnostic(message="different"),
        diagnostic(code="return-value"),
    ],
)
def test_changed_message_or_code_fails(candidate: str) -> None:
    base = parse_mypy_output(diagnostic(), "")
    assert compare_diagnostics(base, parse_mypy_output(candidate, ""))


def test_new_file_diagnostic_fails() -> None:
    base = parse_mypy_output("", "")
    candidate = parse_mypy_output(diagnostic(path="tests/new.py"), "")
    assert compare_diagnostics(base, candidate)


def test_unparseable_error_fails() -> None:
    with pytest.raises(ValueError, match="Unparseable"):
        parse_mypy_output("unparseable: error: bad", "")


def test_execution_failure_is_reported() -> None:
    with pytest.raises(RuntimeError, match="mypy execution failed"):
        parse_mypy_output("", "mypy crashed", returncode=2)
