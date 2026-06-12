import os
import tempfile
import cv2
from typing import List, Dict, Any
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

        try:
            # 3. Download inputs and prepare execution context
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
            for node in sorted_nodes:
                node_id = node["id"]
                node_type = node["type"]
                node_params = node.get("parameters", {})

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

                    fd, temp_path = tempfile.mkstemp(suffix=".png")
                    os.close(fd)
                    temp_files.append(temp_path)

                    try:
                        download_image(source, temp_path, is_presigned_url=is_presigned)
                        img = cv2.imread(temp_path, cv2.IMREAD_UNCHANGED)
                        if img is None:
                            raise ValueError(
                                f"Failed to read downloaded image at '{temp_path}'."
                            )
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

                    # Save image to temp path
                    fd, temp_path = tempfile.mkstemp(suffix=".png")
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
                        target = f"{prefix}output.png"

                    original_bucket = os.getenv("AWS_BUCKET")
                    if "bucket" in output_config:
                        os.environ["AWS_BUCKET"] = output_config["bucket"]

                    try:
                        upload_image(temp_path, target, is_presigned_url=is_presigned)
                    finally:
                        if original_bucket is not None:
                            os.environ["AWS_BUCKET"] = original_bucket
                        else:
                            os.environ.pop("AWS_BUCKET", None)

            # Return successfully processed details
            return {"status": "completed", "output_target": target}

        finally:
            # Clean up all temp files
            for temp_path in temp_files:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
