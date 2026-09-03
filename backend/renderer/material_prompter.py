"""Material Prompt Engineering for Architectural Facade Inpainting (Phase 3).

Translates civil material catalog selections into photorealistic diffusion prompts,
calibrated with negative weights to prevent warping, hallucination, or oversaturation.
"""

from typing import Dict, Optional, Tuple
from backend.engine.materials_catalog import MATERIALS_CATALOG


MATERIAL_PROMPT_CONFIGS: Dict[str, Dict[str, str]] = {
    "stone_cladding": {
        "material_name": "Natural Granite / Slate Stone Cladding",
        "prompt": (
            "modern residential house exterior, exterior facade walls renovated with dark slate and "
            "grey split-face granite stone brick cladding, rustic interlocking stone masonry veneer, "
            "deep textured stone relief, high-end architectural finish, sharp architectural photo, 8k uhd, daylight"
        ),
        "negative_prompt": (
            "smooth white plaster, plain painted wall, distorted windows, broken frames, fake wallpaper pattern, "
            "blurry textures, cartoon, plastic, warped perspective, artifacts, low resolution"
        ),
    },
    "weatherproof_paint": {
        "material_name": "Exterior Weatherproof Acrylic Emulsion",
        "prompt": (
            "modern residential house exterior, exterior facade walls newly painted in rich modern warm "
            "terracotta ochre weatherproof exterior emulsion paint, smooth matte finish, elegant clean "
            "architectural contrast, professional exterior photography, 8k resolution, soft daylight"
        ),
        "negative_prompt": (
            "plain white wall, distorted windows, warped window frames, broken glass, peeling paint, stains, cracks, "
            "low resolution, cartoon, cgi render, 3d model, blurry, oversaturated"
        ),
    },
    "textured_stucco": {
        "material_name": "Textured Stucco Finish",
        "prompt": (
            "contemporary residential house facade, exterior walls finished in warm sand-colored textured "
            "rustic stucco plaster, earthy architectural plastering texture, heavy granular tactile masonry finish, "
            "photorealistic architectural photography, sharp focus, natural daylight, 8k uhd"
        ),
        "negative_prompt": (
            "smooth white wall, deformed window frames, warped architecture, glossy plastic, mud, dirty walls, "
            "blurry, artifacts, cgi, sketch, painting"
        ),
    },
    "vitrified_tiles": {
        "material_name": "Exterior Vitrified Wall Tiles",
        "prompt": (
            "sleek contemporary house facade, exterior wall clad with large format charcoal grey matte porcelain "
            "vitrified exterior facade tiles, visible architectural tile joints, modern luxury villa, "
            "photorealistic architectural photography, sharp focus, 8k resolution"
        ),
        "negative_prompt": (
            "cracked tiles, white plaster, misalignment, warped windows, glossy reflective glare, cartoon, blurry, "
            "low quality, distorted lines"
        ),
    },
    "wpc_panels": {
        "material_name": "WPC Exterior Louver Panels",
        "prompt": (
            "modern architectural exterior facade, accent wall featuring rich dark walnut wood-plastic "
            "composite (WPC) horizontal fluted louver cladding slats, linear architectural rhythm, contemporary "
            "luxury villa exterior, crisp wooden slats, photorealistic architectural photo, 8k"
        ),
        "negative_prompt": (
            "white wall, warped slats, bent wood, distorted window mullions, low resolution, blurry, "
            "cartoon, plastic shine, noisy render"
        ),
    },
    "glass_railing": {
        "material_name": "Frameless Toughened Glass Railing",
        "prompt": (
            "modern residential balcony, frameless clear tempered safety glass railing balustrade with "
            "stainless steel base spigots, sleek minimalist architecture, clear transparent glass, "
            "architectural photo, sharp focus, 8k"
        ),
        "negative_prompt": (
            "cloudy glass, frosted texture, warped railing, broken balcony, blurry, low resolution, "
            "distorted edges, cartoon"
        ),
    },
    "metal_railing": {
        "material_name": "Powder-Coated Metal Railing",
        "prompt": (
            "contemporary residential balcony, sleek architectural matte black powder-coated vertical "
            "slat metal balustrade railing, clean parallel lines, modern architectural design, "
            "sharp focus, natural lighting, 8k"
        ),
        "negative_prompt": (
            "bent metal, rusty railing, crooked bars, distorted perspective, blurry, low resolution, artifacts"
        ),
    },
}

DEFAULT_NEGATIVE_PROMPT = (
    "distorted architecture, warped walls, broken windows, deformed frames, blurry, low resolution, "
    "unrealistic textures, cartoon, CGI render, video game, oversaturated, messy artifacts, noisy"
)


def get_material_prompt(
    material_id: str,
    custom_style: Optional[str] = None,
) -> Tuple[str, str]:
    """Retrieves the tuned prompt and negative prompt for a civil material.
    
    Args:
        material_id: Key matching MATERIALS_CATALOG (e.g. 'stone_cladding').
        custom_style: Optional style modifier (e.g. 'minimalist modern', 'scandinavian warm').
        
    Returns:
        Tuple of (positive_prompt, negative_prompt).
    """
    normalized_id = material_id.lower().strip().replace(" ", "_").replace("-", "_")

    if normalized_id in MATERIAL_PROMPT_CONFIGS:
        cfg = MATERIAL_PROMPT_CONFIGS[normalized_id]
        pos = cfg["prompt"]
        neg = cfg["negative_prompt"]
    elif normalized_id in MATERIALS_CATALOG:
        mat = MATERIALS_CATALOG[normalized_id]
        pos = (
            f"modern residential house exterior, exterior facade walls newly finished with {mat.name}, "
            f"high quality architectural photography, 8k resolution, natural daylight"
        )
        neg = DEFAULT_NEGATIVE_PROMPT
    else:
        # Fallback for generic architectural prompt
        clean_name = material_id.replace("_", " ").title()
        pos = (
            f"modern residential house exterior, exterior facade finished with premium {clean_name}, "
            f"clean architectural lines, professional photography, 8k uhd"
        )
        neg = DEFAULT_NEGATIVE_PROMPT

    if custom_style:
        pos = f"{custom_style}, {pos}"

    return pos, neg


def list_supported_materials() -> Dict[str, str]:
    """Returns a dict mapping material IDs to their display names."""
    return {k: v["material_name"] for k, v in MATERIAL_PROMPT_CONFIGS.items()}
