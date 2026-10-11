"""
JanSetu AI — Test Fixtures & Image Generation Utilities.
Provides in-memory synthetic assets for testing without network or filesystem dependencies.
"""

import io
from fractions import Fraction
import pytest
from PIL import Image, ExifTags


def make_test_image(
    format_name: str = "JPEG",
    width: int = 400,
    height: int = 300,
    color: tuple = (50, 120, 200),
    mode: str = "RGB",
) -> bytes:
    """Helper to generate an in-memory image buffer in specified format and dimensions."""
    img = Image.new(mode, (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format=format_name)
    return buf.getvalue()


@pytest.fixture
def valid_jpeg_bytes() -> bytes:
    """Standard valid JPEG image (400x300 px)."""
    return make_test_image(format_name="JPEG", width=400, height=300)


@pytest.fixture
def valid_png_bytes() -> bytes:
    """Valid PNG image with RGBA transparency (350x250 px)."""
    img = Image.new("RGBA", (350, 250), (220, 80, 50, 180))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def valid_webp_bytes() -> bytes:
    """Valid WebP image (500x400 px)."""
    return make_test_image(format_name="WEBP", width=500, height=400)


@pytest.fixture
def corrupted_image_bytes() -> bytes:
    """Corrupted image payload: valid JPEG magic bytes followed by truncated garbage."""
    # SOI header (FF D8) followed by random invalid data
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x60\x00\x60\x00\x00truncated_corrupted_garbage_bytes_here"


@pytest.fixture
def empty_image_bytes() -> bytes:
    """Empty 0-byte payload."""
    return b""


@pytest.fixture
def oversized_image_bytes() -> bytes:
    """Payload exceeding the 10 MB limit (10.5 MB of data)."""
    # 10.5 * 1024 * 1024 bytes
    return b"0" * (11 * 1024 * 1024)


@pytest.fixture
def small_image_bytes() -> bytes:
    """Image below safe evidence analysis threshold (50x60 px < 100px minimum)."""
    return make_test_image(format_name="JPEG", width=50, height=60)


@pytest.fixture
def large_dimension_image_bytes() -> bytes:
    """Image with excessive dimensions exceeding 4096px boundary (5000x3000 px)."""
    return make_test_image(format_name="JPEG", width=5000, height=3000)


@pytest.fixture
def image_with_exif_gps_and_orientation() -> bytes:
    """
    JPEG image containing:
    - EXIF Orientation tag (tag 274 = 6: 90 degrees CW)
    - Camera Make & Model tags (tag 271 = 'CivicPhone', tag 272 = 'ProCam 12')
    - GPS Latitude and Longitude IFD metadata
    """
    img = Image.new("RGB", (600, 400), (40, 160, 90))
    exif = img.getexif()
    
    # Orientation 6 (90 degrees CW transpose)
    exif[274] = 6
    exif[271] = "CivicPhone"
    exif[272] = "ProCam 12"
    
    # GPS Info IFD (Tag 34853)
    gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
    # Latitude: 28° 36' 50" N
    gps_ifd[2] = (Fraction(28, 1), Fraction(36, 1), Fraction(50, 1))
    # Longitude: 77° 12' 32" E
    gps_ifd[4] = (Fraction(77, 1), Fraction(12, 1), Fraction(32, 1))
    
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


@pytest.fixture
def unsupported_format_gif_bytes() -> bytes:
    """Unsupported GIF format image."""
    img = Image.new("P", (200, 200))
    buf = io.BytesIO()
    img.save(buf, format="GIF")
    return buf.getvalue()


@pytest.fixture
def unsupported_format_bmp_bytes() -> bytes:
    """Unsupported BMP format image."""
    img = Image.new("RGB", (200, 200))
    buf = io.BytesIO()
    img.save(buf, format="BMP")
    return buf.getvalue()


@pytest.fixture
def text_masquerading_as_image_bytes() -> bytes:
    """Plain ASCII text masquerading as an image file."""
    return b"<!DOCTYPE html><html><body><h1>Not an image</h1></body></html>"


@pytest.fixture
def db_session(tmp_path):
    """Provide an isolated database session and override app get_db dependency."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.session import Base, get_db
    from app.main import app
    from app.config import settings

    test_db_file = tmp_path / "test_conftest.db"
    test_db_url = f"sqlite:///{test_db_file}"
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield session

    session.close()
    app.dependency_overrides.pop(get_db, None)
