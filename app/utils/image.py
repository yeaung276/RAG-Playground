import base64
import io

from PIL import Image

MAX_DIMENSION = 1024  # longest side, px


def resize_image_bytes_to_base64_png(
    image_bytes: bytes, max_dimension: int = MAX_DIMENSION
) -> str:
    """
    Resize image bytes down to a max longest-side dimension (only if it currently
    exceeds that size) and re-encode losslessly as PNG, returning base64 text.

    If the image is already within bounds, it is still re-encoded as PNG for a
    consistent output format, but no resampling is applied.
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        img.load()

        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA") if "A" in img.getbands() else img.convert("RGB")

        width, height = img.size
        longest_side = max(width, height)

        if longest_side > max_dimension:
            scale = max_dimension / float(longest_side)
            new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
            img = img.resize(new_size, Image.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


def resize_incoming_base64_image(image_base64: str) -> str:
    """Convenience wrapper for client-supplied base64 (e.g. from /send): decode, resize, re-encode."""
    if image_base64.startswith("data:"):
        _, _, image_base64 = image_base64.partition(",")
    return resize_image_bytes_to_base64_png(base64.b64decode(image_base64))
