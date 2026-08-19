"""
2D Wavelet Transform for X-ray Image Denoising and Background Removal
Uses multi-level wavelet decomposition for superior noise reduction
"""

import cv2
import numpy as np
from pathlib import Path

from mpips.processing.wavelet import PYWT_AVAILABLE, WaveletDenoiser


class WaveletBackgroundRemover:
    """Use wavelet transform to separate background from anatomy."""
    
    def __init__(self, wavelet='db4'):
        if not PYWT_AVAILABLE:
            raise ImportError("PyWavelets required. Install with: pip install PyWavelets")
        
        self.wavelet = wavelet
    
    def remove_background_wavelet(self, image, level=2):
        """
        Remove background using wavelet-based approach.
        
        Args:
            image: Input grayscale image
            level: Decomposition level (lower = preserve more detail)
        
        Returns:
            Tuple of (result, mask)
        """
        is_16bit = image.dtype == np.uint16
        
        # Work directly on original image for mask creation (preserve full resolution)
        if is_16bit:
            image_8bit = (image / 256).astype(np.uint8)
        else:
            image_8bit = image
        
        print(f"  → Background removal: level={level} (preserving high-freq details)")
        
        # Create mask from original image (not downsampled)
        # Apply strong blur to get low-frequency approximation
        blurred = cv2.GaussianBlur(image_8bit, (15, 15), 0)
        
        # Apply Otsu thresholding
        _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Minimal morphological operations to preserve edges
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Keep largest component
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            mask_clean = np.zeros_like(mask)
            cv2.drawContours(mask_clean, [largest], -1, 255, -1)
            mask = mask_clean
        
        # Apply mask using binary multiplication (preserves full resolution)
        mask_binary = (mask > 0).astype(np.float32)
        
        if is_16bit:
            result = (image.astype(np.float32) * mask_binary).astype(np.uint16)
        else:
            result = (image.astype(np.float32) * mask_binary).astype(np.uint8)
        
        return result, mask


def process_with_wavelet(input_path, output_dir, wavelet='db4', method='BayesShrink', 
                         denoise_level=None, background_level=2):
    """
    Complete wavelet-based processing pipeline.
    
    Args:
        input_path: Path to input image
        output_dir: Output directory
        wavelet: Wavelet type ('db4', 'db8', 'sym4', 'coif1', 'bior4.4')
        method: Denoising method ('BayesShrink', 'VisuShrink', 'manual')
        denoise_level: Decomposition level for denoising (None=auto)
        background_level: Decomposition level for background removal
    
    Returns:
        Dict with output paths
    """
    print(f"\nProcessing: {Path(input_path).name}")
    print(f"Wavelet: {wavelet}, Method: {method}")
    print("="*60)
    
    # Read image
    image = cv2.imread(str(input_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"Could not read image: {input_path}")
    
    print(f"Image size: {image.shape[1]}x{image.shape[0]}")
    print(f"Image type: {image.dtype}\n")
    
    # Step 1: Wavelet denoising
    print("[Step 1] Wavelet denoising...")
    denoiser = WaveletDenoiser(wavelet=wavelet, level=denoise_level)
    denoised = denoiser.denoise_wavelet(image, method=method, mode='soft')
    
    # Step 2: Wavelet-based background removal
    print("\n[Step 2] Wavelet background removal...")
    bg_remover = WaveletBackgroundRemover(wavelet=wavelet)
    result, mask = bg_remover.remove_background_wavelet(denoised, level=background_level)
    
    # Save results
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    filename = Path(input_path).stem
    
    orig_file = output_path / f"{filename}_0_original.tiff"
    denoise_file = output_path / f"{filename}_1_wavelet_denoised.tiff"
    mask_file = output_path / f"{filename}_2_mask.png"
    result_file = output_path / f"{filename}_3_final.tiff"
    
    cv2.imwrite(str(orig_file), image)
    cv2.imwrite(str(denoise_file), denoised)
    cv2.imwrite(str(mask_file), mask)
    cv2.imwrite(str(result_file), result)
    
    # Create comparison
    if image.dtype == np.uint16:
        img_vis = (image / 256).astype(np.uint8)
        denoise_vis = (denoised / 256).astype(np.uint8)
        result_vis = (result / 256).astype(np.uint8)
    else:
        img_vis = image
        denoise_vis = denoised
        result_vis = result
    
    # Resize for comparison if needed
    max_width = 800
    if img_vis.shape[1] > max_width:
        scale = max_width / img_vis.shape[1]
        new_size = (max_width, int(img_vis.shape[0] * scale))
        img_vis = cv2.resize(img_vis, new_size)
        denoise_vis = cv2.resize(denoise_vis, new_size)
        result_vis = cv2.resize(result_vis, new_size)
        mask_vis = cv2.resize(mask, new_size)
    else:
        mask_vis = mask
    
    comparison = np.hstack([img_vis, denoise_vis, result_vis, mask_vis])
    comp_file = output_path / f"{filename}_4_comparison.png"
    cv2.imwrite(str(comp_file), comparison)
    
    print("\n" + "="*60)
    print("RESULTS:")
    print(f"  Original: {orig_file.name}")
    print(f"  Denoised: {denoise_file.name}")
    print(f"  Mask: {mask_file.name}")
    print(f"  Final: {result_file.name}")
    print(f"  Comparison: {comp_file.name}")
    print(f"\nSaved to: {output_path}")
    print("="*60)
    
    return {
        'original': str(orig_file),
        'denoised': str(denoise_file),
        'mask': str(mask_file),
        'final': str(result_file),
        'comparison': str(comp_file)
    }


if __name__ == "__main__":
    import sys
    
    if not PYWT_AVAILABLE:
        print("ERROR: PyWavelets not installed")
        print("Install with: pip install PyWavelets")
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("Usage: python wavelet_denoising.py <image_path> [output_dir] [wavelet] [method]")
        print("\nWavelets: db4 (default), db8, sym4, coif1, bior4.4")
        print("Methods: BayesShrink (default), VisuShrink, manual")
        print("\nExample:")
        print("  python wavelet_denoising.py image.tiff Output db4 BayesShrink")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "Wavelet_Results"
    wavelet = sys.argv[3] if len(sys.argv) > 3 else "db4"
    method = sys.argv[4] if len(sys.argv) > 4 else "BayesShrink"
    
    if not Path(input_path).exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
    
    process_with_wavelet(input_path, output_dir, wavelet=wavelet, method=method)
