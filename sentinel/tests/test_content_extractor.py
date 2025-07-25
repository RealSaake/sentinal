from pathlib import Path

from sentinel.app.core.content_extractor import extract_content

from PIL import Image


def test_extract_unsupported_type_returns_none(tmp_path: Path):
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("Just some text.")
    assert extract_content(txt_file) is None


def test_extract_image_returns_dict(tmp_path: Path):
    img_path = tmp_path / "image.png"
    img = Image.new("RGB", (16, 16), color="blue")
    img.save(img_path)
    result = extract_content(img_path)
    assert isinstance(result, dict)
    assert "image_object" in result