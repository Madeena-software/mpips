#!/usr/bin/env python3
"""Validate one immutable cross-agent task contract using the standard library."""

# antigravity-code-agent-template:managed

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path
from typing import Any


NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MODEL_PATTERN = re.compile(r"^[^\s`/]+/[^\s`/]+(?:/[^\s`/]+)*$")
INPUT_NAME_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
INPUT_LINE_PATTERN = re.compile(
    r"^-\s+`(?P<name>[^`]+)`\s+"
    r"\((?P<mode>required|optional)(?:,\s*default:\s*(?P<default>[^)]+))?\):\s+.+$"
)
PLACEHOLDER_PATTERN = re.compile(r"(?<!\$)\$([A-Z][A-Z0-9_]*)")
UNRESOLVED_PATTERN = re.compile(r"\{\{[^{}\n]+\}\}|\b(?:TBD|REPLACE_ME)\b", re.I)
MODEL_PREFERENCE_PATTERN = re.compile(r"^\s+([0-9]+)\.\s+`([^`\r\n]+)`\s*$")
CAPABILITY_PATTERN = re.compile(r"^\s+-\s+`([a-z0-9]+(?:-[a-z0-9]+)*)`\s*$")
MODE_PATTERN = re.compile(r"(?m)^- Mode:\s+`(single-pass|agentic-loop)`\s*$")
ITERATION_PATTERN = re.compile(r"(?m)^- Maximum iterations:\s+`([0-9]+)`\s*$")
APPROVAL_PATTERN = re.compile(r"(?m)^- Approval gates:\s+\S.*$")
ACCEPTANCE_PATTERN = re.compile(r"(?m)^- \[ \]\s+\S.*$")
METHOD_PATTERN = re.compile(r"(?m)^- Method:\s+\S.*$")
EXPECTED_PATTERN = re.compile(r"(?m)^- Expected result:\s+\S.*$")
MUTABLE_HEADING_PATTERN = re.compile(
    r"(?im)^##\s+(?:progress|results|current status|run state|execution log|"
    r"hidden reasoning|transcript)\s*$"
)

TASK_SECTIONS = (
    "Objective",
    "Runtime requirements",
    "Runtime inputs",
    "Context and evidence",
    "Scope and constraints",
    "Execution policy",
    "Execution procedure",
    "Acceptance criteria",
    "Verification",
    "Output",
)
TASK_OUTCOMES = {"succeeded", "failed", "blocked", "awaiting-approval", "exhausted"}
TASK_TEMPLATE_MARKERS = (
    "describe the immutable cross-agent assignment",
    "state the observable result for",
    "identify evidence the executing agent",
    "describe actions requiring approval",
    "define an observable result for",
    "define the smallest relevant command",
    "state the successful outcome",
)


def markdown_section(text: str, heading: str) -> str | None:
    match = re.search(rf"(?ms)^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)", text)
    return match.group(1).strip() if match else None


def clean_scalar(value: str, path: Path, line_number: int, errors: list[str]) -> str:
    value = value.strip()
    if not value:
        return ""
    if value[0:1] in {"'", '"'}:
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            errors.append(f"{path}:{line_number}: invalid quoted YAML scalar")
            return value
        if not isinstance(parsed, str):
            errors.append(f"{path}:{line_number}: frontmatter scalars must be strings")
            return str(parsed)
        return parsed
    if re.search(r":\s", value):
        errors.append(f"{path}:{line_number}: quote YAML scalars containing ': '")
    if value.startswith(("[", "{", "&", "*", "!")):
        errors.append(f"{path}:{line_number}: unsupported complex YAML scalar")
    return value


