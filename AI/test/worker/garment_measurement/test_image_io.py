"""`image_io.load_image`의 EXIF 방향 보정 검증.

아이폰 등 휴대폰은 센서가 찍은 그대로(회전 안 된 상태로) 저장하고, EXIF `Orientation`
태그에 "보여줄 때 이만큼 돌려라"만 적어둔다. `valid_image3.jpg`(실사진 검증,
`AI/validation/garment-landmark-check/`)에서 이걸 무시하면 랜드마크 좌표가 사람이 보는
방향과 어긋나는 걸 확인했다 — 합성 이미지로 회귀 테스트를 남긴다.
"""

from pathlib import Path

from PIL import Image

from garment_measurement.image_io import load_image


def _save_with_orientation(tmp_path: Path, upright: Image.Image, orientation: int) -> Path:
    """`upright`를 사람이 보는 그대로의 이미지라고 할 때, 휴대폰이 저장했을 법한
    (아직 안 돌아간) 원본 픽셀 + EXIF orientation 태그로 저장한다."""
    # orientation 6은 ROTATE_270(반시계 270도 = 시계 90도)을 적용해야 바로 서는 상태라는 뜻 —
    # 그러니 저장할 원본은 그 반대(ROTATE_90)로 미리 돌려둔다.
    raw = upright.transpose(Image.ROTATE_90)
    exif = raw.getexif()
    exif[274] = orientation  # 274 = Orientation 태그
    path = tmp_path / "phone_photo.jpg"
    raw.save(path, exif=exif)
    return path


def test_load_image_applies_exif_orientation(tmp_path):
    # 위(빨강)/아래(파랑)가 뚜렷이 구분되는 세로로 긴 이미지 — 방향이 틀리면 색 배치가 바뀐다.
    upright = Image.new("RGB", (40, 80))
    for y in range(80):
        color = (220, 30, 30) if y < 40 else (30, 30, 220)
        for x in range(40):
            upright.putpixel((x, y), color)

    path = _save_with_orientation(tmp_path, upright, orientation=6)

    loaded = load_image(str(path))

    assert loaded.size == (40, 80)
    assert loaded.getpixel((20, 5))[0] > 150  # 위쪽은 빨강
    assert loaded.getpixel((20, 75))[2] > 150  # 아래쪽은 파랑


def test_load_image_without_exif_is_unchanged(tmp_path):
    """EXIF가 아예 없는 이미지(이번 세션 이전 테스트 사진들처럼)는 그대로 통과해야 한다."""
    upright = Image.new("RGB", (30, 20), color=(10, 200, 10))
    path = tmp_path / "no_exif.png"
    upright.save(path)

    loaded = load_image(str(path))

    assert loaded.size == (30, 20)
    assert loaded.getpixel((0, 0)) == (10, 200, 10)
