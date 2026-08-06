# [AI] 가격 책정 모델 선정 및 검증 — 설계

> 대상 티켓: 에픽 `S15P11A108-211 [PROD] 상품 등록·판매` → 스토리 `-313 [PROD-010] 가격 책정`
> → 작업 **`-333 [PROD-010 | AI] 가격 책정 모델 검증`** (진행 중, 최형수).
> 브랜치: `feat/211-pricing-model-validation`.
>
> 후속 티켓(이번 범위 밖): `-345 아키텍처 설계` → `-338 서비스 구현` → `-365 프롬프트 엔지니어링`
> → `-342 기능 테스트` → `-343/-344 고도화`.
>
> 근거 문서: 노션 `[PRICE] 가격 책정`(LAB-28) / `가격 책정 레퍼런스 비교`(LAB-21)
> / `이미지 기반 상품 가격 책정 전략`(LAB-15) / `데이터 소스`(LAB-33)
> / `[AI] 품질 검수 서비스 프로토타입 설계`(LAB-32) / `AI API 활용 내역`(GMS 게이트웨이)
>
> 산출 범위: **`AI/validation/pricing-model-check/` PoC 스파이크.** 프로덕션 코드
> (`app/pricing/`)는 이번 라운드에서 건드리지 않는다 — 검증 결과가 `-345 아키텍처 설계`의 입력이 된다.

---

## Context — 왜 검증부터인가

LAB-15가 4단계 파이프라인(상태 스코어 조회 → 시장 데이터 RAG → LLM 가격 결정 → range 출력)을
그려 놨지만, **그 중 어느 것도 실측된 적이 없다.** LAB-21은 업계 표준이 "Vision + comps 기반
예측형"이고 우리처럼 자체 거래 데이터가 없으면 **RAG가 필수**라는 결론까지만 냈다.

그래서 이번 라운드는 "무엇을 만들까"가 아니라 **"각 슬롯에 무엇을 꽂을 수 있는지, 그리고 그게
규칙 기반보다 나은지"** 를 실측한다. 특히 두 가지가 미해결이다.

1. **시세 데이터를 어디서 가져오는가** — 국내 중고 의류 comps를 실제로 얻을 수 있는 경로가
   검증된 적이 없다. 이게 안 되면 LAB-15 파이프라인 전체가 성립하지 않는다.
2. **LLM이 규칙 기반보다 나은가** — LAB-15 스스로 "LLM은 정밀한 정량적 추론에 약함"이라
   적었다. 중앙값 × 상태계수 baseline을 이기지 못하면 LLM을 쓸 근거가 없다.

### 사용자 확정 사항 (2026-07-28)

| 항목 | 결정 |
| --- | --- |
| API 키 | **GMS_API_KEY + 네이버 개발자 오픈API 키** 둘 다 확보 가능 |
| 정답셋 | **실거래완료가 30~50건 수동 수집** (MAPE를 실제로 말할 수 있는 유일한 방법) |
| 사진 역할 | **속성 추출만** — 상태는 `app/quality/`의 `condition_score` 조회 (LAB-15 준수) |

### 기존 설계와의 정합성 확인 2건

- **condition_score는 아직 근거 없는 임의값이다.** LAB-32 §6이 명시한 리스크 — 가중치·등급
  경계가 라벨링 검증셋 없이 정해졌는데 가격책정이 이를 소비한다. 이번 검증에서는
  condition_score를 **정답셋에 수동 라벨로 넣고**, 파이프라인 입력으로만 취급한다. 품질검수
  점수의 타당성은 이 검증의 범위가 아니며, 가격 오차를 condition_score 탓으로 돌릴 수 없도록
  분리한다.
- **GMS 사용은 예외로 명시한다.** 노션 `AI 3대 기능 모델 선정 리서치`가 "핵심 3개 기능은 직접
  구현, 상용 API는 오프라인 평가용"으로 잡았으나, LAB-15는 가격책정을 GMS 기반으로 설계했다.
  가격책정은 4번째 기능이고 **실시간 웹 grounding이 본질**이라 자체 모델로 대체 불가하다 —
  이 근거를 검증 문서에 남긴다.

