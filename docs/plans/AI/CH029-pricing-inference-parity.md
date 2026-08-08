# CH029 시세 조회 — 검증 vs 프로덕션 추론 일치 점검

## 배경

시세(가격) 추정은 `AI/app/pricing/`에 있다(다른 두 도메인과 달리 `worker/`가 아니라
게이트웨이 컨테이너 `app/` 안에서 돈다 — CH003 설계). `registry.py`의 `ACTIVE_COMPS_SOURCE`/
`ACTIVE_RETAIL_SOURCE`는 둘 다 커밋 기준 `"mock"`이라 `AI/CLAUDE.md`의 GMS 하드 룰은 지금
지켜지고 있다. **이 계획의 점검·실행 과정에서도 `llm_web_search`/`naver`를 활성화하거나
그 상태로 서버·pytest를 돌리는 것은 절대 금지다 — GMS를 경유하는 코드는 Claude가 실행하지
않는다.**

지금까지 확인된 것(읽기 전용 조사, 실행 없음):

- CH002(모델 선정)·CH003(서비스 프로토타입)·CH017(저비용 개선)의 결론은 대체로
  `registry.py`에 그대로 반영돼 있다 — `gemini-3.5-flash` 고정, 분산도 기반 신뢰도 보정
  (`CONFIDENCE_DISPERSION_MIN_COMPS`), naver를 정가 앵커로 쓰는 설계 등.
- CH020(내부 CLIP 코퍼스 비교)이 추가한 `internal_clip` 백엔드는 **상품 분류(CH027)와 같은
  종류의 전처리 비대칭**을 안고 있다 — 코퍼스 임베딩은 `aihub_seed_pricing_corpus.py`에서
  masked variant(배경 제거)로 만드는데, 실서비스 질의 쪽(`app/pricing/clip_embed.py`)은
  업로드된 원본 사진을 크롭·마스킹 없이 그대로 임베딩한다. 코드 자체가 이 비대칭을
  주석으로 인정하고 있다(`clip_embed.py` 상단, "코퍼스=마스킹, 질의=원본 비대칭").
  `similarity_floor=0.55`는 이 비대칭 상태에서 잡힌 값이라 신뢰도가 낮다.
- `internal_clip`은 torch가 필요한데 코드는 `app/pricing/`(배포 컨테이너, torch 없음)에
  있다 — `AI/CLAUDE.md`의 "추론 코드는 AI/app/에 두지 않는다" 원칙과 어긋난다. CH020 문서가
  이미 "범위 밖"으로 표시해 뒀지만, `ACTIVE_COMPS_SOURCE`를 `internal_clip`으로 켜는 순간
  실제로 동작하지 않는 코드라는 뜻이라 다른 두 도메인의 "워커로 옮겨야 함" 문제와 같은
  종류다.
- 가격 계수(`CONDITION_SENSITIVITY`, `BASE_RANGE_WIDTH` 등)는 검증 라운드(R0~R3/B/S1,
  `pricing-histogram-check/`)가 아직 "최종 선정" 없이 열린 그리드 상태이고, ground-truth
  MAPE/적중률 검증 자체가 없다고 CH002/CH003이 스스로 명시한다 — 비교할 "검증에서 확정된
  최적값"이 아직 없는 항목이 많다.

## 목표

"검증에서 확정된 최적 버전"과 "프로덕션 registry.py 설정값"이 일치하는 항목/일치하지
않는 항목/애초에 검증이 끝나지 않아 비교 대상이 없는 항목을 표로 나눈다. GMS를 쓰는
`llm_web_search` 경로는 이번 점검에서 **실행 없이 정적 비교**만 한다(모델 ID·설정값이
CH002/CH003 결론과 같은지 코드만 읽어서 확인). 이 계획은 재훈련이나 재크롤링을 하지 않는다.

## 작업 내용

1. **`llm_web_search` 정적 비교**: `registry.py`의 `model_id`/`min_comps_for_pricing`/
   `max_output_tokens`가 CH002/CH017 문서의 결론과 실제로 같은 값인지 코드 읽기로만 확인
   (GMS 호출 없음).
2. **`naver` 정적 비교**: CH004(네이버 가격 조회) 문서의 결론(정가 앵커, 5% 중고 비율 등)과
   `RETAIL_BACKENDS["naver"]` 설정이 일치하는지 확인.
3. **`internal_clip` 전처리 비대칭 문서화**: 코퍼스(masked) vs 질의(raw) 비대칭을
   `CH027`(상품 분류)과 같은 형식으로 정리하고, `similarity_floor=0.55`가 이 비대칭이
   해소되기 전까지는 신뢰할 수 없는 값이라는 점을 명시한다. 해소 방법 후보(질의 쪽도
   크롭 적용 vs 코퍼스를 raw로 재구축)는 장단점만 정리한다(결정은 안 함).
4. **배치 위치 재확인**: `internal_clip`이 켜졌을 때 실제로 `app/`(torch 없음) 컨테이너에서
   동작 불가능하다는 걸 재확인하고, `worker/`로 옮기는 게 맞는지 CH020/인프라 문서
   (`AI/docs/infra-architecture.md` §3.2) 기준으로 재검토한다.
5. **미검증 계수 목록화**: `CONDITION_SENSITIVITY` 등 ground-truth 비교가 아직 없는
   가격 계수를 "검증 대상 없음"으로 명확히 표시해, CH027/CH028과 달리 이 항목들은
   "불일치"가 아니라 "애초에 비교 기준이 없다"는 걸 구분한다.

## 구현 목록

- [ ] `llm_web_search`/`naver` 설정값과 CH002/CH004/CH017 결론 대조표(정적 비교만)
- [ ] `internal_clip` 코퍼스-질의 전처리 비대칭 정리 문서(해소 후보 장단점 포함, 결정 아님)
- [ ] `internal_clip`의 `app/` vs `worker/` 배치 재검토 결과 정리
- [ ] ground-truth 미검증 가격 계수 목록 작성("비교 기준 없음" 명시)

## 확인이 필요한 미결정 사항

- `internal_clip` 전처리 비대칭을 해소하려면 상품 분류(CH027)와 마찬가지로 질의 이미지에
  세그멘테이션이 필요하다 — 두 도메인이 크롭 문제를 각자 따로 풀지, 공용 전처리 단계로
  묶을지는 CH027 점검 결과와 같이 놓고 판단하는 게 낫다.
- ground-truth 가격 검증셋 확보 자체가 없다 — 이 계획 범위에 포함할지 별도 작업으로 뺄지는
  점검 결과를 보고 정한다.
