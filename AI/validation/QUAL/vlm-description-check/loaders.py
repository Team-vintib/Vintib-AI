"""Qwen-VL 계열 로딩 헬퍼. vlm-description-check 스파이크 전용, 프로덕션 코드 아님.

model_selection/loaders.py 관례(무거운 import는 함수 내부, dataclass 번들 반환)를 따른다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


def select_device() -> str:
    """RTX 4070 Laptop 개발 노트북 기준. cuda 없으면 이 스파이크는 사실상 못 돈다(4bit도 GPU 전제)."""
    import torch

    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


@dataclass
class VLMBundle:
    name: str
    model: Any
    processor: Any
    device: str


def load_qwen_vl(model_id: str, quantization: str = "4bit") -> VLMBundle:
    """Qwen3VLForConditionalGeneration/AutoProcessor 로 로드.

    quantization="4bit"면 bitsandbytes nf4로 양자화한다(RTX 4070 8GB 기준 bf16 풀로드가
    안 들어가서 필수). "none"이면 dtype="auto" + device_map="auto"로 그대로 올린다 —
    8GB보다 큰 GPU에서만 실제로 돈다.
    """
    import torch
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

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
        model = Qwen3VLForConditionalGeneration.from_pretrained(
            model_id, quantization_config=quant_config, device_map="auto"
        )
    elif quantization == "none":
        model = Qwen3VLForConditionalGeneration.from_pretrained(
            model_id, dtype="auto", device_map="auto"
        )
    else:
        raise ValueError(f"unknown quantization mode: {quantization!r}")

    model.eval()
    return VLMBundle(name=model_id, model=model, processor=processor, device=device)


def generate_from_image(
    bundle: VLMBundle, image, prompt_text: str, max_new_tokens: int = 80
) -> str:
    """이미지 1장 + 임의 프롬프트 텍스트로 생성. 프롬프트 실험(노트북 §4~§5)의 기반 함수.

    `describe_defect()`는 이 함수 위에 CH009 기본 프롬프트를 얹은 얇은 래퍼다 — 노트북에서
    프롬프트 문구 자체를 바꿔보고 싶으면 이 함수를 직접 호출한다.
    """
    import torch

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt_text},
            ],
        }
    ]
    inputs = bundle.processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    ).to(bundle.model.device)

    with torch.no_grad():
        generated_ids = bundle.model.generate(**inputs, max_new_tokens=max_new_tokens)
    trimmed = generated_ids[0][inputs["input_ids"].shape[-1] :]
    return bundle.processor.decode(trimmed, skip_special_tokens=True).strip()


# 문체 고정용 few-shot 예시(CH019). 프로덕션 `worker/models/quality_vlm/prompts.py`의
# `_FEW_SHOT_EXAMPLES`와 동일 문구 — 스파이크와 프로덕션이 같은 프롬프트를 검증하도록 맞춘다.
_FEW_SHOT_EXAMPLES: tuple[str, ...] = (
    "주변 원단보다 갈색빛이 도는 색상 차이가 확인됩니다.",
    "원단이 짧게 해지고 올이 드러난 영역이 확인됩니다.",
)


def build_defect_prompt(defect_label: str) -> str:
    """CH009 기본 프롬프트 + CH019 few-shot. **위치는 절대 묻지 않는다.**

    크롭 이미지만으로는 옷 전체에서 어디인지 알 방법이 없는데, 1차 검증(2026-07-31)에서
    모델이 그걸 "청바지의 허리 부분" 식으로 그럴듯하게 지어내는 게 반복 확인됐다 — 크롭
    범위 밖 정보를 요구해서 생기는 hallucination이었다. 위치는 SAM3 bbox로 기하학적으로
    계산하는 `bbox_grid_position()`에 맡기고, VLM에게는 시각적 특징만 맡긴다.

    프로덕션 `worker/models/quality_vlm/prompts.py`의 `build_defect_prompt()`와 동일
    문구를 쓴다 — 이 노트북의 "default" 변형이 실제 프로덕션 프롬프트를 그대로 검증하게
    하기 위함. 문구를 한쪽만 고치면 노트북 실측이 프로덕션과 어긋난다.
    """
    examples = "\n".join(f"- {example}" for example in _FEW_SHOT_EXAMPLES)
    return (
        "아래는 하자 시각 설명의 좋은 답변 예시입니다.\n"
        f"{examples}\n\n"
        f"이 이미지는 중고 의류의 '{defect_label}' 하자 부분을 확대한 사진입니다. "
        "옷의 어느 부위인지는 추측하거나 언급하지 마세요. "
        "색상, 모양, 크기, 질감 등 사진에서 실제로 보이는 시각적 특징만, 위 예시와 같은 "
        "문체로 한국어 한 문장으로 설명해 주세요. 보이지 않는 내용은 지어내지 마세요."
    )


def describe_defect(
    bundle: VLMBundle, crop_image, defect_label: str, max_new_tokens: int = 80
) -> str:
    """크롭 이미지 1장 + 하자 태그(한글)로 시각적 특징 설명 생성(위치는 다루지 않음).

    CH009 "검증 축 — 입력 단위"의 "bbox 크롭 이미지 1장 + defect_type 컨텍스트" 조합에
    대응한다. 위치는 이 함수가 담당하지 않는다 — `bbox_grid_position()` +
    `compose_finding_bullet()`로 별도 계산해서 합친다.
    """
    prompt_text = build_defect_prompt(defect_label)
    return generate_from_image(bundle, crop_image, prompt_text, max_new_tokens)


_ROW_LABELS = ("위쪽", "가운데", "아래쪽")
_COL_LABELS = ("왼쪽", "가운데", "오른쪽")


def bbox_grid_position(bbox, image_size: tuple[int, int]) -> str:
    """bbox 중심의 3x3 격자 위치를 일반적인 한국어 표현으로 반환한다.

    프로덕션(`worker/models/sam3/prompts.py`의 `section_label()`)은 상의/하의 카테고리별
    부위 명칭(WAIST_LEFT, HEM_CENTER 등)을 쓰는데, 이 스파이크의 SAM3 산출물(`<stem>_qc.json`)
    에는 카테고리 정보가 없어 그 taxonomy를 그대로 못 쓴다. 그래서 카테고리 무관하게 순수
    기하학적 위치(위쪽/가운데/아래쪽 × 왼쪽/가운데/오른쪽)만 계산한다 — bbox는 SAM3가 이미
    확정한 값이라 VLM이 크롭만 보고 추측하는 것보다 훨씬 신뢰할 수 있다.
    """
    x1, y1, x2, y2 = bbox
    img_w, img_h = image_size
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    col = min(int(cx / img_w * 3), 2)
    row = min(int(cy / img_h * 3), 2)

    if row == 1 and col == 1:
        return "중앙"
    if row == 1:
        return f"{_COL_LABELS[col]} 중앙"
    if col == 1:
        return f"{_ROW_LABELS[row]} 가운데"
    return f"{_ROW_LABELS[row]} {_COL_LABELS[col]}"


def compose_finding_bullet(position_label: str, description: str) -> str:
    """SAM3 bbox 기반 위치(신뢰 가능) + VLM 크롭 설명(시각 디테일)을 한 줄로 합친다."""
    return f"{position_label} 부분 — {description}"


def draw_numbered_boxes(image, instances):
    """전체 이미지에 bbox·번호를 그린 복사본을 반환한다 — 일괄 프롬프팅(§4-2) 전용.

    정밀한 렌더링이 목적이 아니라, VLM이 이미지 속 번호와 프롬프트의 번호를 매칭할 수
    있도록 눈에 띄는 사각형 + 큰 숫자만 그린다. 개발 노트북(Windows)과 다른 OS 양쪽에서
    돌 수 있게 폰트 후보를 몇 개 시도하고, 전부 없으면 PIL 기본 폰트로 넘어간다.
    """
    from pathlib import Path

    from PIL import ImageDraw, ImageFont

    font = None
    for candidate in (
        r"C:\Windows\Fonts\arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        if Path(candidate).is_file():
            font = ImageFont.truetype(candidate, 28)
            break
    if font is None:
        font = ImageFont.load_default()

    annotated = image.copy()
    draw = ImageDraw.Draw(annotated)
    for inst in instances:
        x1, y1, x2, y2 = inst["bbox"]
        draw.rectangle([x1, y1, x2, y2], outline="red", width=4)
        tag_y = max(0, y1 - 32)
        draw.rectangle([x1, tag_y, x1 + 30, tag_y + 30], fill="red")
        draw.text((x1 + 6, tag_y + 2), str(inst["no"]), fill="white", font=font)
    return annotated


def build_batch_prompt(instances) -> str:
    """전체 이미지 + 번호 목록으로 모든 finding을 한 번에 요청하는 프롬프트(§4-2).

    크롭 방식(`build_defect_prompt`)과 다르게 위치는 이미지 속 번호 사각형으로 이미
    주어져 있다 — 크롭 N번 호출 대비 인코딩 비용을 줄일 수 있는지 가늠하기 위한 러프
    비교용이라, 출력 형식을 엄격하게 파싱하지 않는다(원문 그대로 눈으로 비교).
    """
    listing = "\n".join(f"{inst['no']}번: '{inst['label']}' 하자" for inst in instances)
    return (
        "이 이미지에는 빨간 사각형과 번호로 표시된 하자 부분이 여러 곳 있습니다.\n"
        f"{listing}\n\n"
        "각 번호에 대해 '번호. 설명' 형식으로 한 줄씩, 색상·모양·크기·질감 등 실제로 "
        "보이는 시각적 특징만 한국어로 설명해 주세요. 보이지 않는 내용은 지어내지 마세요."
    )


def describe_defects_batch(bundle: VLMBundle, image, instances, max_new_tokens: int = 300) -> str:
    """전체 이미지 1장 + 번호 프롬프트로 모든 finding 설명을 한 번에 생성한다(§4-2).

    크롭 N회 호출(`describe_defect` 반복) 대비 이미지 인코딩이 1번뿐이라 지연시간
    이득이 있는지, 대신 번호-영역 매칭 정확도가 떨어지는지를 나란히 비교하기 위한
    함수다. 결과 신뢰도가 크롭 방식보다 낮을 수 있다는 전제의 비교 실험용이다.
    """
    annotated = draw_numbered_boxes(image, instances)
    prompt_text = build_batch_prompt(instances)
    return generate_from_image(bundle, annotated, prompt_text, max_new_tokens)


_BATCH_LINE_PATTERN = re.compile(r"^\s*(\d+)\s*[:.\)]\s*(.+)$")


def parse_batch_response(text: str, expected_nos: list[int]) -> dict[int, str | None]:
    """`describe_defects_batch()` 원문을 번호->설명으로 파싱한다(§4-2 TODO: 번호-영역
    매칭 정확도 확인).

    `build_batch_prompt()`가 "번호. 설명" 형식을 요청하므로 그 형식(구분자는 `:`/`.`/`)`
    관용)을 줄 단위로 매칭한다. 한 줄에 번호가 안 보이면 건너뛴다 — 억지로 분리하지 않는다.
    못 찾은 번호는 조용히 비우지 않고 `None`으로 남겨 "이 번호는 배치 방식이 놓쳤다"는 걸
    드러낸다.
    """
    found: dict[int, str] = {}
    for line in text.splitlines():
        match = _BATCH_LINE_PATTERN.match(line)
        if not match:
            continue
        no = int(match.group(1))
        found[no] = match.group(2).strip()
    return {no: found.get(no) for no in expected_nos}


def missing_batch_numbers(parsed: dict[int, str | None]) -> list[int]:
    """`parse_batch_response()` 결과에서 설명을 못 받은 번호 목록(정렬됨)."""
    return sorted(no for no, description in parsed.items() if description is None)
