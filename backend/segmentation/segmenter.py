"""Core Architectural Facade Segmenter using Meta SAM 3 (Segment Anything Model 3).

Detects walls, windows, balconies, pillars, roof overhangs/cantilevers, and foreground objects
from residential building photos using zero-shot vision-language text prompts.
Extracts polygon coordinate representations and assigns civil material categories.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import os
import sys

# Configure PyTorch memory allocator to avoid VRAM fragmentation on consumer GPUs (e.g. RTX 3050 4GB)
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import cv2
import numpy as np
from PIL import Image
import torch

from backend.engine.area_estimator import ScaleFactor, compute_net_area
from .quality_checker import check_image_quality, ImageQualityReport
from .exif_reader import extract_exif, ExifMetadata
from .area_calculator import (
    compute_zone_measurements,
    calibrate_scale_from_detection,
    polygon_area_pixels,
    polygon_bounding_box,
)

# Import SAM 3 from environment, vendor/sam3, or sibling sam3 repo
try:
    import sam3
except ImportError:
    candidate_paths = [
        Path(__file__).resolve().parent.parent.parent.parent / "sam3",
        Path(__file__).resolve().parent.parent.parent / "sam3",
        Path(__file__).resolve().parent.parent.parent / "vendor" / "sam3",
    ]
    for cp in candidate_paths:
        if cp.exists() and str(cp) not in sys.path:
            sys.path.insert(0, str(cp))
            break
    try:
        import sam3
    except ImportError:
        sam3 = None

if sam3 is not None:
    from sam3 import build_sam3_image_model
    from sam3.model.sam3_image_processor import Sam3Processor
else:
    build_sam3_image_model = None
    Sam3Processor = None


ARCHITECTURAL_CONCEPTS = [
    "window",
    "exterior wall",
    "building facade",
    "balcony",
    "porch column",
    "roof overhang",
    "person",
    "car",
]

# Mapping from text prompt concepts to normalized civil categories
CONCEPT_MAPPING = {
    "window": {
        "label": "window",
        "display_prefix": "Window",
        "category": "opening",
        "protected": True,
        "materials": [],
    },
    "exterior wall": {
        "label": "wall",
        "display_prefix": "Wall",
        "category": "surface",
        "protected": False,
        "materials": ["weatherproof_paint", "textured_stucco", "vitrified_tiles", "wpc_panels"],
    },
    "building facade": {
        "label": "wall",
        "display_prefix": "Wall",
        "category": "surface",
        "protected": False,
        "materials": ["weatherproof_paint", "textured_stucco", "vitrified_tiles", "wpc_panels"],
    },
    "balcony": {
        "label": "balcony_railing",
        "display_prefix": "Balcony",
        "category": "railing",
        "protected": False,
        "materials": ["glass_railing", "metal_railing"],
    },
    "porch column": {
        "label": "pillar",
        "display_prefix": "Pillar",
        "category": "surface",
        "protected": False,
        "materials": ["stone_cladding", "textured_stucco", "weatherproof_paint"],
    },
    "roof overhang": {
        "label": "roof_parapet",
        "display_prefix": "Roof Overhang",
        "category": "surface",
        "protected": False,
        "materials": ["weatherproof_paint", "stone_cladding"],
    },
    "person": {
        "label": "person",
        "display_prefix": "Person",
        "category": "foreground",
        "protected": True,
        "materials": [],
    },
    "car": {
        "label": "car",
        "display_prefix": "Car",
        "category": "foreground",
        "protected": True,
        "materials": [],
    },
}


@dataclass
class SegmentedZone:
    """Represents a single detected architectural zone with spatial and takeoff metadata."""
    id: str
    label: str
    display_name: str
    category: str  # "surface", "opening", "railing", "foreground"
    is_protected: bool  # True for windows/doors/foreground (must remain unchanged during inpaint)
    confidence: float
    polygon: List[List[float]]  # [[x1, y1], [x2, y2], ...]
    bbox: List[int]  # [x_min, y_min, x_max, y_max]
    pixel_area: float
    gross_area_sqft: float
    deductions_sqft: float
    net_area_sqft: float
    running_feet: float
    recommended_materials: List[str]
    mask_filename: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SegmentationResult:
    """Complete facade parsing result containing all detected zones and metrology."""
    image_path: str
    image_dimensions: Tuple[int, int]  # (width, height)
    quality_report: ImageQualityReport
    exif_metadata: ExifMetadata
    calibration_method: str
    scale_factor: ScaleFactor
    zones: List[SegmentedZone]
    total_gross_wall_area_sqft: float
    total_window_area_sqft: float
    net_paintable_wall_area_sqft: float

    def to_dict(self) -> dict:
        return {
            "image_path": str(self.image_path),
            "image_dimensions": {"width": self.image_dimensions[0], "height": self.image_dimensions[1]},
            "quality_report": self.quality_report.to_dict(),
            "exif_metadata": self.exif_metadata.to_dict(),
            "calibration_method": self.calibration_method,
            "scale_factor": {
                "meters_per_pixel": round(self.scale_factor.meters_per_pixel, 5),
                "feet_per_pixel": round(self.scale_factor.feet_per_pixel, 5),
                "sq_feet_per_sq_pixel": round(self.scale_factor.sq_feet_per_sq_pixel, 6),
            },
            "total_gross_wall_area_sqft": round(self.total_gross_wall_area_sqft, 2),
            "total_window_area_sqft": round(self.total_window_area_sqft, 2),
            "net_paintable_wall_area_sqft": round(self.net_paintable_wall_area_sqft, 2),
            "zones": [z.to_dict() for z in self.zones],
        }


class FacadeSegmenter:
    """Manages model loading, inference, and polygon extraction for architectural facades."""

    def __init__(
        self,
        model_name: str = "weights/sam3.pt",
        device: Optional[str] = None,
        conf_threshold: float = 0.35,
    ):
        self.model_name = model_name
        self.conf_threshold = conf_threshold
        
        # Auto-detect CUDA if available
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        self.model = None
        self.processor = None

    def _get_bpe_path(self) -> str:
        """Locates the BPE vocabulary file needed by SAM 3's text encoder."""
        if sam3 is not None:
            pkg_path = Path(sam3.__file__).parent / "assets" / "bpe_simple_vocab_16e6.txt.gz"
            if pkg_path.exists():
                return str(pkg_path)
            
            repo_path = Path(sam3.__file__).parent.parent / "sam3" / "assets" / "bpe_simple_vocab_16e6.txt.gz"
            if repo_path.exists():
                return str(repo_path)

        # Fallback search paths in workspace
        for p in [
            Path("p:/Syncthing/personal-progs/sam3/sam3/assets/bpe_simple_vocab_16e6.txt.gz"),
            Path("../sam3/sam3/assets/bpe_simple_vocab_16e6.txt.gz"),
            Path("vendor/sam3/sam3/assets/bpe_simple_vocab_16e6.txt.gz"),
        ]:
            if p.exists():
                return str(p.resolve())

        return ""

    def _resolve_checkpoint(self) -> Optional[str]:
        """Resolves the checkpoint path on disk with graceful fallbacks."""
        # 1. Check explicit model_name path
        explicit = Path(self.model_name)
        if explicit.exists():
            return str(explicit.resolve())

        # 2. Check standard project weights path
        root = Path(__file__).resolve().parent.parent.parent
        proj_weight = root / "weights" / "sam3.pt"
        if proj_weight.exists():
            return str(proj_weight.resolve())

        # 3. Check HuggingFace local cache
        hf_cache = Path(r"P:\hf_model_cache\models--facebook--sam3\snapshots\3c879f39826c281e95690f02c7821c4de09afae7\sam3.pt")
        if hf_cache.exists():
            return str(hf_cache)

        return None

    def _ensure_model_loaded(self):
        """Lazy loader for SAM 3 to minimize startup latency."""
        if self.processor is not None:
            return

        if build_sam3_image_model is None:
            raise ImportError(
                "SAM 3 package is not installed or available in PYTHONPATH. "
                "Ensure 'sam3' is cloned or installed via pip."
            )

        ckpt_path = self._resolve_checkpoint()
        bpe_path = self._get_bpe_path()

        if self.device == "cuda":
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

        load_from_hf = ckpt_path is None
        self.model = build_sam3_image_model(
            bpe_path=bpe_path if bpe_path else None,
            device=self.device,
            eval_mode=True,
            checkpoint_path=ckpt_path,
            load_from_HF=load_from_hf,
        )
        self.processor = Sam3Processor(self.model, confidence_threshold=self.conf_threshold)

    def segment_image(
        self,
        image_input: Union[str, Path, np.ndarray],
        known_door_height_m: float = 2.10,
        custom_prompts: Optional[List[str]] = None,
    ) -> SegmentationResult:
        """Runs full segmentation and metrology pipeline on a facade image.
        
        Args:
            image_input: Path to image file or BGR numpy array.
            known_door_height_m: Reference door height in meters for calibration.
            custom_prompts: Optional list of text concepts to segment.
            
        Returns:
            SegmentationResult with all detected zones, metrics, and opening deductions.
        """
        # 1. Image Quality Validation
        quality = check_image_quality(image_input)
        
        # Read image to memory (BGR)
        if isinstance(image_input, (str, Path)):
            img_path_str = str(image_input)
            img = cv2.imread(img_path_str)
            if img is None:
                raise ValueError(f"Could not load image from path: {img_path_str}")
            exif_data = extract_exif(img_path_str, image_width_px=img.shape[1])
        else:
            img = image_input
            img_path_str = "in_memory_array.jpg"
            exif_data = ExifMetadata(has_exif=False)

        orig_h, orig_w = img.shape[:2]
        prompts = custom_prompts or ARCHITECTURAL_CONCEPTS

        # Adaptive resolution scaling: Scale high-res images (e.g. 16MP/4K) to max 1280px for inference
        # to guarantee zero OOM errors on 4GB VRAM GPUs (e.g. RTX 3050), then scale polygons back 1:1.
        max_inference_dim = 1280
        scale = 1.0
        if max(orig_h, orig_w) > max_inference_dim:
            scale = max_inference_dim / max(orig_h, orig_w)
            inf_w = int(round(orig_w * scale))
            inf_h = int(round(orig_h * scale))
            inf_img = cv2.resize(img, (inf_w, inf_h), interpolation=cv2.INTER_AREA)
        else:
            inf_img = img
            inf_w, inf_h = orig_w, orig_h

        # Convert to PIL RGB for SAM 3
        img_rgb = cv2.cvtColor(inf_img, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(img_rgb)

        # 2. SAM 3 Inference
        self._ensure_model_loaded()
        if self.device == "cuda":
            torch.cuda.empty_cache()

        autocast_ctx = (
            torch.autocast("cuda", dtype=torch.bfloat16)
            if self.device == "cuda"
            else torch.nullcontext()
        )

        with torch.inference_mode(), autocast_ctx:
            inference_state = self.processor.set_image(pil_image)

            # Query all prompt concepts and extract to CPU numpy immediately to prevent state overwrite
            prompt_outputs = {}
            for prompt in prompts:
                out = self.processor.set_text_prompt(
                    state=inference_state,
                    prompt=prompt,
                )
                masks = out.get("masks")
                scores = out.get("scores")
                masks_np = [m.detach().cpu().numpy().squeeze() for m in masks] if masks is not None else []
                scores_np = [float(s) for s in scores] if scores is not None else []
                prompt_outputs[prompt] = (masks_np, scores_np)
                self.processor.reset_all_prompts(inference_state)

        if self.device == "cuda":
            torch.cuda.empty_cache()

        # 3. Collect Exclusion Masks (Car & Person foreground)
        car_mask = np.zeros((inf_h, inf_w), dtype=np.uint8)
        if "car" in prompt_outputs:
            for m_np in prompt_outputs["car"][0]:
                car_mask = cv2.bitwise_or(car_mask, (m_np > 0.5).astype(np.uint8) * 255)

        person_mask = np.zeros((inf_h, inf_w), dtype=np.uint8)
        if "person" in prompt_outputs:
            for m_np in prompt_outputs["person"][0]:
                person_mask = cv2.bitwise_or(person_mask, (m_np > 0.5).astype(np.uint8) * 255)

        foreground_exclusion = cv2.bitwise_or(car_mask, person_mask)

        # 4. Process Architectural Elements & Extract Clean Contours
        raw_zones = []

        # Priority order for zone extraction
        eval_order = ["window", "balcony", "porch column", "roof overhang", "exterior wall"]

        # First union masks for each category to eliminate redundant overlapping detections
        concept_combined_masks = {}
        for prompt in prompt_outputs:
            if prompt not in prompt_outputs:
                continue
            masks_np, scores_np = prompt_outputs[prompt]
            combined = np.zeros((inf_h, inf_w), dtype=np.uint8)
            for m_np in masks_np:
                combined = cv2.bitwise_or(combined, (m_np > 0.5).astype(np.uint8) * 255)
            concept_combined_masks[prompt] = combined

        # Clean windows: subtract car mask to exclude car windows
        window_mask = concept_combined_masks.get("window", np.zeros((inf_h, inf_w), dtype=np.uint8))
        window_mask = cv2.bitwise_and(window_mask, cv2.bitwise_not(car_mask))
        concept_combined_masks["window"] = window_mask

        # Clean wall: union exterior wall and building facade to handle both finished houses and raw masonry/commercial facades
        wall_raw = np.zeros((inf_h, inf_w), dtype=np.uint8)
        if "exterior wall" in concept_combined_masks:
            wall_raw = cv2.bitwise_or(wall_raw, concept_combined_masks["exterior wall"])
        if "building facade" in concept_combined_masks:
            wall_raw = cv2.bitwise_or(wall_raw, concept_combined_masks["building facade"])

        if np.sum(wall_raw > 0) > 0:
            wall_clean = wall_raw
            wall_clean = cv2.bitwise_and(wall_clean, cv2.bitwise_not(foreground_exclusion))
            wall_clean = cv2.bitwise_and(wall_clean, cv2.bitwise_not(window_mask))
            # Also subtract balcony and pillar from wall
            if "balcony" in concept_combined_masks:
                wall_clean = cv2.bitwise_and(wall_clean, cv2.bitwise_not(concept_combined_masks["balcony"]))
            if "porch column" in concept_combined_masks:
                wall_clean = cv2.bitwise_and(wall_clean, cv2.bitwise_not(concept_combined_masks["porch column"]))
            concept_combined_masks["exterior wall"] = wall_clean

        for prompt in eval_order:
            if prompt not in concept_combined_masks:
                continue

            m_bin = concept_combined_masks[prompt]
            if np.sum(m_bin > 0) < 500:
                continue

            cfg = CONCEPT_MAPPING.get(prompt, {
                "label": "surface",
                "display_prefix": "Surface",
                "category": "surface",
                "protected": False,
                "materials": ["weatherproof_paint"],
            })

            # Extract distinct continuous components (ZERO diagonal lines)
            contours, _ = cv2.findContours(m_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                cnt_area = cv2.contourArea(cnt)
                # Filter small noise fragments based on category
                min_area = 300 if cfg["label"] == "window" else 800
                if cnt_area < min_area:
                    continue

                # Simplify contour for crisp architectural edges
                approx = cv2.approxPolyDP(cnt, 1.5, True)
                if len(approx) < 3:
                    continue

                # Scale coordinates back to original image resolution (1:1 precision)
                poly_pts = [
                    [round(float(pt[0][0]) / scale, 1), round(float(pt[0][1]) / scale, 1)]
                    for pt in approx
                ]
                bbox = [
                    int(round(float(b) / scale))
                    for b in polygon_bounding_box(approx.reshape(-1, 2).tolist())
                ]

                zone_num = len(raw_zones) + 1
                raw_zones.append({
                    "id": f"zone_{zone_num:02d}_{cfg['label']}",
                    "label": cfg["label"],
                    "display_name": f"{cfg['display_prefix']} #{zone_num}",
                    "category": cfg["category"],
                    "is_protected": cfg["protected"],
                    "confidence": 0.90,
                    "polygon": poly_pts,
                    "bbox": bbox,
                    "recommended_materials": cfg["materials"],
                })

        # 5. Metrology Calibration (Tier 1 Anchor calibrated on original image dimensions)
        scale_factor, calib_method = calibrate_scale_from_detection(
            raw_zones,
            image_shape=(orig_h, orig_w),
            known_door_height_m=known_door_height_m,
        )

        # 6. Opening Deduction & Net Area Computation
        openings_area_sqft = 0.0
        for z in raw_zones:
            if z["is_protected"]:
                measurements = compute_zone_measurements(z["polygon"], scale_factor, is_linear=False)
                openings_area_sqft += measurements["area_sqft"]

        total_gross_wall = 0.0
        final_zones: List[SegmentedZone] = []

        for z in raw_zones:
            is_linear = z["category"] == "railing"
            measurements = compute_zone_measurements(z["polygon"], scale_factor, is_linear=is_linear)
            gross_area = measurements["area_sqft"]

            if z["label"] == "wall":
                total_gross_wall += gross_area
                deductions = min(openings_area_sqft, gross_area)
                net_area = max(0.0, gross_area - deductions)
            else:
                deductions = 0.0
                net_area = gross_area

            zone_obj = SegmentedZone(
                id=z["id"],
                label=z["label"],
                display_name=z["display_name"],
                category=z["category"],
                is_protected=z["is_protected"],
                confidence=z["confidence"],
                polygon=z["polygon"],
                bbox=z["bbox"],
                pixel_area=measurements["pixel_area"],
                gross_area_sqft=gross_area,
                deductions_sqft=round(deductions, 2),
                net_area_sqft=round(net_area, 2),
                running_feet=measurements["running_feet"],
                recommended_materials=z["recommended_materials"],
                mask_filename=f"{z['id']}_mask.png",
            )
            final_zones.append(zone_obj)

        net_wall_area = max(0.0, total_gross_wall - openings_area_sqft)

        return SegmentationResult(
            image_path=img_path_str,
            image_dimensions=(orig_w, orig_h),
            quality_report=quality,
            exif_metadata=exif_data,
            calibration_method=calib_method,
            scale_factor=scale_factor,
            zones=final_zones,
            total_gross_wall_area_sqft=round(total_gross_wall, 2),
            total_window_area_sqft=round(openings_area_sqft, 2),
            net_paintable_wall_area_sqft=round(net_wall_area, 2),
        )
