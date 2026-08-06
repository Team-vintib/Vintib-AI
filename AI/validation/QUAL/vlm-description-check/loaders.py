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

    2026-08-06 실측: 4bit 경로에서 `device_map="auto"`를 쓰면 "Some modules are
    dispatched on the CPU or the disk" 에러가 났다 — SAM3를 먼저 로드해서 여유 VRAM이
    줄어든 상태였거나, accelerate가 Qwen3-VL처럼 비교적 새 아키텍처의 메모리를 보수적으로
    추정해 실제로는 자리가 있는데도 일부 모듈을 CPU로 돌리려 한 것으로 보인다. 4bit 양자화된
    모듈은 CPU/디스크 오프로드가 안 되니 그 자리에서 바로 예외가 난다. 단일 GPU 전제(이
    스파이크는 처음부터 RTX 4070 Laptop 1장 기준)라 `device_map="auto"` 대신 GPU 0에
    통째로 고정하는 게 이 에러의 표준 우회법이다.
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
            model_id, quantization_config=quant_config, device_map={"": 0}
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

    2026-08-06 실측: `do_sample`을 안 정해주면 Qwen3-VL-Instruct 체크포인트에 내장된
    `generation_config.json`의 샘플링 기본값이 그대로 적용돼서, **같은 이미지·같은
    프롬프트로 다시 불러도 매번 다른 문장이 나온다** — 배치 방식 응답이 한 번은 findings와
    무관한 로고 텍스트를 반복하고, 바로 다음 번엔 위치·유형에 맞는 문장이 나오는 게 실제로
    재현됐다(같은 코드, 같은 입력). "이 방식을 채택할 만한가"를 판단하려면 운에 흔들리지
    않는 결정적 출력이 필요해서 `do_sample=False`(greedy)로 고정한다.
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
        generated_ids = bundle.model.generate(
            **inputs, max_new_tokens=max_new_tokens, do_sample=False
        )
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


def garment_section_label_ko(bbox, image_size: tuple[int, int], category_value: str) -> str:
    """bbox 중심이 속한 3x3 섹션을 프로덕션과 같은 방식(카테고리별 실제 옷 부위명)으로
    반환한다("오른쪽 중앙" 대신 "오른쪽 어깨"/"가슴 중앙" 등).

    `bbox_grid_position()`은 카테고리 정보가 없어 순수 기하학적 표현만 돌려주는데, 실제
    FE 노출용으로는 옷 부위 이름이 훨씬 유용하다(2026-08-06, 사용자 요청). 이 스파이크에는
    실제 카테고리 분류(FashionCLIP)가 없어서 `category_value`를 데모용으로 고정해 받는다
    (`model_registry.DEMO_GARMENT_CATEGORY`) — 실제 서비스에서는 상품 등록 파이프라인의
    분류 브랜치 결과를 받는다. section_no 계산(3x3 그리드 → 1~9, 행 우선)과 부위명 매핑은
    새로 만들지 않고 프로덕션 `worker/models/sam3/findings.py`(`_section_no_of`와 동일한
    공식)·`prompts.py`(`section_label`/`SECTION_LABELS_KO`)를 그대로 재사용한다.
    """
    from worker.models.sam3.contracts import GarmentCategory
    from worker.models.sam3.prompts import SECTION_LABELS_KO, section_label

    x1, y1, x2, y2 = bbox
    img_w, img_h = image_size
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    col = min(int(cx / img_w * 3), 2)
    row = min(int(cy / img_h * 3), 2)
    section_no = row * 3 + col + 1

    section = section_label(GarmentCategory(category_value), section_no)
    return SECTION_LABELS_KO[section]


def compose_finding_bullet(position_label: str, description: str) -> str:
    """SAM3 bbox 기반 위치(신뢰 가능) + VLM 크롭 설명(시각 디테일)을 한 줄로 합친다."""
    return f"{position_label} 부분 — {description}"


