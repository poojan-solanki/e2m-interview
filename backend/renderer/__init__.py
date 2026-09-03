"""Phase 3: AI Rendering & Architectural Facade Inpainting Module.

Provides ControlNet-guided inpainting with authentic civil material textures,
4GB VRAM GPU memory optimizations, and before/after comparison generation.
"""

from .controlnet_guide import build_canny_control_image
from .material_prompter import (
    get_material_prompt,
    list_supported_materials,
    MATERIAL_PROMPT_CONFIGS,
)
from .before_after_exporter import generate_before_after_comparison
from .instant_preview import render_instant_preview, PreviewResult
from .inpainter import (
    FacadeInpainter,
    RenderResult,
    apply_pixel_lock,
    prepare_diffusion_dimensions,
)

__all__ = [
    "build_canny_control_image",
    "get_material_prompt",
    "list_supported_materials",
    "MATERIAL_PROMPT_CONFIGS",
    "generate_before_after_comparison",
    "render_instant_preview",
    "PreviewResult",
    "FacadeInpainter",
    "RenderResult",
    "apply_pixel_lock",
    "prepare_diffusion_dimensions",
]
