import os
import tempfile
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Callable, cast
from mpips.storage import S3StorageBackend, StorageBackend
from mpips.engine.registry import get_node_class

# Madeena radiograph capture NPZ (id/gainid/darkid/xrayparams/...) image
# keys, most-preferred first: rawimage is the sensor capture, processedimage
# a derived fallback, darkimage a calibration reference used only if
# nothing else is present.
MADEENA_IMAGE_KEYS = ("rawimage", "processedimage", "darkimage")


def load_npz_image(path: str) -> np.ndarray:
    """Loads a single 2D/3D image array from an NPZ file for use as a DAG image slot."""
    with np.load(path) as data:
        if "image" in data.files:
            return cast(np.ndarray, data["image"])
        for key in MADEENA_IMAGE_KEYS:
            if key in data.files:
                return cast(np.ndarray, data[key])
        if len(data.files) == 1:
            return cast(np.ndarray, data[data.files[0]])
        raise ValueError(
            f"NPZ '{path}' has no 'image' key and contains multiple arrays "
            f"{data.files}; ambiguous which one is the image."
        )


def load_npz_named_images(path: str) -> Dict[str, np.ndarray]:
    """Loads every Madeena image slot present in a capture NPZ, by name.

    Lets a DAG input node expose each image (rawimage/darkimage/processedimage)
    as its own output slot, so edges can wire the exact image a downstream
    node needs instead of relying on a single auto-picked "output_image".
    """
    with np.load(path) as data:
        return {
            key: cast(np.ndarray, data[key])
            for key in MADEENA_IMAGE_KEYS
            if key in data.files
        }


# Non-image Madeena capture metadata keys. Every key is optional here - not
# every Madeena NPZ variant carries all of them (e.g. gain-catalog NPZs have
# cameraparams/xrayparams but no frameusedcount/description, see
# mpips.workflows.imager_pipeline.npz_io.load_gain_catalog) - so this is a
# lenient "grab what's there" reader, unlike npz_io.py's strict validating
# readers used by the imager pipeline workflow.
MADEENA_METADATA_KEYS = (
    "id",
    "gainid",
    "darkid",
    "xrayparams",
    "cameraparams",
    "frameusedcount",
    "description",
)


def load_npz_madeena_metadata(path: str) -> Dict[str, Any]:
    """Loads whichever Madeena capture metadata keys are present in an NPZ.

    xrayparams/cameraparams are stored as pickled dict scalars (0-d object
    arrays), hence allow_pickle=True; callers must only pass trusted files,
    same caveat as npz_io.py.
    """
    with np.load(path, allow_pickle=True) as data:
        metadata: Dict[str, Any] = {}
        for key in MADEENA_METADATA_KEYS:
            if key not in data.files:
                continue
            value = data[key]
            metadata[key] = value.item() if value.ndim == 0 else value
        return metadata


def load_gain_npz_images(path: str) -> Dict[str, np.ndarray]:
    """Loads a gain/flat-field calibration NPZ's images, renamed to
    gain_flat_image/gain_dark_image so they don't collide with the
    same-named rawimage/darkimage slots the capture NPZ already exposes on
    the same input_npz node.

    A gain NPZ's own "rawimage" is the flat-field reference and "darkimage"
    the paired dark reference (see
    mpips.workflows.imager_pipeline.npz_io.load_gain_catalog, the only other
    place in this codebase that already reads a gain file this way) - a
    different meaning from a capture NPZ's "rawimage"/"darkimage".
    """
    with np.load(path) as data:
        result: Dict[str, np.ndarray] = {}
        if "rawimage" in data.files:
            result["gain_flat_image"] = cast(np.ndarray, data["rawimage"])
        if "darkimage" in data.files:
            result["gain_dark_image"] = cast(np.ndarray, data["darkimage"])
        return result


def _convert_to_8bit(image: np.ndarray) -> np.ndarray:
    if image.dtype in [np.float32, np.float64]:
        min_val = image.min()
        max_val = image.max()
        if max_val > min_val:
            return cast(
                np.ndarray,
                ((image - min_val) / (max_val - min_val) * 255.0).astype(np.uint8),
            )
        return cast(np.ndarray, (image * 255.0).clip(0, 255).astype(np.uint8))
    if image.dtype in [np.uint16, np.int32, np.uint32]:
        min_val = image.min()
        max_val = image.max()
        if max_val > min_val:
            return cast(
                np.ndarray,
                ((image - min_val) / (max_val - min_val) * 255.0).astype(np.uint8),
            )
        return cast(np.ndarray, image.clip(0, 255).astype(np.uint8))
    return image


def _resolve_output_config(
    output_config: Dict[str, Any], node_id: str
) -> Dict[str, Any]:
    """Merges a per-output-node override onto the shared output config.

    A pipeline with multiple "output" nodes can route each one to its own
    S3 key/bucket/URL via ``output_config["nodes"][node_id]``; fields not
    overridden fall back to the top-level config, so a single flat config
    (the pre-existing shape, one output node) still works unchanged.
    """
    per_node = output_config.get("nodes")
    if isinstance(per_node, dict) and isinstance(per_node.get(node_id), dict):
        return {**output_config, **per_node[node_id]}
    return output_config


