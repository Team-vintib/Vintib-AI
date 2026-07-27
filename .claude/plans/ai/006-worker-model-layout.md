# worker/models/ 신설 + app/pricing/ 스텁 생성

## 배경/목표

사용자가 제시한 배치 예상도(`AI/app/` 도메인 구조 + `worker/models/`)를 실제 저장소와 대조한 결과,
`AI/app/gateway`·`recommend`·`chat`·`worker/`(base_worker 등)는 이미 `AI/docs/infra-architecture.md`가
규정한 대로 존재한다. 남은 두 항목만 처리한다.

1. `worker/models/catvton/` — 지금 `AI/validation/AI_tryon/catvton/`에 있는 코드를
   `worker/tryon_worker_example.py`가 이미 실제로 import해서 쓰고 있다(스텁이 아니라 동작하는 코드).
   "추론 코드는 `worker/`" 원칙에 맞는 위치로 옮긴다.
2. `AI/app/pricing/` — 아직 미구현 도메인의 자리만 잡아 둔다.

`.claude/requests/ai/001-migration-tryon-worker-followup.md`가 "품질 검수 쪽(`app/quality/`,
clipseg 워커 이관)은 건드리지 말아 달라 — 요청자가 직접 진행 중이며 로컬 작업물과 충돌한다"고
명시적으로 예약해 두었으므로, 이번 범위에서 **clipseg/winclip 워커 이관은 제외**한다. 채팅용 로컬
LLM 폴더도 만들지 않는다 — `app/chat/answers.py`는 생성된 답변을 담는 저장소(in-memory/Redis)
껍데기일 뿐 LLM을 직접 호출하는 코드가 없어 옮길 대상이 없다.

`app/pricing/`은 저장소 전체에서 관련 문서가 `infra-architecture.md`의 한 줄("동기, 품질검수 완료
후 자동 트리거 | GMS API + 품질점수 기반")뿐이라 실제 요청/응답 스키마나 GMS API 계약이 없다.
지금은 **빈 패키지(`__init__.py`)만** 만들고, router/service/schemas는 GMS 계약이 정해지면 별도
계획 문서로 설계한다.

## 작업 내용

- `git mv AI/validation/AI_tryon/catvton worker/models/catvton`로 디렉터리 전체(추적 파일 476개,
  ~22MB) 이동, 이 경로를 참조하는 곳(`worker/tryon_worker_example.py`, `worker/README.md`,
  `AI/docs/tryon-advancement-strategy.md`, `AI/pyproject.toml`)을 전부 갱신.
- `AI/pyproject.toml`에서 `validation/AI_tryon/catvton` 관련 ruff/black/pytest 설정 항목 제거
  (경로가 `AI/` 밖으로 나가므로). `tryondiffusion` 관련 항목은 무관하니 그대로 둔다.
- `AI/app/pricing/__init__.py` 빈 파일 하나만 생성. `app/main.py`에는 등록하지 않는다(router 없음).
- 건드리지 않는 것: `AI/test/AI_tryon/catvton/`(git 미추적 로컬 잔재), `AI/validation/clipseg-condition-check/`,
  `AI/validation/winclip-condition-check/`, `AI/app/quality/`, `worker/quality_check_worker_example.py`.

## 구현 목록

- [x] 브랜치 `feat/27-worker-model-layout`(`develop-AI` 기준) 생성
- [x] 이 계획 문서 작성
- [x] `git mv AI/validation/AI_tryon/catvton worker/models/catvton` (추적 파일 478개, rename으로 인식됨)
- [x] `worker/tryon_worker_example.py` 경로/주석 갱신
- [x] `worker/README.md` 경로 문자열 3곳 갱신
- [x] `AI/docs/tryon-advancement-strategy.md` 경로 문자열 1곳 갱신
- [x] `AI/pyproject.toml`에서 `validation/AI_tryon/catvton` 관련 3개 섹션 항목 제거
- [x] `AI/app/pricing/__init__.py` 빈 파일 생성
- [x] 검증: `ruff check .`/`black --check .` (miniforge `clipseg` 환경, ruff 0.16.0/black 26.5.1) —
      새로 만든 `app/pricing/`은 통과. `AI/test/AI_tryon/catvton/`(git 미추적 잔재)과 기존 코드 일부에서
      나는 에러는 ruff 버전 드리프트(pinned 0.15.22 vs 설치된 0.16.0)·미추적 잔재 때문으로, 이번
      변경과 무관 — 상세는 세션 보고 참고.
- [ ] 검증: `pytest -q` — 로컬에 pytest가 설치된 conda 환경을 찾지 못해 이번 세션에서는 실행하지
      못함. `requirements-dev.txt` 기준 환경에서 사용자가 직접 확인 필요.
- [x] 검증: `worker/tryon_worker_example.py` 구문 확인(실제 워커 실행은 GPU 노트북에서만 가능)

## 확인이 필요한 미결정 사항

- `app/pricing/` 실제 스키마/서비스는 GMS API 계약이 정해지면 새 계획 문서(`.claude/plans/ai/00N-pricing-*.md`)로 설계.
- `clipseg`/`winclip` 워커 이관은 품질검수 담당자(요청 문서 작성자)가 별도로 진행.
- `AI/test/AI_tryon/catvton/`(untracked 잔재) 삭제 여부는 이번 범위 밖.

커밋 메시지 JIRA 키: `S15P11A108-188`. 브랜치: `feat/27-worker-model-layout`.
