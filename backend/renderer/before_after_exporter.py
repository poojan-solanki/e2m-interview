"""Side-by-side comparison generator for Before & After architectural visualizations (Phase 3).

Composites original facade and AI-redesigned facade with clean divider bars and badges.
"""

from pathlib import Path
from typing import Optional, Union
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def generate_before_after_comparison(
    original_image: Union[str, Path, Image.Image, np.ndarray],
    redesigned_image: Union[str, Path, Image.Image, np.ndarray],
    output_path: Optional[Union[str, Path]] = None,
    divider_width: int = 6,
) -> Image.Image:
    """Creates a horizontal side-by-side Before/After comparison image with architectural badges.
    
    Args:
        original_image: Path, PIL Image, or BGR numpy array of the original photo.
        redesigned_image: Path, PIL Image, or BGR numpy array of the redesigned output.
        output_path: Optional destination file path (e.g. output/comparison.png).
        divider_width: Thickness in pixels of the center dividing line.
        
    Returns:
        PIL Image of the combined before-and-after comparison.
    """
    # 1. Convert inputs to RGB PIL Images
    def to_pil_rgb(img_input):
        if isinstance(img_input, (str, Path)):
            return Image.open(str(img_input)).convert("RGB")
        elif isinstance(img_input, np.ndarray):
            if img_input.ndim == 2:
                return Image.fromarray(cv2.cvtColor(img_input, cv2.COLOR_GRAY2RGB))
            elif img_input.shape[2] == 3:
                return Image.fromarray(cv2.cvtColor(img_input, cv2.COLOR_BGR2RGB))
            else:
                return Image.fromarray(cv2.cvtColor(img_input, cv2.COLOR_BGRA2RGB))
        elif isinstance(img_input, Image.Image):
            return img_input.convert("RGB")
        raise TypeError(f"Unsupported image input type: {type(img_input)}")

    orig_pil = to_pil_rgb(original_image)
    redesign_pil = to_pil_rgb(redesigned_image)

    # 2. Match heights to preserve aspect ratio
    target_h = orig_pil.height
    if redesign_pil.height != target_h:
        target_w = int(round(redesign_pil.width * (target_h / redesign_pil.height)))
        redesign_pil = redesign_pil.resize((target_w, target_h), Image.Resampling.LANCZOS)

    w1, h1 = orig_pil.size
    w2, h2 = redesign_pil.size

    # 3. Canvas setup
    total_w = w1 + divider_width + w2
    canvas = Image.new("RGB", (total_w, target_h), (28, 28, 30))  # Dark charcoal background

    # Paste original and redesigned
    canvas.paste(orig_pil, (0, 0))
    canvas.paste(redesign_pil, (w1 + divider_width, 0))

    # 4. Draw center divider line
    draw = ImageDraw.Draw(canvas)
    draw.rectangle(
        [(w1, 0), (w1 + divider_width - 1, target_h)],
        fill=(245, 240, 235),  # Warm white divider
    )

    # 5. Overlay badges
    badge_color = (20, 20, 22, 210)  # Semi-transparent dark
    text_color = (255, 255, 255)

    def draw_badge(img_draw, text, x, y):
        font = None
        try:
            # Try default truetype font if available
            font = ImageFont.truetype("arial.ttf", 22)
        except Exception:
            font = ImageFont.load_default()

        bbox = img_draw.textbbox((x, y), text, font=font)
        pad = 8
        rect = [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad]
        img_draw.rectangle(rect, fill=(20, 20, 22))
        img_draw.text((x, y), text, fill=text_color, font=font)

    # Place "BEFORE (ORIGINAL)" badge on left panel bottom-left
    draw_badge(draw, "BEFORE  [ ORIGINAL ]", 25, target_h - 45)

    # Place "AFTER (AI RENOVATION)" badge on right panel bottom-left
    draw_badge(draw, "AFTER  [ AI RENOVATION ]", w1 + divider_width + 25, target_h - 45)

    # 6. Save if output path provided
    if output_path is not None:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(str(out_p), quality=95)

    return canvas
