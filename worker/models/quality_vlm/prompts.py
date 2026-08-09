"""VLM 하자 설명 프롬프트 — `AI/validation/QUAL/vlm-description-check/`에서 검증된 문구.

hotfix/472: 크롭 1장 + finding 1건당 개별 호출(구 `build_defect_prompt`)에서 **원본 이미지
1장 + 번호별 위치·유형 텍스트 힌트로 모든 finding을 한 번에 묻는 배치 방식**
(`build_batch_prompt`)으로 교체했다 — 사용자가 `worker/validation/
quality_vlm_batch_prompt_check.ipynb`로 실측 비교 후 확정. 크롭을 아예 안 만드므로
describer.py의 `_crop_finding`/`_expand_bbox_to_min_size`도 이 교체와 함께 제거했다.

**bbox를 이미지에 그려 넣지 않는다.** 2026-08-06 검증(`AI/validation/QUAL/
vlm-description-check/batch_pipeline_check.ipynb`)에서 넘버링 bbox를 그린 이미지를 그대로
넣으면 VLM이 그 사각형 자체를 "작은 사각형 하자"로 묘사하는 문제가 확인됐다 — 그래서 원본
이미지를 그대로 쓰고, 위치는 `build_batch_prompt()`가 텍스트로만(`Finding.section`을
`SECTION_LABELS_KO`로 한글 변환) 알려준다.

**Few-shot(CH019)**: 사용자가 확정한 예시 2건을 텍스트로 프롬프트에 포함해 답변 문체를
고정한다("~이 확인됩니다"체, 재질/색상/형태 위주 객관 묘사, 위치 미언급). 이미지 few-shot이
아니라 텍스트 예시인 이유는 지연시간 비용 때문(CH011 TODO에서 이미 정함). 예시는 특정
하자 유형 전용이 아니라 모든 요청에 공통으로 붙는다 — 목적이 "정답을 알려주기"가 아니라
"문장 스타일·길이·톤을 고정하기"라서, 질문 중인 유형과 예시 유형이 달라도 무방하다.

설계: `.claude/plans/ai/CH011-quality-vlm-production-wiring.md`,
`.claude/plans/ai/CH019-quality-vlm-fewshot-prompt.md`
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from sam3.contracts import Finding
from sam3.prompts import SECTION_LABELS_KO

# 문체 고정용 few-shot 예시(CH019). 위치를 언급하지 않고 재질/색상/형태만 객관적으로
# 서술한 뒤 "~이 확인됩니다"로 끝맺는 패턴 — 실제 화면 산출물 예시에서 그대로 가져왔다.
#
# hotfix/472: 원래 예시 2개가 전부 "원단"이라는 단어를 직접 썼다("주변 원단보다...",
# "원단이 짧게 해지고...") — 지시문에서 "원단·배경 언급하지 말라"고 해도 few-shot이
# 지시문보다 스타일에 훨씬 강하게 작용해서 실제로는 "흰색 원단 위에" 식으로 계속 나왔다.
# 예시 자체에서 "원단"이라는 단어를 빼서 근본 원인을 없앤다.
_FEW_SHOT_EXAMPLES: tuple[str, ...] = (
    "주변보다 갈색빛이 도는 색상 차이가 확인됩니다.",
    "짧게 해지고 올이 드러난 영역이 확인됩니다.",
)


def build_batch_prompt(findings: Sequence[Finding]) -> str:
    """한 이미지의 finding 전부 -> 번호별 위치·유형 힌트가 포함된 배치 프롬프트 텍스트.

    2026-08-10 사용자가 `worker/validation/quality_vlm_batch_prompt_check.ipynb`로 최종
    확정한 문구를 그대로 옮겼다(원본: `AI/validation/QUAL/vlm-description-check/loaders.py`의
    `build_batch_prompt`). `findings`는 같은 이미지(`image_index`가 동일)의 finding들이어야
    한다 — 여러 이미지를 섞어 넘기면 안 된다(호출부인 `describer.py`가 이미지별로 나눠 부른다).
    """
    examples = "\n".join(f"- {example}" for example in _FEW_SHOT_EXAMPLES)
    listing = "\n".join(
        f"{f.no}번 ({SECTION_LABELS_KO[f.section]} 부근): '{f.label}' 하자" for f in findings
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


# 2026-08-06 실측(`AI/validation/QUAL/vlm-description-check/loaders.py`): 응답이 "1번. 설명"
# 처럼 숫자와 구분자(`.`/`:`/`)`) 사이에 한국어 카운터 "번"이 끼어 있는 경우가 실제로
# 많았다 — `build_batch_prompt()`의 입력 목록 문구("1번 (위치 부근): ...")를 모델이 출력에서도
# 그대로 따라 하기 때문. "번" 선택적 허용 + 마크다운 볼드/불릿 허용까지 검증된 그대로 옮긴다.
_BATCH_LINE_PATTERN = re.compile(r"^[\s*#\-•]*(\d+)\s*번?[\s*]*[:.\)][\s*]*(.+)$")


def parse_batch_response(text: str, expected_nos: Sequence[int]) -> dict[int, str | None]:
    """배치 응답 원문을 번호->설명으로 파싱한다.

    한 줄에 번호가 안 보이면 건너뛴다 — 억지로 분리하지 않는다. 못 찾은 번호는 조용히
    비우지 않고 `None`으로 남겨 "이 번호는 배치 방식이 놓쳤다"는 걸 드러낸다
    (`describer.py`가 실패 로그를 남길 때 이 정보를 쓴다).
    """
    found: dict[int, str] = {}
    for line in text.splitlines():
        match = _BATCH_LINE_PATTERN.match(line)
        if not match:
            continue
        no = int(match.group(1))
        found[no] = match.group(2).strip()
    return {no: found.get(no) for no in expected_nos}
