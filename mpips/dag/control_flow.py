"""Structured image-pipeline control flow; ordinary DAG ordering remains unchanged."""
from __future__ import annotations

import ast
import math
import operator
import re
from collections import defaultdict
from typing import Any, Callable, Iterator

import numpy as np

from mpips.dag.graph import topological_sort

INACTIVE = object()
CONTROL_TYPES = {"condition", "loop", "branch_merge"}
NAMES = {"iteration", "value", "previous_value", "mean", "std", "entropy",
         "delta_mean", "delta_std", "delta_entropy", "delta_value"}
BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
          ast.Div: operator.truediv, ast.Mod: operator.mod}
COMPARE = {ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt,
           ast.GtE: operator.ge, ast.Eq: operator.eq, ast.NotEq: operator.ne}


def parse_condition(expression: str) -> ast.Expression:
    if not isinstance(expression, str) or not expression.strip() or len(expression) > 512:
        raise ValueError("Condition must contain 1..512 characters.")
    # Keep the public grammar identical to the browser and Laravel validators.
    tokens = re.findall(r"\d+(?:\.\d*)?(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?|[A-Za-z_][A-Za-z_0-9]*|<=|>=|==|!=|[()+*/%<>-]", expression)
    if len(tokens) > 60 or re.sub(r"\s+", "", expression) != "".join(tokens):
        raise ValueError("Condition has invalid syntax or exceeds 60 tokens.")
    if any(token[0].isalpha() or token[0] == "_" for token in tokens if token not in NAMES | {"and", "or", "not", "True", "False"}):
        raise ValueError("Unknown condition variable or invalid literal.")
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise ValueError("Invalid condition expression.") from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > 128:
        raise ValueError("Condition is too complex (maximum 128 syntax nodes).")
    allowed = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp,
               ast.Not, ast.UAdd, ast.USub, ast.BinOp, ast.Compare, ast.Name,
               ast.Load, ast.Constant, *BINARY, *COMPARE)
    for node in nodes:
        if not isinstance(node, allowed):
            raise ValueError("Conditions allow only numbers, variables, arithmetic, comparisons and and/or/not.")
        if isinstance(node, ast.Name) and node.id not in NAMES:
            raise ValueError(f"Unknown condition variable: {node.id}.")
        if isinstance(node, ast.Constant):
            if type(node.value) not in (bool, int, float):
                raise ValueError("Condition literals must be numbers or booleans.")
            try:
                finite = math.isfinite(float(node.value))
            except (OverflowError, ValueError):
                finite = False
            if not finite:
                raise ValueError("Condition literals must be finite.")
    root = tree.body
    if not (isinstance(root, (ast.Compare, ast.BoolOp))
            or isinstance(root, ast.UnaryOp) and isinstance(root.op, ast.Not)
            or isinstance(root, ast.Constant) and type(root.value) is bool):
        raise ValueError("A condition must produce True or False; use a comparison.")
    return tree


