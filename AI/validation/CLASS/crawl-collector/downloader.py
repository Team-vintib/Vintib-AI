"""이미지 저장 + 내용 해시 기반 중복 제거.

쇼핑몰은 같은 사진을 여러 카테고리·목록에 재노출하고, 페이지네이션이 겹치면 같은 상품을
두 번 긁게 된다. URL이 달라도 **바이트가 같으면 같은 이미지**이므로 sha256으로 판정한다 —
학습셋에 같은 사진이 여러 라벨로 들어가는 것만은 막아야 한다.

브리핑 §4.1: "가능하면 고해상도 원본을 보관하고 학습 시점에 리사이즈" — 그래서 여기서는
리사이즈하지 않고 받은 바이트를 그대로 저장한다(Pillow 의존성도 필요 없다).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

# 매직 넘버 → 확장자. Content-Type 헤더는 쇼핑몰 CDN에서 자주 부정확해 바이트로 판별한다.
_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
    (b"RIFF", ".webp"),  # RIFF....WEBP
)

MIN_IMAGE_BYTES = 4096  # 이보다 작으면 플레이스홀더/1x1 픽셀로 본다


class ImageRejected(RuntimeError):
    """저장할 가치가 없는 이미지(너무 작거나, 이미지가 아니거나, 중복)."""


def guess_extension(data: bytes, url: str = "") -> str:
    for magic, ext in _MAGIC:
        if data.startswith(magic):
            if ext == ".webp" and b"WEBP" not in data[:16]:
                continue
            return ext
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp"} else ".bin"


@dataclass
class ImageStore:
    """`root/<site>/<sha256 앞 16자>.<ext>`로 저장하고 해시로 중복을 거른다."""

    root: Path
    site: str
    seen_hashes: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.dir = self.root / self.site
        self.dir.mkdir(parents=True, exist_ok=True)
        # 재실행 시 이미 받아둔 파일을 해시 집합에 복원한다(파일명이 곧 해시 접두사).
        for path in self.dir.glob("*"):
            if path.is_file():
                self.seen_hashes.add(path.stem)

    def save(self, data: bytes, url: str = "") -> tuple[str, str]:
        """(out_dir 기준 상대경로, sha256) 반환. 중복/불량이면 ImageRejected."""
        if len(data) < MIN_IMAGE_BYTES:
            raise ImageRejected(f"이미지가 너무 작다({len(data)}B) — 플레이스홀더로 보임: {url}")
        ext = guess_extension(data, url)
        if ext == ".bin":
            raise ImageRejected(f"이미지 형식을 알 수 없다: {url}")

        digest = hashlib.sha256(data).hexdigest()
        stem = digest[:16]
        if stem in self.seen_hashes:
            raise ImageRejected(f"중복 이미지(sha256 {stem}): {url}")

        path = self.dir / f"{stem}{ext}"
        path.write_bytes(data)
        self.seen_hashes.add(stem)
        return str(path.relative_to(self.root)), digest
