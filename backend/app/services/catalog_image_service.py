"""Deterministic product-image cleanup used by retailer imports."""
from io import BytesIO

from PIL import Image, ImageChops, ImageOps, ImageStat

from app.services import background_removal


class CatalogImageService:
    CONTENT_SCALE = 0.82
    BACKGROUND_THRESHOLD = 24
    ALPHA_THRESHOLD = 8

    def __init__(self, provider=None, canvas_size: int = 1200):
        self.provider = provider or background_removal.get_provider()
        self.canvas_size = canvas_size

    def _foreground_bbox(self, image: Image.Image) -> tuple[int, int, int, int] | None:
        """Find the visible garment bounds, including retailer white backgrounds."""
        rgba = image.convert("RGBA")
        alpha = rgba.getchannel("A")
        if alpha.getextrema()[0] < 255:
            bbox = alpha.point(
                lambda value: 255 if value > self.ALPHA_THRESHOLD else 0
            ).getbbox()
            if bbox:
                return bbox

        rgb = rgba.convert("RGB")
        width, height = rgb.size
        sample = max(1, min(width, height) // 20)
        corner_pixels = []
        for left, top in ((0, 0), (width - sample, 0), (0, height - sample), (width - sample, height - sample)):
            corner_pixels.append(ImageStat.Stat(rgb.crop((left, top, left + sample, top + sample))).mean)
        background = tuple(round(sum(channel) / len(corner_pixels)) for channel in zip(*corner_pixels))
        background_image = Image.new("RGB", rgb.size, background)
        difference = ImageChops.difference(rgb, background_image).convert("L")
        mask = difference.point(
            lambda value: 255 if value > self.BACKGROUND_THRESHOLD else 0
        )
        bbox = mask.getbbox()
        if not bbox:
            return None

        # A full-frame difference means there is no separable margin to trim.
        if bbox == (0, 0, width, height):
            return None
        return bbox

    def normalize(self, image_data: bytes, filename: str) -> tuple[bytes, bytes]:
        """Return (normalized JPEG, original bytes); never mutates source bytes."""
        source = image_data
        image = ImageOps.exif_transpose(Image.open(BytesIO(image_data))).convert("RGB")
        result = self.provider.remove(image)
        bbox = self._foreground_bbox(result)
        if bbox:
            result = result.crop(bbox)
        target_size = max(1, round(self.canvas_size * self.CONTENT_SCALE))
        longest_edge = max(result.size)
        if longest_edge != target_size:
            scale = target_size / longest_edge
            result = result.resize(
                (max(1, round(result.width * scale)), max(1, round(result.height * scale))),
                Image.Resampling.LANCZOS,
            )
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
