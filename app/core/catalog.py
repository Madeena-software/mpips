from app.schemas.nodes import ProcessorNodeSchema, InputSlot, OutputSlot, Parameter

NODE_CATALOG = [
    ProcessorNodeSchema(
        id="input",
        name="Input Node",
        category="io",
        description=(
            "Maps S3 source configurations into the DAG execution pipeline. "
            "Downloads file to memory or temporary local workspace."
        ),
        inputs=[],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[],
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
        id="resize",
        name="Resize Image",
        category="geometry",
        description="Resizes images based on width, height, and interpolation mode.",
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
    ),
    ProcessorNodeSchema(
        id="crop",
        name="Crop Image",
        category="geometry",
        description="Crops image relative to bounding box.",
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
    ),
    ProcessorNodeSchema(
        id="rotate",
        name="Rotate Image",
        category="geometry",
        description="Rotates image by an arbitrary angle.",
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
    ),
    ProcessorNodeSchema(
        id="flip",
        name="Flip Image",
        category="geometry",
        description="Flips image horizontally, vertically, or both.",
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
    ),
    ProcessorNodeSchema(
        id="grayscale",
        name="Grayscale Conversion",
        category="adjustments",
        description=(
            "Converts multi-channel RGB/RGBA images into "
            "single-channel luminance arrays."
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[],
        version="1.0.0",
    ),
    ProcessorNodeSchema(
        id="brightness_contrast",
        name="Brightness & Contrast",
        category="adjustments",
        description="Adjusts brightness and contrast using linear scaling.",
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
    ),
    ProcessorNodeSchema(
        id="thresholding",
        name="Thresholding",
        category="adjustments",
        description=(
            "Converts image to binary using simple threshold " "or Otsu's thresholding."
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
    ),
    ProcessorNodeSchema(
        id="gamma_correction",
        name="Gamma Correction",
        category="adjustments",
        description="Non-linear luminance correction using power-law transformations.",
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
    ),
    ProcessorNodeSchema(
        id="gaussian_blur",
        name="Gaussian Blur",
        category="filtering",
        description="Smooths images to reduce noise using Gaussian filter.",
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
    ),
    ProcessorNodeSchema(
        id="median_blur",
        name="Median Blur",
        category="filtering",
        description=(
            "Non-linear blur using median filter, "
            "highly effective for salt-and-pepper noise."
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
    ),
    ProcessorNodeSchema(
        id="canny",
        name="Canny Edge Detection",
        category="filtering",
        description="Detects edges using multi-stage hysteresis thresholding.",
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
    ),
    ProcessorNodeSchema(
        id="sobel",
        name="Sobel Filter",
        category="filtering",
        description="Computes horizontal or vertical derivatives to extract gradients.",
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
    ),
    ProcessorNodeSchema(
        id="nlm_denoising",
        name="Non-Local Means (NLM) Denoising",
        category="advanced",
        description=(
            "Smooths images based on patch similarity. "
            "Highly effective for low-light sensor noise."
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
            "Used to correct non-uniform lighting."
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
            "thresholding coefficients, and inverse transform."
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
            "using flat and dark calibration frames."
        ),
        inputs=[InputSlot(name="input_image", type="image")],
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
        id="camera_calibration",
        name="Camera Calibration",
        category="advanced",
        description=(
            "Supports correcting geometric lens distortion "
            "using pre-calculated camera matrices (.npz files)."
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
        id="fabemd",
        name="FABEMD Decompose",
        category="advanced",
        description=(
            "Fast Adaptive Bi-dimensional Empirical Mode Decomposition. "
            "Decomposes images into BIMFs and a residue."
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="output_image", type="image")],
        parameters=[
            Parameter(
                name="num_imfs",
                type="integer",
                default=2,
                description="Number of Intrinsic Mode Functions to extract",
                min=1,
            )
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
            "Lower values indicate higher perceptual quality."
        ),
        inputs=[InputSlot(name="input_image", type="image")],
        outputs=[OutputSlot(name="brisque_score", type="float")],
        parameters=[],
        version="1.0.0",
    ),
]