---

## 검증 대상 — 4개 슬롯

`model_selection/model_registry.py` 관례대로 **중앙 레지스트리 dict + `ACTIVE_*` 상수**로 관리하고,
키 한 줄로 스왑한다.

| 슬롯 | 역할 | 후보 |
| --- | --- | --- |
| **A. 속성 추출 (VLM)** | 상품명 + 사진 → 브랜드·카테고리·모델명·색상 → 검색 쿼리 | GMS 경유 Claude(vision) / Gemini(vision, 저비용) |
| **B. 시세 수집** | 쿼리 → comps(가격·날짜·상태·출처) | ① LLM 서버사이드 웹검색 ② 네이버 쇼핑 오픈API ③ mock |
| **C. 가격 결정** | comps + condition_score → range + 신뢰도 + 근거 | LLM(structured output) / **규칙 baseline** |
| **D. comps 필터 (선택)** | 검색 결과 중 동일 상품만 잔류 | 기존 `bge-m3` 재사용. **B 결과에 노이즈가 많을 때만** 착수 |

**C의 규칙 baseline이 이 검증의 대조군이다.** `median(comps) × 상태계수`로 구현하고, LLM이
이를 이기는지가 채택 근거가 된다.

### 모델 ID 주의

GMS는 SSAFY 프록시라 **노출 모델 목록이 Anthropic 공식과 다를 수 있다**(기존 문서 기준
`claude-sonnet-4-6`, `gemini-3.5-flash`, `gemini-embedding-2`). 레지스트리에는 GMS가 실제로
받아주는 ID만 넣고, 확인 자체를 V1에 포함한다.

---

## 검증 항목과 성공 기준

| # | 검증 | 방법 | 성공 기준 |
| --- | --- | --- | --- |
| **V1** | GMS가 서버사이드 웹검색 툴을 프록시하는가 | 최소 요청 1건 (`web_search` 툴 선언 → `web_search_tool_result` 블록 수신 여부). 동시에 GMS 노출 모델 목록 확인 | 통과/실패 이분 판정. **다른 모든 설계가 여기 걸려 있어 최우선** |
| **V2** | 중고 의류 comps 커버리지 | 빈티지 상품명 30건을 각 백엔드에 질의 | 쿼리당 comps ≥ 3건 비율, 중고 매물 비율, 데이터 최신성(일) |
| **V3** | VLM 속성 추출 정확도 | 정답셋 사진 → 브랜드·카테고리 추출, 수동 라벨과 대조 | LAB-21의 eBay 벤치마크(유명 브랜드 75~92%, 니치 60~75%) 대비 |
| **V4** | 가격 정확도 (핵심) | 정답셋 30~50건, LLM vs 규칙 baseline | MAPE, range hit rate, **range 폭 비율** |
| **V5** | 비용·지연시간 | 슬롯별 토큰/latency 집계 | 모델 라우팅 정책(LAB-15 "태스크별 라우팅")의 근거 확보 |

**V4에서 range hit rate만 보면 안 된다.** range를 무한정 넓히면 hit rate는 100%가 되므로
`(max−min)/mid`를 **항상 같이 보고한다.** 이 둘을 분리해서 보고하지 않으면 지표가 무의미하다.

### V2의 실패 시나리오를 미리 인정한다

네이버 쇼핑 오픈API는 **신품 위주**라 중고 시세가 안 잡힐 가능성이 크다. V2가 실패하면
LAB-15 파이프라인의 ②단계가 무너지므로, 그 경우의 대안을 결론에 함께 적는다 —
(a) LLM 웹검색 단독, (b) LAB-33 정가 데이터 + 중고 할인율 모델, (c) 스크래핑(약관 검토 필요,
프로토타입 범위 밖).

