"""Comprehensive Unit Tests for Phase 3: AI Rendering Module."""

import numpy as np
from PIL import Image
import pytest

from backend.engine.materials_catalog import MATERIALS_CATALOG
from backend.renderer.controlnet_guide import build_canny_control_image
from backend.renderer.material_prompter import (
    get_material_prompt,
    list_supported_materials,
    MATERIAL_PROMPT_CONFIGS,
    DEFAULT_NEGATIVE_PROMPT,
)
from backend.renderer.inpainter import (
    apply_pixel_lock,
    prepare_diffusion_dimensions,
)
from backend.renderer.before_after_exporter import generate_before_after_comparison


# -------------------------------------------------------------------------
# 1. ControlNet Canny Edge Guide Tests
# -------------------------------------------------------------------------

def test_canny_edge_generator_output_format():
    """Verify Canny edge generator produces a 3-channel PIL Image matching input size."""
    w, h = 400, 300
    # Create test image with distinct geometric contrast
    img_np = np.zeros((h, w, 3), dtype=np.uint8)
    img_np[50:150, 50:200] = 255  # White rectangle
    pil_img = Image.fromarray(img_np)

    edge_img = build_canny_control_image(pil_img)

    assert isinstance(edge_img, Image.Image)
    assert edge_img.size == (w, h)
    assert edge_img.mode == "RGB"

    edge_np = np.array(edge_img)
    assert edge_np.shape == (h, w, 3)
    # The edges should be detected along the rectangle perimeter
    assert np.any(edge_np > 0)


def test_canny_edge_generator_numpy_input():
    """Verify Canny edge generator accepts raw BGR numpy arrays."""
    img_bgr = np.full((200, 200, 3), 100, dtype=np.uint8)
    img_bgr[50:150, 50:150] = 255
    edge_img = build_canny_control_image(img_bgr)
    assert edge_img.size == (200, 200)


# -------------------------------------------------------------------------
# 2. Material Prompter Tests
# -------------------------------------------------------------------------

def test_material_prompter_catalog_coverage():
    """Verify all materials in civil catalog produce valid, detailed diffusion prompts."""
    for mat_id in MATERIALS_CATALOG.keys():
        pos, neg = get_material_prompt(mat_id)
        assert pos != "", f"Positive prompt for {mat_id} must not be empty"
        assert neg != "", f"Negative prompt for {mat_id} must not be empty"
        assert len(pos) > 20, f"Prompt for {mat_id} should be descriptive"
        # Verify negative prompt includes architectural distortion guards
        assert "distorted" in neg or "warped" in neg or "blurry" in neg


def test_material_prompter_custom_style_injection():
    """Verify custom architectural style modifier prepends properly to the prompt."""
    pos, _ = get_material_prompt("stone_cladding", custom_style="modern scandinavian")
    assert pos.startswith("modern scandinavian,")


def test_list_supported_materials():
    """Verify list_supported_materials returns clean display mappings."""
    mats = list_supported_materials()
    assert "stone_cladding" in mats
    assert "weatherproof_paint" in mats
    assert "vitrified_tiles" in mats


# -------------------------------------------------------------------------
# 3. Pixel Lock Guarantee Tests (Mathematical Proof)
# -------------------------------------------------------------------------

def test_pixel_lock_mathematical_guarantee():
    """Verify that any pixel with mask=0 is strictly 100% identical to original."""
    w, h = 100, 100
    # Original image: All Blue (0, 0, 255)
    orig_np = np.zeros((h, w, 3), dtype=np.uint8)
    orig_np[:, :] = (0, 0, 255)
    orig_pil = Image.fromarray(orig_np)

    # Generated image: All Red (255, 0, 0)
    gen_np = np.zeros((h, w, 3), dtype=np.uint8)
    gen_np[:, :] = (255, 0, 0)
    gen_pil = Image.fromarray(gen_np)

    # Inpaint mask: Center 40x40 is protected (0), outer region is renovatable (255)
    mask_np = np.full((h, w), 255, dtype=np.uint8)
    mask_np[30:70, 30:70] = 0  # Protected opening (e.g. window)
    mask_pil = Image.fromarray(mask_np)

    # Apply pixel lock
    locked_img = apply_pixel_lock(orig_pil, gen_pil, mask_pil)
    result_np = np.array(locked_img)

    # 1. Protected region (30:70, 30:70) must be 100% Blue (original)
    protected_crop = result_np[30:70, 30:70]
    expected_blue = np.zeros_like(protected_crop)
    expected_blue[:, :] = (0, 0, 255)
    assert np.array_equal(protected_crop, expected_blue), "Protected region must be identical to original"

    # 2. Renovated region (e.g. 0:20, 0:20) must be 100% Red (generated)
    renovated_crop = result_np[0:20, 0:20]
    expected_red = np.zeros_like(renovated_crop)
    expected_red[:, :] = (255, 0, 0)
    assert np.array_equal(renovated_crop, expected_red), "Renovated region must match generated texture"


# -------------------------------------------------------------------------
# 4. Diffusion Dimensions Preparation Tests
# -------------------------------------------------------------------------

def test_prepare_diffusion_dimensions_multiples_of_eight():
    """Verify diffusion dimensions are strictly divisible by 8."""
    test_sizes = [
        (1200, 900),
        (1920, 1080),
        (5000, 3333),
        (750, 1334),
    ]
    for w, h in test_sizes:
        nw, nh = prepare_diffusion_dimensions(w, h, max_dim=1024)
        assert nw % 8 == 0, f"Width {nw} must be divisible by 8"
        assert nh % 8 == 0, f"Height {nh} must be divisible by 8"
        assert nw <= 1024 and nh <= 1024


# -------------------------------------------------------------------------
# 5. Before & After Comparison Exporter Tests
# -------------------------------------------------------------------------

def test_before_after_comparison_dimensions_and_divider(tmp_path):
    """Verify side-by-side comparison stitching and dimensions."""
    orig = Image.new("RGB", (300, 200), (100, 150, 200))
    redesign = Image.new("RGB", (300, 200), (200, 150, 100))
    divider_w = 6

    out_file = tmp_path / "comparison_test.png"
    comparison = generate_before_after_comparison(orig, redesign, output_path=out_file, divider_width=divider_w)

    assert out_file.exists()
    assert comparison.size == (300 + divider_w + 300, 200)

    # Check center divider color
    comp_np = np.array(comparison)
    center_x = 300 + (divider_w // 2)
    # Warm white divider: (245, 240, 235)
    assert np.all(comp_np[:, center_x] == (245, 240, 235))
