"""Core Architectural Facade Inpainter with ControlNet Canny Guidance (Phase 3).

Applies selected civil materials to segmented facade walls using Stable Diffusion Inpainting,
while enforcing a 100% mathematical pixel-lock on windows, doors, vehicles, and foreground.
Optimized for consumer GPUs (e.g. 4GB RTX 3050) using FP16, model CPU offload, and attention slicing.
"""

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Optional, Tuple, Union
import cv2
import numpy as np
from PIL import Image
import torch

from .controlnet_guide import build_canny_control_image
from .material_prompter import get_material_prompt

# Lazy imports for diffusers components to allow lightweight unit testing
try:
    from diffusers import (
        ControlNetModel,
        StableDiffusionControlNetInpaintPipeline,
        DPMSolverMultistepScheduler,
    )
except ImportError:
    ControlNetModel = None
    StableDiffusionControlNetInpaintPipeline = None
    DPMSolverMultistepScheduler = None


@dataclass
class RenderResult:
    """Encapsulates the rendered architectural visual and execution metadata."""
    redesigned_image: Image.Image
    original_image: Image.Image
    control_image: Image.Image
    inpaint_mask: Image.Image
    material_id: str
    prompt: str
    negative_prompt: str
    inference_time_sec: float
    output_dimensions: Tuple[int, int]


def apply_pixel_lock(
    original_image: Image.Image,
    generated_image: Image.Image,
    inpaint_mask: Image.Image,
) -> Image.Image:
    """Guarantees 100% pixel-perfect preservation of all non-renovation areas.
    
    Any pixel with mask value 0 (windows, doors, car, painter, sky) is directly
    restored from the original photo, eliminating any potential edge bleeding.
    """
    orig_np = np.array(original_image.convert("RGB"))
    w, h = original_image.size

    # Resize generated output to exact original photo dimensions
    gen_resized = generated_image.convert("RGB").resize((w, h), Image.Resampling.LANCZOS)
    gen_np = np.array(gen_resized)

    # Resize mask using nearest neighbor to keep hard binary edges
    mask_resized = inpaint_mask.convert("L").resize((w, h), Image.Resampling.NEAREST)
    mask_np = np.array(mask_resized)

    # 255 = renovatable surface (use AI-generated texture)
    # 0   = protected element (lock 100% original pixels)
    mask_bool = (mask_np > 128)[:, :, None]
    result_np = np.where(mask_bool, gen_np, orig_np)
    return Image.fromarray(result_np)


def prepare_diffusion_dimensions(width: int, height: int, max_dim: int = 1024) -> Tuple[int, int]:
    """Calculates optimal dimensions for diffusion, ensuring both are multiples of 8."""
    scale = min(1.0, max_dim / max(width, height))
    new_w = int(round(width * scale / 8.0) * 8)
    new_h = int(round(height * scale / 8.0) * 8)
    # Ensure minimum 512 for quality
    new_w = max(512, new_w)
    new_h = max(512, new_h)
    return (new_w, new_h)