---

## 구현 구조

`validation/` 관례(`<feature>-check/`, `dataset.py` + 실행 + 평가 3분할)를 따른다.

```
AI/validation/pricing-model-check/
  gms_client.py       GMS 프록시 얇은 래퍼. 공식 anthropic SDK에 base_url 주입.
                      무거운 import는 함수 내부 지연 import, 키 없으면 명확히 스킵.
  smoke_gms.py        V1 — 웹검색 툴 지원 여부 + GMS 노출 모델 목록 확인 (제일 먼저 실행)
  comps_sources.py    슬롯 B — naver_shopping / llm_web_search / mock. 공통 CompItem으로 정규화
  attributes.py       슬롯 A — 상품명(+이미지) → 속성 추출
  pricer.py           슬롯 C — rule_baseline(중앙값×상태계수) / llm_pricer
  dataset.py          정답셋 로더 + 스키마 검증 (순수 로직)
  evaluate.py         V2~V5 지표 집계 + 리포트 출력
  data/ground_truth.json   수동 수집 30~50건
  test_pricing_dataset.py  순수 로직 테스트 (가드 불필요, CI에서 실행)
```

- 슬롯 후보·모델 ID는 `validation/model_selection/model_registry.py`에 `PRICING_*` 상수로
  추가한다(중앙 레지스트리 관례). 스파이크 디렉터리는 그걸 import만 한다.
- `anthropic` SDK와 `requests`는 `validation/requirements-test.txt`에 추가한다 —
  **CI에는 설치되지 않으므로** `pytest.importorskip("anthropic")` 가드를 건다.
- 키는 `.env`(gitignore)에서 읽고, **없으면 mock 백엔드로 폴백**한다. 품질검수가 mock을 기본
  백엔드로 둔 것과 같은 이유 — CI에서 전 경로가 돌아야 한다.

### 정답셋 스키마

```
id / product_name / image_path / category / condition_note
condition_score(수동 라벨) / actual_sold_price / source / sold_at / source_url
```

가격·상품명·URL만 담고 판매자 개인정보는 넣지 않는다. 이미지는 용량을 보고
`.gitignore` 여부를 판단한다(학습 산출물 커밋 금지 관례).

---

## 구현 목록

- [ ] `model_registry.py`에 `PRICING_VLM_MODELS` / `PRICING_LLM_MODELS` / `COMPS_SOURCES` + `ACTIVE_*` 추가
- [ ] `validation/requirements-test.txt`에 `anthropic`, `requests` 반영
- [ ] `gms_client.py` — GMS base_url 주입, 키 부재 시 스킵 경로
- [ ] **`smoke_gms.py` 실행 → V1 판정** (여기서 B 슬롯의 최종 후보가 결정됨)
- [ ] `comps_sources.py` — 3개 백엔드 + `CompItem` 정규화
- [ ] `dataset.py` + `data/ground_truth.json` 스키마 확정 → **정답셋 30~50건 수동 수집**
- [ ] `attributes.py` (슬롯 A), `pricer.py` (슬롯 C: baseline 먼저, LLM 나중)
- [ ] `evaluate.py` — MAPE / range hit rate / **range 폭** / comps 커버리지 / 비용·지연
- [ ] `test_pricing_dataset.py` + `ruff check .` / `black --check .` / `pytest -q` 통과
- [ ] 노션 `[PRICE] 가격 책정` 하위에 검증 결과 문서 작성, Jira `-333` 정리

**순서 주의**: V1 → 정답셋 수집 → V2 → V4 순으로 진행한다. V1이 실패하면 B 슬롯 후보가
바뀌므로 그 앞에서 `comps_sources.py`를 완성해 놓으면 헛일이 된다.

---

## V1 · V2 실측 결과 (2026-07-29)

**V1 통과 — LLM 내장 웹검색이 GMS를 통과한다.** 슬롯 B가 외부 검색 API로 강제되지 않는다.

