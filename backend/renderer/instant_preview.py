"""Instant Facade Material Preview Engine (Dual-Tier Rendering Architecture - Tier 1).

Generates real-time, sub-50ms procedural surface material previews directly on CPU/GPU
without requiring deep diffusion model loading. Preserves real architectural lighting,
shadows, and sun angles via luminance-preserving LAB color-space transfer, while enforcing
a 100% mathematical pixel-lock on windows, doors, and protected elements.
"""

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Optional, Tuple, Union
import cv2
import numpy as np
from PIL import Image

from .inpainter import apply_pixel_lock


@dataclass
class PreviewResult:
    """Encapsulates the instant procedural preview and execution metadata."""
    preview_image: Image.Image
    original_image: Image.Image
    inpaint_mask: Image.Image
    material_id: str
    execution_time_ms: float
    output_dimensions: Tuple[int, int]


# Authentic architectural color palettes (Hex / BGR / LAB calibrated)
MATERIAL_PREVIEW_PALETTES = {
    "weatherproof_paint": {
        "base_bgr": (140, 165, 200),  # Warm terracotta ochre
        "roughness": 0.05,
        "texture_type": "matte",
    },
    "textured_stucco": {
        "base_bgr": (170, 195, 215),  # Tuscan sand stucco
        "roughness": 0.22,
        "texture_type": "granular",
    },
    "stone_cladding": {
        "base_bgr": (120, 125, 130),  # Charcoal / slate grey
        "roughness": 0.35,
        "texture_type": "stone_blocks",
    },
    "vitrified_tiles": {
        "base_bgr": (95, 100, 105),   # Matte porcelain tile
        "roughness": 0.08,
        "texture_type": "tile_grid",
    },
    "wpc_panels": {
        "base_bgr": (45, 80, 140),    # Rich dark teak / walnut wood
        "roughness": 0.15,
        "texture_type": "wooden_louvers",
    },
    "glass_railing": {
        "base_bgr": (220, 215, 180),  # Light cyan transparent tint
        "roughness": 0.02,
        "texture_type": "tinted_glass",
    },
    "metal_railing": {
        "base_bgr": (35, 35, 35),     # Matte black powder-coated
        "roughness": 0.05,
        "texture_type": "metal_slats",
    },
}


