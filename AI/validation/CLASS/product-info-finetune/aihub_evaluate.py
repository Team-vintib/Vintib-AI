"""헤드 평가 — AI-Hub 홀드아웃 **그리고** 우리 정답셋을 항상 같이 본다(브리핑 §11).

두 세트를 같이 보는 이유는 도메인이 다르기 때문이다. AI-Hub는 착용샷 중심이고 우리 서비스
입력은 flat/hanging이다. **둘이 어긋나면 우리 정답셋을 믿는다.**

평가하는 것
-----------
1. **AI-Hub val/test** — `aihub_train_head.py`가 저장한 헤드를 홀드아웃 임베딩에 적용.
   클래스별 precision/recall과 상위 혼동쌍.
2. **우리 정답셋**(선택, `--ground-truth-dir`) — 브리핑 §11의 수용 기준 3개를 직접 찍는다.
   - 색상 정확도가 zero-shot 기준선을 넘는가
   - 폴로 2건(`small_pro` `black_stain`)이 회복되는가
   - **나머지 이미지의 예측이 불변인가** (회귀 가드 — 이게 깨지면 실패다)

카테고리 최종 예측 = **zero-shot top-1**, 단 top-2가 {TSHIRT, SHIRT}일 때만 폴로 헤드가
뒤집는다. 35-way 자체를 헤드로 대체하지 않는다(브리핑 §3-B: 회귀 위험 0이 이 설계의 핵심).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from aihub_dataset import (
    ALL_SUBCATEGORIES,
    CATEGORY_PROMPT,
    COLOR_CODES,
    EN_COLOR_LABELS,
)
from aihub_train_head import build_task_dataset, evaluate, head_filename, load_split

# `product-info-check/classify.py`의 `EmbeddingZeroShotClassifier`와 같은 값 — 기준선을
# 재현하려면 스코어링 방식이 같아야 한다(CH014 §2-1이 지적한 과신 문제는 임계값 자동채움에만
# 영향을 주고 top-1 랭킹은 바꾸지 않는다).
TEMPERATURE = 100.0

POLO_PAIR = frozenset({"TSHIRT", "SHIRT"})
# 브리핑 §11이 이름으로 지목한 폴로 2건.
POLO_CASES = ("small_pro", "black_stain")


def _softmax(scores: Any) -> Any:
    import numpy as np

    shifted = scores - scores.max(axis=-1, keepdims=True)
    exponent = np.exp(shifted)
    return exponent / exponent.sum(axis=-1, keepdims=True)


def encode_texts(texts: list[str], model: Any, processor: Any, device: str) -> Any:
    """텍스트 라벨 → L2 정규화 임베딩."""
    inputs = processor(text=texts, return_tensors="pt", padding=True)
    inputs = {key: value.to(device) for key, value in inputs.items()}
    features = model.get_text_features(**inputs)
    features = features / features.norm(dim=-1, keepdim=True)
    return features.cpu().float().numpy()


def zero_shot(
    image_embeddings: Any, text_embeddings: Any, codes: list[str]
) -> list[list[tuple[str, float]]]:
    """이미지별 (코드, 확률) 내림차순 목록."""
    logits = image_embeddings @ text_embeddings.T * TEMPERATURE
    probabilities = _softmax(logits)
    ranked = []
    for row in probabilities:
        order = sorted(range(len(codes)), key=lambda i: -row[i])
        ranked.append([(codes[i], float(row[i])) for i in order])
    return ranked


def apply_polo_head(
    ranked: list[tuple[str, float]], embedding: Any, polo_head: Any
) -> tuple[str, bool]:
    """zero-shot 랭킹 + 폴로 헤드 → (최종 코드, 헤드가 개입했는지).

    top-2가 정확히 {TSHIRT, SHIRT}일 때만 개입한다. 그 외에는 zero-shot을 그대로 통과시켜
    나머지 33종 동작을 전혀 건드리지 않는다.
    """
    top1 = ranked[0][0]
    if polo_head is None or len(ranked) < 2:
        return top1, False
    if {ranked[0][0], ranked[1][0]} != POLO_PAIR:
        return top1, False
    predicted = polo_head.predict(embedding.reshape(1, -1))[0]
    return str(predicted), predicted != top1


# --------------------------------------------------------------------------
# 1. AI-Hub 홀드아웃
# --------------------------------------------------------------------------


def evaluate_holdout(artifacts: Path, task: str, variant: str, source: str | None) -> str:
    """`source`는 헤드 학습에 쓴 것과 **같은 값**을 준다 — 파일명과 행 필터 양쪽에 걸린다.

    색상 헤드를 `--source clothes`로 학습했으면 평가도 그렇게 불러야 같은 헤드를 집는다.
    다만 아래 소스별 분해는 `only_source`를 걸지 않은 전체 홀드아웃에서만 의미가 있다.
    """
    import joblib

    head_path = artifacts / head_filename(task, variant, source)
    if not head_path.exists():
        return f"(헤드 없음: {head_path} — aihub_train_head.py를 먼저 돌릴 것)"
    bundle = joblib.load(head_path)
    model = bundle["model"]

    label = f"### AI-Hub 홀드아웃 — task={task} variant={variant}"
    lines = [label + (f" source={source}" if source else "")]
    for split in ("val", "test"):
        try:
            embeddings, rows = load_split(artifacts, split, variant)
        except FileNotFoundError:
            lines.append(f"- {split}: 임베딩 없음(건너뜀)")
            continue
        x, y, kept = build_task_dataset(embeddings, rows, task, only_source=source)
        if not y:
            lines.append(f"- {split}: 대상 표본 0건")
            continue
        result = evaluate(model, x, y)
        lines.append(f"- **{split}** n={result['n']:,} accuracy={result['accuracy']:.4f}")
        for pair, count in result["top_confusions"][:5]:
            lines.append(f"  - {pair}: {count}")

        # 소스별로 쪼개 본다 — 액세서리를 섞었을 때 의류 성능이 깎이지 않았는지 확인.
        by_source: dict[str, list[int]] = {}
        for index, row in enumerate(kept):
            by_source.setdefault(row.get("source", "clothes"), []).append(index)
        if len(by_source) > 1:
            for source_name, indices in sorted(by_source.items()):
                subset = evaluate(model, x[indices], [y[i] for i in indices])
                lines.append(
                    f"  - [{source_name}] n={subset['n']:,} accuracy={subset['accuracy']:.4f}"
                )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 2. 우리 정답셋 (브리핑 §11의 수용 기준)
# --------------------------------------------------------------------------


def evaluate_ground_truth(
    ground_truth_dir: Path,
    artifacts: Path,
    variant: str,
    model_id: str,
    device: str,
) -> str:
    """정답셋 이미지를 직접 인코딩해 zero-shot과 헤드를 나란히 비교한다."""
    import joblib
    import numpy as np
    from PIL import Image

    import aihub_embed
    import aihub_preprocess

    truth_path = ground_truth_dir / "data" / "ground_truth.json"
    if not truth_path.exists():
        return f"(정답셋 없음: {truth_path})"
    rows = json.loads(truth_path.read_text(encoding="utf-8"))

    inputs_dir = ground_truth_dir / "inputs"
    shared_dir = ground_truth_dir.parents[1] / "QUAL" / "sam3-condition-check" / "sample_images"

    usable, images = [], []
    for row in rows:
        if row.get("synthetic"):
            continue  # 실제 사진이 아니다 — 기본 집계에서 제외(product-info-check 관례)
        path = inputs_dir / row["image_file"]
        if not path.exists():
            path = shared_dir / row["image_file"]
        if not path.exists():
            continue
        usable.append(row)
        images.append(path)

    if not usable:
        return (
            f"(정답셋 이미지를 하나도 못 찾았다 — {inputs_dir} 와 {shared_dir} 확인.\n"
            " 이 폴더들은 gitignore라 서버에 따로 올려야 한다)"
        )

    model, processor = aihub_embed.load_model(model_id, device)

    vectors = []
    for path in images:
        with Image.open(path) as image:
            prepared = aihub_preprocess.render_variant(image, None, "raw")
        inputs = processor(images=[prepared], return_tensors="pt")
        inputs = {key: value.to(device) for key, value in inputs.items()}
        features = model.get_image_features(**inputs)
        features = features / features.norm(dim=-1, keepdim=True)
        vectors.append(features.cpu().float().numpy()[0])
    embeddings = np.stack(vectors)

    category_codes = list(ALL_SUBCATEGORIES)
    category_texts = encode_texts(
        [CATEGORY_PROMPT(code) for code in category_codes], model, processor, device
    )
    color_codes = list(COLOR_CODES)
    color_texts = encode_texts(
        [f"a photo of {EN_COLOR_LABELS[code]} clothing" for code in color_codes],
        model,
        processor,
        device,
    )

    category_ranked = zero_shot(embeddings, category_texts, category_codes)
    color_ranked = zero_shot(embeddings, color_texts, color_codes)

    def maybe_load(task: str) -> Any:
        """소스별 헤드를 먼저 찾고 없으면 전체 소스 헤드로 폴백한다.

        색상 헤드는 `--source clothes`로 학습하는 걸 권장하므로(액세서리 금속색 오염)
        `head_color_masked_clothes.joblib`이 있으면 그걸 쓴다. 우리 정답셋은 전부
        의류라 이쪽이 맞다.
        """
        for candidate in ("clothes", None):
            path = artifacts / head_filename(task, variant, candidate)
            if path.exists():
                return joblib.load(path)["model"]
        return None

    color_head_model = maybe_load("color")
    polo_head = maybe_load("polo")

    lines = [
        f"### 우리 정답셋 — N={len(usable)} (synthetic 제외, variant={variant})",
        "",
        "| 이미지 | 카테고리 정답 | zero-shot | 헤드 적용 | 색상 정답 | zero-shot | 헤드 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    counters = {
        "cat_zero": 0,
        "cat_head": 0,
        "color_zero": 0,
        "color_head": 0,
        "changed": [],
        "polo_fixed": 0,
        "polo_total": 0,
    }

    for index, row in enumerate(usable):
        stem = Path(row["image_file"]).stem
        cat_truth = row["subcategory"]
        cat_zero = category_ranked[index][0][0]
        cat_head, intervened = apply_polo_head(category_ranked[index], embeddings[index], polo_head)

        color_truth = row["primary_color"]
        color_zero = color_ranked[index][0][0]
        if color_head_model is None:
            color_head = color_zero
        else:
            color_head = str(color_head_model.predict(embeddings[index].reshape(1, -1))[0])

        counters["cat_zero"] += cat_zero == cat_truth
        counters["cat_head"] += cat_head == cat_truth
        counters["color_zero"] += color_zero == color_truth
        counters["color_head"] += color_head == color_truth
        if stem in POLO_CASES:
            counters["polo_total"] += 1
            counters["polo_fixed"] += cat_head == cat_truth
        elif intervened or cat_head != cat_zero:
            counters["changed"].append(f"{stem}: {cat_zero} → {cat_head}")

        lines.append(
            f"| {stem} | {cat_truth} | {cat_zero} | {cat_head} | "
            f"{color_truth} | {color_zero} | {color_head} |"
        )

    total = len(usable)
    lines.extend(
        [
            "",
            f"- 카테고리: zero-shot {counters['cat_zero']}/{total} "
            f"({counters['cat_zero'] / total:.4f}) → 헤드 {counters['cat_head']}/{total} "
            f"({counters['cat_head'] / total:.4f})",
            f"- 색상: zero-shot {counters['color_zero']}/{total} "
            f"({counters['color_zero'] / total:.4f}) → 헤드 {counters['color_head']}/{total} "
            f"({counters['color_head'] / total:.4f})",
            f"- 폴로 케이스: {counters['polo_fixed']}/{counters['polo_total']} 회복 "
            f"(수용 기준 2/2)",
        ]
    )
    if counters["changed"]:
        lines.append("- ⚠ **회귀 가드 위반** — 폴로 외 이미지의 예측이 바뀌었다:")
        lines.extend(f"  - {change}" for change in counters["changed"])
    else:
        lines.append("- 회귀 가드: 폴로 외 예측 **불변** ✅")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="헤드 평가 — AI-Hub 홀드아웃 + 우리 정답셋")
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--variant", default="masked", choices=("raw", "masked"))
    parser.add_argument("--source", default=None, choices=("clothes", "accessory"))
    parser.add_argument(
        "--tasks", nargs="+", default=["color", "polo"], choices=["color", "polo", "category"]
    )
    parser.add_argument(
        "--ground-truth-dir",
        type=Path,
        default=None,
        help="product-info-check 폴더. 주면 정답셋 평가까지 한다(fashion_clip 로드 필요)",
    )
    parser.add_argument("--model-id", default="patrickjohncyh/fashion-clip")
    parser.add_argument("--device", default=None)
    parser.add_argument("--out", type=Path, default=None, help="마크다운 리포트 저장 경로")
    args = parser.parse_args(argv)

    parts = ["# 분류 헤드 평가 리포트", ""]
    for task in args.tasks:
        parts.append(evaluate_holdout(args.artifacts, task, args.variant, args.source))
        parts.append("")

    if args.ground_truth_dir:
        import torch

        device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
        parts.append(
            evaluate_ground_truth(
                args.ground_truth_dir, args.artifacts, args.variant, args.model_id, device
            )
        )

    report = "\n".join(parts)
    print(report)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
        print(f"\n(저장: {args.out})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
