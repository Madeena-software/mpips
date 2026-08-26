import hashlib
import importlib
import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from mpips.workflows.imager_pipeline import (
    CalibrationArtifacts,
    NeuralCalibrationConfig,
    NPZValidationError,
    ImagerPipelineConfig,
    SourceResolutionError,
    load_gain_catalog,
    process_npz_batch,
    resolve_npz_sources,
)
from mpips.workflows.imager_pipeline.calibration import (
    CalibrationValidationError,
    _load_calibration_image,
    _validate_metrics,
    extract_dot_grid,
)
from mpips.workflows.imager_pipeline.npz_io import (
    load_calibration_processed_image,
    load_radiograph,
    sha256_file,
    to_uint16,
)
from mpips.workflows.imager_pipeline.pipeline import (
    apply_calibration_remap,
    apply_clahe,
    apply_threshold_separation,
    flat_field_correction,
    hybrid_median_filter,
    imagej_equalize,
    imagej_stretch,
    process_radiography_arrays,
)
from mpips.engine.imager_pipeline.imagej_replicator import ImageJReplicator

CAMERA = {
    "cameraUserID": "BED-1",
    "cameraModel": "TEST",
    "cameraSerial": "SERIAL-1",
}
XRAY = {
    "expType": "radiograf",
    "detectorMode": "BED",
}


def save_gain(
    path: Path,
    gain_id: str = "gain-1",
    shape: tuple[int, int] = (8, 8),
    *,
    detector_mode: str = "BED",
    camera: dict[str, str] | None = None,
) -> None:
    np.savez_compressed(
        path,
        id=gain_id,
        xrayparams=np.asarray(
            {**XRAY, "expType": "gain", "detectorMode": detector_mode},
            dtype=object,
        ),
        cameraparams=np.asarray(camera or CAMERA, dtype=object),
        darkimage=np.zeros(shape, dtype=np.uint16),
        rawimage=np.full(shape, 1000, dtype=np.uint16),
    )


def save_radiograph(
    path: Path,
    gain_id: str = "gain-1",
    shape: tuple[int, int] = (8, 8),
    camera: dict[str, str] | None = None,
) -> np.ndarray:
    raw = np.arange(np.prod(shape), dtype=np.uint16).reshape(shape) + 100
    np.savez_compressed(
        path,
        id="radio-1",
        gainid=gain_id,
        xrayparams=np.asarray(XRAY, dtype=object),
        cameraparams=np.asarray(camera or CAMERA, dtype=object),
        rawimage=raw,
    )
    return raw


def save_calibration(path: Path, shape: tuple[int, int] = (8, 8)) -> None:
    np.savez_compressed(
        path,
        id="cal-1",
        gainid="gain-1",
        xrayparams=np.asarray(XRAY, dtype=object),
        cameraparams=np.asarray(CAMERA, dtype=object),
        rawimage=np.arange(np.prod(shape), dtype=np.uint16).reshape(shape) + 100,
        processedimage=np.linspace(0, 1, np.prod(shape)).reshape(shape),
    )


def identity_artifacts(
    tmp_path: Path, shape: tuple[int, int] = (8, 8)
) -> CalibrationArtifacts:
    directory = tmp_path / "calibration"
    directory.mkdir()
    y_values, x_values = np.indices(shape, dtype=np.float32)
    remap = directory / "remap.npz"
    np.savez_compressed(remap, map_x=x_values, map_y=y_values)
    model = directory / "compensation_model.pth"
    model.write_bytes(b"test")
    mask = directory / "valid_mask.png"
    assert cv2.imwrite(str(mask), np.full(shape, 255, dtype=np.uint8))
    metrics = directory / "metrics.json"
    metrics.write_text('{"validated": true}\n')
    metadata = directory / "metadata.json"
    metadata.write_text(
        json.dumps(
            {
                "validated": True,
                "fingerprint": "identity",
                "image_shape": list(shape),
                "source_metadata": {
                    "detector_mode": "BED",
                    "camera_params": CAMERA,
                },
            }
        )
    )
    return CalibrationArtifacts(
        fingerprint="identity",
        directory=directory,
        model_path=model,
        remap_path=remap,
        mask_path=mask,
        metrics_path=metrics,
        metadata_path=metadata,
        image_shape=shape,
        validated=True,
    )


