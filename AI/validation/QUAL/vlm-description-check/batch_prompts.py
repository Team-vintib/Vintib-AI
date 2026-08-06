"""여러 하자를 한 이미지(넘버링 bbox)로 한 번에 설명받는 배치 프롬프트 — CH011 이후 실측.

지금까지 검증된 건 "하자 1건 크롭 -> 1번 호출"(`loaders.build_defect_prompt`/
`describe_defect`)뿐이다. 이 모듈은 그 반대 극단 — **"이미지 1장(번호별 하자 여러 건) ->
1번 호출"**을 테스트한다. 목표는 finding 수만큼 호출하던 걸 이미지 수만큼으로 줄이는 것
(`worker/models/quality_vlm/describer.py`의 `attach_descriptions()`가 지금 finding당
개별 호출·개별 크롭을 한다).

위치는 여기서도 묻지 않는다(`loaders.build_defect_prompt`와 같은 이유 — 크롭 범위 밖
정보를 물으면 hallucination이 난다는 게 CH009에서 이미 확인됨). 번호별 시각적 특징만
받고, 위치는 프로덕션처럼 SAM3 section으로 이미 알고 있으니 그대로 쓴다.

스파이크 코드다. 프로덕션(`worker/models/quality_vlm/`)에서 import하지 않는다.
"""

from __future__ import annotations

import re


def build_batch_defect_prompt(labels_by_no: dict[int, str]) -> str:
    """번호별 하자 유형 라벨을 주고, 번호마다 한 문장씩 설명을 요청하는 프롬프트.

    출력 형식을 엄격히 지정한다("N: 설명" 줄 단위) — `parse_batch_response()`가 이 형식을
    전제로 파싱하므로, 형식이 바뀌면 두 함수를 같이 고쳐야 한다.
    """
    lines = [f"{no}번: {label}" for no, label in sorted(labels_by_no.items())]
    listing = "\n".join(lines)
    return (
        "이 이미지는 중고 의류 사진이며, 빨간 숫자로 하자 위치가 표시되어 있습니다. "
        f"각 번호가 가리키는 하자 유형은 다음과 같습니다:\n{listing}\n\n"
        "번호 순서대로, 각 하자의 색상·모양·크기·질감 등 실제로 보이는 시각적 특징만 "
        "한국어 한 문장으로 설명해 주세요. 옷의 어느 부위인지는 추측하거나 언급하지 마세요. "
        "다른 번호와 헷갈리지 않게, 반드시 아래 형식만 사용하세요(그 외 문구 금지):\n"
        "1: <설명>\n2: <설명>\n...(번호 개수만큼, 번호 순서대로)"
    )


_LINE_PATTERN = re.compile(r"^\s*(\d+)\s*[:.\)]\s*(.+)$")


def parse_batch_response(text: str, expected_nos: list[int]) -> dict[int, str | None]:
    """ "N: 설명" 형식 줄들을 번호->설명으로 파싱한다. 못 찾은 번호는 None.

    VLM이 형식을 정확히 안 지킬 수 있어(구분자가 "."이나 ")"이거나, 줄바꿈 없이 이어 쓰거나)
    구분자 종류엔 관용적이지만, **줄 단위 매칭**은 그대로 유지한다 — 한 줄에 여러 번호가
    섞여 나오면 그 자체가 "번호를 헷갈렸다"는 신호라 억지로 분리하지 않는다.
    못 찾은 번호는 조용히 빈 문자열로 채우지 않고 `None`으로 남겨, 배치 방식이 그 번호를
    놓쳤다는 사실이 결과에 드러나게 한다.
    """
    found: dict[int, str] = {}
    for line in text.splitlines():
        match = _LINE_PATTERN.match(line)
        if not match:
            continue
        no = int(match.group(1))
        found[no] = match.group(2).strip()
    return {no: found.get(no) for no in expected_nos}


def missing_numbers(parsed: dict[int, str | None]) -> list[int]:
    """파싱 결과에서 설명을 못 받은 번호 목록(정렬됨)."""
    return sorted(no for no, description in parsed.items() if description is None)


# 프로덕션(worker/models/quality_vlm/describer.py)의 _expand_bbox_to_min_size와 같은 값·
# 같은 공식이다 — "건별 크롭 방식" 비교 대상을 지금 프로덕션이 실제로 쓰는 크롭과 최대한
# 같게 맞추려는 것이다. 로컬 사본을 두는 이유: 이 스파이크가 quality_vlm 패키지 전체
# (bitsandbytes 등 무거운 의존성 로딩 경로)를 끌어오지 않게 하기 위해서다.
_CROP_PAD_RATIO = 0.6
_MIN_CROP_SIZE = 160


def crop_for_individual_baseline(
    image, bbox_px: tuple[float, float, float, float], image_size: tuple[int, int]
):
    """건별(개별 호출) 비교 대상 크롭. 프로덕션 `_crop_finding`과 같은 여백·최소크기 공식."""
    x1, y1, x2, y2 = bbox_px
    img_w, img_h = image_size
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    half_w = max((x2 - x1) * (1 + _CROP_PAD_RATIO) / 2, _MIN_CROP_SIZE / 2)
    half_h = max((y2 - y1) * (1 + _CROP_PAD_RATIO) / 2, _MIN_CROP_SIZE / 2)
    crop_box = (
        max(0, int(cx - half_w)),
        max(0, int(cy - half_h)),
        min(img_w, int(cx + half_w)),
        min(img_h, int(cy + half_h)),
    )
    return image.crop(crop_box)
