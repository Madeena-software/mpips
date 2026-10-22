"""Output IQA comparisons use the source branch, never an unrelated input."""

import unittest
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np

from mpips.dag.executor import DAGExecutor
from mpips.dag.registry import get_node_class
from mpips.iqa import calculate_all_metrics


def edge(
    source: str,
    target: str,
    source_handle: str = "output_image",
    target_handle: str = "input_image",
) -> dict[str, str]:
    return {
        "source": source,
        "target": target,
        "source_handle": source_handle,
        "target_handle": target_handle,
    }


class IqaComparisonTests(unittest.TestCase):
    def run_graph(
        self,
        nodes: list[dict[str, str]],
        edges: list[dict[str, str]],
        images: list[np.ndarray],
        custom_nodes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        inputs = {
            node["id"]: {"key": node["id"] + ".png"}
            for node in nodes
            if node["type"] == "input"
        }
        custom_nodes = custom_nodes or {}
        with (
            patch("mpips.dag.executor.cv2.imread", side_effect=images),
            patch(
                "mpips.dag.executor.get_node_class",
                side_effect=lambda kind: custom_nodes.get(kind) or get_node_class(kind),
            ),
        ):
            return DAGExecutor(MagicMock()).execute(
                {"nodes": nodes, "edges": edges}, inputs, {"prefix": "outputs/"}
            )["outputs"]

    def test_each_output_uses_its_own_original_input(self) -> None:
        a = np.arange(256, dtype=np.uint8).reshape(16, 16)
        b = np.full((16, 16), 100, dtype=np.uint8)
        outputs = self.run_graph(
            [
                {"id": "a", "type": "input"},
                {"id": "b", "type": "input"},
                {"id": "oa", "type": "output"},
                {"id": "ob", "type": "output"},
            ],
            [edge("a", "oa"), edge("b", "ob")],
            [a, b],
        )
        for node, image in [("oa", a), ("ob", b)]:
            expected = calculate_all_metrics(image, image)
            quality = outputs[node]["quality_assessment"]
            self.assertEqual(quality["before"], expected)
            self.assertEqual({k: quality[k] for k in expected}, expected)

    def test_baseline_survives_processing_and_in_place_mutation(self) -> None:
        class MutatingNode:
            def execute(
                self, inputs: dict[str, Any], params: dict[str, Any]
            ) -> dict[str, Any]:
                image = inputs["input_image"]
                image[:] = image // 2
                return {"output_image": image}

        image = np.arange(256, dtype=np.uint8).reshape(16, 16)
        original = image.copy()
        outputs = self.run_graph(
            [
                {"id": "a", "type": "input"},
                {"id": "mutate", "type": "mutate"},
                {"id": "out", "type": "output"},
            ],
            [edge("a", "mutate"), edge("mutate", "out")],
            [image],
            {"mutate": MutatingNode},
        )
        quality = outputs["out"]["quality_assessment"]
        self.assertEqual(quality["before"], calculate_all_metrics(original, original))
        expected_after = calculate_all_metrics(original // 2, original)
        self.assertEqual({k: quality[k] for k in expected_after}, expected_after)
        self.assertLess(quality["cii"], quality["before"]["cii"])

    def test_generated_image_has_no_invented_original(self) -> None:
        class GeneratorNode:
            def execute(
                self, inputs: dict[str, Any], params: dict[str, Any]
            ) -> dict[str, Any]:
                return {"output_image": np.ones((16, 16), dtype=np.uint8)}

        output = self.run_graph(
            [{"id": "gen", "type": "generate"}, {"id": "out", "type": "output"}],
            [edge("gen", "out")],
            [],
            {"generate": GeneratorNode},
        )
        quality = output["out"]["quality_assessment"]
        self.assertNotIn("before", quality)
        self.assertIsNone(quality["cii"])
        self.assertEqual(set(quality), {"brisque", "cii", "entropy", "eme"})

    def test_ambiguous_merge_does_not_choose_an_arbitrary_original(self) -> None:
        class MergeNode:
            def execute(
                self, inputs: dict[str, Any], params: dict[str, Any]
            ) -> dict[str, Any]:
                return {"output_image": np.maximum(inputs["a"], inputs["b"])}

        image = np.arange(256, dtype=np.uint8).reshape(16, 16)
        output = self.run_graph(
            [
                {"id": "a", "type": "input"},
                {"id": "b", "type": "input"},
                {"id": "merge", "type": "merge"},
                {"id": "out", "type": "output"},
            ],
            [
                edge("a", "merge", target_handle="a"),
                edge("b", "merge", target_handle="b"),
                edge("merge", "out"),
            ],
            [image, image // 2],
            {"merge": MergeNode},
        )
        quality = output["out"]["quality_assessment"]
        self.assertNotIn("before", quality)
        self.assertIsNone(quality["cii"])

    def test_named_npz_slot_uses_its_own_original_pixels(self) -> None:
        raw = np.arange(256, dtype=np.uint8).reshape(16, 16)
        processed = raw // 2
        storage = MagicMock()

        def download(source: str, path: str, **kwargs: Any) -> None:
            np.savez(path, rawimage=raw, processedimage=processed)

        storage.download_image.side_effect = download
        outputs = DAGExecutor(storage).execute(
            {
                "nodes": [
                    {"id": "a", "type": "input_npz"},
                    {"id": "out", "type": "output"},
                ],
                "edges": [edge("a", "out", source_handle="processedimage")],
            },
            {"a": {"key": "capture.npz"}},
            {"prefix": "outputs/"},
        )["outputs"]
        self.assertEqual(
            outputs["out"]["quality_assessment"]["before"],
            calculate_all_metrics(processed, processed),
        )

    def test_npz_output_uses_the_source_of_the_measured_slot(self) -> None:
        a = np.arange(256, dtype=np.uint8).reshape(16, 16)
        b = np.full((16, 16), 80, dtype=np.uint8)
        output = self.run_graph(
            [
                {"id": "a", "type": "input"},
                {"id": "b", "type": "input"},
                {"id": "out", "type": "output_npz"},
            ],
            [
                edge("a", "out", target_handle="processedimage"),
                edge("b", "out", target_handle="rawimage"),
            ],
            [a, b],
        )
        # NPZ IQA measures rawimage first when that slot is connected.
        self.assertEqual(
            output["out"]["quality_assessment"]["before"], calculate_all_metrics(b, b)
        )


if __name__ == "__main__":
    unittest.main()
