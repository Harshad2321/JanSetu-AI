"""
JanSetu AI — Secure Image Upload Sanitization Utility.

Responsible for:
- Enforcing the 10 MB upload ceiling
- Magic-byte and binary content verification via Pillow (not trusting file extension or MIME)
- Safe handling of corrupted files and decompression-bomb risks
- Orientation correction via EXIF transposition
- Complete EXIF stripping (removing GPS coords, camera serials, timestamps)
- Safe dimension bounding (min 100x100px, max 4096px downscaling)
- Re-encoding to clean, optimized JPEG format suitable for Groq vision models
- Zero-leakage privacy-preserving logging
"""

from __future__ import annotations

import base64
import io
import logging
from typing import Optional, Tuple
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.incident import (
    ImageQualityAssessment,
    EvidenceOutcome,
    EvidenceRecommendation,
    PhotoEvidenceAnalysis,
)

# Configure logger with zero sensitive payload logging
logger = logging.getLogger("jansetu.image_sanitizer")

# ============================================================================
# Operational Constraints & Thresholds
# ============================================================================

MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB hard upload ceiling
SUPPORTED_FORMATS: tuple[str, ...] = ("JPEG", "PNG", "WEBP")
MIN_DIMENSION_PX: int = 100                     # Under 100px flagged as TOO_SMALL
MAX_DIMENSION_PX: int = 4096                    # Upper dimension boundary
SAFE_DECOMPRESSION_PIXELS: int = 25_000_000     # 25 MP ceiling protecting against zip/decompression bombs
DEFAULT_JPEG_QUALITY: int = 88                  # High visual clarity with efficient token payload size


# Set Pillow global decompression bomb limit
Image.MAX_IMAGE_PIXELS = SAFE_DECOMPRESSION_PIXELS


# ============================================================================
# Sanitization Result Models
# ============================================================================

