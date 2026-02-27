"""
Utility functions for image processing in TCG Nakama.
"""
import io
from PIL import Image


def convert_to_webp(image_data: bytes, quality: int = 85, max_width: int = 0) -> bytes:
    """
    Convert raw image bytes (any format) to optimized WebP bytes.

    Args:
        image_data: Raw bytes of the source image (JPG, PNG, etc.)
        quality: WebP quality 0-100, default 85.
        max_width: If > 0, downscale the image proportionally so its width
                   does not exceed this value (e.g. 1920 for banners).

    Returns:
        WebP-encoded bytes.
    """
    img = Image.open(io.BytesIO(image_data))

    # Preserve transparency for RGBA images, otherwise convert to RGB
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")

    # Optionally downscale large images
    if max_width > 0 and img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    output = io.BytesIO()
    img.save(output, format="webp", quality=quality, method=6)
    output.seek(0)
    return output.read()
