"""EXIF Metadata Extractor for Camera Calibration & Metrology (Requirement 5.5).

Extracts focal length, 35mm equivalent, camera model, and GPS tags to assist
in perspective estimation, while providing graceful fallback when metadata is stripped.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Tuple, Union
from PIL import Image, ExifTags


@dataclass
class ExifMetadata:
    """Parsed camera and capture metadata."""
    has_exif: bool
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    focal_length_mm: Optional[float] = None
    focal_length_35mm_equiv: Optional[float] = None
    estimated_sensor_width_mm: Optional[float] = None
    focal_length_pixels: Optional[float] = None
    f_number: Optional[float] = None
    iso: Optional[int] = None
    capture_time: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    gps_altitude_m: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _convert_gps_to_decimal(coords, ref: str) -> Optional[float]:
    """Converts GPS DMS tuples to decimal degrees."""
    try:
        degrees = float(coords[0])
        minutes = float(coords[1]) / 60.0
        seconds = float(coords[2]) / 3600.0
        decimal = degrees + minutes + seconds
        if ref in ["S", "W"]:
            decimal = -decimal
        return round(decimal, 6)
    except Exception:
        return None


def extract_exif(
    image_path: Union[str, Path],
    image_width_px: Optional[int] = None,
) -> ExifMetadata:
    """Reads and parses camera metadata from an image file.
    
    Args:
        image_path: Path to the JPEG or PNG file.
        image_width_px: Optional width of the image to compute focal length in pixels.
        
    Returns:
        ExifMetadata object. If metadata is missing or stripped, returns has_exif=False.
    """
    path = Path(image_path)
    if not path.exists():
        return ExifMetadata(has_exif=False)

    try:
        with Image.open(path) as img:
            w, h = img.size
            if image_width_px is None:
                image_width_px = w

            raw_exif = img.getexif()
            if not raw_exif:
                return ExifMetadata(has_exif=False)

            # Map tag IDs to tag names
            tag_map = {ExifTags.TAGS.get(k, k): v for k, v in raw_exif.items()}

            # Handle SubIFD / ExifIFD for extended camera tags
            if hasattr(raw_exif, "get_ifd"):
                try:
                    exif_ifd = raw_exif.get_ifd(ExifTags.IFD.Exif)
                    for k, v in exif_ifd.items():
                        tag_map[ExifTags.TAGS.get(k, k)] = v
                except Exception:
                    pass

                try:
                    gps_ifd = raw_exif.get_ifd(ExifTags.IFD.GPSInfo)
                    for k, v in gps_ifd.items():
                        tag_map[f"GPS_{ExifTags.GPSTAGS.get(k, k)}"] = v
                except Exception:
                    pass

            camera_make = str(tag_map.get("Make", "")).strip() or None
            camera_model = str(tag_map.get("Model", "")).strip() or None
            capture_time = str(tag_map.get("DateTime", "")).strip() or None

            # Focal Length extraction
            focal_length_mm = None
            raw_fl = tag_map.get("FocalLength")
            if raw_fl is not None:
                try:
                    focal_length_mm = float(raw_fl)
                except Exception:
                    pass

            # 35mm equivalent focal length
            fl_35mm = None
            raw_35mm = tag_map.get("FocalLengthIn35mmFilm")
            if raw_35mm is not None:
                try:
                    fl_35mm = float(raw_35mm)
                except Exception:
                    pass

            # Estimate sensor width (Standard full-frame 35mm film width is 36.0mm)
            # Crop factor = fl_35mm / focal_length_mm
            # Sensor width = 36.0 / Crop factor = 36.0 * (focal_length_mm / fl_35mm)
            sensor_width_mm = None
            if focal_length_mm and fl_35mm and fl_35mm > 0:
                sensor_width_mm = round(36.0 * (focal_length_mm / fl_35mm), 2)
            elif focal_length_mm:
                # Default smartphone sensor assumption if 35mm equivalent is not reported:
                # Most consumer smartphones have ~1/1.7" to 1/2.5" sensor (width ~6.4mm)
                sensor_width_mm = 6.4

            # Focal length in pixels
            focal_length_px = None
            if focal_length_mm and sensor_width_mm and sensor_width_mm > 0 and image_width_px:
                focal_length_px = round((focal_length_mm * image_width_px) / sensor_width_mm, 1)

            # Aperture and ISO
            f_number = None
            raw_fn = tag_map.get("FNumber")
            if raw_fn is not None:
                try:
                    f_number = float(raw_fn)
                except Exception:
                    pass

            iso = None
            raw_iso = tag_map.get("ISOSpeedRatings") or tag_map.get("PhotographicSensitivity")
            if raw_iso is not None:
                try:
                    iso = int(raw_iso)
                except Exception:
                    pass

            # GPS extraction
            lat = None
            lon = None
            alt = None
            raw_lat = tag_map.get("GPS_GPSLatitude")
            lat_ref = tag_map.get("GPS_GPSLatitudeRef", "N")
            raw_lon = tag_map.get("GPS_GPSLongitude")
            lon_ref = tag_map.get("GPS_GPSLongitudeRef", "E")
            raw_alt = tag_map.get("GPS_GPSAltitude")

            if raw_lat and lat_ref:
                lat = _convert_gps_to_decimal(raw_lat, str(lat_ref))
            if raw_lon and lon_ref:
                lon = _convert_gps_to_decimal(raw_lon, str(lon_ref))
            if raw_alt is not None:
                try:
                    alt = round(float(raw_alt), 1)
                except Exception:
                    pass

            has_valid_info = bool(camera_make or camera_model or focal_length_mm or lat)

            return ExifMetadata(
                has_exif=has_valid_info,
                camera_make=camera_make,
                camera_model=camera_model,
                focal_length_mm=focal_length_mm,
                focal_length_35mm_equiv=fl_35mm,
                estimated_sensor_width_mm=sensor_width_mm,
                focal_length_pixels=focal_length_px,
                f_number=f_number,
                iso=iso,
                capture_time=capture_time,
                gps_latitude=lat,
                gps_longitude=lon,
                gps_altitude_m=alt,
            )

    except Exception:
        return ExifMetadata(has_exif=False)