def parse_frontmatter(path: Path) -> tuple[dict[str, Any], str, list[str]]:
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {}, "", [f"{path}: file is not valid UTF-8"]
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text, [f"{path}: missing opening YAML frontmatter delimiter"]
    try:
        closing = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return {}, text, [f"{path}: missing closing YAML frontmatter delimiter"]

    metadata: dict[str, Any] = {}
    for index, line in enumerate(lines[1:closing], 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")) or ":" not in line:
            errors.append(f"{path}:{index}: invalid task frontmatter line")
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if not key:
            errors.append(f"{path}:{index}: empty frontmatter key")
        elif key in metadata:
            errors.append(f"{path}:{index}: duplicate frontmatter field {key!r}")
        else:
            metadata[key] = clean_scalar(raw_value, path, index, errors)
    body = "\n".join(lines[closing + 1 :]).strip()
    return metadata, body, errors


def validate_task(
    path: Path,
    *,
    template: bool | None = None,
    task_root: Path | None = None,
) -> list[str]:
    path = path.resolve()
    errors: list[str] = []
    if not path.is_file():
        return [f"{path}: task file does not exist"]
    if path.suffix.lower() != ".md":
        errors.append(f"{path}: task contracts must use Markdown")
    template = path.name == "_template.md" if template is None else template
    if task_root is not None:
        task_root = task_root.resolve()
        if path.parent != task_root:
            errors.append(f"{path}: task files must be directly under {task_root}")

    text = path.read_text(encoding="utf-8")
    metadata, body, frontmatter_errors = parse_frontmatter(path)
    errors.extend(frontmatter_errors)
    allowed = {"name", "description", "version"}
    for field in sorted(set(metadata) - allowed):
        errors.append(f"{path}: unsupported task frontmatter field {field!r}")
    name = metadata.get("name", "")
    description = metadata.get("description", "")
    version_text = str(metadata.get("version", ""))
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name) or len(name) > 64:
        errors.append(f"{path}: invalid task name")
    if not isinstance(description, str) or not description or len(description) > 1024:
        errors.append(f"{path}: description must contain 1-1024 characters")
    version = int(version_text) if re.fullmatch(r"[1-9][0-9]*", version_text) else 0
    if not version:
        errors.append(f"{path}: version must be a positive integer")
    if not template and name and version and path.name != f"{name}-v{version}.md":
        errors.append(f"{path}: filename must be {name}-v{version}.md")
    if not body:
        errors.append(f"{path}: task body must not be empty")
    for heading in TASK_SECTIONS:
        section = markdown_section(text, heading)
        if section is None:
            errors.append(f"{path}: missing required section {heading!r}")
        elif not section:
            errors.append(f"{path}: section {heading!r} must not be empty")

    runtime = markdown_section(text, "Runtime requirements") or ""
    lines = runtime.splitlines()
    cap_indexes = [i for i, line in enumerate(lines) if line == "- Required capabilities:"]
    capabilities: list[str] = []
    if len(cap_indexes) != 1:
        errors.append(f"{path}: Runtime requirements must declare Required capabilities once")
    else:
        for line in lines[cap_indexes[0] + 1 :]:
            match = CAPABILITY_PATTERN.fullmatch(line)
            if not match:
                break
            capabilities.append(match.group(1))
        if not capabilities:
            errors.append(f"{path}: at least one required capability is required")
        elif len(capabilities) != len(set(capabilities)):
            errors.append(f"{path}: required capabilities must be unique")

    preference_indexes = [
        i for i, line in enumerate(lines) if line.startswith("- Ordered model preferences:")
    ]
    preferences: list[str] = []
    if len(preference_indexes) != 1:
        errors.append(f"{path}: Ordered model preferences must be declared once")
    else:
        index = preference_indexes[0]
        value = lines[index].split(":", 1)[1].strip()
        if value != "None.":
            if value:
                errors.append(f"{path}: model preferences must be a numbered list or None.")
            else:
                expected = 1
                for line in lines[index + 1 :]:
                    if line.startswith("- Require preferred model:"):
                        break
                    if not line.strip():
                        continue
                    match = MODEL_PREFERENCE_PATTERN.fullmatch(line)
                    if not match:
                        errors.append(f"{path}: invalid model preference line {line!r}")
                        continue
                    if int(match.group(1)) != expected:
                        errors.append(f"{path}: model preference numbering must be contiguous")
                    expected += 1
                    model = match.group(2)
                    if not MODEL_PATTERN.fullmatch(model):
                        errors.append(f"{path}: invalid provider/model preference {model!r}")
                    preferences.append(model)
                if not preferences:
                    errors.append(f"{path}: model preferences list must not be empty")
    require_matches = re.findall(
        r"(?m)^- Require preferred model:\s+`(true|false)`\s*$", runtime
    )
    if len(require_matches) != 1:
        errors.append(f"{path}: Require preferred model must be true or false exactly once")
    elif require_matches[0] == "true" and not preferences:
        errors.append(f"{path}: required preferred model needs at least one preference")
    if len(preferences) != len(set(preferences)):
        errors.append(f"{path}: model preferences must be unique")

    declared: set[str] = set()
    inputs = markdown_section(text, "Runtime inputs")
    if inputs is not None:
        input_lines = [line.strip() for line in inputs.splitlines() if line.strip()]
        if input_lines != ["None."]:
            if "None." in input_lines:
                errors.append(f"{path}: Runtime inputs cannot mix None. and declarations")
            for line in input_lines:
                match = INPUT_LINE_PATTERN.fullmatch(line)
                if not match:
                    errors.append(f"{path}: invalid runtime input declaration {line!r}")
                    continue
                input_name = match.group("name")
                mode = match.group("mode")
                default = match.group("default")
                if not INPUT_NAME_PATTERN.fullmatch(input_name):
                    errors.append(f"{path}: invalid runtime input name {input_name!r}")
                if input_name in declared:
                    errors.append(f"{path}: duplicate runtime input {input_name!r}")
                declared.add(input_name)
                if mode == "required" and default is not None:
                    errors.append(f"{path}: required input cannot declare a default")
                if mode == "optional" and not default:
                    errors.append(f"{path}: optional input must declare a default")
    placeholders = set(PLACEHOLDER_PATTERN.findall(text))
    for name in sorted(placeholders - declared):
        errors.append(f"{path}: placeholder references undeclared input {name!r}")
    for name in sorted(declared - placeholders):
        errors.append(f"{path}: declared input {name!r} is never referenced")

    if not template and UNRESOLVED_PATTERN.search(text):
        errors.append(f"{path}: unresolved placeholder syntax is not allowed")
    if not template:
        lowered = text.lower()
        for marker in TASK_TEMPLATE_MARKERS:
            if marker in lowered:
                errors.append(f"{path}: unresolved template text {marker!r}")
    policy = markdown_section(text, "Execution policy") or ""
    modes = MODE_PATTERN.findall(policy)
    iterations = ITERATION_PATTERN.findall(policy)
    if len(modes) != 1 or len(iterations) != 1:
        errors.append(f"{path}: Execution policy needs one mode and iteration count")
    elif int(iterations[0]) < 1 or (
        modes[0] == "single-pass" and int(iterations[0]) != 1
    ):
        errors.append(f"{path}: invalid execution iteration policy")
    if len(APPROVAL_PATTERN.findall(policy)) != 1:
        errors.append(f"{path}: Execution policy must declare approval gates once")
    acceptance = markdown_section(text, "Acceptance criteria") or ""
    if not ACCEPTANCE_PATTERN.search(acceptance):
        errors.append(f"{path}: at least one unchecked acceptance criterion is required")
    verification = markdown_section(text, "Verification") or ""
    if len(METHOD_PATTERN.findall(verification)) != 1 or len(
        EXPECTED_PATTERN.findall(verification)
    ) != 1:
        errors.append(f"{path}: Verification needs one Method and Expected result")
    output = markdown_section(text, "Output") or ""
    missing = sorted(outcome for outcome in TASK_OUTCOMES if f"`{outcome}`" not in output)
    if missing:
        errors.append(f"{path}: Output is missing outcomes {missing}")
    if MUTABLE_HEADING_PATTERN.search(text):
        errors.append(f"{path}: mutable run-state or transcript heading is not allowed")
    return errors


def find_task_root(path: Path) -> Path | None:
    for parent in path.resolve().parents:
        if parent.name == "tasks" and parent.parent.name == ".agents":
            return parent
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", type=Path, help="Task Markdown file under .agents/tasks.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = args.task.resolve()
    task_root = find_task_root(path)
    if task_root is None:
        errors = [f"{path}: task must be under .agents/tasks"]
    else:
        errors = validate_task(path, task_root=task_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Task validation failed with {len(errors)} error(s).")
        return 1
    print(f"Task contract is valid: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
