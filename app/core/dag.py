import os
import tempfile
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Callable
from app.core.storage import download_image, upload_image
from image_engine.factory import get_node_class


def topological_sort(
    nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    # Build graph
    adj: Dict[str, List[str]] = {n["id"]: [] for n in nodes}
    in_degree = {n["id"]: 0 for n in nodes}
    node_map = {n["id"]: n for n in nodes}

    for edge in edges:
        src = edge["source"]
        tgt = edge["target"]
        if src not in node_map or tgt not in node_map:
            raise ValueError(f"Edge references non-existent node: {src} -> {tgt}")
        adj[src].append(tgt)
        in_degree[tgt] += 1

    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    sorted_nodes = []

    while queue:
        u = queue.pop(0)
        sorted_nodes.append(node_map[u])
        for v in adj[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    if len(sorted_nodes) < len(nodes):
        raise ValueError("Cycle detected in graph")

    return sorted_nodes


class DAGExecutor:
    """Parses, validates, and executes Directed Acyclic Graphs (DAGs) on images."""

    def __init__(self) -> None:
        pass

    def execute(
        self,
        pipeline: Dict[str, Any],
        inputs_config: Dict[str, Any],
        output_config: Dict[str, Any],
        on_progress: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the visual pipeline DAG.

        Args:
            pipeline: Dict with "nodes" and "edges" list.
            inputs_config: Mapping of input node ID to source S3/URL details.
            output_config: Configuration of output destination S3/URL.

        Returns:
            Dict containing output mapping details.
        """
        nodes = pipeline.get("nodes", [])
        edges = pipeline.get("edges", [])

        # 1. Topological sort (includes cycle detection)
        sorted_nodes = topological_sort(nodes, edges)

        # 2. Track temp files to clean them up
        temp_files: List[str] = []
        target = ""
        outputs_metadata: Dict[str, Any] = {}
        input_ext = ".png"

        try:
            # 3. Download inputs and prepare execution context
            original_input_img = None
            context: Dict[tuple[str, str], Any] = (
                {}
            )  # maps (node_id, slot_name) -> value

            # Map of node ID to incoming edges for quick lookup
            incoming_edges: Dict[str, List[Dict[str, Any]]] = {
                n["id"]: [] for n in nodes
            }
            for edge in edges:
                incoming_edges[edge["target"]].append(edge)

            # Process each node in topological order
            total_nodes = len(sorted_nodes)
            for idx, node in enumerate(sorted_nodes, start=1):
                node_id = node["id"]
                node_type = node["type"]
                raw_node_params = node.get("parameters", {})
                node_params = (
                    raw_node_params if isinstance(raw_node_params, dict) else {}
                )

                if on_progress:
                    on_progress(node_id, round(((idx - 1) / total_nodes) * 100.0, 2))

                # Fetch node class
                node_cls = get_node_class(node_type)
                node_inst = node_cls()

                # Resolve inputs from incoming edges
                node_inputs = {}

                if node_type == "input":
                    # Download input image to a temp file
                    if node_id not in inputs_config:
                        raise ValueError(
                            f"Missing input configuration for node '{node_id}'."
                        )

                    input_src = inputs_config[node_id]
                    # Determine source path/URL
                    source = input_src.get("key") or input_src.get("url")
                    if not source:
                        raise ValueError(
                            f"Input config for '{node_id}' "
                            f"must specify 'key' or 'url'."
                        )

                    is_presigned = "url" in input_src or source.startswith("http")

                    # Override bucket if specified in direct S3 type
                    original_bucket = os.getenv("AWS_BUCKET")
                    if "bucket" in input_src:
                        os.environ["AWS_BUCKET"] = input_src["bucket"]

                    # Determine source file extension to preserve it
                    _, parsed_ext = os.path.splitext(source.split("?")[0])
                    ext = (
                        parsed_ext.lower()
                        if parsed_ext.lower()
                        in [
                            ".tiff",
                            ".tif",
                            ".jpg",
                            ".jpeg",
                            ".webp",
                            ".gif",
                            ".svg",
                            ".bmp",
                        ]
                        else ".png"
                    )
                    if parsed_ext.lower() in [".tiff", ".tif"]:
                        input_ext = parsed_ext.lower()

                    fd, temp_path = tempfile.mkstemp(suffix=ext)
                    os.close(fd)
                    temp_files.append(temp_path)

                    try:
                        download_image(source, temp_path, is_presigned_url=is_presigned)
                        img = cv2.imread(temp_path, cv2.IMREAD_UNCHANGED)
                        if img is None:
                            raise ValueError(
                                f"Failed to read downloaded image at '{temp_path}'."
                            )

                        # Convert to 8-bit ONLY if explicitly requested by the user
                        convert_to_8bit = node_params.get("convert_to_8bit", False)
                        if convert_to_8bit:
                            if img.dtype in [np.float32, np.float64]:
                                min_val = img.min()
                                max_val = img.max()
                                if max_val > min_val:
                                    img = (
                                        (img - min_val) / (max_val - min_val) * 255.0
                                    ).astype(np.uint8)
                                else:
                                    img = (img * 255.0).clip(0, 255).astype(np.uint8)
                            elif img.dtype in [np.uint16, np.int32, np.uint32]:
                                min_val = img.min()
                                max_val = img.max()
                                if max_val > min_val:
                                    img = (
                                        (img - min_val) / (max_val - min_val) * 255.0
                                    ).astype(np.uint8)
                                else:
                                    img = img.clip(0, 255).astype(np.uint8)

                        if original_input_img is None:
                            original_input_img = img
                    finally:
                        if original_bucket is not None:
                            os.environ["AWS_BUCKET"] = original_bucket
                        else:
                            os.environ.pop("AWS_BUCKET", None)

                    # InputNode expects inputs["output_image"] to be set in execute
                    node_inputs["output_image"] = img

                else:
                    # Resolve inputs from edges
                    for edge in incoming_edges[node_id]:
                        target_handle = edge["target_handle"]
                        source_id = edge["source"]
                        source_handle = edge["source_handle"]

                        val = context.get((source_id, source_handle))
                        if val is None:
                            raise ValueError(
                                f"Missing connection for " f"{node_id}:{target_handle}"
                            )
                        node_inputs[target_handle] = val

                # Execute node
                outputs = node_inst.execute(node_inputs, node_params)

                # Write outputs to context
                for slot_name, val in outputs.items():
                    context[(node_id, slot_name)] = val

                # Special handling for OutputNode: upload output image
                if node_type == "output":
                    output_img = node_inputs.get("input_image")
                    if output_img is None:
                        # Fallback if connected differently
                        output_img = context.get((node_id, "output_image"))

                    if output_img is None:
                        raise ValueError(
                            f"OutputNode '{node_id}' has no input image to upload."
                        )

                    # Save image to temp path using dynamic extension
                    out_ext = input_ext if input_ext in [".tiff", ".tif"] else ".png"
                    fd, temp_path = tempfile.mkstemp(suffix=out_ext)
                    os.close(fd)
                    temp_files.append(temp_path)

                    cv2.imwrite(temp_path, output_img)

                    # Upload output
                    dest_type = output_config.get("destination_type", "s3")
                    is_presigned = dest_type == "url" or "url" in output_config

                    target_url = output_config.get("url")
                    if target_url:
                        target = str(target_url)
                    else:
                        # Direct S3 key construct
                        prefix = output_config.get("prefix", "")
                        # Construct a unique output key
                        target = f"{prefix}output{out_ext}"

                    original_bucket = os.getenv("AWS_BUCKET")
                    if "bucket" in output_config:
                        os.environ["AWS_BUCKET"] = output_config["bucket"]

                    try:
                        upload_image(temp_path, target, is_presigned_url=is_presigned)

                        import hashlib

                        size_bytes = os.path.getsize(temp_path)
                        hasher = hashlib.md5()
                        with open(temp_path, "rb") as f:
                            for chunk in iter(lambda: f.read(4096), b""):
                                hasher.update(chunk)
                        checksum = hasher.hexdigest()

                        from image_engine.iqa import calculate_all_metrics

                        ref_img = (
                            original_input_img
                            if original_input_img is not None
                            else output_img
                        )

                        # Normalize copies for IQA metrics
                        def to_uint8_copy(arr: np.ndarray) -> np.ndarray:
                            if arr.dtype == np.uint8:
                                return arr
                            min_v = arr.min()
                            max_v = arr.max()
                            if max_v > min_v:
                                return ((arr - min_v) / (max_v - min_v) * 255.0).astype(
                                    np.uint8
                                )
                            else:
                                if arr.dtype in [np.float32, np.float64]:
                                    return (arr * 255.0).clip(0, 255).astype(np.uint8)
                                return arr.clip(0, 255).astype(np.uint8)

                        ref_img_u8 = to_uint8_copy(ref_img)
                        output_img_u8 = to_uint8_copy(output_img)
                        quality_assessment = calculate_all_metrics(
                            output_img_u8, ref_img_u8
                        )

                        outputs_metadata = {
                            node_id: {
                                "storage_disk": "s3" if not is_presigned else "url",
                                "bucket": output_config.get(
                                    "bucket", os.getenv("AWS_BUCKET", "madeena-media")
                                ),
                                "key": target if not is_presigned else None,
                                "url": target if is_presigned else None,
                                "mime_type": (
                                    "image/tiff"
                                    if out_ext in [".tiff", ".tif"]
                                    else "image/png"
                                ),
                                "size_bytes": size_bytes,
                                "checksum": checksum,
                                "quality_assessment": quality_assessment,
                            }
                        }
                    finally:
                        if original_bucket is not None:
                            os.environ["AWS_BUCKET"] = original_bucket
                        else:
                            os.environ.pop("AWS_BUCKET", None)

            # Return successfully processed details
            return {
                "status": "completed",
                "output_target": target,
                "outputs": outputs_metadata,
            }

        finally:
            # Clean up all temp files
            for temp_path in temp_files:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
