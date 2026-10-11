"""
JanSetu AI — Image Sanitizer Test Suite.

Validates:
- Valid JPEG, PNG, and WebP processing
- Rejection of unsupported formats (GIF, BMP) and masquerading text files
- Handling of corrupted payloads and empty files
- Enforcement of 10 MB upload ceiling
- Downscaling of excessive dimensions (> 4096px)
- Rejection of undersized images (< 100px)
- Transposition of EXIF orientation and complete removal of GPS / device metadata
- Base64 input parsing and error recovery
- Evidence intake evaluation decoupling
"""

import io
import base64
from PIL import Image, ExifTags
from app.core.image_processing import (
    sanitize_image_bytes,
    sanitize_base64_image,
    evaluate_evidence_intake,
    MAX_UPLOAD_SIZE_BYTES,
    MAX_DIMENSION_PX,
    MIN_DIMENSION_PX,
)
from app.schemas.incident import (
    ImageQualityAssessment,
    EvidenceOutcome,
    EvidenceRecommendation,
)


def test_valid_jpeg_sanitization(valid_jpeg_bytes):
    """Ensure standard JPEG images are verified, sanitized, and re-encoded cleanly."""
    result = sanitize_image_bytes(valid_jpeg_bytes)
    
    assert result.is_valid is True
    assert result.error_code is None
    assert result.output_format == "JPEG"
    assert result.mime_type == "image/jpeg"
    assert result.width == 400
    assert result.height == 300
    assert result.exif_stripped is True
    assert result.quality_assessment == ImageQualityAssessment.GOOD
    assert result.sanitized_bytes is not None
    assert len(result.sanitized_bytes) > 0
    assert result.base64_data_uri.startswith("data:image/jpeg;base64,")


def test_valid_png_sanitization(valid_png_bytes):
    """Ensure PNG images with RGBA transparency are composited and converted to JPEG."""
    result = sanitize_image_bytes(valid_png_bytes)
    
    assert result.is_valid is True
    assert result.original_format == "PNG"
    assert result.output_format == "JPEG"
    assert result.width == 350
    assert result.height == 250
    assert result.sanitized_bytes is not None


def test_valid_webp_sanitization(valid_webp_bytes):
    """Ensure WebP images are verified and converted to JPEG."""
    result = sanitize_image_bytes(valid_webp_bytes)
    
    assert result.is_valid is True
    assert result.original_format == "WEBP"
    assert result.output_format == "JPEG"
    assert result.width == 500
    assert result.height == 400


def test_unsupported_formats_rejected(unsupported_format_gif_bytes, unsupported_format_bmp_bytes):
    """Ensure non-whitelisted formats (GIF, BMP) are rejected with clear error codes."""
    res_gif = sanitize_image_bytes(unsupported_format_gif_bytes)
    assert res_gif.is_valid is False
    assert res_gif.error_code == "UNSUPPORTED_FORMAT"
    assert res_gif.original_format == "GIF"

    res_bmp = sanitize_image_bytes(unsupported_format_bmp_bytes)
    assert res_bmp.is_valid is False
    assert res_bmp.error_code == "UNSUPPORTED_FORMAT"
    assert res_bmp.original_format == "BMP"


def test_masquerading_text_file_rejected(text_masquerading_as_image_bytes):
    """Ensure binary content validation detects non-images regardless of intended extension."""
    result = sanitize_image_bytes(text_masquerading_as_image_bytes)
    
    assert result.is_valid is False
    assert result.error_code == "CORRUPTED_IMAGE"


def test_corrupted_image_handling(corrupted_image_bytes, empty_image_bytes):
    """Ensure corrupted byte streams and empty payloads fail safely without unhandled exceptions."""
    res_corrupt = sanitize_image_bytes(corrupted_image_bytes)
    assert res_corrupt.is_valid is False
    assert res_corrupt.error_code == "CORRUPTED_IMAGE"

    res_empty = sanitize_image_bytes(empty_image_bytes)
    assert res_empty.is_valid is False
    assert res_empty.error_code == "EMPTY_PAYLOAD"


def test_oversized_upload_rejection(oversized_image_bytes):
    """Ensure uploads exceeding the 10 MB limit are rejected before decompression."""
    assert len(oversized_image_bytes) > MAX_UPLOAD_SIZE_BYTES
    
    result = sanitize_image_bytes(oversized_image_bytes)
    assert result.is_valid is False
    assert result.error_code == "FILE_TOO_LARGE"
    assert "10 MB" in result.error_message


