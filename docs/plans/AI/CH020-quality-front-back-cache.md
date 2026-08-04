# [AI] 품질 검수 앞/뒤 입력 처리 + 캐싱

> 대상 티켓: `S15P11A108-508`([PROD-009 | AI] 품질 검수 앞/뒤 시멘틱 캐싱). 같은 에픽(`-211`) 아래
> `-501`(검수 결과 시각화 개선)/`-512`(bbox 색상 전환 로직 고도화)가 이어지지만, 이 문서는 508만
> 다룬다. 브랜치: `feat/211-quality-front-back-cache`(가안).

## 배경/목표

FE가 상품 상세에 검수 이미지 여러 장(필수 앞/뒤 2장) 캐러셀을 이미 구현해두고 AI 데이터를
기다리는 상태다(`docs/requests/BE/019-product-quality-multi-image.md`, 처리 결과 미기입).
AI 쪽 세그멘테이션·`Finding`·`AttentionMap`·`AnnotatedImage`는 이미 `image_index` 기준으로
이미지별로 동작하지만, 점검해보니 **`section_scores`와 `summary`는 여전히 이미지 전체를 하나로
합쳐서** 낸다 — 앞/뒤를 구분하지 못한다. 508 범위에 이 입력 처리를 포함해서, 캐싱·성능 작업
전에 먼저 앞/뒤 2장이 실제로 독립적으로 잘 처리되는지부터 고친다.

## 작업 내용

### A. 입력 처리 — 앞/뒤 2장 분리 (선행)

- **`section_scores` 이미지별 분리**: `worker/models/sam3/findings.py:293-320`의
  `section_peaks`가 `for result in results` 루프에서 이미지 간 `max()`로 섹션 확률을 합친다
  (`SectionScore`에 `image_index`가 없음 — `worker/models/sam3/contracts.py:118-125`). 앞면
  5번 섹션과 뒷면 5번 섹션 확률이 지금은 서로 섞인다. `SectionScore`에 `image_index`를 추가하고
  이미지별로 9개씩(앞/뒤면 총 18개) 내도록 바꾼다.
- **`summary` 이미지별 분리**: `worker/quality_check_worker_example.py:154`가
  `summarize(extracted.findings)`를 전체에 대해 한 번만 부른다. `image_index`로 findings를
  나눠 이미지별 summary를 만든다 — `scoring.summarize()`는 이미 `Sequence[Finding]`을 받으므로
  로직 변경 없이 호출부에서 필터링만 하면 된다.
- **응답 스키마 동기화**: `AI/app/quality/schemas.py`의 `SectionScore`/`InspectionResult`도
  워커 계약과 맞춰 갱신한다(두 사본 일치는 `AI/test/quality/test_quality_contract.py`가 검사).
- **바꾸지 않는 것(명시)**: `Finding`(key/no/section_no/bbox 전부 이미 image_index 스코프로
  정확함), `AttentionMap`/`AnnotatedImage`(이미 image_index별), cross-type dedup·benign 억제 등
  `findings.py`의 판정 로직 — 요청대로 그대로 둔다.

### B. 캐싱·성능 (508 나머지 항목 — 탐색적, 채택 여부 미확정)

**A를 끝낸 뒤에 필요성을 다시 판단한다.** 아래 항목은 "반드시 구현"이 아니라 "적용 여지가
있는지 확인하는" 단계다 — 실측해보고 이득이 불명확하거나 복잡도 대비 실익이 없으면 채택하지
않는다.

- **모델 로드 유지**: 이미 구조적으로 되어 있다 — `Sam3PcsSegmenter._ensure_loaded()`
  (`worker/models/sam3/segmenter.py:281`)가 프로세스당 1회만 로드하고 이후 재사용하고,
  `quality_vlm`의 `Qwen3VlDescriber`도 `__init__`에서 1회 로드한다(CH011). **새로 구현할 게
  아니라 지연시간 실측으로 확인만** 하면 되는 항목으로 보인다.
- **프롬프트 캐싱**: 무엇을 캐싱하는지 확정 필요 — 아래 미결정 사항.
- **앞/뒤 검수 로드 병렬 처리**: 현재 `worker/quality_check_worker_example.py:121`가 이미지
  루프를 순차 실행한다. GPU 세그멘터가 스레드 안전한지, 단일 GPU에서 forward pass가 어차피
  직렬화돼 실익이 없는지 확인이 먼저다.
- **시멘틱 캐싱 적용 테스트**: 이 리포에 기존 구현이 없다(참고용 설계만
  `AI/docs/chat-advancement-strategy.md` §6에 있음, chat 도메인용). 캐시 키·적용 범위 확정
  필요 — 아래 미결정 사항.
- GPU 실측(지연시간 측정, 실제 SAM3/Qwen3-VL 구동)은 `AI/CLAUDE.md` 관례대로 **AI가 직접
  실행하지 않고 사용자가 로컬 GPU에서 실행**한다. AI는 스크립트만 준비한다.

## 구현 목록

- [ ] `worker/models/sam3/contracts.py` — `SectionScore`에 `image_index` 추가
- [ ] `worker/models/sam3/findings.py` — `section_peaks`를 이미지별로 분리해 계산
- [ ] `worker/quality_check_worker_example.py` — summary를 image_index별로 생성
- [ ] `AI/app/quality/schemas.py` — `SectionScore`/`InspectionResult` 계약 갱신
- [ ] `AI/test/quality/test_quality_contract.py` 등 — 계약 동기화 테스트 갱신
- [ ] 앞/뒤 2장 목업 시나리오로 회귀 테스트(섹션 점수·요약이 이미지별로 분리되는지)
- [ ] (B) 지연시간 측정 스크립트 준비 — 실행은 사용자
- [ ] (B) 프롬프트 캐싱/병렬 처리/시멘틱 캐싱 — 미결정 사항 확정 후 착수
- [ ] `ruff check . && black --check . && pytest -q` 통과 후 커밋(푸시는 사용자)

## 확인이 필요한 미결정 사항

- BE 응답 형태를 지금처럼 평면(`image_index` 필드) 구조로 유지할지, `docs/requests/BE/019`가
  요구한 `images[]` 묶음 구조로 AI가 직접 그룹핑해서 낼지.
- "프롬프트 캐싱"이 구체적으로 무엇을 가리키는지(SAM3 프롬프트 임베딩 재사용? 다른 의미?).
- "시멘틱 캐싱"의 캐시 키·무효화 정책(이미지 임베딩 유사도 기준? 상품 단위 재검수 감지?) —
  판정에 유사도 캐시를 쓰면 오탐/미탐 리스크가 있다는 점은 `chat-advancement-strategy.md`
  §6.1("판정에는 유사도 캐시를 쓰지 않는다")의 경계가 여기도 적용되는지 검토 필요.
- 앞/뒤 병렬 처리가 실제로 지연시간을 줄이는지(GPU 직렬화 가능성) — 실측 전에는 설계를
  확정하지 않는다.
