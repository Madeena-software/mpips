import cv2
import numpy as np
from typing import Dict


class EntropyCalculator:
    """Evaluates image information content from pixel probabilities."""

    def calculate(self, image: np.ndarray) -> float:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        hist, _ = np.histogram(gray, bins=256, range=(0, 256))
        total = hist.sum()
        if total == 0:
            return 0.0

        hist_norm = hist / total
        hist_norm = hist_norm[hist_norm > 0]
        entropy = -np.sum(hist_norm * np.log2(hist_norm))
        return float(entropy)


class EnhancementMeasureCalculator:
    """Computes EME with block-wise Weber-Fechner contrast ratios."""

    def calculate(self, image: np.ndarray, block_size: int = 8) -> float:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        h, w = gray.shape
        k1 = h // block_size
        k2 = w // block_size
        if k1 == 0 or k2 == 0:
            return 0.0

        total_val = 0.0
        count = 0
        for i in range(k1):
            for j in range(k2):
                block = gray[
                    i * block_size : (i + 1) * block_size,
                    j * block_size : (j + 1) * block_size,
                ]
                b_max = float(np.max(block))
                b_min = float(np.min(block))
                if b_min == 0:
                    b_min = 0.0001

                ratio = b_max / b_min
                if ratio > 0:
                    total_val += np.log(ratio)
                    count += 1

        if count == 0:
            return 0.0

        eme = (2.0 / (k1 * k2)) * total_val
        return float(eme)


class ContrastImprovementIndexCalculator:
    """Computes CII as processed local contrast divided by original contrast."""

    def calculate_local_contrast(self, image: np.ndarray) -> float:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        block_size = 8
        h, w = gray.shape
        k1 = h // block_size
        k2 = w // block_size
        if k1 == 0 or k2 == 0:
            return float(np.std(gray))

        stds = []
        for i in range(k1):
            for j in range(k2):
                block = gray[
                    i * block_size : (i + 1) * block_size,
                    j * block_size : (j + 1) * block_size,
                ]
                stds.append(np.std(block))
        return float(np.mean(stds))

    def calculate(self, processed: np.ndarray, original: np.ndarray) -> float:
        c_proc = self.calculate_local_contrast(processed)
        c_orig = self.calculate_local_contrast(original)
        if c_orig == 0:
            return 1.0
        return float(c_proc / c_orig)


class BrisqueCalculator:
    """MSCN-based BRISQUE proxy score; lower scores represent higher quality."""

    def calculate(self, image: np.ndarray) -> float:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(float)
        else:
            gray = image.astype(float)

        mu = cv2.GaussianBlur(gray, (7, 7), 1.16)
        mu_sq = mu * mu
        gray_sq = gray * gray
        sigma = np.sqrt(np.abs(cv2.GaussianBlur(gray_sq, (7, 7), 1.16) - mu_sq))

        mscn = (gray - mu) / (sigma + 1.0)

        mscn_var = np.var(mscn)
        mean_mscn = np.mean(mscn)
        mscn_diff = mscn - mean_mscn
        numerator = np.mean(mscn_diff**4)
        denominator = (np.var(mscn_diff) ** 2) + 1e-5
        mscn_kurt = numerator / denominator

        deviation = np.abs(mscn_var - 1.0) * 25.0 + np.abs(mscn_kurt - 3.0) * 15.0
        brisque_score = np.clip(deviation, 0.0, 100.0)

        return float(brisque_score)


def calculate_entropy(image: np.ndarray) -> float:
    """Evaluates image information content based on pixel probability distribution."""
    return EntropyCalculator().calculate(image)


def calculate_eme(image: np.ndarray, block_size: int = 8) -> float:
    """Quantitative metric of image contrast/enhancement based on Weber-Fechner law."""
    return EnhancementMeasureCalculator().calculate(image, block_size)


def calculate_local_contrast(image: np.ndarray) -> float:
    """Calculates local standard deviation average over blocks."""
    return ContrastImprovementIndexCalculator().calculate_local_contrast(image)


def calculate_cii(processed: np.ndarray, original: np.ndarray) -> float:
    """Computes CII as ratio of processed to original local contrast."""
    return ContrastImprovementIndexCalculator().calculate(processed, original)


def calculate_brisque(image: np.ndarray) -> float:
    """MSCN-based Natural Scene Statistics proxy score representing quality."""
    return BrisqueCalculator().calculate(image)


def calculate_all_metrics(
    processed: np.ndarray, original: np.ndarray
) -> Dict[str, float]:
    """Calculates and gathers all four IQA metrics."""
    return {
        "cii": round(calculate_cii(processed, original), 4),
        "entropy": round(calculate_entropy(processed), 4),
        "eme": round(calculate_eme(processed), 4),
        "brisque": round(calculate_brisque(processed), 4),
    }