def test_npz_readers_validate_and_extract_schema(tmp_path: Path) -> None:
    gain_path = tmp_path / "gain.npz"
    radio_path = tmp_path / "radio.npz"
    calibration_path = tmp_path / "calibration.npz"
    save_gain(gain_path)
    raw = save_radiograph(radio_path)
    save_calibration(calibration_path)

    catalog = load_gain_catalog([gain_path])
    radiograph = load_radiograph(radio_path)
    calibration, metadata = load_calibration_processed_image(calibration_path)

    assert set(catalog.records) == {"gain-1"}
    np.testing.assert_array_equal(radiograph["raw"], raw)
    assert metadata["gain_id"] == "gain-1"
    assert calibration.dtype == np.float32


def test_calibration_gain_override_is_optional_and_requires_matching_id(
    tmp_path: Path,
) -> None:
    calibration_path = tmp_path / "calibration.npz"
    gain_path = tmp_path / "gain.npz"
    save_calibration(calibration_path)
    save_gain(gain_path)

    stored, stored_metadata, stored_gain = _load_calibration_image(calibration_path)
    rebuilt, rebuilt_metadata, rebuilt_gain = _load_calibration_image(
        calibration_path, gain_path
    )

    assert stored_gain is None
    assert stored_metadata["gain_id"] == "gain-1"
    assert rebuilt_gain == {"id": "gain-1", "sha256": sha256_file(gain_path)}
    assert rebuilt_metadata == stored_metadata
    assert rebuilt.shape == stored.shape
    assert rebuilt.dtype == np.float32
    assert not np.array_equal(rebuilt, stored)

    save_gain(gain_path, "different-gain")
    with pytest.raises(NPZValidationError, match="does not match calibration gainid"):
        _load_calibration_image(calibration_path, gain_path)


@pytest.mark.parametrize(
    ("shape", "detector_mode", "message"),
    [
        ((7, 8), "BED", "shape"),
        ((8, 8), "TRX", "detector mode"),
    ],
)
def test_calibration_gain_override_validates_compatibility(
    tmp_path: Path,
    shape: tuple[int, int],
    detector_mode: str,
    message: str,
) -> None:
    calibration_path = tmp_path / "calibration.npz"
    gain_path = tmp_path / "gain.npz"
    save_calibration(calibration_path)
    save_gain(
        gain_path,
        shape=shape,
        detector_mode=detector_mode,
    )

    with pytest.raises(NPZValidationError, match=message):
        _load_calibration_image(calibration_path, gain_path)


def test_calibration_gain_camera_mismatch_is_informational(tmp_path: Path) -> None:
    calibration_path = tmp_path / "calibration.npz"
    gain_path = tmp_path / "gain.npz"
    save_calibration(calibration_path)
    save_gain(gain_path, camera={**CAMERA, "cameraSerial": "DIFFERENT"})

    image, metadata, gain_metadata = _load_calibration_image(
        calibration_path, gain_path
    )

    assert image.shape == (8, 8)
    assert metadata["camera_params"]["cameraSerial"] == "SERIAL-1"
    assert gain_metadata["id"] == "gain-1"


def test_gain_catalog_rejects_duplicate_ids(tmp_path: Path) -> None:
    first = tmp_path / "first.npz"
    second = tmp_path / "second.npz"
    save_gain(first)
    save_gain(second)
    with pytest.raises(NPZValidationError, match="Duplicate gain id"):
        load_gain_catalog([first, second])


def test_npz_reader_rejects_missing_gainid(tmp_path: Path) -> None:
    path = tmp_path / "invalid.npz"
    np.savez_compressed(
        path,
        id="radio-1",
        xrayparams=np.asarray(XRAY, dtype=object),
        cameraparams=np.asarray(CAMERA, dtype=object),
        rawimage=np.ones((2, 2)),
    )
    with pytest.raises(NPZValidationError, match="gainid"):
        load_radiograph(path)


