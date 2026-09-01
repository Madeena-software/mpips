from mpips.engine.schemas import ProcessorNodeSchema, InputSlot, OutputSlot, Parameter

PRESERVES_BIT_DEPTH = (
    " Bit depth: supports uint8/uint16/uint32/float inputs and preserves the "
    "input bit depth where the operation semantics allow."
)
USES_8BIT_WORKING_COPY = (
    " Bit depth note: accepts high bit-depth inputs, but this algorithm uses a "
    "normalized 8-bit working copy internally."
)
OUTPUTS_8BIT = (
    " Bit depth note: accepts high bit-depth inputs, but the algorithm outputs "
    "an 8-bit result."
)

NODE_CATALOG = [
    ProcessorNodeSchema(
        id="input",
        name="Input Node",
        category="io",
        description=(
            "Maps S3 source configurations into the DAG execution pipeline. "
            "Downloads file to memory or temporary local workspace. "
            "Preserves native bit depth unless convert_to_8bit is enabled."
        ),
        inputs=[],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="convert_to_8bit",
                type="boolean",
                default=False,
                description=(
                    "Automatically convert high bit-depth/float inputs to 8-bit "
                    "(0-255 uint8). Leave disabled to preserve native bit depth."
                ),
            )
        ],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="input_npz",
        name="Madeena NPZ Input Node",
        category="io",
        description=(
            "Maps S3 source configurations into the DAG execution pipeline, "
            "for a Madeena radiograph capture NPZ specifically. Downloads file "
            "to memory or temporary local workspace. Preserves native bit "
            "depth unless convert_to_8bit is enabled. Exposes rawimage/"
            "darkimage/processedimage as separate slots so each can be wired "
            "to a different downstream node, plus the capture's non-image "
            "metadata (id/gainid/darkid/xrayparams/cameraparams/"
            "frameusedcount/description, whichever keys are present) as a "
            "single npz_metadata slot; unused slots when the source NPZ "
            "doesn't carry every key are left unconnected. Optionally also "
            "downloads a separate gain/flat-field calibration NPZ (configured "
            "per-node via gain_key/gain_url alongside the capture's own "
            "key/url) and exposes its rawimage/darkimage as gain_flat_image/"
            "gain_dark_image; left unconnected if no gain source is "
            "configured for this node."
        ),
        inputs=[],
        outputs=[
            OutputSlot(name="output_image", type="image"),
            OutputSlot(name="rawimage", type="image"),
            OutputSlot(name="darkimage", type="image"),
            OutputSlot(name="processedimage", type="image"),
            OutputSlot(name="npz_metadata", type="metadata"),
            OutputSlot(name="gain_flat_image", type="image"),
            OutputSlot(name="gain_dark_image", type="image"),
        ],
        parameters=[
            Parameter(
                name="convert_to_8bit",
                type="boolean",
                default=False,
                description=(
                    "Automatically convert high bit-depth/float inputs to 8-bit "
                    "(0-255 uint8). Leave disabled to preserve native bit depth."
                ),
            )
        ],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="output",
        name="Output Node",
        category="io",
        description=(
            "Encapsulates S3 destination parameters. " "Uploads the final result image."
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[],
        parameters=[],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="output_npz",
        name="Madeena NPZ Output Node",
        category="io",
        description=(
            "Encapsulates S3 destination parameters for a Madeena radiograph "
            "capture NPZ. Declares rawimage/darkimage/processedimage as "
            "individually optional input slots (wire as many or as few as "
            "needed) plus an optional npz_metadata slot for the capture's "
            "non-image fields; writes an NPZ containing whichever slots were "
            "actually wired in."
        ),
        inputs=[
            InputSlot(name="rawimage", type="image"),
            InputSlot(name="darkimage", type="image"),
            InputSlot(name="processedimage", type="image"),
            InputSlot(name="npz_metadata", type="metadata"),
        ],
        outputs=[],
        parameters=[],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="resize",
        name="Resize Image",
        category="geometry",
        description="Resizes images based on width, height, and interpolation mode."
        + PRESERVES_BIT_DEPTH,
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="width",
                type="integer",
                default=800,
                description="Target width in pixels",
                min=1,
            ),
            Parameter(
                name="height",
                type="integer",
                default=600,
                description="Target height in pixels",
                min=1,
            ),
            Parameter(
                name="interpolation",
                type="string",
                default="BILINEAR",
                description="Interpolation algorithm",
                options=["NEAREST", "BILINEAR", "BICUBIC", "LANCZOS4"],
            ),
        ],
        version="1.0.0",
        executable_in_browser=True,
    ),
    ProcessorNodeSchema(
        id="crop",
        name="Crop Image",
        category="geometry",
        description="Crops image relative to bounding box." + PRESERVES_BIT_DEPTH,
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="x_start",
                type="integer",
                default=0,
                description="Starting X coordinate (left)",
                min=0,
            ),
            Parameter(
                name="y_start",
                type="integer",
                default=0,
                description="Starting Y coordinate (top)",
                min=0,
            ),
            Parameter(
                name="width",
                type="integer",
                default=100,
                description="Crop width in pixels",
                min=1,
            ),
            Parameter(
                name="height",
                type="integer",
                default=100,
                description="Crop height in pixels",
                min=1,
            ),
        ],
        version="1.0.0",
        executable_in_browser=True,
    ),
    ProcessorNodeSchema(
        id="rotate",
        name="Rotate Image",
        category="geometry",
        description="Rotates image by an arbitrary angle." + PRESERVES_BIT_DEPTH,
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="angle",
                type="float",
                default=0.0,
                description="Rotation angle in degrees",
            ),
            Parameter(
                name="expand",
                type="boolean",
                default=True,
                description="True to expand image boundaries to fit rotated content",
            ),
        ],
        version="1.0.0",
        executable_in_browser=True,
    ),
    ProcessorNodeSchema(
        id="flip",
        name="Flip Image",
        category="geometry",
        description="Flips image horizontally, vertically, or both."
        + PRESERVES_BIT_DEPTH,
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="direction",
                type="string",
                default="horizontal",
                description="Flip direction",
                options=["horizontal", "vertical", "both"],
            )
        ],
        version="1.0.0",
        executable_in_browser=True,
    ),
    ProcessorNodeSchema(
        id="grayscale",
        name="Grayscale Conversion",
        category="adjustments",
        description=(
            "Converts multi-channel RGB/RGBA images into "
            "single-channel luminance arrays." + PRESERVES_BIT_DEPTH
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[],
        version="1.0.0",
        executable_in_browser=True,
    ),
    ProcessorNodeSchema(
        id="brightness_contrast",
        name="Brightness & Contrast",
        category="adjustments",
        description="Adjusts brightness and contrast using linear scaling."
        + PRESERVES_BIT_DEPTH,
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="alpha",
                type="float",
                default=1.0,
                description="Contrast gain multiplier",
                min=0.0,
            ),
            Parameter(
                name="beta",
                type="float",
                default=0.0,
                description="Brightness bias offset",
            ),
        ],
        version="1.0.0",
        executable_in_browser=True,
    ),
    ProcessorNodeSchema(
        id="thresholding",
        name="Thresholding",
        category="adjustments",
        description=(
            "Converts image to binary using simple threshold "
            "or Otsu's thresholding." + PRESERVES_BIT_DEPTH
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="threshold_value",
                type="integer",
                default=127,
                description="Threshold value used in simple binary mode",
                min=0,
                max=255,
            ),
            Parameter(
                name="type",
                type="string",
                default="binary",
                description="Threshold algorithm type",
                options=["binary", "otsu"],
            ),
        ],
        version="1.0.0",
        executable_in_browser=True,
    ),
    ProcessorNodeSchema(
        id="gamma_correction",
        name="Gamma Correction",
        category="adjustments",
        description="Non-linear luminance correction using power-law transformations."
        + PRESERVES_BIT_DEPTH,
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="gamma",
                type="float",
                default=1.0,
                description="Gamma scaling power",
                min=0.1,
            )
        ],
        version="1.0.0",
        executable_in_browser=True,
    ),
    ProcessorNodeSchema(
        id="clahe",
        name="CLAHE",
        category="adjustments",
        description=(
            "Contrast Limited Adaptive Histogram Equalization. Enhances local "
            "contrast without over-amplifying noise; color images are processed "
            "in LAB space so hue/saturation aren't shifted." + USES_8BIT_WORKING_COPY
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="clip_limit",
                type="float",
                default=2.0,
                description="Contrast clip threshold — higher allows more contrast",
                min=0.1,
            ),
            Parameter(
                name="tile_grid_size",
                type="integer",
                default=8,
                description="Grid size (NxN tiles) local equalization is computed over",
                min=1,
            ),
        ],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="gaussian_blur",
        name="Gaussian Blur",
        category="filtering",
        description="Smooths images to reduce noise using Gaussian filter."
        + PRESERVES_BIT_DEPTH,
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="kernel_size",
                type="integer",
                default=5,
                description="Size of the blurring kernel (must be odd)",
                min=1,
            ),
            Parameter(
                name="sigma",
                type="float",
                default=1.0,
                description="Gaussian kernel standard deviation",
                min=0.0,
            ),
        ],
        version="1.0.0",
        executable_in_browser=True,
    ),
    ProcessorNodeSchema(
        id="median_blur",
        name="Median Blur",
        category="filtering",
        description=(
            "Non-linear blur using median filter, "
            "highly effective for salt-and-pepper noise." + PRESERVES_BIT_DEPTH
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="kernel_size",
                type="integer",
                default=5,
                description="Aperture linear size (must be odd)",
                min=1,
            )
        ],
        version="1.0.0",
        executable_in_browser=True,
    ),
    ProcessorNodeSchema(
        id="canny",
        name="Canny Edge Detection",
        category="filtering",
        description="Detects edges using multi-stage hysteresis thresholding."
        + OUTPUTS_8BIT,
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="low_threshold",
                type="float",
                default=50.0,
                description="First threshold for the hysteresis procedure",
                min=0.0,
                max=255.0,
            ),
            Parameter(
                name="high_threshold",
                type="float",
                default=150.0,
                description="Second threshold for the hysteresis procedure",
                min=0.0,
                max=255.0,
            ),
        ],
        version="1.0.0",
        executable_in_browser=True,
    ),
    ProcessorNodeSchema(
        id="sobel",
        name="Sobel Filter",
        category="filtering",
        description="Computes horizontal or vertical derivatives to extract gradients."
        + PRESERVES_BIT_DEPTH,
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="dx",
                type="integer",
                default=1,
                description="Derivative order in x direction",
                min=0,
                max=2,
            ),
            Parameter(
                name="dy",
                type="integer",
                default=0,
                description="Derivative order in y direction",
                min=0,
                max=2,
            ),
            Parameter(
                name="ksize",
                type="integer",
                default=3,
                description="Size of the extended Sobel kernel (must be 1, 3, 5, or 7)",
                min=1,
            ),
        ],
        version="1.0.0",
        executable_in_browser=True,
    ),
    ProcessorNodeSchema(
        id="nlm_denoising",
        name="Non-Local Means (NLM) Denoising",
        category="advanced",
        description=(
            "Smooths images based on patch similarity. "
            "Highly effective for low-light sensor noise." + USES_8BIT_WORKING_COPY
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="h",
                type="float",
                default=3.0,
                description=(
                    "Filter strength (higher removes noise " "but reduces details)"
                ),
                min=0.0,
            ),
            Parameter(
                name="template_window_size",
                type="integer",
                default=7,
                description="Size in pixels of the template patch",
                min=1,
            ),
            Parameter(
                name="search_window_size",
                type="integer",
                default=21,
                description="Size in pixels of the search window",
                min=1,
            ),
        ],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="homomorphic_filter",
        name="Homomorphic Filter",
        category="advanced",
        description=(
            "Frequency domain filter that separates illumination and reflectance. "
            "Used to correct non-uniform lighting." + PRESERVES_BIT_DEPTH
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="low_frequency_gain",
                type="float",
                default=0.5,
                description="Gain for low frequencies (gamma_l)",
                min=0.0,
            ),
            Parameter(
                name="high_frequency_gain",
                type="float",
                default=1.5,
                description="Gain for high frequencies (gamma_h)",
                min=0.0,
            ),
            Parameter(
                name="cutoff_frequency",
                type="float",
                default=30.0,
                description="Cutoff frequency in pixels",
                min=1.0,
            ),
        ],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="wavelet_denoising",
        name="Wavelet Denoising",
        category="advanced",
        description=(
            "Multiscale image denoising using discrete wavelet transform (DWT), "
            "thresholding coefficients, and inverse transform." + USES_8BIT_WORKING_COPY
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="wavelet",
                type="string",
                default="db1",
                description="Wavelet type basis",
                options=["db1", "sym2", "haar"],
            ),
            Parameter(
                name="mode",
                type="string",
                default="soft",
                description="Thresholding mode",
                options=["soft", "hard"],
            ),
        ],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="flat_field_correction",
        name="Flat-Field Correction",
        category="advanced",
        description=(
            "Corrects uneven sensor sensitivity and lens vignetting "
            "using flat and dark calibration frames." + PRESERVES_BIT_DEPTH
        ),
        inputs=[
            InputSlot(name="input_image", type="image"),
            InputSlot(name="dark_field_image", type="image"),
            InputSlot(name="flat_field_image", type="image"),
        ],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="dark_field_key",
                type="string",
                default="",
                description="S3 storage key of the dark-field image",
            ),
            Parameter(
                name="flat_field_key",
                type="string",
                default="",
                description="S3 storage key of the flat-field image",
            ),
        ],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="leveling",
        name="Leveling",
        category="adjustments",
        description=(
            "Rescales overall brightness so the image's mean matches a "
            "reference mean, correcting exposure/intensity drift between "
            "captures in a batch. The correction's current mean is measured "
            "within the ROI (width/height 0 means the full image from "
            "x_start/y_start); the scale factor is then applied to the "
            "whole image." + PRESERVES_BIT_DEPTH
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="target_mean",
                type="float",
                default=0.0,
                description=(
                    "Reference brightness (the mean of the batch's baseline "
                    "image, measured over the same ROI); the image is "
                    "scaled so its ROI mean matches this value"
                ),
                min=0.0,
            ),
            Parameter(
                name="x_start",
                type="integer",
                default=0,
                description="ROI starting X coordinate (left) used to measure the current mean",
                min=0,
            ),
            Parameter(
                name="y_start",
                type="integer",
                default=0,
                description="ROI starting Y coordinate (top) used to measure the current mean",
                min=0,
            ),
            Parameter(
                name="width",
                type="integer",
                default=0,
                description="ROI width in pixels; 0 extends to the right edge of the image",
                min=0,
            ),
            Parameter(
                name="height",
                type="integer",
                default=0,
                description="ROI height in pixels; 0 extends to the bottom edge of the image",
                min=0,
            ),
        ],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="camera_calibration",
        name="Camera Calibration",
        category="advanced",
        description=(
            "Supports correcting geometric lens distortion "
            "using pre-calculated camera matrices (.npz files)." + PRESERVES_BIT_DEPTH
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="calibration_file_key",
                type="string",
                default="",
                description="S3 storage key of the .npz calibration matrix file",
            )
        ],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="camera_calibration_warp",
        name="Camera Calibration Warp",
        category="advanced",
        description=(
            "Applies promoted calibration remap coordinates to an image. "
            "This node is the backend exposure path for calibration warp logic "
            "that has graduated from research code."
        )
        + PRESERVES_BIT_DEPTH,
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="map_x",
                type="array",
                default=None,
                description=(
                    "Optional x-coordinate remap array. If omitted, identity "
                    "mapping is used."
                ),
            ),
            Parameter(
                name="map_y",
                type="array",
                default=None,
                description=(
                    "Optional y-coordinate remap array. If omitted, identity "
                    "mapping is used."
                ),
            ),
        ],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="fabemd",
        name="FABEMD Decompose",
        category="advanced",
        description=(
            "Fast Adaptive Bi-dimensional Empirical Mode Decomposition. "
            "Decomposes an image into up to 10 bi-dimensional intrinsic mode "
            "functions (bimf_1 highest frequency .. bimf_10 lowest) plus a "
            "residual, each its own output slot so every component can be "
            "wired to a different downstream node. Only the first num_imfs "
            "slots are populated; the rest are left unconnected." + PRESERVES_BIT_DEPTH
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[
            *[OutputSlot(name=f"bimf_{i}", type="image") for i in range(1, 11)],
            OutputSlot(name="residual", type="image"),
        ],
        parameters=[
            Parameter(
                name="num_imfs",
                type="integer",
                default=2,
                description="Number of Intrinsic Mode Functions to extract (max 10)",
                min=1,
                max=10,
            )
        ],
        version="1.1.0",
    ),
    ProcessorNodeSchema(
        id="merge",
        name="Merge",
        category="advanced",
        description=(
            "Weighted sum of multiple wired image inputs — the fan-in / "
            "recombination counterpart to FABEMD Decompose's fan-out. Declares "
            "10 named input slots; wire as many or as few as needed, unwired "
            "slots are ignored. With Normalize enabled the result is a "
            "weighted average (safe default); disable it for a raw weighted "
            "sum such as PACE 2.0's I_L = I_E + βI_HMF."
        ),
        inputs=[InputSlot(name=f"input_{i}", type="image") for i in range(1, 11)],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            *[
                Parameter(
                    name=f"input_{i}_weight",
                    type="float",
                    default=1.0,
                    description=f"Weight applied to input_{i} if wired",
                    min=0.0,
                )
                for i in range(1, 11)
            ],
            Parameter(
                name="normalize",
                type="boolean",
                default=True,
                description=(
                    "Divide the weighted sum by the total weight (weighted "
                    "average). Disable for a raw weighted sum."
                ),
            ),
        ],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="cii",
        name="CII (Contrast Improvement Index)",
        category="iqa",
        description=(
            "Computes local and global contrast index to "
            "measure details enhancement."
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="cii_score", type="float")],
        parameters=[],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="ent",
        name="ENT (Entropy)",
        category="iqa",
        description=(
            "Evaluates image information content based on "
            "pixel probability distribution."
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="entropy_score", type="float")],
        parameters=[],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="eme",
        name="EME (Measure of Enhancement)",
        category="iqa",
        description=(
            "Quantitative metric of image contrast/enhancement "
            "based on Weber-Fechner law computed on sub-blocks."
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="eme_score", type="float")],
        parameters=[
            Parameter(
                name="block_size",
                type="integer",
                default=8,
                description="Linear size of the sub-blocks in pixels",
                min=2,
            )
        ],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="brisque",
        name="BRISQUE Quality score",
        category="iqa",
        description=(
            "No-reference image quality metric evaluating naturalness. "
            "Lower values indicate higher perceptual quality." + USES_8BIT_WORKING_COPY
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="brisque_score", type="float")],
        parameters=[],
        version="1.0.0",
    ),
]