def test_excessive_dimensions_downscaling(large_dimension_image_bytes):
    """Ensure images exceeding 4096px are proportionally downscaled while preserving aspect ratio."""
    result = sanitize_image_bytes(large_dimension_image_bytes)
    
    assert result.is_valid is True
    assert result.width <= MAX_DIMENSION_PX
    assert result.height <= MAX_DIMENSION_PX
    
    # Original was 5000 x 3000 (aspect ratio 5:3 = 1.6667)
    # Scaled down to max dimension 4096 => width = 4096, height = 2457
    assert result.width == MAX_DIMENSION_PX
    expected_height = int(3000 * (4096 / 5000))
    assert abs(result.height - expected_height) <= 1


def test_dimensions_too_small(small_image_bytes):
    """Ensure images smaller than 100x100px receive a clear quality review outcome."""
    result = sanitize_image_bytes(small_image_bytes)
    
    assert result.is_valid is False
    assert result.error_code == "DIMENSIONS_TOO_SMALL"
    assert result.quality_assessment == ImageQualityAssessment.TOO_SMALL
    assert "too small" in result.error_message.lower()


def test_exif_orientation_and_metadata_removal(image_with_exif_gps_and_orientation):
    """
    Ensure:
    1. EXIF orientation is transposed (dimensions transposed from 600x400 to 400x600)
    2. All EXIF metadata (camera model, GPS coordinates) is completely stripped
    """
    result = sanitize_image_bytes(image_with_exif_gps_and_orientation)
    
    assert result.is_valid is True
    # Orientation 6 rotates 90 CW => 600x400 becomes 400x600
    assert result.width == 400
    assert result.height == 600
    assert result.exif_stripped is True

    # Inspect the sanitized output image directly to verify total EXIF removal
    sanitized_img = Image.open(io.BytesIO(result.sanitized_bytes))
    exif_data = dict(sanitized_img.getexif())
    
    # Verify no GPS or camera tags exist
    assert len(exif_data) == 0
    assert 271 not in exif_data  # Make
    assert 272 not in exif_data  # Model
    assert 34853 not in exif_data  # GPSInfo


def test_base64_sanitization(valid_jpeg_bytes):
    """Ensure Base64 data URIs and raw Base64 strings are processed correctly."""
    b64_raw = base64.b64encode(valid_jpeg_bytes).decode("ascii")
    data_uri = f"data:image/jpeg;base64,{b64_raw}"

    # Test with data URI prefix
    res1 = sanitize_base64_image(data_uri)
    assert res1.is_valid is True
    assert res1.width == 400

    # Test with raw base64 string
    res2 = sanitize_base64_image(b64_raw)
    assert res2.is_valid is True
    assert res2.width == 400

    # Test with invalid base64 string
    res3 = sanitize_base64_image("NotValidBase64!!###")
    assert res3.is_valid is False
    assert res3.error_code in ("INVALID_BASE64", "CORRUPTED_IMAGE")


def test_evaluate_evidence_intake_missing_photo():
    """Ensure missing optional photos are handled gracefully without errors."""
    res, analysis = evaluate_evidence_intake(image_bytes=None, image_base64=None)
    
    assert res is None
    assert analysis.outcome == EvidenceOutcome.NOT_PROVIDED
    assert analysis.image_quality == ImageQualityAssessment.ABSENT
    assert analysis.recommendation == EvidenceRecommendation.HUMAN_REVIEW


def test_evaluate_evidence_intake_valid_photo(valid_jpeg_bytes):
    """Ensure valid photos return clean sanitized result and MATCHED candidate."""
    res, analysis = evaluate_evidence_intake(image_bytes=valid_jpeg_bytes)
    
    assert res is not None
    assert res.is_valid is True
    assert analysis.outcome == EvidenceOutcome.MATCHED
    assert analysis.image_quality == ImageQualityAssessment.GOOD
    assert analysis.recommendation == EvidenceRecommendation.PROCEED


def test_evaluate_evidence_intake_small_photo(small_image_bytes):
    """Ensure undersized photos route to retake recommendation."""
    res, analysis = evaluate_evidence_intake(image_bytes=small_image_bytes)
    
    assert res is not None
    assert res.is_valid is False
    assert analysis.outcome == EvidenceOutcome.LOW_QUALITY
    assert analysis.image_quality == ImageQualityAssessment.TOO_SMALL
    assert analysis.recommendation == EvidenceRecommendation.REQUEST_RETAKE
