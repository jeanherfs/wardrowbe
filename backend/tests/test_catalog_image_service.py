from io import BytesIO

from PIL import Image

from app.services.catalog_image_service import CatalogImageService


class IdentityBackgroundProvider:
    def remove(self, image: Image.Image) -> Image.Image:
        return image


def _jpeg(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="JPEG", quality=100)
    return output.getvalue()


def _foreground_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    pixels = image.convert("RGB")
    mask = pixels.convert("L").point(lambda value: 255 if value < 180 else 0)
    return mask.getbbox()  # type: ignore[return-value]


def test_normalize_crops_large_white_margins_to_fixed_content_occupancy():
    image = Image.new("RGB", (400, 400), "white")
    for x in range(180, 220):
        for y in range(170, 230):
            image.putpixel((x, y), (30, 70, 120))

    normalized, original = CatalogImageService(
        provider=IdentityBackgroundProvider(), canvas_size=100
    ).normalize(_jpeg(image), "shirt.jpg")

    result = Image.open(BytesIO(normalized)).convert("RGB")
    bbox = _foreground_bbox(result)

    assert original == _jpeg(image)
    assert result.size == (100, 100)
    assert bbox[2] - bbox[0] in range(50, 60)
    assert bbox[3] - bbox[1] in range(78, 85)
    assert abs((bbox[0] + bbox[2]) / 2 - 50) <= 1
    assert abs((bbox[1] + bbox[3]) / 2 - 50) <= 1