| 조합 | 검색 결과 |
| --- | --- |
| `claude-haiku-4-5-20251001` + `web_search_20250305` | 20건 |
| `claude-sonnet-4-6` + `web_search_20260209` | 81건 |
| `claude-opus-4-6` + `web_search_20260209` | 162건 |
| `gemini-3.5-flash` + `google_search` | grounding 9건 |

부수 확인:

- **GMS는 alias도 받는다** — `claude-sonnet-4-6` / `claude-opus-4-6` 모두 동작. dated ID 전용이 아니다.
- **`/v1/models`는 프록시되지 않는다**(400). 모델 목록은 후보를 직접 찔러서만 알 수 있다.
- **haiku는 `web_search_20260209`를 못 쓴다** — dynamic filtering이 programmatic tool calling을
  요구하는데 haiku가 미지원이다. 구형 규격 폴백이 없었으면 "미지원"으로 오판했을 자리다.
- `gemini-3.5-flash-lite`는 GMS에 없다.

**V2 부분 — 네이버와 LLM은 경쟁이 아니라 상호보완이다.**

| 지표 | 네이버 쇼핑 (10쿼리) | LLM haiku (3쿼리) |
| --- | --- | --- |
| 평균 comps | 18건 | 1.7건 |
| comps ≥ 3 | 9/10 | 1/3 |
| **중고 비율** | **5%** (9/180) | **100%** (5/5) |
| 등록일 | **0건** | 3건 |
| 평균 지연 | **177ms** | **7,687ms** |

- `productType` 가설은 실측 확인됐다(관측 분포 `{1: 38, 2: 133, 5: 9}` — 5가 중고). 다만
  **중고가 5%뿐이라 중고 시세 소스로는 부적합**하고 등록일이 없어 최신성 측정도 불가하다.
  대신 신품 정가는 빠르고 정확하다 → **정가 앵커로 재배치**한다(LAB-33 대안 (b)의 실시간판).
- 니치 쿼리("구제 워크웨어 헤링본 코트")는 네이버에서 0건이었다. LAB-21의 카테고리별 차등이
  검색 단계에서 이미 나타난다.

**⚠️ 동기 가정이 깨졌다.** `docs/infra-architecture.md`는 가격책정을 "동기"로 적어 뒀으나
**가장 싼 모델·가장 적은 검색 라운드에서 이미 7.7초**다. sonnet은 검색 결과가 4배라 더 걸린다.
`-345 아키텍처 설계`는 **품질검수와 같은 job 큐 경로**를 기본으로 잡아야 한다.

---

## 미결정 사항

- ~~GMS 노출 모델 목록~~ — 해소. alias·dated 모두 수용, `/v1/models`는 미프록시.
- ~~네이버 중고 필터~~ — 해소. `productType` 로 판별되나 중고 비율이 5%라 역할을 정가 앵커로 변경.
- **슬롯 B 최종 구성** — 하이브리드(네이버 정가 + LLM 중고 comps)로 갈지, LLM 단독으로 갈지.
  LLM 단독은 comps 수가 평균 1.7건이라 표본이 너무 작다. 프롬프트 완화·모델 상향으로 늘어나는지
  먼저 확인해야 결정 가능하다.
- **모델 선택(haiku vs sonnet)** — 검색 결과 수가 20 vs 81로 4배 차이다. comps 수와 지연·비용의
  트레이드오프를 V5에서 정량화한 뒤 정한다.
- **정답셋 수집 대상 카테고리** — LAB-21의 카테고리별 차등을 재현하려면 유명 브랜드와 니치를
  섞어야 한다. 수집 시작 전에 3~5개를 확정한다.
- **condition_score 수동 라벨 기준** — LAB-32의 점수 체계가 임의값이라, 정답셋 라벨을 그 체계에
  맞출지 별도 기준(예: 상/중/하 3단계)을 쓸지 결정 필요.