def _generate_procedural_texture(
    width: int,
    height: int,
    texture_type: str,
    base_bgr: Tuple[int, int, int],
    roughness: float,
) -> np.ndarray:
    """Generates a procedural architectural texture matching the selected material."""
    base = np.zeros((height, width, 3), dtype=np.float32)
    base[:, :] = base_bgr

    if texture_type == "matte":
        # Ultra-fine micro-grain for smooth exterior paint
        noise = np.random.normal(0, roughness * 35, (height, width, 1)).astype(np.float32)
        tex = np.clip(base + noise, 0, 255)

    elif texture_type == "granular":
        # Multi-frequency granular noise for rustic stucco
        noise_fine = np.random.normal(0, roughness * 45, (height, width, 1)).astype(np.float32)
        # Small blur for cohesive plaster clumps
        noise_blurred = cv2.GaussianBlur(noise_fine, (3, 3), 0)[:, :, None]
        tex = np.clip(base + noise_blurred, 0, 255)

    elif texture_type == "stone_blocks":
        # Interlocking split-face stone cladding texture
        tex = base.copy()
        # Random stone shading noise
        stone_noise = np.random.normal(0, roughness * 55, (height, width, 1)).astype(np.float32)
        tex = np.clip(tex + stone_noise, 0, 255)

        # Horizontal mortar course lines (every ~28 pixels)
        course_h = max(16, int(height // 24))
        for y in range(0, height, course_h):
            y_end = min(y + 2, height)
            tex[y:y_end, :] *= 0.65  # Dark mortar line

            # Staggered vertical joints
            col_w = course_h * 2
            stagger = (y // course_h) % 2 * (col_w // 2)
            for x in range(stagger, width, col_w):
                x_end = min(x + 2, width)
                tex[y:min(y + course_h, height), x:x_end] *= 0.65

    elif texture_type == "wooden_louvers":
        # Modern fluted vertical/horizontal architectural wooden louvers
        tex = base.copy()
        # Wood grain noise along vertical axis
        wood_grain = np.random.normal(0, roughness * 30, (height, width, 1)).astype(np.float32)
        tex = np.clip(tex + wood_grain, 0, 255)

        # Vertical slat channels
        slat_w = max(12, int(width // 45))
        gap_w = max(2, int(slat_w * 0.25))
        for x in range(0, width, slat_w):
            x_gap = min(x + gap_w, width)
            tex[:, x:x_gap] *= 0.45  # Deep shadow in louver recessed channel
            # Subtle highlight on right slat edge
            x_hi = min(x + gap_w + 1, width)
            tex[:, x_gap:x_hi] = np.clip(tex[:, x_gap:x_hi] * 1.25, 0, 255)

    elif texture_type == "tile_grid":
        # Large-format porcelain facade tiles (e.g. 60x120cm grid)
        tex = base.copy()
        tile_noise = np.random.normal(0, roughness * 25, (height, width, 1)).astype(np.float32)
        tex = np.clip(tex + tile_noise, 0, 255)

        # Grout line grid
        grid_x = max(35, int(width // 16))
        grid_y = max(35, int(height // 14))
        for x in range(0, width, grid_x):
            tex[:, x:min(x + 2, width)] *= 0.70  # Dark grout
        for y in range(0, height, grid_y):
            tex[y:min(y + 2, height), :] *= 0.70  # Dark grout

    elif texture_type == "metal_slats":
        # Sleek vertical balustrade slats
        tex = base.copy()
        bar_w = max(6, int(width // 60))
        for x in range(0, width, bar_w * 2):
            tex[:, x:min(x + bar_w, width)] = (25, 25, 25)

    elif texture_type == "tinted_glass":
        # Transparent tinted architectural glass with soft reflections
        tex = base.copy()
        # Diagonal highlight sheen
        gradient = np.tile(np.linspace(0.85, 1.15, width, dtype=np.float32), (height, 1))[:, :, None]
        tex = np.clip(tex * gradient, 0, 255)

    else:
        tex = base

    return tex.astype(np.uint8)


def _blend_luminance(
    original_bgr: np.ndarray,
    texture_bgr: np.ndarray,
    alpha: float = 0.85,
) -> np.ndarray:
    """Blends procedural texture with real photo luminance in LAB color space.
    
    This preserves authentic facade shadow gradients, cast tree shadows,
    and daylight highlights while transferring the new surface texture and hue.
    """
    # Convert both to LAB color space
    orig_lab = cv2.cvtColor(original_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    tex_lab = cv2.cvtColor(texture_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)

    # L channel (0-255) = Luminance / Physical shading
    orig_l = orig_lab[:, :, 0]
    tex_l = tex_lab[:, :, 0]

    # Combine original luminance with texture surface relief
    # Normalize lighting to avoid over-darkening
    l_mean = np.mean(orig_l) if np.mean(orig_l) > 10 else 128.0
    combined_l = np.clip(orig_l * (tex_l / l_mean), 0, 255)

    # Blend A and B color channels from new material texture
    blended_lab = np.zeros_like(orig_lab)
    blended_lab[:, :, 0] = combined_l
    blended_lab[:, :, 1] = (1 - alpha) * orig_lab[:, :, 1] + alpha * tex_lab[:, :, 1]
    blended_lab[:, :, 2] = (1 - alpha) * orig_lab[:, :, 2] + alpha * tex_lab[:, :, 2]

    blended_bgr = cv2.cvtColor(blended_lab.astype(np.uint8), cv2.COLOR_LAB2BGR)
    return blended_bgr


def render_instant_preview(
    image: Union[str, Path, Image.Image],
    inpaint_mask: Union[str, Path, Image.Image],
    material_id: str = "stone_cladding",
    blend_intensity: float = 0.88,
    custom_bgr: Optional[Tuple[int, int, int]] = None,
) -> PreviewResult:
    """Executes ultra-fast procedural architectural preview in < 50ms.
    
    Args:
        image: Original exterior house photo (Path or PIL Image).
        inpaint_mask: Binary mask where 255=renovatable wall, 0=protected window/car.
        material_id: Key from materials catalog (e.g. 'stone_cladding', 'wpc_panels').
        blend_intensity: Texture opacity factor (0.0 to 1.0, default: 0.88).
        custom_bgr: Optional custom tint (B, G, R).
        
    Returns:
        PreviewResult containing the preview image and execution metrics.
    """
    start_time = time.perf_counter()

    # 1. Load inputs
    if isinstance(image, (str, Path)):
        orig_pil = Image.open(str(image)).convert("RGB")
    else:
        orig_pil = image.convert("RGB")

    if isinstance(inpaint_mask, (str, Path)):
        mask_pil = Image.open(str(inpaint_mask)).convert("L")
    else:
        mask_pil = inpaint_mask.convert("L")

    w, h = orig_pil.size

    # Validate dimensions
    if (mask_pil.width, mask_pil.height) != (w, h):
        mask_pil = mask_pil.resize((w, h), Image.Resampling.NEAREST)

    # 2. Convert to OpenCV BGR
    orig_bgr = cv2.cvtColor(np.array(orig_pil), cv2.COLOR_RGB2BGR)

    # 3. Retrieve material configuration
    mat_key = material_id.lower().strip().replace(" ", "_").replace("-", "_")
    config = MATERIAL_PREVIEW_PALETTES.get(
        mat_key,
        MATERIAL_PREVIEW_PALETTES["weatherproof_paint"]
    )

    base_bgr = custom_bgr if custom_bgr is not None else config["base_bgr"]
    texture_type = config["texture_type"]
    roughness = config["roughness"]

    # 4. Generate procedural texture
    procedural_tex = _generate_procedural_texture(
        width=w,
        height=h,
        texture_type=texture_type,
        base_bgr=base_bgr,
        roughness=roughness,
    )

    # 5. Blend with original physical building illumination (LAB luminance transfer)
    blended_bgr = _blend_luminance(
        original_bgr=orig_bgr,
        texture_bgr=procedural_tex,
        alpha=blend_intensity,
    )
    blended_rgb = cv2.cvtColor(blended_bgr, cv2.COLOR_BGR2RGB)
    blended_pil = Image.fromarray(blended_rgb)

    # 6. Apply 100% mathematical pixel-lock on protected elements (windows, doors, sky)
    final_preview = apply_pixel_lock(orig_pil, blended_pil, mask_pil)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    return PreviewResult(
        preview_image=final_preview,
        original_image=orig_pil,
        inpaint_mask=mask_pil,
        material_id=material_id,
        execution_time_ms=round(elapsed_ms, 2),
        output_dimensions=(w, h),
    )
