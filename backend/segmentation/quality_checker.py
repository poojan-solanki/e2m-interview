"""Image Quality Verification for Media Ingestion (Requirement 5.1).

Validates input images to extract clear usable views, detect blur via Laplacian variance,
evaluate lighting/exposure conditions, and guide users if an image is not suitable.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Union
import cv2
import numpy as np


@dataclass
class ImageQualityReport:
    """Report detailing the quality and usability of an uploaded building photo."""
    is_valid: bool
    blur_score: float
    is_blurry: bool
    brightness: float
    is_under_exposed: bool
    is_over_exposed: bool
    resolution: Tuple[int, int]  # (width, height)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "blur_score": round(self.blur_score, 2),
            "is_blurry": self.is_blurry,
            "brightness": round(self.brightness, 2),
            "is_under_exposed": self.is_under_exposed,
            "is_over_exposed": self.is_over_exposed,
            "resolution": {"width": self.resolution[0], "height": self.resolution[1]},
            "warnings": self.warnings,
            "errors": self.errors,
        }


def check_image_quality(
    image_input: Union[str, Path, np.ndarray],
    min_resolution: Tuple[int, int] = (640, 480),
    blur_threshold: float = 100.0,
    min_brightness: float = 30.0,
    max_brightness: float = 230.0,
) -> ImageQualityReport:
    """Evaluates sharpness, exposure, and resolution of an exterior house photo.
    
    Args:
        image_input: File path string, Path object, or BGR numpy array.
        min_resolution: Minimum required (width, height).
        blur_threshold: Minimum acceptable variance of Laplacian (lower = blurrier).
        min_brightness: Minimum acceptable mean luminance (0-255).
        max_brightness: Maximum acceptable mean luminance (0-255).
        
    Returns:
        ImageQualityReport with pass/fail status, scores, and actionable feedback.
    """
    if isinstance(image_input, (str, Path)):
        path = Path(image_input)
        if not path.exists():
            return ImageQualityReport(
                is_valid=False,
                blur_score=0.0,
                is_blurry=True,
                brightness=0.0,
                is_under_exposed=False,
                is_over_exposed=False,
                resolution=(0, 0),
                errors=[f"Image file does not exist: {path}"],
            )
        img = cv2.imread(str(path))
        if img is None:
            return ImageQualityReport(
                is_valid=False,
                blur_score=0.0,
                is_blurry=True,
                brightness=0.0,
                is_under_exposed=False,
                is_over_exposed=False,
                resolution=(0, 0),
                errors=[f"Failed to decode image file. File may be corrupted: {path}"],
            )
    elif isinstance(image_input, np.ndarray):
        img = image_input
    else:
        raise TypeError(f"Unsupported image input type: {type(image_input)}")

    height, width = img.shape[:2]
    resolution = (width, height)
    warnings: List[str] = []
    errors: List[str] = []

    # 1. Resolution Check
    min_w, min_h = min_resolution
    if width < min_w or height < min_h:
        errors.append(
            f"Image resolution ({width}x{height}) is below minimum requirement ({min_w}x{min_h}). "
            "Please upload a higher-resolution photo for accurate area measurement."
        )

    # 2. Sharpness / Blur Check (Variance of Laplacian)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    blur_score = float(laplacian.var())
    is_blurry = blur_score < blur_threshold

    if is_blurry:
        if blur_score < (blur_threshold / 2):
            errors.append(
                f"Image is severely blurred (sharpness score: {blur_score:.1f} < {blur_threshold}). "
                "Architectural edges cannot be detected reliably. Please retake a sharper photo."
            )
        else:
            warnings.append(
                f"Image shows mild blur (sharpness score: {blur_score:.1f}). "
                "Boundary detection precision may be reduced."
            )

    # 3. Exposure / Lighting Check
    brightness = float(np.mean(gray))
    is_under_exposed = brightness < min_brightness
    is_over_exposed = brightness > max_brightness

    if is_under_exposed:
        errors.append(
            f"Photo is underexposed/too dark (brightness: {brightness:.1f}/255). "
            "Exterior details and texture boundaries are obscured. Please upload a daylight photo."
        )
    elif brightness < (min_brightness + 20.0):
        warnings.append(
            f"Photo lighting is somewhat dim (brightness: {brightness:.1f}/255). "
            "Shaded wall regions may have lower segmentation accuracy."
        )

    if is_over_exposed:
        errors.append(
            f"Photo is overexposed/washed out (brightness: {brightness:.1f}/255). "
            "Excessive glare obscures surface textures. Please upload a photo with balanced exposure."
        )

    is_valid = len(errors) == 0

    return ImageQualityReport(
        is_valid=is_valid,
        blur_score=blur_score,
        is_blurry=is_blurry,
        brightness=brightness,
        is_under_exposed=is_under_exposed,
        is_over_exposed=is_over_exposed,
        resolution=resolution,
        warnings=warnings,
        errors=errors,
    )
