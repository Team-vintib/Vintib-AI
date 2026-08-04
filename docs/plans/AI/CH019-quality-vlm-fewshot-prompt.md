# 하자 설명 VLM — Few-shot 프롬프트 고도화 (+ 위치 탐지 방법론 로드맵)

> CH011("VLM 프로덕션 연결")이 남긴 TODO 두 줄(`worker/models/quality_vlm/prompts.py` 상단)의
> 후속. 브랜치는 CH018과 동일 `feat/211-quality-summary-detail`.

## 배경 / 목표

CH011은 `build_defect_prompt()`를 "위치는 묻지 않고 시각적 특징만 한 문장" 지시문 하나로
구현하고, few-shot은 "노트북에서 먼저 검증 후 반영"이라는 TODO로 미뤄 뒀다.

이번 라운드 결정(사용자 확인):
- **모델 파인튜닝은 하지 않는다** — 프롬프트 레벨 개선만.
- **하자 위치 탐지도 고도화 대상**이지만, 방식은 SAM3의 시맨틱 세그먼트 방법론(옷 파츠별
  마스크 — collar/sleeve/hem 등, `상품 등록 AI 파이프라인` 노션 문서(LAB-77)의 "하자 요약
  보완" 절이 이미 이 아이디어를 스케치해 뒀다)을 적용하는 방향으로 **별도 계획에서** 다룬다.
  지금 3×3 그리드(`findings.py`의 `_section_no_of`)를 대체하는 건 이번 범위 밖이다.
- **이번 라운드는 프롬프트 few-shot 적용까지만** 마친다.

## 작업 내용

### 1. Few-shot 예시 확정 — `worker/models/quality_vlm/prompts.py`

사용자가 제시한 예시 2건을 **텍스트 few-shot**으로 반영한다(이미지 few-shot 아님 — CH011
TODO가 이미 "지연시간 비용 때문에 텍스트 예시부터"라고 정해 뒀다).

```
예시 1) 오염 — "주변 원단보다 갈색빛이 도는 색상 차이가 확인됩니다."
예시 2) 올풀림(마모) — "원단이 짧게 해지고 올이 드러난 영역이 확인됩니다."
```

두 예시 모두 위치를 언급하지 않고("왼쪽 앞면 밑단"/"오른쪽 소매 끝단"은 화면에서 부위
헤더로 별도 표시되는 것이지 예시 문장 자체엔 없다), 원단/재질 관찰 + "~이 확인됩니다"체로
끝난다 — 이 스타일을 문체 고정용 few-shot으로 그대로 쓴다.

- `_FEW_SHOT_EXAMPLES` 상수(튜플)로 두 문장을 보관.
- `build_defect_prompt(defect_label)`는 "아래는 좋은 답변 예시입니다" 안내 + 예시 2개를
  프롬프트 앞부분에 넣고, 기존 지시문(위치 언급 금지·지어내지 않기·시각적 특징만·한 문장)은
  그대로 유지한 뒤 "위 예시와 같은 문체로 '{defect_label}'에 대해 답하라"로 마무리한다.
- **시그니처는 바꾸지 않는다**(`defect_label: str -> str`) — `describer.py`의 호출부
  (`build_defect_prompt(label)`) 수정 불필요.
- 예시는 특정 defect_type 전용이 아니라 **모든 요청에 공통으로 포함**한다 — few-shot의
  목적이 "이 유형에 맞는 예시를 보여준다"가 아니라 "문장 스타일·길이·톤을 고정한다"이므로,
  요청 중인 defect_label과 예시의 유형이 달라도(예: HOLE_TEAR를 물으면서 오염/올풀림 예시를
  보여줌) 문제되지 않는다.

### 2. 테스트 — `AI/test/worker/quality_vlm/test_quality_vlm_prompts.py`(신규)

순수 문자열 조립이라 torch 불필요(가드 없이 CI에서 그대로 실행). 확인 항목:
- few-shot 예시 두 문장이 프롬프트에 그대로 포함되는지
- `defect_label` 인자가 프롬프트에 반영되는지
- 기존 회귀 방지 문구(위치 언급 금지·지어내지 않기)가 유지되는지
- `compose_finding_bullet()`는 이번에 변경하지 않으므로 회귀 스모크 정도만(있으면 유지, 없으면 생략)

## 영향받는 기존 코드

- `worker/models/quality_vlm/prompts.py` — `build_defect_prompt()` 재작성 + 모듈 상단 TODO
  주석 정리(few-shot 항목은 반영 완료로 표시, 위치 방법론 로드맵은 별도 참조로 남김).
- `describer.py`/`registry.py`/`loader.py` — 변경 없음(호출 시그니처 동일).

## 구현 목록

- [ ] `worker/models/quality_vlm/prompts.py`: `_FEW_SHOT_EXAMPLES` + `build_defect_prompt()` 재작성, TODO 주석 갱신
- [ ] `AI/test/worker/quality_vlm/test_quality_vlm_prompts.py` 신규
- [ ] `ruff`/`black`/`pytest` 로컬 통과 확인 후 커밋 (push는 사용자)

## 확인이 필요한 미결정 사항 / 후속 과제

1. **실모델 검증 미완료** — few-shot이 실제 `Qwen3-VL` 출력 스타일에 효과가 있는지는
   GPU 실측이 필요하다(`QUALITY_VLM_BACKEND=qwen3_vl`). 무거운 리소스라 팀원 노트북에서
   사용자가 직접 실행해 확인한다 — 이 계획은 프롬프트 코드까지만 다룬다.
2. **위치 탐지 방법론 고도화(시맨틱 파츠 세그먼트)** — 별도 CH 계획으로 분리한다. 이번
   커밋에는 포함하지 않는다.
