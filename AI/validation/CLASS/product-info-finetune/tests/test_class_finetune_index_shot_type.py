"""`run_index`의 `--accessory-shot-type` 필터 테스트.

실측(2026-08-04): 액세서리 라벨의 94%가 착용샷(worn)인데, 그 실물 이미지는 받지 않는 게
방침이다(90GB라 스킵). 필터 없이 층화 샘플링하면 카테고리 상한 대부분이 이미지 없는 worn
행으로 채워져 STEP 3에서 조용히 버려진다 — 여기서 그 필터가 실제로 작동하는지 고정한다.
"""

from __future__ import annotations

import json

import aihub_dataset as ad


def _write_accessory_tree(tmp_path):
    """속성 1건 + 이미지 3건(worn 2 · product 1) — 실측 비율(worn 다수)을 축소 재현."""
    attrs = [
        {
            "accessory_id": "A0001",
            "accessory_type1": "모자",
            "accessory_color": "블랙",
        }
    ]
    (tmp_path / "attr.json").write_text(json.dumps(attrs, ensure_ascii=False), encoding="utf-8")

    def image_json(path: str, angle: str) -> dict:
        return {
            "info": [
                {
                    "id": f"M000_0001_{angle}",
                    "accessory_id": "A0001",
                    "model_id": "M000",
                    "image": {"path": path, "width": "100", "height": "100", "angle": angle},
                    "segmentation_class": ["Background", "Hat"],
                }
            ],
            "annotation": [{"segmentation": {}}],
        }

    (tmp_path / "img_worn1.json").write_text(
        json.dumps(image_json("/원천데이터/제품 착용/모자/w1.jpg", "1"), ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "img_worn2.json").write_text(
        json.dumps(image_json("/원천데이터/제품 착용/모자/w2.jpg", "2"), ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "img_product.json").write_text(
        json.dumps(image_json("/원천데이터/제품/모자/p1.jpg", "3"), ensure_ascii=False),
        encoding="utf-8",
    )


def test_accessory_shot_type_filter_drops_worn_rows(tmp_path) -> None:
    accessory_root = tmp_path / "accessory"
    accessory_root.mkdir()
    _write_accessory_tree(accessory_root)
    out_dir = tmp_path / "artifacts"

    report = ad.run_index(
        None,
        out_dir,
        limit=None,
        short_pants_max_cm=None,
        category_cap=10,
        color_cap=10,
        eval_cap=10,
        progress_every=0,
        accessory_root=accessory_root,
        accessory_shot_type="product",
    )

    assert "촬영유형 필터 'product' 적용" in report
    assert "2건 제외" in report  # worn 2건이 걸러진다

    rows = [
        json.loads(line)
        for line in (out_dir / "index.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 1
    assert rows[0]["shot_type"] == "product"


def test_without_filter_all_shot_types_pass(tmp_path) -> None:
    accessory_root = tmp_path / "accessory"
    accessory_root.mkdir()
    _write_accessory_tree(accessory_root)
    out_dir = tmp_path / "artifacts"

    report = ad.run_index(
        None,
        out_dir,
        limit=None,
        short_pants_max_cm=None,
        category_cap=10,
        color_cap=10,
        eval_cap=10,
        progress_every=0,
        accessory_root=accessory_root,
    )

    assert "촬영유형 필터" not in report
    rows = [
        json.loads(line)
        for line in (out_dir / "index.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 3
