"""AI-Hub `04bottom_01pants`(하위 5종 구분 불가로 제외됐던 통짜 팬츠) 이미지를
fashion_clip 또는 Qwen3-VL로 시각 재라벨링한다.

배경: `aihub_dataset.py`의 `EXCLUDED_CATEGORY_TYPES["04bottom_01pants"]`가 이미 결론
냈다 — AI-Hub 메타데이터에는 팬츠 소재·디테일 컬럼이 없어 DENIM/SLACKS/CARGO_PANTS/
JOGGER_PANTS/COTTON_PANTS을 구조화 데이터로는 못 가른다. 이 스크립트는 그 결론을
뒤집는 게 아니라 **다른 신호(이미지 자체)로 우회**한다 — 메타데이터에 없는 소재 정보를
모델이 사진에서 직접 보고 판단하게 한다. `SKIRT`(직접 매핑됨)와 `SHORT_PANTS`(길이
기반 파생)는 이미 커버되므로 대상이 아니다 — 후보는 위 5종뿐이다.

두 백엔드, 처리 속도가 100배 이상 다르다
----------------------------------------
- ``fashion_clip``(기본): 임베딩 유사도, GPU에서 수천 장/분. 파인튜닝 헤드가 이미 이
  백본 위에 서 있어(`aihub_embed.py`) 같은 임베딩 공간을 쓴다는 이점도 있다.
- ``qwen3_vl``: 생성형 VLM, 장당 수 초. 수만 장 전체에 쓰면 하룻밤에 못 끝난다.

**권장 사용법은 2-패스**: 1차로 ``fashion_clip``을 대상 전체에 돌리고, confidence가
낮게 나온(``--min-confidence`` 미만이라 ``accepted=false``인) 행만 ``--only-uncertain
<1차 출력.jsonl>``으로 걸러 ``qwen3_vl``로 재검증한다. 이러면 대부분은 빠른 백본이
처리하고, 애매한 소수만 느리지만 더 나은 판단을 하는 VLM에 맡길 수 있다.

실행 위치 — GPU 서버, tmux 안에서 돌릴 것(`aihub_dataset.py`·`aihub_embed.py`와 동일
제약 — AI-Hub 이미지가 로컬에 없는 환경에서는 못 돈다). 장시간 작업이므로 노트북이
아니라 argparse 스크립트다.

**결과를 추측해서 임계치를 낮추지 마라.** ``--min-confidence`` 기본값(0.5, 5-way
zero-shot 균등 기준선 0.2의 2.5배)은 임의값이다 — 실제 정확도는 `aihub_evaluate.py`류로
소규모 정답셋을 만들어 따로 검증해야 한다(다른 임계치들과 같은 한계, `aihub_dataset.py`
주석 참고). 이 스크립트는 후보를 만드는 첫 단계이지 검증이 끝났다는 뜻이 아니다.

출력은 JSONL 하나 — `label_path`를 키로 `aihub_dataset.py`의 `--bottom-pseudo-labels`가
그대로 읽는다. 각 행:
    {"label_path": ..., "image_path": (디버그용, resolve 결과),
     "backend": "fashion_clip"|"qwen3_vl", "subcategory": "DENIM"|None,
     "confidence": float, "accepted": bool, "candidates": [{"code":..., "score":...}, ...],
     "raw_response": (qwen3_vl만, 생성된 원문)}

사용 예:
    # 1차: 빠른 백본으로 전체 스캔
    python aihub_bottom_label.py \\
        --index /data/aihub/index.jsonl --image-root /data/aihub/images \\
        --out bottom_pseudo_pass1.jsonl --backend fashion_clip

    # 2차: 1차에서 애매했던 것만 VLM으로 재검증
    python aihub_bottom_label.py \\
        --index /data/aihub/index.jsonl --image-root /data/aihub/images \\
        --out bottom_pseudo_pass2.jsonl --backend qwen3_vl \\
        --only-uncertain bottom_pseudo_pass1.jsonl

    # 두 출력을 합쳐 aihub_dataset.py에 넘긴다(2차가 우선하도록 이어붙이기 순서만 주의 —
    # load_bottom_pseudo_labels()는 dict 갱신이라 뒤에 오는 파일이 이긴다. 아직 병합
    # 스크립트는 없으니 필요하면 `cat pass1.jsonl pass2.jsonl > merged.jsonl`로 합치고
    # --bottom-pseudo-labels merged.jsonl 로 넘길 것 — 같은 label_path가 중복되면
    # load_bottom_pseudo_labels가 마지막 값으로 덮어써서 자연히 2차 결과가 이긴다)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import aihub_embed  # 같은 폴더 — resolve_image_path() 재사용

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[3]  # product-info-finetune -> CLASS -> validation -> AI -> repo root

# `product-info-check/classify.py`·`taxonomy.py`를 재사용한다. 이 스크립트는 pytest가
# 수집하는 test 파일이 아니라 `python aihub_bottom_label.py`로 직접 실행하는 단독
# 스크립트라, `aihub_dataset.py`가 쓰는 importlib 우회(sys.path 오염이 pytest 수집을
# 깨는 문제, `AI/CLAUDE.md` 기록)가 여기선 필요 없다 — 그냥 sys.path에 얹는다.
_LABEL_SOURCE_DIR = _HERE.parent / "product-info-check"
sys.path.insert(0, str(_LABEL_SOURCE_DIR))

from classify import make_embedding_classifier  # noqa: E402
from taxonomy import BOUNDARY_RULES, CONFUSION_PAIRS, PROMPT_TEMPLATES, SUBCATEGORIES  # noqa: E402

_kr_label = PROMPT_TEMPLATES["kr_plain"]  # 코드 -> 한글 라벨 문구(예: "데님"). 공개 접근점.

# `worker/models/quality_vlm/loader.py`의 Qwen3-VL 로딩(4bit 양자화 + 캐시)을 그대로
# 재사용한다 — 품질검수 워커와 같은 체크포인트·같은 로딩 코드를 쓰면 검증된 경로를
# 중복 구현하지 않아도 된다.
_WORKER_MODELS_DIR = _REPO_ROOT / "worker" / "models"
sys.path.insert(0, str(_WORKER_MODELS_DIR))

# 후보 5종 — SKIRT(직접 매핑됨)·SHORT_PANTS(길이 기반 파생)는 이미 커버되므로 제외.
PANTS_MATERIAL_CODES: tuple[str, ...] = tuple(
    code for code in SUBCATEGORIES["BOTTOM"] if code not in ("SKIRT", "SHORT_PANTS")
)

# 5종 사이 시각적 구분 기준. taxonomy.py의 두 소스를 그대로 반영한다 — 새로 지어낸 기준이
# 아니라 이미 이 저장소가 실측/합의한 것을 재사용한다:
#   - BOUNDARY_RULES["COTTON_PANTS"] — 유일하게 명문화된 경계 규칙(정장 원단 주름=SLACKS).
#   - CONFUSION_PAIRS 중 하의 3쌍(SLACKS/CARGO_PANTS, SLACKS/COTTON_PANTS,
#     CARGO_PANTS/JOGGER_PANTS) — CLIP이 실제로 헷갈렸던 조합(product-info-check/REPORT.md
#     §10). 이 3쌍에 걸친 코드(SLACKS/CARGO_PANTS/JOGGER_PANTS/COTTON_PANTS)만 구분 포인트를
#     명시하고, 혼동쌍에 없는 DENIM은 원단 설명만 준다 — 오탐 위험이 낮다고 실측이 이미 말해준
#     조합에 억지로 규칙을 만들지 않는다.
#
# **한글/영문 두 벌을 따로 둔다.** fashion-clip의 텍스트 인코더는 영문 CLIP 토크나이저
# 그대로라(classify.py: "LAION CLIP ViT-B/32 위에 파인튜닝") 한글 문장을 넣으면 토큰화가
# 깨져 오히려 성능이 떨어진다 — Qwen3-VL(다국어 생성 모델)에만 한글 버전을 쓴다.
_PANTS_VISUAL_HINTS_KO: dict[str, str] = {
    "DENIM": "데님(청바지) 원단 — 능직 면, 대개 파란색/검은색 계열, 리벳·오렌지 스티치",
    "SLACKS": "정장/캐주얼 슬랙스 — 매끈한 원단에 다림질된 앞주름(crease line), 카고 포켓 없음",
    "CARGO_PANTS": "카고팬츠 — 허벅지·옆면에 덮개 달린 큰 포켓(카고 포켓)이 있는 게 핵심 특징",
    "JOGGER_PANTS": "조거팬츠 — 밑단이 고무줄/니트 커프스로 조여진 트레이닝복 원단(플리스·저지)",
    "COTTON_PANTS": (
        "면 치노 팬츠 — 캐주얼한 면 소재, 자연스러운 구김. "
        # BOUNDARY_RULES 원문을 그대로 인용하되 코드명(SLACKS)만 한글 라벨로 바꿔
        # VLM 프롬프트 문장이 자연스럽게 읽히게 한다 — 내용 자체는 손대지 않는다.
        + BOUNDARY_RULES["COTTON_PANTS"].replace("SLACKS", _kr_label("SLACKS"))
    ),
}
_PANTS_VISUAL_HINTS_EN: dict[str, str] = {
    "DENIM": "a photo of blue denim jeans with visible stitching",
    "SLACKS": "a photo of dress slacks with a crisp pressed front crease, no thigh pockets",
    "CARGO_PANTS": "a photo of cargo pants with large flap pockets on the thigh",
    "JOGGER_PANTS": "a photo of jogger sweatpants with elastic cuffs at the ankle",
    "COTTON_PANTS": "a photo of casual cotton chino pants, smooth fabric with no crease line",
}
assert set(_PANTS_VISUAL_HINTS_KO) == set(_PANTS_VISUAL_HINTS_EN) == set(PANTS_MATERIAL_CODES)
# 위 힌트가 겨냥한 3쌍이 실제로 taxonomy.py의 실측 혼동쌍과 일치하는지 대조 — 나중에
# taxonomy.py가 바뀌었는데 여기 힌트를 안 고치면 여기서 바로 드러난다.
for _pair in (
    ("SLACKS", "CARGO_PANTS"),
    ("SLACKS", "COTTON_PANTS"),
    ("CARGO_PANTS", "JOGGER_PANTS"),
):
    assert _pair in CONFUSION_PAIRS, f"taxonomy.py의 CONFUSION_PAIRS와 어긋남: {_pair}"

DEFAULT_MIN_CONFIDENCE = 0.5  # 5-way 균등 기준선(0.2)의 2.5배. 근거 없는 값 — 스윕 대상.

# 기본값은 quality_vlm/registry.py와 같은 계열(4B, 항상 안전하게 돈다).
#
# **GPU가 널널하면 --model-id "Qwen/Qwen3-VL-30B-A3B-Instruct"를 권장한다** — 실측
# 벤치마크상 8B(114 tok/s)와 30B-A3B(110.8 tok/s)의 생성 속도가 거의 같다(MoE라 토큰당
# 실제 활성 파라미터는 ~3B뿐이라서다). 즉 속도 손해는 미미한데 총 파라미터·표현력은
# 훨씬 커서, "정확도 vs 속도" 트레이드오프에서 8B보다 순수하게 더 나은 선택이다.
# 다만 VRAM은 총 가중치(30B) 기준으로 든다 — MoE는 토큰당 활성 파라미터만 적을 뿐,
# 전체 전문가 가중치가 다 GPU에 상주해야 한다. bf16 풀로드(~60GB)는 47GB급 단일 GPU
# (예: L40S)에도 안 들어간다. **공식 FP8 체크포인트
# ("Qwen/Qwen3-VL-30B-A3B-Instruct-FP8")는 확인 결과 transformers로 직접 못 싣는다**
# (2026-08, HF 모델 카드: vLLM/SGLang 전용, transformers 미지원) — --model-id에 이
# 리포를 쓰지 말 것. 대신:
#   - **VRAM 30GB 안팎 여유(L40S 47.7GB 등)면 --quantization 8bit를 쓴다** — bitsandbytes
#     int8로 로드 시점에 양자화한다(추가 설치 불필요, 4bit 브랜치와 같은 bitsandbytes
#     재사용). 4bit보다 정밀도 손실이 훨씬 적으면서도 원본 30B bf16(~60GB)보다 절반
#     이하 VRAM만 쓴다 — "정확도 vs 속도"에서 굳이 4bit까지 내려갈 필요가 없을 때 최선.
#   - VRAM이 그보다 더 빠듯하면 --quantization 4bit(기본값, bitsandbytes nf4) 또는
#     커뮤니티 4bit AWQ 리포("QuantTrio/Qwen3-VL-30B-A3B-Instruct-AWQ",
#     --quantization none으로 쓸 것 — 리포 자체가 이미 양자화됨, `pip install autoawq` 필요)를
#     쓴다. MoE 로딩은 `_load_qwen_vl_bundle()`이 별도로 처리한다(아래 참고) — dense
#     전용인 quality_vlm/loader.py는 무수정이다.
QWEN3_VL_MODEL_ID = "Qwen/Qwen3-VL-4B-Instruct"


def load_index_rows(index_path: Path) -> list[dict]:
    """`index.jsonl`에서 재라벨링 대상만 골라낸다.

    대상: `source_type == "04bottom_01pants"`이고 `subcategory`가 아직 없는 행(이미
    SHORT_PANTS로 파생됐거나 다른 이유로 채워진 행은 손대지 않는다).
    """
    rows: list[dict] = []
    with index_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("source_type") != "04bottom_01pants":
                continue
            if row.get("subcategory"):
                continue
            rows.append(row)
    return rows


def load_uncertain_label_paths(path: Path) -> set[str]:
    """이전 패스 출력에서 `accepted=false`인 `label_path`만 뽑는다(2차 패스 입력용)."""
    paths: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if not row.get("accepted", False):
                paths.add(row["label_path"])
    return paths


def load_done_label_paths(out_path: Path) -> set[str]:
    """`--resume`용 — 이미 처리된 `label_path`를 읽어 재처리를 건너뛴다."""
    if not out_path.exists():
        return set()
    done: set[str] = set()
    with out_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["label_path"])
            except (json.JSONDecodeError, KeyError):
                continue
    return done


# --------------------------------------------------------------------------
# 백엔드 1 — fashion_clip zero-shot (빠름, 대량 처리용)
# --------------------------------------------------------------------------


def label_with_fashion_clip(
    rows: list[dict],
    *,
    image_root: Path,
    min_confidence: float,
    progress_every: int,
) -> list[dict[str, Any]]:
    classifier = make_embedding_classifier("fashion_clip")
    # `PROMPT_TEMPLATES["en_clip_style"]`(예: "a photo of a denim jeans")는 소재 이름만
    # 담아 SLACKS/CARGO_PANTS/COTTON_PANTS처럼 원단이 비슷한 조합을 못 가른다. fashion-clip은
    # 상품 설명 문구로 파인튜닝됐으니(classify.py 주석) 구분 포인트를 문장에 얹어 준다 —
    # `_PANTS_VISUAL_HINTS_EN`이 곧 그 문장이다(영문 — CLIP 토크나이저가 영문 전용).
    label_texts = [_PANTS_VISUAL_HINTS_EN[code] for code in PANTS_MATERIAL_CODES]

    results: list[dict[str, Any]] = []
    missing_image = 0
    for index, row in enumerate(rows):
        if progress_every and index and index % progress_every == 0:
            print(f"  ... {index:,}/{len(rows):,}", file=sys.stderr, flush=True)

        image_path = aihub_embed.resolve_image_path(row, image_root)
        if image_path is None or not image_path.exists():
            missing_image += 1
            continue

        try:
            scores = classifier.score_labels(image_path, label_texts)
        except Exception as exc:  # noqa: BLE001 — 이미지 하나 실패로 전체를 죽이지 않는다
            print(f"  [실패] {row['label_path']}: {exc}", file=sys.stderr)
            continue

        ranked = sorted(zip(PANTS_MATERIAL_CODES, scores), key=lambda p: -p[1])
        top_code, top_score = ranked[0]
        results.append(
            {
                "label_path": row["label_path"],
                "image_path": str(image_path),
                "backend": "fashion_clip",
                "subcategory": top_code,
                "confidence": round(float(top_score), 4),
                "accepted": top_score >= min_confidence,
                "candidates": [
                    {"code": code, "score": round(float(score), 4)} for code, score in ranked
                ],
            }
        )

    if missing_image:
        print(f"이미지 못 찾음: {missing_image:,}건 (건너뜀)", file=sys.stderr)
    return results


# --------------------------------------------------------------------------
# 백엔드 2 — Qwen3-VL (느림, 애매한 케이스 재검증용)
# --------------------------------------------------------------------------


def _match_kr_label(response: str) -> str | None:
    """생성된 한글 응답에서 후보 5종 중 정확히 하나만 언급됐는지 확인한다.

    둘 이상 언급되면(예: "데님이나 코튼팬츠 같습니다") 모델이 확신하지 못했다는 뜻이라
    애매함으로 처리한다 — 임의로 하나를 골라 잘못된 라벨을 만들지 않는다.
    """
    hits = [code for code in PANTS_MATERIAL_CODES if _kr_label(code) in response]
    return hits[0] if len(hits) == 1 else None


def _load_qwen_vl_bundle(model_id: str, quantization: str):
    """`quality_vlm/loader.py`의 `load_qwen_vl()`은 dense 계열(4B/8B)만 지원한다 —
    `Qwen3VLForConditionalGeneration`으로 싣는데, 30B-A3B/235B-A22B 같은 MoE 계열은
    라우팅 레이어 구조가 달라 이 클래스로 못 싣는다(실측: HF 공식 로딩 예제가
    `Qwen3VLMoeForConditionalGeneration`을 쓴다). 체크포인트 이름의 "-A숫자B"
    표기(공식 명명 규칙: <총파라미터>-A<활성파라미터>, 예: 30B-A3B)로 MoE 여부를
    판별해 그 경우만 이 함수 안에서 직접 싣는다 — 프로덕션 검수 워커가 쓰는 공유
    로더(`quality_vlm/loader.py`)는 dense 전용으로 그대로 두고 건드리지 않는다."""
    import re

    from quality_vlm.loader import VLMBundle, load_qwen_vl, select_device

    if not re.search(r"-A\d+B", model_id):
        return load_qwen_vl(model_id, quantization=quantization)

    import torch
    from transformers import AutoProcessor, Qwen3VLMoeForConditionalGeneration

    device = select_device()
    processor = AutoProcessor.from_pretrained(model_id)
    if quantization == "4bit":
        from transformers import BitsAndBytesConfig

        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )
        model = Qwen3VLMoeForConditionalGeneration.from_pretrained(
            model_id, quantization_config=quant_config, device_map="auto"
        )
    elif quantization == "8bit":
        # 4bit보다 정밀도 손실이 적으면서(bitsandbytes int8, 추가 설치 불필요) 원본
        # bf16(~60GB, 30B-A3B 기준) 절반 이하 VRAM만 쓴다 — VRAM 30GB 안팎 여유가 있는
        # GPU(L40S 47.7GB 등)에서 4bit 대신 쓰기 좋다.
        from transformers import BitsAndBytesConfig

        quant_config = BitsAndBytesConfig(load_in_8bit=True)
        model = Qwen3VLMoeForConditionalGeneration.from_pretrained(
            model_id, quantization_config=quant_config, device_map="auto"
        )
    elif quantization == "none":
        # `-AWQ` 접미사가 붙은 체크포인트(예: QuantTrio/Qwen3-VL-30B-A3B-Instruct-AWQ)는
        # 리포 자체가 이미 양자화돼 있다 — 그런 리포에는 항상 이 분기(quantization="none")를
        # 쓴다. AWQ 리포는 `pip install autoawq`가 추가로 필요하다. 주의: 공식 FP8
        # 체크포인트("-FP8" 접미사)는 여기 해당하지 않는다 — transformers가 아직 직접
        # 로딩을 지원하지 않는다(2026-08 기준 vLLM/SGLang 전용, HF 모델 카드 확인).
        model = Qwen3VLMoeForConditionalGeneration.from_pretrained(
            model_id, dtype="auto", device_map="auto"
        )
    else:
        raise ValueError(f"unknown quantization mode: {quantization!r}")
    model.eval()
    return VLMBundle(name=model_id, model=model, processor=processor, device=device)


def label_with_qwen3_vl(
    rows: list[dict],
    *,
    image_root: Path,
    progress_every: int,
    model_id: str,
    quantization: str,
) -> list[dict[str, Any]]:
    from quality_vlm.loader import generate_from_image
    from PIL import Image

    bundle = _load_qwen_vl_bundle(model_id, quantization)

    # 후보를 그냥 나열만 하면(기존: "데님/슬랙스/카고팬츠/조거팬츠/코튼팬츠 중...") 모델이
    # 원단 명칭만 보고 고르게 되는데, 그게 바로 CLIP도 헷갈렸던 지점이다(위 힌트 주석 참고).
    # 후보마다 구분 포인트를 같이 주면 VLM이 실제로 봐야 할 특징(카고 포켓 유무, 밑단
    # 커프스, 앞주름 등)을 먼저 알고 이미지를 본다 — taxonomy.py의 BOUNDARY_RULES가
    # "사람 라벨러도 기준이 없으면 갈린다"는 전제로 만들어진 것과 같은 이유다.
    candidate_lines = "\n".join(
        f"- {_kr_label(code)}: {_PANTS_VISUAL_HINTS_KO[code]}" for code in PANTS_MATERIAL_CODES
    )
    prompt = (
        "이 사진은 중고 의류 하의(팬츠) 사진입니다. 아래 5종의 구분 기준을 참고해서 "
        f"가장 알맞은 것 하나를 정확히 그 단어로만 답하세요.\n{candidate_lines}\n"
        "다른 설명 없이 명칭 단어 하나만 출력하세요."
    )

    results: list[dict[str, Any]] = []
    missing_image = 0
    for index, row in enumerate(rows):
        if progress_every and index and index % progress_every == 0:
            print(f"  ... {index:,}/{len(rows):,}", file=sys.stderr, flush=True)

        image_path = aihub_embed.resolve_image_path(row, image_root)
        if image_path is None or not image_path.exists():
            missing_image += 1
            continue

        try:
            with Image.open(image_path) as img:
                image = img.convert("RGB")
                response = generate_from_image(bundle, image, prompt, max_new_tokens=20)
        except Exception as exc:  # noqa: BLE001 — 이미지 하나 실패로 전체를 죽이지 않는다
            print(f"  [실패] {row['label_path']}: {exc}", file=sys.stderr)
            continue

        matched = _match_kr_label(response)
        results.append(
            {
                "label_path": row["label_path"],
                "image_path": str(image_path),
                "backend": "qwen3_vl",
                "subcategory": matched,
                # 생성형 응답이라 연속값 confidence가 없다 — 후보 5종 중 정확히 하나만
                # 언급됐으면 1.0(수용), 아니면 0.0(모호/무응답)으로 이진 처리한다.
                "confidence": 1.0 if matched else 0.0,
                "accepted": matched is not None,
                "raw_response": response,
            }
        )

    if missing_image:
        print(f"이미지 못 찾음: {missing_image:,}건 (건너뜀)", file=sys.stderr)
    return results


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _force_utf8_stdout() -> None:
    """Windows 콘솔 기본 인코딩(cp949)이 한글 출력에서 터진다(`aihub_dataset.py`와 동일)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdout()
    parser = argparse.ArgumentParser(
        description="AI-Hub 04bottom_01pants 이미지를 fashion_clip/VLM으로 재라벨링"
    )
    parser.add_argument("--index", type=Path, required=True, help="aihub_dataset.py의 index.jsonl")
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="출력 JSONL 경로")
    parser.add_argument("--backend", choices=("fashion_clip", "qwen3_vl"), default="fashion_clip")
    parser.add_argument(
        "--model-id",
        default=QWEN3_VL_MODEL_ID,
        help="qwen3_vl 전용. 기본은 4B(항상 안전). GPU가 널널하면 "
        "'Qwen/Qwen3-VL-30B-A3B-Instruct'를 권장 — 실측 벤치마크상 8B와 생성 속도가 "
        "거의 같은데(MoE, 토큰당 활성 파라미터 ~3B) 총 표현력은 훨씬 크다. VRAM이 "
        "30GB 안팎 여유(L40S 47.7GB 등)면 --quantization 8bit와 같이 쓴다. 공식 FP8 리포는 "
        "transformers 미지원이라 쓰지 말 것 — VRAM이 더 빠듯하면 "
        "'QuantTrio/Qwen3-VL-30B-A3B-Instruct-AWQ'(커뮤니티 4bit, --quantization none과 "
        "같이 쓸 것, `pip install autoawq` 필요)를 대신 쓴다",
    )
    parser.add_argument(
        "--quantization",
        choices=("4bit", "8bit", "none"),
        default="4bit",
        help="qwen3_vl 전용. 'none'이면 그대로 로드(AWQ처럼 리포 자체가 이미 양자화된 "
        "체크포인트는 항상 이 값을 쓴다). '4bit'/'8bit'는 로드 시점에 bitsandbytes로 "
        "양자화한다(원본이 아직 안 양자화된 체크포인트에만 의미가 있다) — '8bit'가 "
        "정밀도 손실이 더 적으니 VRAM 여유가 있으면 '8bit'를 쓴다. 기본은 로컬 8GB급 GPU "
        "기준 4bit(quality_vlm/loader.py와 동일)",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=DEFAULT_MIN_CONFIDENCE,
        help="fashion_clip 전용 — top-1 점수가 이 미만이면 accepted=false(모듈 docstring의 "
        "'추측해서 낮추지 마라' 경고 참고)",
    )
    parser.add_argument(
        "--only-uncertain",
        type=Path,
        default=None,
        help="이 파일의 accepted=false 행(label_path)만 대상으로 삼는다 — 2차 패스(보통 "
        "qwen3_vl)에서 쓴다. 생략하면 --index 전체에서 대상 조건에 맞는 행을 다 돈다",
    )
    parser.add_argument("--limit", type=int, default=None, help="앞에서부터 N개만(스모크 테스트용)")
    parser.add_argument(
        "--resume", action="store_true", help="--out에 이미 있는 label_path는 건너뛰고 이어붙인다"
    )
    parser.add_argument("--progress-every", type=int, default=500)
    args = parser.parse_args(argv)

    if not args.index.exists():
        print(f"--index 경로가 없다: {args.index}", file=sys.stderr)
        return 2
    if not args.image_root.exists():
        print(f"--image-root 경로가 없다: {args.image_root}", file=sys.stderr)
        return 2

    rows = load_index_rows(args.index)
    print(f"재라벨링 대상 후보(04bottom_01pants, subcategory 없음): {len(rows):,}건")

    if args.only_uncertain is not None:
        if not args.only_uncertain.exists():
            print(f"--only-uncertain 경로가 없다: {args.only_uncertain}", file=sys.stderr)
            return 2
        uncertain = load_uncertain_label_paths(args.only_uncertain)
        rows = [r for r in rows if r["label_path"] in uncertain]
        print(f"  -> --only-uncertain 필터 적용 후: {len(rows):,}건")

    if args.resume and args.out.exists():
        done = load_done_label_paths(args.out)
        before = len(rows)
        rows = [r for r in rows if r["label_path"] not in done]
        print(f"  -> --resume: 이미 처리된 {before - len(rows):,}건 건너뜀")

    if args.limit:
        rows = rows[: args.limit]

    if not rows:
        print("대상 행이 0개다 — 필터 조건을 확인할 것", file=sys.stderr)
        return 1

    backend_detail = (
        f" (model={args.model_id}, quantization={args.quantization})"
        if args.backend == "qwen3_vl"
        else ""
    )
    print(f"백엔드={args.backend}{backend_detail} 대상={len(rows):,}건 -> {args.out}")
    if args.backend == "fashion_clip":
        results = label_with_fashion_clip(
            rows,
            image_root=args.image_root,
            min_confidence=args.min_confidence,
            progress_every=args.progress_every,
        )
    else:
        results = label_with_qwen3_vl(
            rows,
            image_root=args.image_root,
            progress_every=args.progress_every,
            model_id=args.model_id,
            quantization=args.quantization,
        )

    mode = "a" if args.resume else "w"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open(mode, encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")

    accepted = sum(1 for r in results if r["accepted"])
    print(f"\n처리 {len(results):,}건 (accepted {accepted:,} / {len(results) - accepted:,} 미확정)")
    from collections import Counter

    code_counts = Counter(r["subcategory"] for r in results if r["accepted"])
    for code, count in code_counts.most_common():
        print(f"  {code:15s} {count:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
