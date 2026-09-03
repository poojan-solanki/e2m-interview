"""ControlNet Guidance Generation for Architectural Facades (Phase 3).

Extracts structural Canny edge maps and architectural wireframes from exterior photos
to ensure building geometry, perspective, and window frames stay 100% rigid during inpainting.
"""

from typing import Union
import cv2
import numpy as np
from PIL import Image


def build_canny_control_image(
    image: Union[Image.Image, np.ndarray],
    low_threshold: int = 100,
    high_threshold: int = 200,
) -> Image.Image:
    """Generates a 3-channel Canny edge condition image for ControlNet.
    
    Args:
        image: Source facade photo as PIL Image or numpy array (RGB or BGR).
        low_threshold: Lower bound for hysteresis thresholding (default: 100).
        high_threshold: Upper bound for hysteresis thresholding (default: 200).
        
    Returns:
        3-channel uint8 PIL Image with white edges on black background.
    """
    if isinstance(image, Image.Image):
        img_np = np.array(image.convert("RGB"))
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    else:
        if image.ndim == 2:
            gray = image
        elif image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)

    # Gaussian blur to reduce high-frequency foliage/texture noise while keeping building lines crisp
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(blurred, low_threshold, high_threshold)

    # ControlNet expects a 3-channel (RGB) condition image
    edges_3ch = np.stack([edges, edges, edges], axis=-1)
    return Image.fromarray(edges_3ch)
