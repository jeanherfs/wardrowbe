"""Deterministic product-image cleanup used by retailer imports."""
from io import BytesIO

from PIL import Image, ImageOps

from app.services import background_removal


class CatalogImageService:
    def __init__(self, provider=None, canvas_size: int = 1200):
        self.provider = provider or background_removal.get_provider()
        self.canvas_size = canvas_size

    def normalize(self, image_data: bytes, filename: str) -> tuple[bytes, bytes]:
        """Return (normalized JPEG, original bytes); never mutates source bytes."""
        source = image_data
        image = ImageOps.exif_transpose(Image.open(BytesIO(image_data))).convert("RGB")
        result = self.provider.remove(image)
        alpha = result.getchannel("A") if result.mode == "RGBA" else None
        if alpha:
            bbox = alpha.getbbox()
            if bbox:
                result = result.crop(bbox)
        result.thumbnail((self.canvas_size - 120, self.canvas_size - 120), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (self.canvas_size, self.canvas_size), (250, 250, 250))
        x = (self.canvas_size - result.width) // 2
        y = (self.canvas_size - result.height) // 2
        if result.mode == "RGBA":
            canvas.paste(result, (x, y), result.getchannel("A"))
        else:
            canvas.paste(result, (x, y))
        output = BytesIO()
        canvas.save(output, format="JPEG", quality=95, optimize=True)
        return output.getvalue(), source