def save_npz_image(path: str, image: np.ndarray) -> None:
    """Saves a single image array to an NPZ file under the 'image' key."""
    np.savez(path, image=image)


def save_npz_madeena(
    path: str, images: Dict[str, np.ndarray], metadata: Dict[str, Any]
) -> None:
    """Saves a Madeena-shaped NPZ from whichever image/metadata slots a
    pipeline actually wired into the output_npz node.

    Both dicts may be a partial subset (e.g. a pipeline that only rewires
    processedimage, or one with no input_npz node upstream so metadata is
    empty) - only present keys are written, so this always produces a valid
    npz even for the minimal case of a single image and no metadata.
    """
    payload: Dict[str, Any] = {**metadata, **images}
    np.savez(path, **payload)


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

    def __init__(self, storage: StorageBackend | None = None) -> None:
        self.storage = storage or S3StorageBackend()

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
        output_node_count = sum(
            1 for n in nodes if n.get("type") in ("output", "output_npz")
        )
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

                if node_type in ("input", "input_npz"):
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
                            ".npz",
                        ]
                        else ".png"
                    )
                    if parsed_ext.lower() in [".tiff", ".tif", ".npz"]:
                        input_ext = parsed_ext.lower()

                    fd, temp_path = tempfile.mkstemp(suffix=ext)
                    os.close(fd)
                    temp_files.append(temp_path)

                    try:
                        self.storage.download_image(
                            source,
                            temp_path,
                            is_presigned_url=is_presigned,
                        )
                        img: Optional[np.ndarray]
                        named_images: Dict[str, np.ndarray] = {}
                        npz_metadata: Dict[str, Any] = {}
                        if ext == ".npz":
                            img = load_npz_image(temp_path)
                            # Only the Madeena-specific input node surfaces the
                            # individual rawimage/darkimage/processedimage slots
                            # (and the non-image capture metadata); a plain
                            # "input" node stays single-slot even when pointed
                            # at a Madeena-shaped NPZ.
                            if node_type == "input_npz":
                                named_images = load_npz_named_images(temp_path)
                                npz_metadata = load_npz_madeena_metadata(temp_path)
                        else:
                            img = cv2.imread(temp_path, cv2.IMREAD_UNCHANGED)
                        if img is None:
                            raise ValueError(
                                f"Failed to read downloaded image at '{temp_path}'."
                            )

                        # Convert to 8-bit ONLY if explicitly requested by the user
                        convert_to_8bit = node_params.get("convert_to_8bit", False)
                        if convert_to_8bit:
                            img = _convert_to_8bit(img)
                            named_images = {
                                slot: _convert_to_8bit(slot_img)
                                for slot, slot_img in named_images.items()
                            }

                        # Optional second download: a gain/flat-field
                        # calibration NPZ for this capture, only meaningful
                        # for input_npz. gainid alone (in npz_metadata) isn't
                        # a resolvable path - the pipeline has to tell us
                        # where the gain file actually lives, the same way it
                        # already tells us where the capture file lives.
                        gain_images: Dict[str, np.ndarray] = {}
                        if node_type == "input_npz":
                            gain_source = input_src.get("gain_key") or input_src.get(
                                "gain_url"
                            )
                            if gain_source:
                                gain_is_presigned = (
                                    "gain_url" in input_src
                                    or gain_source.startswith("http")
                                )
                                gain_fd, gain_temp_path = tempfile.mkstemp(
                                    suffix=".npz"
                                )
                                os.close(gain_fd)
                                temp_files.append(gain_temp_path)
                                self.storage.download_image(
                                    gain_source,
                                    gain_temp_path,
                                    is_presigned_url=gain_is_presigned,
                                )
                                gain_images = load_gain_npz_images(gain_temp_path)
                                if convert_to_8bit:
                                    gain_images = {
                                        slot: _convert_to_8bit(slot_img)
                                        for slot, slot_img in gain_images.items()
                                    }

                        if original_input_img is None:
                            original_input_img = img
                    finally:
                        if original_bucket is not None:
                            os.environ["AWS_BUCKET"] = original_bucket
                        else:
                            os.environ.pop("AWS_BUCKET", None)

                    # InputNode passes through every output slot it's given. For
                    # node_type == "input_npz", named_images/npz_metadata/
                    # gain_images were populated above so the Madeena slots
                    # (rawimage/darkimage/processedimage/npz_metadata/
                    # gain_flat_image/gain_dark_image) become individually
                    # wireable in addition to output_image; for plain "input"
                    # they're always empty here, so this is a no-op and only
                    # output_image is ever exposed.
                    node_inputs["output_image"] = img
                    node_inputs.update(named_images)
                    node_inputs.update(gain_images)
                    if npz_metadata:
                        node_inputs["npz_metadata"] = npz_metadata

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

                # Special handling for OutputNode/MadeenaNpzOutputNode: upload
                # the result image(s)
                if node_type in ("output", "output_npz"):
                    npz_images: Dict[str, np.ndarray] = {}
                    npz_out_metadata: Dict[str, Any] = {}

                    if node_type == "output_npz":
                        # Whichever of rawimage/darkimage/processedimage a
                        # pipeline actually wired in - all individually
                        # optional, e.g. a pipeline might only rewire
                        # processedimage and leave the rest unconnected.
                        npz_images = {
                            slot: node_inputs[slot]
                            for slot in ("rawimage", "darkimage", "processedimage")
                            if node_inputs.get(slot) is not None
                        }
                        # Metadata is optional too - a pipeline that builds a
                        # Madeena file from scratch without an input_npz node
                        # upstream just won't have any to carry through.
                        npz_out_metadata = node_inputs.get("npz_metadata") or {}
                        if not npz_images:
                            raise ValueError(
                                f"MadeenaNpzOutputNode '{node_id}' has no "
                                f"rawimage/darkimage/processedimage input to upload."
                            )
                        # Reference image for checksum/IQA metrics below.
                        output_img = next(iter(npz_images.values()))
                    else:
                        output_img = node_inputs.get("input_image")
                        if output_img is None:
                            # Fallback if connected differently
                            output_img = context.get((node_id, "output_image"))

                        if output_img is None:
                            raise ValueError(
                                f"OutputNode '{node_id}' has no input image to upload."
                            )

                    # Save image to temp path using dynamic extension. The
                    # Madeena NPZ output node always writes .npz regardless of
                    # the pipeline's original input format - that's the point
                    # of the node.
                    out_ext = (
                        ".npz"
                        if node_type == "output_npz"
                        else (
                            input_ext
                            if input_ext in [".tiff", ".tif", ".npz"]
                            else ".png"
                        )
                    )
                    fd, temp_path = tempfile.mkstemp(suffix=out_ext)
                    os.close(fd)
                    temp_files.append(temp_path)

                    if node_type == "output_npz":
                        save_npz_madeena(temp_path, npz_images, npz_out_metadata)
                    elif out_ext == ".npz":
                        save_npz_image(temp_path, output_img)
                    else:
                        cv2.imwrite(temp_path, output_img)

                    # Upload output (per-node override if this pipeline has
                    # more than one output node, else the shared config)
                    node_output_config = _resolve_output_config(output_config, node_id)
                    dest_type = node_output_config.get("destination_type", "s3")
                    is_presigned = dest_type == "url" or "url" in node_output_config

                    target_url = node_output_config.get("url")
                    if target_url:
                        target = str(target_url)
                    else:
                        # Direct S3 key construct. With multiple output nodes,
                        # fold the node id into the filename so they can't
                        # collide on the same prefix/key.
                        prefix = node_output_config.get("prefix", "")
                        filename = node_id if output_node_count > 1 else "output"
                        target = f"{prefix}{filename}{out_ext}"

                    original_bucket = os.getenv("AWS_BUCKET")
                    if "bucket" in node_output_config:
                        os.environ["AWS_BUCKET"] = node_output_config["bucket"]

                    try:
                        self.storage.upload_image(
                            temp_path,
                            target,
                            is_presigned_url=is_presigned,
                            mime_type=(
                                "image/tiff"
                                if out_ext in [".tiff", ".tif"]
                                else (
                                    "application/octet-stream"
                                    if out_ext == ".npz"
                                    else "image/png"
                                )
                            ),
                        )

                        import hashlib

                        size_bytes = os.path.getsize(temp_path)
                        hasher = hashlib.md5()
                        with open(temp_path, "rb") as f:
                            for chunk in iter(lambda: f.read(4096), b""):
                                hasher.update(chunk)
                        checksum = hasher.hexdigest()

                        from mpips.engine.iqa import calculate_all_metrics

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
                                return cast(
                                    np.ndarray,
                                    ((arr - min_v) / (max_v - min_v) * 255.0).astype(
                                        np.uint8
                                    ),
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

                        outputs_metadata[node_id] = {
                            "storage_disk": "s3" if not is_presigned else "url",
                            "bucket": node_output_config.get(
                                "bucket", os.getenv("AWS_BUCKET", "madeena-media")
                            ),
                            "key": target if not is_presigned else None,
                            "url": target if is_presigned else None,
                            "mime_type": (
                                "image/tiff"
                                if out_ext in [".tiff", ".tif"]
                                else (
                                    "application/octet-stream"
                                    if out_ext == ".npz"
                                    else "image/png"
                                )
                            ),
                            "size_bytes": size_bytes,
                            "checksum": checksum,
                            "quality_assessment": quality_assessment,
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