def test_uint16_conversion_rejects_overflow() -> None:
    with pytest.raises(NPZValidationError, match="cannot be represented"):
        to_uint16(np.array([[65536]], dtype=np.uint64))


def test_source_resolver_accepts_mounted_folder_and_newline_list(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "folder"
    nested = folder / "nested"
    nested.mkdir(parents=True)
    save_gain(folder / "a.npz")
    save_gain(nested / "b.npz", "gain-2")
    (folder / "ignored.txt").write_text("ignored")

    resolved = resolve_npz_sources(
        f"{folder / 'a.npz'}\n{nested}", tmp_path / "downloads"
    )
    assert resolved == sorted(
        [(folder / "a.npz").resolve(), (nested / "b.npz").resolve()]
    )


def test_source_resolver_downloads_public_file_and_folder(tmp_path: Path) -> None:
    def downloader(url: str, output: Path, is_folder: bool) -> object:
        if is_folder:
            save_gain(output / "downloaded.npz")
        else:
            save_gain(output)
        return output

    resolved = resolve_npz_sources(
        [
            "https://drive.google.com/file/d/file-id/view",
            "https://drive.google.com/drive/folders/folder-id",
        ],
        tmp_path / "downloads",
        downloader=downloader,
    )
    assert len(resolved) == 2
    assert all(path.suffix == ".npz" for path in resolved)


def test_source_resolver_rejects_non_npz_path(tmp_path: Path) -> None:
    text = tmp_path / "input.txt"
    text.write_text("no")
    with pytest.raises(SourceResolutionError, match="not an NPZ"):
        resolve_npz_sources(text, tmp_path / "downloads")


def test_extract_dot_grid_requires_rectangular_grid() -> None:
    image = np.zeros((180, 220), dtype=np.uint8)
    for row in range(4):
        for column in range(5):
            cv2.circle(image, (30 + column * 40, 30 + row * 40), 7, 255, -1)
    coords, diameters, circularity = extract_dot_grid(
        image, NeuralCalibrationConfig(row_tolerance=20)
    )
    assert coords.shape == (4, 5, 2)
    assert diameters.shape == (4, 5)
    assert circularity.shape == (4, 5)


def test_extract_dot_grid_rejects_irregular_rows_instead_of_trimming() -> None:
    image = np.zeros((260, 220), dtype=np.uint8)
    for row in range(6):
        for column in range(5):
            if row != 2 or column != 4:
                cv2.circle(image, (30 + column * 40, 30 + row * 40), 7, 255, -1)

    with pytest.raises(
        CalibrationValidationError,
        match=r"not rectangular; refusing to discard rows; row widths: "
        r"5, 5, 4, 5, 5, 5",
    ):
        extract_dot_grid(image, NeuralCalibrationConfig(row_tolerance=20))


def test_supplied_gotri_extracts_19_by_26_grid() -> None:
    source = Path("research/kambing-260714/data/kalibrasi-gotri/BED_1783219960026.npz")
    gain = Path("research/kambing-260714/data/gain/BED_1783219207291.npz")
    if not source.exists() or not gain.exists():
        pytest.skip("Local acceptance sample is not present")
    processed, _, gain_metadata = _load_calibration_image(source, gain)
    image = np.rint(processed * 255).astype(np.uint8)
    coords, _, _ = extract_dot_grid(image, NeuralCalibrationConfig())
    assert gain_metadata is not None
    assert gain_metadata["id"] == "1783219207291"
    assert coords.shape == (19, 26, 2)
    assert coords.shape[0] * coords.shape[1] == 494


def test_calibration_quality_gate_rejects_weak_metrics() -> None:
    metrics = {
        "straightness_rmse": 10.0,
        "reprojection_rmse": 10.0,
        "spacing_x_std": 10.0,
        "spacing_y_std": 10.0,
        "diameter_std": 10.0,
    }
    with pytest.raises(CalibrationValidationError, match="quality gate"):
        _validate_metrics(metrics, metrics, NeuralCalibrationConfig())


def test_pipeline_primitives_preserve_shapes_and_dtype() -> None:
    image = np.arange(25, dtype=np.uint16).reshape(5, 5)
    y_values, x_values = np.indices(image.shape, dtype=np.float32)
    np.testing.assert_array_equal(
        apply_calibration_remap(image, x_values, y_values), image
    )
    corrected = flat_field_correction(
        image.astype(np.float32),
        np.zeros_like(image, dtype=np.float32),
        np.full_like(image, 100, dtype=np.float32),
    )
    assert corrected.shape == image.shape
    filtered = hybrid_median_filter(image, radius=1)
    assert filtered.shape == image.shape
    assert filtered.dtype == np.uint16


def test_imagej_operations_match_golden_arrays() -> None:
    image = np.array([[0, 0, 1, 2], [2, 2, 3, 3]], dtype=np.uint8)
    np.testing.assert_array_equal(
        imagej_equalize(image),
        np.array([[0, 0, 63, 135], [135, 135, 218, 218]], dtype=np.uint8),
    )
    np.testing.assert_array_equal(
        imagej_stretch(image, 0.0),
        np.array([[0, 0, 85, 170], [170, 170, 255, 255]], dtype=np.uint8),
    )
    separated = apply_threshold_separation(
        np.array([[0.0, 0.25, 0.5, 0.75, 1.0]], dtype=np.float32), 0.5
    )
    np.testing.assert_array_equal(
        separated, np.array([[0.0, 0.5, 1.0, 1.0, 1.0]], dtype=np.float32)
    )


def test_reference_notebook_defaults_are_preserved() -> None:
    config = ImagerPipelineConfig()
    assert config.wavelet == "sym4"
    assert config.wavelet_level == 3
    assert config.wavelet_method == "BayesShrink"
    assert config.wavelet_mode == "soft"
    assert config.threshold_method == "auto"
    assert config.contrast_saturated_pixels == 5.0
    assert config.clahe_blocksize == 127
    assert config.clahe_max_slope == 0.6
    assert config.clahe_fast is False
    assert config.clahe_composite is True
    assert config.median_filter_type == "hybrid_imagej"
    assert config.median_filter_radius == 2


def test_promoted_canonical_modules_are_importable() -> None:
    modules = (
        "mpips.engine.calibration.dotgrid.extract_grid",
        "mpips.engine.calibration.dotgrid.neural_model.phantom",
        "mpips.engine.imager_pipeline.complete_pipeline",
        "mpips.engine.imager_pipeline.imagej_replicator",
        "mpips.engine.imager_pipeline.wavelet_denoising",
    )
    for module in modules:
        assert importlib.import_module(module) is not None


def test_precise_and_fast_clahe_adapters_match_canonical_engine() -> None:
    image = np.arange(256, dtype=np.uint16).reshape(16, 16) * 257
    for fast in (False, True):
        expected = ImageJReplicator.apply_clahe(
            image,
            blocksize=7,
            histogram_bins=256,
            max_slope=0.6,
            fast=fast,
            composite=True,
        )
        actual = apply_clahe(
            image,
            7,
            256,
            0.6,
            fast=fast,
            composite=True,
        )
        np.testing.assert_array_equal(actual, expected)


def test_complete_promoted_recipe_matches_golden_tiff_pixels() -> None:
    shape = (24, 24)
    y_values, x_values = np.indices(shape)
    raw = (
        800 + x_values * 27 + y_values * 19 + ((x_values * y_values) % 11) * 13
    ).astype(np.uint16)
    dark = (40 + ((x_values + y_values) % 7)).astype(np.uint16)
    flat = (3100 + x_values * 3 + y_values * 5).astype(np.uint16)
    output = process_radiography_arrays(raw, dark, flat, "BED", ImagerPipelineConfig())
    assert output.dtype == np.uint16
    assert hashlib.sha256(output.tobytes()).hexdigest() == (
        "777a868cb95ccf0a7fdf915c8cb7b82cfe760f27a4138f1c109e335f7d108361"
    )


def test_full_pipeline_can_run_fixed_recipe_without_optional_steps() -> None:
    raw = np.arange(64, dtype=np.uint16).reshape(8, 8) + 100
    dark = np.zeros((8, 8), dtype=np.uint16)
    flat = np.full((8, 8), 1000, dtype=np.uint16)
    config = ImagerPipelineConfig(
        use_denoise=False,
        threshold_method="none",
        use_invert=False,
        use_contrast_enhancement=False,
        use_clahe=False,
        use_median_filter=False,
    )
    output = process_radiography_arrays(raw, dark, flat, "BED", config)
    np.testing.assert_allclose(output, raw, atol=1)
    assert output.dtype == np.uint16


def test_batch_writes_tiff_and_manifest_and_continues_failures(tmp_path: Path) -> None:
    gain_path = tmp_path / "gain.npz"
    valid_path = tmp_path / "valid.npz"
    invalid_path = tmp_path / "missing-gain.npz"
    save_gain(gain_path)
    expected = save_radiograph(valid_path)
    save_radiograph(invalid_path, gain_id="does-not-exist")
    config = ImagerPipelineConfig(
        use_denoise=False,
        threshold_method="none",
        use_invert=False,
        use_contrast_enhancement=False,
        use_clahe=False,
        use_median_filter=False,
    )
    result = process_npz_batch(
        [valid_path, invalid_path],
        load_gain_catalog([gain_path]),
        identity_artifacts(tmp_path),
        tmp_path / "output",
        config,
    )
    assert result.succeeded == 1
    assert result.failed == 1
    manifest = json.loads(result.manifest_path.read_text())
    assert manifest["counts"] == {"total": 2, "succeeded": 1, "failed": 1}
    assert result.items[0].output is not None
    written = cv2.imread(result.items[0].output, cv2.IMREAD_UNCHANGED)
    assert written is not None
    np.testing.assert_allclose(written, expected, atol=1)


def test_batch_accepts_camera_mismatch_as_informational(tmp_path: Path) -> None:
    gain_path = tmp_path / "gain.npz"
    radio_path = tmp_path / "radio.npz"
    save_gain(gain_path)
    save_radiograph(
        radio_path,
        camera={**CAMERA, "cameraSerial": "DIFFERENT"},
    )
    result = process_npz_batch(
        [radio_path],
        load_gain_catalog([gain_path]),
        identity_artifacts(tmp_path),
        tmp_path / "output",
        ImagerPipelineConfig(use_denoise=False),
    )
    assert result.succeeded == 1
    assert result.failed == 0
    assert result.items[0].output is not None


def test_batch_uses_collision_safe_output_names(tmp_path: Path) -> None:
    gain_path = tmp_path / "gain.npz"
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first = first_dir / "same.npz"
    second = second_dir / "same.npz"
    save_gain(gain_path)
    save_radiograph(first)
    save_radiograph(second)
    config = ImagerPipelineConfig(
        use_denoise=False,
        threshold_method="none",
        use_invert=False,
        use_contrast_enhancement=False,
        use_clahe=False,
        use_median_filter=False,
    )
    result = process_npz_batch(
        [first, second],
        load_gain_catalog([gain_path]),
        identity_artifacts(tmp_path),
        tmp_path / "output",
        config,
    )
    outputs = [item.output for item in result.items]
    assert result.succeeded == 2
    assert len(set(outputs)) == 2
    assert all(output and Path(output).is_file() for output in outputs)


def test_pipeline_applies_remap_after_ffc_with_different_output_shape() -> None:
    raw = np.arange(64, dtype=np.uint16).reshape(8, 8) + 100
    dark = np.zeros((8, 8), dtype=np.uint16)
    flat = np.full((8, 8), 1000, dtype=np.uint16)
    config = ImagerPipelineConfig(
        use_denoise=False,
        threshold_method="none",
        use_invert=True,
        use_contrast_enhancement=False,
        use_clahe=False,
        use_median_filter=True,
    )
    # create 12x12 map_x and map_y
    y_values, x_values = np.indices((12, 12), dtype=np.float32)
    output = process_radiography_arrays(
        raw, dark, flat, "BED", config, map_x=x_values, map_y=y_values
    )
    assert output.shape == (12, 12)
    assert output.dtype == np.uint16
    assert output[:8, :8].any()
    assert not output[8:, :].any()
    assert not output[:, 8:].any()