def draw_numbered_boxes(image, instances):
    """전체 이미지에 bbox·번호를 그린 복사본을 반환한다 — **사람이 보는 미리보기 전용,
    VLM 입력으로 쓰지 않는다.**

    2026-08-06 실측: 이 사각형을 그대로 VLM 입력에 넣었더니 모델이 사각형 자체를
    "작은 사각형 하자"로 묘사하는 문제가 나왔다("붉은 사각형, ... 위치한 작은 사각형
    하자"처럼 사각형 마킹이 반복 등장) — bbox는 FE가 사용자 확인용으로 그리는 것이지
    (빨강=미확인/초록=사용자가 아니라고 답한 것) VLM이 보는 이미지에 들어가면 안 된다.
    그래서 `describe_defects_batch()`는 이 함수를 더 이상 쓰지 않고, 이 함수는 노트북에서
    "지금 몇 번이 어디인지" 사람이 확인하는 용도로만 남긴다.

    정밀한 렌더링이 목적이 아니라, 눈에 띄는 사각형 + 큰 숫자만 그린다. 개발 노트북
    (Windows)과 다른 OS 양쪽에서 돌 수 있게 폰트 후보를 몇 개 시도하고, 전부 없으면
    PIL 기본 폰트로 넘어간다.
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


def build_batch_prompt(instances, image_size: tuple[int, int], category_value: str) -> str:
    """전체(bbox 미표시) 이미지 + 번호별 위치·유형 목록으로 모든 finding을 한 번에
    요청하는 프롬프트(§4-2, 2026-08-06 수정).

    위치는 이미지에 사각형을 그려 보여주는 대신 **텍스트로만** 알려준다 —
    `garment_section_label_ko()`(SAM3 bbox 기반 계산값 + 카테고리별 실제 부위명)를
    재사용한다. 모델에게는 "이 위치를 참고해서 그 자리의 시각적 특징만 설명하라"고 지시하고,
    위치 자체를 답변에 다시 쓰지는 말라고 명시한다 — 위치는 이미 안전하게 계산되어 있으니
    VLM이 또 언급하면 표현만 흔들리거나 hallucination 재발 여지가 생긴다.

    2026-08-06: `_FEW_SHOT_EXAMPLES`(CH019)를 여기에도 넣는다 — 처음엔 안 넣었었는데,
    그래서 배치 방식 설명 품질이 건별 크롭 방식(`build_defect_prompt`, few-shot 포함)
    보다 눈에 띄게 떨어졌다. 두 경로가 같은 문체 기준을 쓰게 맞춘다.

    2026-08-06(2차): 지시문이 "색상·모양·크기·질감 등"을 전부 나열하라고 요구해서, 정작
    few-shot 예시는 특징 하나만 짧게 말하는데도 모델이 체크리스트를 채우려는 듯 길고
    장황한 문장을 냈다(예시 문체를 무시하는 것처럼 보였던 실제 원인). 예시와 지시문의
    "요구 범위"를 맞춰서 — 예시처럼 딱 한 가지 특징만, 짧게 한 문장으로 요구한다.
    """
    examples = "\n".join(f"- {example}" for example in _FEW_SHOT_EXAMPLES)
    listing = "\n".join(
        f"{inst['no']}번 ({garment_section_label_ko(inst['bbox'], image_size, category_value)}"
        f" 부근): '{inst['label']}' 하자"
        for inst in instances
    )
    return (
        "아래는 하자 시각 설명의 좋은 답변 예시입니다.\n"
        f"{examples}\n\n"
        "이 이미지는 중고 의류 사진입니다. 번호별 하자의 대략적인 위치와 유형을 미리 "
        f"알려드립니다(위치는 참고만 하세요):\n{listing}\n\n"
        "각 번호에 대해 '번호. 설명' 형식으로 한 줄씩, 위 예시처럼 그 위치에서 가장 눈에 "
        "띄는 시각적 특징 딱 한 가지만 짧게 한국어 한 문장으로 설명해 주세요. 색상, 모양, "
        "크기, 질감을 전부 나열하지 마세요 — 예시들도 그중 하나만 말합니다. 위치는 이미"
        " 알려드렸으니 답변에서 다시 언급하지 마세요. 보이지 않는 내용은 지어내지 마세요."
    )


_TOKENS_PER_FINDING = 80  # describe_defect()의 기본 max_new_tokens(단문 1개)와 같은 예산


def describe_defects_batch(
    bundle: VLMBundle,
    image,
    instances,
    category_value: str,
    max_new_tokens: int | None = None,
) -> str:
    """전체 이미지 1장(bbox 표시 없음) + 번호·위치 텍스트 프롬프트로 모든 finding 설명을
    한 번에 생성한다(§4-2).

    `category_value`는 `garment_section_label_ko()`에 그대로 전달된다 — 데모에서는
    `model_registry.DEMO_GARMENT_CATEGORY`(고정값, 실제 분류 없음)를 넘긴다.

    2026-08-06 실측: 이전 버전은 `draw_numbered_boxes()`로 사각형을 그린 이미지를 그대로
    넣었는데, VLM이 그 사각형 자체를 "작은 사각형 하자"로 묘사하는 문제가 나왔다 — bbox는
    FE가 사용자 확인용(빨강/초록 전환)으로만 쓰는 것이지 VLM 입력에 들어가면 안 된다. 그래서
    원본 이미지를 그대로 쓰고 위치는 `build_batch_prompt()`가 텍스트로만 전달한다.

    `max_new_tokens`를 안 주면 `len(instances) * _TOKENS_PER_FINDING`으로 스케일링한다 —
    고정 300으로 두면 finding이 많은 이미지(30건 이상)는 응답이 중간에 끊긴다(2026-08-06
    실측: 8건짜리 응답도 마지막 문장이 끊겼다).

    크롭 N회 호출(`describe_defect` 반복) 대비 이미지 인코딩이 1번뿐이라 지연시간
    이득이 있는지, 대신 번호-영역 매칭 정확도가 떨어지는지를 나란히 비교하기 위한
    함수다. 결과 신뢰도가 크롭 방식보다 낮을 수 있다는 전제의 비교 실험용이다.
    """
    if max_new_tokens is None:
        max_new_tokens = max(1, len(instances)) * _TOKENS_PER_FINDING
    prompt_text = build_batch_prompt(instances, image.size, category_value)
    return generate_from_image(bundle, image, prompt_text, max_new_tokens)


# 2026-08-06 실측: 실제 하자가 있는 이미지 전부(누락 == 건수)가 파싱에 실패한 진짜 원인은
# 마크다운이 아니라 `build_batch_prompt()`의 입력 목록 문구("1번 (위치 부근): '유형' 하자")를
# 모델이 출력에서도 그대로 따라 해서였다 — 응답이 "1번. 설명"처럼 숫자와 구분자(`.`/`:`/`)`)
# 사이에 한국어 카운터 "번"이 끼어 있는데, 기존 정규식은 숫자 바로 뒤에 구분자가 와야 매칭됐다.
# 캡처된 raw_response(outputs/batch_pipeline_check/result.json)로 재검증: "번" 허용 후
# denim/fix/scratch/small_pro는 누락 0건으로 해소. 마크다운 볼드/불릿 허용은 만일을 위해 유지.
_BATCH_LINE_PATTERN = re.compile(r"^[\s*#\-•]*(\d+)\s*번?[\s*]*[:.\)][\s*]*(.+)$")


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
