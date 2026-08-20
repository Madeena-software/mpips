from typing import Any, Dict, cast

import numpy as np

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
        return (image * 255.0).clip(0, 255).astype(np.uint8)
    if image.dtype in [np.uint16, np.int32, np.uint32]:
        min_val = image.min()
        max_val = image.max()
        if max_val > min_val:
            return cast(
                np.ndarray,
                ((image - min_val) / (max_val - min_val) * 255.0).astype(np.uint8),
            )
        return image.clip(0, 255).astype(np.uint8)
    return image


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