def evaluate_condition(expression: str, variables: dict[str, Any]) -> bool:
    tree = parse_condition(expression)

    def visit(node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            value = variables.get(node.id)
            if value is None or not isinstance(value, (int, float, bool, np.number)) or not math.isfinite(float(value)):
                raise ValueError(f"Condition variable '{node.id}' is unavailable or nonfinite; guard previous values with iteration > 1.")
            return value
        if isinstance(node, ast.BoolOp):
            return all(bool(visit(item)) for item in node.values) if isinstance(node.op, ast.And) else any(bool(visit(item)) for item in node.values)
        if isinstance(node, ast.UnaryOp):
            value = visit(node.operand)
            return not value if isinstance(node.op, ast.Not) else (-value if isinstance(node.op, ast.USub) else +value)
        if isinstance(node, ast.BinOp):
            value = BINARY[type(node.op)](visit(node.left), visit(node.right))
            if not math.isfinite(float(value)):
                raise ValueError("Condition arithmetic produced a nonfinite value.")
            return value
        if isinstance(node, ast.Compare):
            left = visit(node.left)
            for op, right_node in zip(node.ops, node.comparators):
                right = visit(right_node)
                if not COMPARE[type(op)](left, right):
                    return False
                left = right
            return True
        raise ValueError("Unsupported condition syntax.")

    try:
        result = visit(tree)
        if not isinstance(result, (bool, np.bool_)):
            raise ValueError("A condition must produce True or False; use a comparison.")
        return bool(result)
    except (ArithmeticError, TypeError, OverflowError) as exc:
        raise ValueError(f"Condition evaluation failed: {exc}") from exc


def measurements(image: np.ndarray) -> dict[str, float]:
    if not isinstance(image, np.ndarray) or image.size == 0 or not np.isfinite(image).all():
        raise ValueError("Control flow requires a nonempty finite image.")
    values = image.astype(np.float64)
    low, high = float(values.min()), float(values.max())
    hist, _ = np.histogram(values, bins=256, range=(low, high if high > low else low + 1))
    probability = hist[hist > 0] / values.size
    return {"mean": float(values.mean()), "std": float(values.std()),
            "entropy": float(-np.sum(probability * np.log2(probability)))}


class PipelinePlan:
    """Validate structured loops, then yield active ordinary nodes for the existing executor.

    A loop owns all nodes reachable from current_image, ending at its feedback/stop
    inputs. Loops may be sequential/disjoint; nested or crossing regions are rejected.
    """

    def __init__(self, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> None:
        self.nodes, self.edges = nodes, edges
        self.node_map = {n["id"]: n for n in nodes}
        self.extended = any(n.get("type") in CONTROL_TYPES for n in nodes)
        self.incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.current_edges: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.loops: dict[str, dict[str, Any]] = {}
        self.max_steps = len(nodes)
        self.visits = 0
        self.on_control: Callable[[str, float], None] | None = None
        if len(self.node_map) != len(nodes):
            raise ValueError("Pipeline node IDs must be unique.")
        for edge in edges:
            if edge.get("source") not in self.node_map or edge.get("target") not in self.node_map:
                raise ValueError("Edge references non-existent node.")
            self.incoming[edge["target"]].append(edge)
            self.outgoing[edge["source"]].append(edge)
        if not self.extended:
            self.order = topological_sort(nodes, edges)
            return
        if len(nodes) > 1000:
            raise ValueError("Control-flow pipelines support at most 1000 nodes.")
        for node in nodes:
            kind, params = node.get("type"), node.get("parameters", {})
            if kind in CONTROL_TYPES and not isinstance(params, dict):
                raise ValueError("Control node parameters must be an object.")
            if kind == "condition":
                parse_condition(params.get("condition", "iteration >= 3"))
            if kind in CONTROL_TYPES:
                seen: set[str] = set()
                allowed = {"loop": {"input_image", "feedback_image", "stop_image"},
                           "condition": {"input_image", "value"},
                           "branch_merge": {"true_image", "false_image"}}[kind]
                for edge in self.incoming[node["id"]]:
                    handle = edge.get("target_handle")
                    if handle not in allowed or handle in seen:
                        raise ValueError(f"Invalid or duplicate control input on {node['id']}.")
                    seen.add(handle)
                if kind == "condition" and "input_image" not in seen:
                    raise ValueError("Condition requires input_image.")
                if kind == "branch_merge" and not seen:
                    raise ValueError("Branch Merge requires at least one input.")
                output_slots = {"loop": {"current_image", "output_image"},
                                "condition": {"true_image", "false_image"},
                                "branch_merge": {"output_image"}}[kind]
                if any(e.get("source_handle") not in output_slots for e in self.outgoing[node["id"]]):
                    raise ValueError(f"Invalid control output on {node['id']}.")
            if kind == "loop":
                limit = params.get("max_iterations", 10)
                if type(limit) is not int or not 1 <= limit <= 100:
                    raise ValueError("Loop max_iterations must be an integer from 1 to 100.")
                if params.get("result_mode", "latest") not in {"latest", "best"}:
                    raise ValueError("Loop result_mode must be latest or best.")
                if params.get("score_metric", "entropy") not in {"mean", "std", "entropy"} or params.get("score_direction", "maximize") not in {"maximize", "minimize"}:
                    raise ValueError("Invalid loop score metric/direction.")
                inputs = {e["target_handle"]: e for e in self.incoming[node["id"]]}
                if "input_image" not in inputs or "feedback_image" not in inputs:
                    raise ValueError("Loop requires one initial input and one feedback input.")
                self.loops[node["id"]] = {"node": node, "inputs": inputs, "limit": limit}
        forward = [e for e in edges if not self.is_return(e)]
        topological_sort(nodes, forward)  # All other cycles remain invalid.
        owner: dict[str, str] = {}
        for loop_id, loop in self.loops.items():
            pending = [e["target"] for e in self.outgoing[loop_id] if e.get("source_handle") == "current_image"]
            body: set[str] = set()
            while pending:
                nid = pending.pop()
                if nid in body:
                    continue
                if nid == loop_id or self.node_map[nid].get("type") in {"loop", "input", "input_npz", "output", "output_npz"}:
                    raise ValueError("Nested loops and IO within loop bodies are not supported; route exits through loop.output_image.")
                if nid in owner and owner[nid] != loop_id:
                    raise ValueError("Loop regions cannot overlap.")
                owner[nid] = loop_id
                body.add(nid)
                pending.extend(e["target"] for e in self.outgoing[nid] if not self.is_return(e))
            if not body:
                raise ValueError("Loop current_image must feed a nonempty body.")
            for handle in ("feedback_image", "stop_image"):
                if handle in loop["inputs"] and loop["inputs"][handle]["source"] not in body:
                    raise ValueError("Loop return must come from its own body.")
            for nid in body:
                if any(self.is_return(e) and e["target"] != loop_id for e in self.outgoing[nid]):
                    raise ValueError("Cross-loop return edges are not allowed.")
                if any(e["source"] == loop_id and e.get("source_handle") != "current_image" for e in self.incoming[nid]):
                    raise ValueError("Loop body reads current_image, not output_image.")
            loop["body"] = body
            loop["order"] = topological_sort([n for n in nodes if n["id"] in body], [e for e in forward if e["source"] in body and e["target"] in body])
        self.owner = owner
        main = [n for n in nodes if n["id"] not in owner]
        coarse = []
        for edge in forward:
            src, dst = owner.get(edge["source"], edge["source"]), owner.get(edge["target"], edge["target"])
            if src != dst:
                coarse.append({"source": src, "target": dst})
        self.order = topological_sort(main, coarse)
        self.max_steps = len(main) + sum(len(loop["body"]) * loop["limit"] for loop in self.loops.values())
        if self.max_steps > 10000:
            raise ValueError("Pipeline exceeds the 10000 stage-evaluation limit.")

    def is_return(self, edge: dict[str, Any]) -> bool:
        return self.node_map[edge["target"]].get("type") == "loop" and edge.get("target_handle") in {"feedback_image", "stop_image"}

    def _slots(self, node: dict[str, Any]) -> list[str]:
        kind = node.get("type")
        if kind not in CONTROL_TYPES and isinstance(node.get("outputs"), list) and node["outputs"]:
            return [s["name"] for s in node["outputs"]]
        return {"condition": ["true_image", "false_image"], "loop": ["current_image", "output_image"],
                "ent": ["entropy_score"], "eme": ["eme_score"], "cii": ["cii_score"], "brisque": ["brisque_score"]}.get(kind, ["output_image"])

    def _write(self, node: dict[str, Any], outputs: dict[str, Any], reference: Any, context: dict[Any, Any], refs: dict[Any, Any]) -> None:
        for slot in self._slots(node):
            key = (node["id"], slot)
            context[key] = outputs.get(slot, INACTIVE)
            refs[key] = reference

    def _scope(self, order: list[dict[str, Any]], context: dict[Any, Any], refs: dict[Any, Any], iteration: int, history: dict[str, dict[str, Any]]) -> Iterator[dict[str, Any]]:
        for node in order:
            self.visits += 1
            if self.on_control and node.get("type") in CONTROL_TYPES:
                self.on_control(node["id"], min(99.0, round((self.visits - 1) / max(1, self.max_steps) * 100, 2)))
            nid, kind = node["id"], node.get("type")
            if kind == "loop":
                yield from self._loop(nid, context, refs)
                continue
            incoming = self.incoming[nid]
            active = [e for e in incoming if context.get((e["source"], e.get("source_handle"))) is not INACTIVE]
            if len(active) != len(incoming) and kind not in {"merge", "branch_merge"}:
                self._write(node, {}, None, context, refs)
                continue
            if incoming and not active:
                self._write(node, {}, None, context, refs)
                continue
            inputs = {}
            for edge in active:
                key = (edge["source"], edge.get("source_handle"))
                if key not in context:
                    raise ValueError(f"Missing connection for {nid}:{edge.get('target_handle')}")
                inputs[edge["target_handle"]] = context[key]
            if kind == "branch_merge":
                images = [v for v in inputs.values() if isinstance(v, np.ndarray)]
                if len(images) != 1:
                    raise ValueError("Branch Merge needs exactly one active image branch.")
                self._write(node, {"output_image": images[0]}, refs.get((active[0]["source"], active[0]["source_handle"])), context, refs)
            elif kind == "condition":
                image = inputs.get("input_image")
                stats = measurements(image)
                previous = history.get(nid, {})
                values = {"iteration": iteration, **stats}
                for name in ("mean", "std", "entropy"):
                    if name in previous:
                        values["delta_" + name] = abs(stats[name] - previous[name])
                if "value" in inputs:
                    scalar = inputs["value"]
                    if not isinstance(scalar, (int, float, np.number)) or not math.isfinite(float(scalar)):
                        raise ValueError("Condition value must be a finite scalar.")
                    values["value"] = float(scalar)
                    if "value" in previous:
                        values["previous_value"] = previous["value"]
                        values["delta_value"] = abs(float(scalar) - previous["value"])
                decision = evaluate_condition(node.get("parameters", {}).get("condition", "iteration >= 3"), values)
                history[nid] = {**stats, **({"value": values["value"]} if "value" in values else {})}
                image_edge = next(e for e in active if e["target_handle"] == "input_image")
                reference = refs.get((image_edge["source"], image_edge["source_handle"]))
                self._write(node, {"true_image" if decision else "false_image": image}, reference, context, refs)
                self.events.append({"node_id": nid, "iteration": iteration, "branch": "true" if decision else "false"})
            else:
                self.current_edges = active
                yield node

    def _loop(self, nid: str, context: dict[Any, Any], refs: dict[Any, Any]) -> Iterator[dict[str, Any]]:
        loop = self.loops[nid]
        seed_edge = loop["inputs"]["input_image"]
        seed_key = (seed_edge["source"], seed_edge["source_handle"])
        if context.get(seed_key) is INACTIVE:
            self._write(loop["node"], {}, None, context, refs)
            return
        current = context.get(seed_key)
        measurements(current)
        current = current.copy()
        current_ref = refs.get(seed_key)
        params = loop["node"].get("parameters", {})
        history: dict[str, dict[str, Any]] = {}
        best, best_ref, best_score = None, None, None
        reason = "iteration_limit"
        for iteration in range(1, loop["limit"] + 1):
            for member in loop["order"]:
                for key in [k for k in context if k[0] == member["id"]]:
                    context.pop(key, None); refs.pop(key, None)
            context[(nid, "current_image")] = current
            refs[(nid, "current_image")] = current_ref
            yield from self._scope(loop["order"], context, refs, iteration, history)
            returned = []
            for handle in ("stop_image", "feedback_image"):
                edge = loop["inputs"].get(handle)
                if edge:
                    key = (edge["source"], edge["source_handle"])
                    value = context.get(key, INACTIVE)
                    if value is not INACTIVE:
                        measurements(value)
                        returned.append((handle, value, refs.get(key)))
            if len(returned) != 1:
                raise ValueError("Loop must receive exactly one active stop or feedback image per iteration.")
            handle, candidate, reference = returned[0]
            score = measurements(candidate)[params.get("score_metric", "entropy")]
            better = best_score is None or (score > best_score if params.get("score_direction", "maximize") == "maximize" else score < best_score)
            if params.get("result_mode", "latest") == "latest" or better:
                best, best_ref, best_score = candidate.copy(), reference, score
            if handle == "stop_image":
                reason = "condition"
                break
            current, current_ref = candidate.copy(), reference
        self._write(loop["node"], {"output_image": best}, best_ref, context, refs)
        self.events.append({"node_id": nid, "iterations": iteration, "stop_reason": reason,
                            "result_mode": params.get("result_mode", "latest"), "selected_score": best_score})

    def steps(self, context: dict[Any, Any], refs: dict[Any, Any]) -> Iterator[dict[str, Any]]:
        self.events = []
        self.visits = 0
        if not self.extended:
            for node in self.order:
                self.current_edges = self.incoming[node["id"]]
                yield node
            return
        yield from self._scope(self.order, context, refs, 1, {})