class FacadeInpainter:
    """Manages ControlNet + SD Inpainting pipeline with 4GB VRAM safety guardrails."""

    def __init__(
        self,
        base_model_id: str = "runwayml/stable-diffusion-inpainting",
        controlnet_model_id: str = "lllyasviel/control_v11p_sd15_canny",
        device: Optional[str] = None,
        low_vram_mode: bool = True,
    ):
        self.base_model_id = base_model_id
        self.controlnet_model_id = controlnet_model_id
        self.low_vram_mode = low_vram_mode

        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.pipe = None

    def _ensure_pipeline_loaded(self):
        """Lazy loader for ControlNet Inpaint pipeline with memory offloading."""
        if self.pipe is not None:
            return

        if StableDiffusionControlNetInpaintPipeline is None:
            raise ImportError(
                "diffusers is not installed or available. "
                "Ensure 'diffusers>=0.30' is installed."
            )

        print(f"Loading ControlNet condition model ({self.controlnet_model_id})...")
        controlnet = ControlNetModel.from_pretrained(
            self.controlnet_model_id,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
        )

        print(f"Loading Base Inpainting pipeline ({self.base_model_id})...")
        pipe = StableDiffusionControlNetInpaintPipeline.from_pretrained(
            self.base_model_id,
            controlnet=controlnet,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            safety_checker=None,
        )

        # Use DPMSolverMultistepScheduler with Karras sigmas for sharp architectural masonry
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            pipe.scheduler.config,
            use_karras_sigmas=True,
        )

        if self.device == "cuda":
            if self.low_vram_mode:
                # Enables sequential component offloading (keeps VRAM ~2.2 GB)
                pipe.enable_model_cpu_offload()
                pipe.enable_attention_slicing()
            else:
                pipe.to("cuda")

        self.pipe = pipe
        print("✓ Inpainting pipeline ready.")

    def render_facade(
        self,
        image: Union[str, Path, Image.Image],
        inpaint_mask: Union[str, Path, Image.Image],
        material_id: str = "stone_cladding",
        custom_style: Optional[str] = None,
        num_inference_steps: int = 25,
        guidance_scale: float = 7.5,
        controlnet_conditioning_scale: float = 0.65,
        seed: Optional[int] = 42,
    ) -> RenderResult:
        """Executes ControlNet-guided inpainting with authentic architectural materials.
        
        Args:
            image: Source house photo (path or PIL Image).
            inpaint_mask: Binary mask where 255=renovatable wall, 0=locked element.
            material_id: Material key from materials catalog (e.g. 'stone_cladding').
            custom_style: Optional style modifier prompt.
            num_inference_steps: Number of denoising steps (default: 25).
            guidance_scale: Classifier-free guidance scale (default: 7.5).
            controlnet_conditioning_scale: Weight of Canny edge guidance (default: 0.65).
            seed: RNG seed for reproducible generation (default: 42).
            
        Returns:
            RenderResult containing the redesigned image and metadata.
        """
        start_time = time.time()

        # 1. Load and normalize inputs
        if isinstance(image, (str, Path)):
            orig_pil = Image.open(str(image)).convert("RGB")
        else:
            orig_pil = image.convert("RGB")

        if isinstance(inpaint_mask, (str, Path)):
            mask_pil = Image.open(str(inpaint_mask)).convert("L")
        else:
            mask_pil = inpaint_mask.convert("L")

        orig_w, orig_h = orig_pil.size

        # Safety Guard: Ensure mask dimensions match image dimensions
        if (mask_pil.width, mask_pil.height) != (orig_w, orig_h):
            raise ValueError(
                f"Dimension mismatch error! Input image is ({orig_w}x{orig_h}), but the inpaint mask is "
                f"({mask_pil.width}x{mask_pil.height}). The mask belongs to a different image! "
                f"Please run segmentation on {image} first to produce a matching mask."
            )

        # 2. Extract Canny edge condition from original image
        canny_control = build_canny_control_image(orig_pil)

        # 3. Scale images to diffusion-compatible resolution (multiple of 8, max 1024)
        diff_w, diff_h = prepare_diffusion_dimensions(orig_w, orig_h, max_dim=1024)
        input_image_scaled = orig_pil.resize((diff_w, diff_h), Image.Resampling.LANCZOS)
        mask_scaled = mask_pil.resize((diff_w, diff_h), Image.Resampling.NEAREST)
        control_scaled = canny_control.resize((diff_w, diff_h), Image.Resampling.NEAREST)

        # 4. Generate prompts
        prompt, negative_prompt = get_material_prompt(material_id, custom_style=custom_style)

        # 5. Load model and run inpainting
        self._ensure_pipeline_loaded()

        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device if not self.low_vram_mode else "cpu").manual_seed(seed)

        with torch.inference_mode():
            output = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                image=input_image_scaled,
                mask_image=mask_scaled,
                control_image=control_scaled,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                controlnet_conditioning_scale=controlnet_conditioning_scale,
                generator=generator,
            )

        raw_generated = output.images[0]

        # 6. Apply 100% mathematical pixel-lock on protected elements
        locked_result = apply_pixel_lock(orig_pil, raw_generated, mask_pil)

        elapsed = time.time() - start_time

        return RenderResult(
            redesigned_image=locked_result,
            original_image=orig_pil,
            control_image=canny_control,
            inpaint_mask=mask_pil,
            material_id=material_id,
            prompt=prompt,
            negative_prompt=negative_prompt,
            inference_time_sec=round(elapsed, 2),
            output_dimensions=(orig_w, orig_h),
        )
