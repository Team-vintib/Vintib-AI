# 품질 검수 — 하자 짧은 설명 생성(sVLM) 선정·검증·연결 — 설계

> 대상 티켓: 에픽 `S15P11A108-299 [INS] 품질 검수` → 스토리 `-300 [PROD-009] 품질 검수` →
> 작업 **`-309 [PROD-009 | AI] 품질 검수 서비스 고도화`**(진행 중, 담당 미배정 설명, 최형수).
> 브랜치는 기존과 동일 `feat/211-quality-sam3-segmenter` 유지.
>
> 이전 단계: `-304`(서비스 구현, CH006/CH007/CH008로 완료) → `-307`(전처리, 완료).
> 이번 계획은 CH007이 열어 둔 `Finding.description`(항상 `None`)을 실제로 채우는 작업이다.

## Context — 왜 지금인가

CH006부터 반복적으로 "sVLM 설명 생성은 이 계획 밖"이라고 미뤄 온 항목이다. CH007에서
`Finding.no`/`label`(태그) + `annotated_images`(넘버링 bbox 이미지)까지 끝나서, FE/BE가
"1. 오염", "2. 찢어짐" 같은 **태그 불릿 리스트**는 이미 만들 수 있는 상태다. 남은 건
**상품상세에 넣을 한 줄 설명**뿐이다 — 그 자리(`description`)는 스키마에 이미 있고 항상
`None`이다.

노션 LAB-43은 VLM 대신 템플릿+실측값 조합안을 대안으로 검토했었는데, 이번엔 VLM 경로로
가기로 확정했다(사용자 결정, 2026-07-31). 이 계획은 그 확정을 전제로 **① sVLM 후보 선정
② 검증 ③ 프로덕션 연결**까지를 다룬다.

## 왜 "sVLM"인가 — GMS 경유 배제

`AI/CLAUDE.md` 하드룰: GMS 게이트웨이를 경유하는 코드는 Claude가 절대 실행하지 않고, 고가
모델은 기본 후보로 넣지 않는다. 그래서 이번 계획은 처음부터 **로컬에서 도는 소형 VLM(sVLM)만
후보로 삼는다** — `worker/models/sam3/`(SAM3)·`chat_rag_worker_example.py`(LFM2.5-230M)와
같은 패턴: 팀원 GPU 노트북에서 conda 환경으로 직접 실행, GMS 무관, 실행은 항상 사용자가 한다.

## 작업 내용

### 1. 후보 선정 (`AI/validation/QUAL/vlm-description-check/` 신규 스파이크)

`model_selection/model_registry.py` 관례대로 후보 dict + `ACTIVE_*` 상수로 관리한다.

| 후보 | 특징 | 확인할 것 |
| --- | --- | --- |
| Moondream2 (~1.9B) | 가볍고 빠름, 캡셔닝 특화 | 한국어 출력 품질(영어 전용 가능성 높음) |
| SmolVLM2 (256M~2.2B) | HF 공식, 여러 크기 | 가장 작은 크기로도 하자 설명이 되는지 |
| Qwen2-VL-2B-Instruct | 다국어(중국어권 포함) 학습 | 한국어 직접 출력 가능성이 상대적으로 높음 |
| PaliGemma2 (3B) | Google, VQA 강점 | 짧은 설명 vs 장황한 캡션 경향 |

⚠️ 표의 크기·특징은 일반 공개 정보 기준이며, 실측 전까지는 참고용이다.

### 2. 검증 축

- **한국어 출력**: 프롬프트로 한국어를 요청했을 때 실제로 한국어 문장이 나오는지(안 되면
  영어 생성 후 번역 단계 추가 필요 — 아키텍처가 한 단계 늘어남).
- **입력 단위**: `Finding.bbox`로 크롭한 이미지 1장 + `defect_type`/`section` 컨텍스트를
  프롬프트에 같이 줬을 때 설명 품질이 얼마나 나아지는지(vs bbox 크롭 이미지만 단독으로).
- **할루시네이션**: 실제로 안 보이는 하자를 지어내는지 — 육안 대조.
  `sam3_qc_test_masking.ipynb` §8(윤곽선 확대 비교) 산출물을 재사용해 같은 이미지로 대조한다.
- **VRAM 동시 적재**: SAM3(RTX 4070 8GB 기준 fp16 ~1.7GB)와 같은 프로세스/노트북에 같이
  올릴 수 있는지 실측(`_vram_report` 스타일 로깅, CH006/007 스파이크와 동일 방식).
- **지연시간**: 검수 1건당 finding 개수만큼 VLM을 반복 호출하면 누적 지연이 커진다 — 이미지
  1장당 등록 findings 평균 개수 기준으로 예상 총 지연을 실측한다(품질검수는 비동기 큐라
  여유는 있지만 무한정 늘어나면 안 됨).

### 3. 프로덕션 연결 (검증 통과 후)

- `worker/models/sam3/` 안에 신규 모듈(가칭 `vlm.py`) 또는 `worker/models/quality_vlm/`
  별도 패키지 — `describe_defect(crop_image, defect_type, section) -> str` 인터페이스 하나.
  (별도 패키지로 할지는 CH006의 "왜 별도 분리인가" 판단 기준을 그대로 적용 —
  conda 환경이 SAM3와 다르면 분리, 같으면 합쳐도 됨. 검증 단계에서 정한다.)
- `findings.py`의 `_to_findings()` 이후 단계에서 각 finding을 크롭해 VLM 호출, 결과를
  `description`에 채운다.
- **목업 우선**: `describe_defect`도 SAM3와 같은 원칙 — `QUALITY_VLM_BACKEND`(가칭)
  환경변수로 스왑, 기본값은 mock(예: `f"{label} 발견"` 같은 정적 문구). 실모델 전환은
  사용자만 한다.
- 워커 오케스트레이션(`quality_check_worker_example.py`)에 호출 배선 추가.

## 확인이 필요한 미결정 사항

1. **크롭 단위** — finding 1건당 1회 호출 vs 이미지 1장에 findings 전체를 한 번에 설명시킬지.
   후자는 호출 수가 줄지만 "몇 번이 무슨 설명인지" 매칭 로직이 새로 필요하다.
2. **한국어 직접 생성 vs 번역 단계 추가** — 후보 검증 결과에 따라 확정.
3. **지연시간이 예산을 넘으면** — 배치 처리·캐싱·모델 축소 중 무엇으로 대응할지는 검증 실측
   이후 판단.
4. **패키지 분리 여부** — SAM3와 같은 conda 환경에 들어갈 수 있으면 `worker/models/sam3/`
   안에, 아니면 별도 패키지로.

## 구현 목록

- [ ] `AI/validation/QUAL/vlm-description-check/` 스파이크 폴더 + 후보 레지스트리
- [ ] 후보 3~4개 실측 검증(한국어 출력·할루시네이션·VRAM·지연시간)
- [ ] 검증 결과로 후보 확정 + 미결정 사항 4개 결론
- [ ] 프로덕션 모듈(`vlm.py` 또는 별도 패키지) 구현, `QUALITY_VLM_BACKEND` mock 기본값
- [ ] `findings.py`/`quality_check_worker_example.py`에 배선
- [ ] `app/quality/schemas.py`/`worker/.../contracts.py`는 변경 없음(`description` 필드는
      CH007에서 이미 추가됨 — 이번엔 값만 채움)
- [ ] 테스트: mock VLM 백엔드 순수 로직 테스트, 계약 회귀(`test_quality_contract.py`)
- [ ] `ruff`/`black`/`pytest` 로컬 통과 확인 후 커밋 (push는 사용자)