class SanitizedImageResult(BaseModel):
    """Result of image content verification, EXIF stripping, and sanitization."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    is_valid: bool = Field(description="True if image is valid, supported, and successfully sanitized")
    error_code: Optional[str] = Field(default=None, description="Error code if invalid")
    error_message: Optional[str] = Field(default=None, description="User-safe error description")
    sanitized_bytes: Optional[bytes] = Field(default=None, description="Clean re-encoded JPEG bytes without EXIF")
    base64_data_uri: Optional[str] = Field(default=None, description="data:image/jpeg;base64,... URI for Groq vision")
    width: int = Field(default=0, ge=0, description="Sanitized image width in pixels")
    height: int = Field(default=0, ge=0, description="Sanitized image height in pixels")
    original_format: Optional[str] = Field(default=None, description="Detected original format (e.g. JPEG, PNG)")
    output_format: str = Field(default="JPEG", description="Output format of sanitized image")
    mime_type: Optional[str] = Field(default=None, description="Sanitized MIME type (e.g. image/jpeg)")
    original_size_bytes: int = Field(default=0, ge=0, description="Raw incoming payload size in bytes")
    sanitized_size_bytes: int = Field(default=0, ge=0, description="Output payload size in bytes")
    exif_stripped: bool = Field(default=False, description="True if EXIF metadata was removed")
    quality_assessment: ImageQualityAssessment = Field(
        default=ImageQualityAssessment.GOOD,
        description="Quality assessment tier"
    )


# ============================================================================
# Core Sanitization Functionality
# ============================================================================

def sanitize_image_bytes(raw_bytes: bytes) -> SanitizedImageResult:
    """
    Sanitize raw image bytes using Pillow.
    
    Validates actual binary image content, applies EXIF orientation, strips all
    EXIF metadata (including embedded GPS and camera metadata), enforces dimension
    and decompression-bomb bounds, and re-encodes to clean JPEG.
    
    Zero sensitive image data or base64 payloads are ever logged.
    """
    original_size = len(raw_bytes)

    # 1. Check size limit
    if original_size == 0:
        return SanitizedImageResult(
            is_valid=False,
            error_code="EMPTY_PAYLOAD",
            error_message="Uploaded image payload is empty.",
            original_size_bytes=0,
            quality_assessment=ImageQualityAssessment.CORRUPTED,
        )

    if original_size > MAX_UPLOAD_SIZE_BYTES:
        logger.warning(
            "Rejected oversized upload: %d bytes (limit: %d bytes)",
            original_size,
            MAX_UPLOAD_SIZE_BYTES,
        )
        return SanitizedImageResult(
            is_valid=False,
            error_code="FILE_TOO_LARGE",
            error_message=f"Image size ({original_size / (1024 * 1024):.2f} MB) exceeds the 10 MB limit.",
            original_size_bytes=original_size,
            quality_assessment=ImageQualityAssessment.CORRUPTED,
        )

    # 2. Verify binary integrity with PIL
    try:
        with Image.open(io.BytesIO(raw_bytes)) as verify_img:
            # verify() checks stream headers without decoding full pixel matrix
            verify_img.verify()
    except Image.DecompressionBombError:
        logger.warning("Rejected potential decompression bomb: size=%d bytes", original_size)
        return SanitizedImageResult(
            is_valid=False,
            error_code="DECOMPRESSION_BOMB_RISK",
            error_message="Image exceeds safe pixel density limits (decompression bomb risk).",
            original_size_bytes=original_size,
            quality_assessment=ImageQualityAssessment.CORRUPTED,
        )
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as e:
        logger.warning("Rejected unidentifiable or corrupt image payload: size=%d bytes", original_size)
        return SanitizedImageResult(
            is_valid=False,
            error_code="CORRUPTED_IMAGE",
            error_message="File content is corrupted or not a recognizable image.",
            original_size_bytes=original_size,
            quality_assessment=ImageQualityAssessment.CORRUPTED,
        )

    # 3. Open second fresh stream for pixel decoding and transformation
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            detected_format = (img.format or "").upper()

            # Enforce format whitelist
            if detected_format not in SUPPORTED_FORMATS:
                logger.info("Rejected unsupported image format: %s", detected_format)
                return SanitizedImageResult(
                    is_valid=False,
                    error_code="UNSUPPORTED_FORMAT",
                    error_message=f"Unsupported format '{detected_format}'. Only JPEG, PNG, and WebP are accepted.",
                    original_format=detected_format,
                    original_size_bytes=original_size,
                    quality_assessment=ImageQualityAssessment.CORRUPTED,
                )

            # Check decompression bomb pixel count explicitly
            pixel_count = img.width * img.height
            if pixel_count > SAFE_DECOMPRESSION_PIXELS:
                return SanitizedImageResult(
                    is_valid=False,
                    error_code="DECOMPRESSION_BOMB_RISK",
                    error_message=f"Image resolution ({img.width}x{img.height}) exceeds safe processing limits.",
                    original_format=detected_format,
                    original_size_bytes=original_size,
                    quality_assessment=ImageQualityAssessment.CORRUPTED,
                )

            # Check minimum dimensions
            if img.width < MIN_DIMENSION_PX or img.height < MIN_DIMENSION_PX:
                return SanitizedImageResult(
                    is_valid=False,
                    error_code="DIMENSIONS_TOO_SMALL",
                    error_message=f"Image dimensions ({img.width}x{img.height}px) are too small for reliable evidence analysis (minimum {MIN_DIMENSION_PX}x{MIN_DIMENSION_PX}px).",
                    width=img.width,
                    height=img.height,
                    original_format=detected_format,
                    original_size_bytes=original_size,
                    quality_assessment=ImageQualityAssessment.TOO_SMALL,
                )

            # 4. Apply EXIF orientation
            try:
                transposed = ImageOps.exif_transpose(img)
                if transposed is not None:
                    img = transposed
            except Exception:
                # If transposition fails on malformed EXIF header, continue with original
                pass

            # 5. Downscale if dimensions exceed safe ceiling (4096px)
            curr_w, curr_h = img.width, img.height
            if curr_w > MAX_DIMENSION_PX or curr_h > MAX_DIMENSION_PX:
                scale = min(MAX_DIMENSION_PX / curr_w, MAX_DIMENSION_PX / curr_h)
                new_w = max(1, int(curr_w * scale))
                new_h = max(1, int(curr_h * scale))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                curr_w, curr_h = new_w, new_h

            # 6. Normalize color mode for clean JPEG encoding
            # Handles transparency by alpha-compositing over a neutral background
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                rgba_img = img.convert("RGBA")
                background = Image.new("RGB", rgba_img.size, (255, 255, 255))
                background.paste(rgba_img, mask=rgba_img.split()[-1])
                processed_img = background
            elif img.mode != "RGB":
                processed_img = img.convert("RGB")
            else:
                processed_img = img

            # 7. Re-encode to clean JPEG buffer WITHOUT EXIF tags
            output_buffer = io.BytesIO()
            processed_img.save(
                output_buffer,
                format="JPEG",
                quality=DEFAULT_JPEG_QUALITY,
                optimize=True,
            )
            sanitized_bytes = output_buffer.getvalue()

            # 8. Construct clean Base64 data URI for Groq vision
            b64_str = base64.b64encode(sanitized_bytes).decode("ascii")
            base64_data_uri = f"data:image/jpeg;base64,{b64_str}"

            # Log safe telemetry only
            logger.info(
                "Image sanitized: orig_size=%d bytes, sanitized_size=%d bytes, dims=%dx%d, format=%s->JPEG",
                original_size,
                len(sanitized_bytes),
                curr_w,
                curr_h,
                detected_format,
            )

            return SanitizedImageResult(
                is_valid=True,
                sanitized_bytes=sanitized_bytes,
                base64_data_uri=base64_data_uri,
                width=curr_w,
                height=curr_h,
                original_format=detected_format,
                output_format="JPEG",
                mime_type="image/jpeg",
                original_size_bytes=original_size,
                sanitized_size_bytes=len(sanitized_bytes),
                exif_stripped=True,
                quality_assessment=ImageQualityAssessment.GOOD,
            )

    except Exception as e:
        logger.error("Unexpected error during image sanitization: %s", type(e).__name__)
        return SanitizedImageResult(
            is_valid=False,
            error_code="PROCESSING_ERROR",
            error_message="An error occurred while processing the uploaded image.",
            original_size_bytes=original_size,
            quality_assessment=ImageQualityAssessment.CORRUPTED,
        )


def sanitize_base64_image(base64_str: str) -> SanitizedImageResult:
    """
    Sanitize an image provided as a Base64 string or Data URI.
    Strips data URI prefix if present and passes decoded bytes to sanitize_image_bytes.
    """
    if not base64_str or not base64_str.strip():
        return SanitizedImageResult(
            is_valid=False,
            error_code="EMPTY_PAYLOAD",
            error_message="Empty Base64 image payload.",
            quality_assessment=ImageQualityAssessment.ABSENT,
        )

    # Strip data URI header if present (e.g. data:image/png;base64,...)
    clean_str = base64_str.strip()
    if "," in clean_str and clean_str.startswith("data:"):
        clean_str = clean_str.split(",", 1)[1]

    try:
        raw_bytes = base64.b64decode(clean_str, validate=True)
    except Exception:
        return SanitizedImageResult(
            is_valid=False,
            error_code="INVALID_BASE64",
            error_message="Invalid Base64 encoding.",
            quality_assessment=ImageQualityAssessment.CORRUPTED,
        )

    return sanitize_image_bytes(raw_bytes)


def evaluate_evidence_intake(
    image_bytes: Optional[bytes] = None,
    image_base64: Optional[str] = None,
) -> Tuple[Optional[SanitizedImageResult], PhotoEvidenceAnalysis]:
    """
    Clean intake interface evaluating photographic evidence presence.
    
    Returns:
    - (sanitized_result, PhotoEvidenceAnalysis)
    
    If no photo is supplied, gracefully returns NOT_PROVIDED without error.
    If image is invalid/too small, returns appropriate LOW_QUALITY outcome.
    If valid, returns clean SanitizedImageResult ready for Phase 2 Groq vision.
    """
    # Case 1: No photograph provided
    if image_bytes is None and (not image_base64 or not image_base64.strip()):
        analysis = PhotoEvidenceAnalysis(
            detected_category="none",
            visible_evidence="No photographic evidence provided with report.",
            relevance_score=0.0,
            image_quality=ImageQualityAssessment.ABSENT,
            confidence_score=0.0,
            recommendation=EvidenceRecommendation.HUMAN_REVIEW,
            outcome=EvidenceOutcome.NOT_PROVIDED,
            quality_explanation="Citizen did not attach a photograph. Awaiting field inspection.",
            provenance="NOT_PROVIDED",
        )
        return None, analysis

    # Case 2: Process provided image bytes or base64
    if image_bytes is not None:
        result = sanitize_image_bytes(image_bytes)
    else:
        result = sanitize_base64_image(image_base64 or "")

    # Case 3: Image sanitization failed (corrupt, too small, invalid format)
    if not result.is_valid:
        recommendation = (
            EvidenceRecommendation.REQUEST_RETAKE
            if result.quality_assessment == ImageQualityAssessment.TOO_SMALL
            else EvidenceRecommendation.HUMAN_REVIEW
        )
        analysis = PhotoEvidenceAnalysis(
            detected_category="unusable",
            visible_evidence=f"Unusable image: {result.error_message or 'validation failed'}",
            relevance_score=0.0,
            image_quality=result.quality_assessment,
            confidence_score=0.0,
            recommendation=recommendation,
            outcome=EvidenceOutcome.LOW_QUALITY,
            quality_explanation=result.error_message,
            provenance="INTAKE_SANITIZED_REJECTED",
        )
        return result, analysis

    # Case 4: Valid sanitized image ready for vision analysis
    analysis = PhotoEvidenceAnalysis(
        detected_category="pending_vision_analysis",
        visible_evidence="Sanitized photograph successfully verified and queued for vision analysis.",
        relevance_score=1.0,
        image_quality=ImageQualityAssessment.GOOD,
        confidence_score=1.0,
        recommendation=EvidenceRecommendation.PROCEED,
        outcome=EvidenceOutcome.MATCHED,
        provenance="INTAKE_SANITIZED_PRELIMINARY",
    )
    return result, analysis
