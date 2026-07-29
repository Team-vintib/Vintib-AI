# [AI] 가격 책정 — 네이버 신상품가 병행 수집 설계

> 대상 티켓: 에픽 `S15P11A108-211 [PROD] 상품 등록·판매` → 스토리 `-313 [PROD-010] 가격 책정`.
> 브랜치는 `feat/211-pricing-service`.
>
> 선행: `CH002-pricing-model-selection.md`(네이버 comps 커버리지 실측) /
> `CH003-pricing-service-prototype.md`(가격 책정 서비스 프로토타입, 이 문서가 그 위에 얹힌다)
>
> 산출 범위: **신상품(정가) 수집·응답 노출까지.** `pricer.py`의 가격 계산에 반영하는 것은
> 다음 라운드다.

---

## Context — 왜 이 구조인가

가격 책정 서비스는 지금 LLM 웹검색으로 **중고 매물 시세**만 받아온다(`comps.py`의
`LlmWebSearchCompsSource`). CH002 V2 실측이 이미 결론을 내려 뒀다 — 네이버 쇼핑 오픈API는
평균 comps 18건·지연 177ms로 빠르고 표본이 많지만 **중고 비율이 5%뿐**이라 중고 시세
소스로는 못 쓴다. 대신 신상품(정가) 조회에는 적합하다 → **"정가 앵커"로 재배치**하기로
CH002가 이미 정해 뒀고, 이 문서가 그 실행이다.

이번 라운드는 네이버로 신상품가 몇 건을 가져와 **응답에 노출**하는 것까지다.
`pricer.py`의 가격 계산(중앙값·상태계수·range)에 신상품가를 반영하는 로직은 만들지 않는다
— 그 값을 실제로 쓰기로 정했을 때, 그 시점의 요구에 맞춰 별도로 설계한다.

---

## 핵심 설계 결정

### 1. `CompsSource`에 끼워넣지 않고 완전히 분리 — `RetailSource`

`RuleBaselinePricer.price()`는 `is_used is not False`인 항목만 산정에 쓴다. 신상품가를
`CompsSource.fetch()`가 반환하는 같은 리스트에 `is_used=False`로 섞으면, 가격 계산에서는
자동으로 빠지지만 **`comps_used` 응답 필드에서도 같이 사라져 노출할 방법이 없어진다.**
그래서 `RetailSource`를 별도 인터페이스로 둔다. 실패 계약도 서로 다르다(④).

값 객체는 재사용한다 — `CompItem`(title/price/source/url/listed_at/is_used) 그대로 쓴다.
신상품은 "판별 불가"가 아니라 "확실히 신품"이므로 `is_used=False`가 의미상 정확하다.

### 2. 파일 하나로 — `app/pricing/retail.py`

`comps.py`와 같은 패턴(인터페이스+구현체 한 파일)으로 신설. `gms.py`가 따로 빠진 이유
(모델 폴백 루프·재시도)가 네이버엔 없다 — 단순 GET 1회.

- `RetailSource(ABC)` — `key: str` + `fetch(query: str) -> RetailFetch`
- `RetailFetch`(dataclass) — `items: list[CompItem]`, `notes: list[str]`
- `MockRetailSource` — `MockCompsSource`와 같은 sha256 결정적 생성
- `NaverRetailSource` — 네이버 쇼핑 API 호출(URL·헤더·파싱은
  `validation/pricing-model-check/comps_sources.py:105-138`에서 **복사**, import 금지 —
  `validation/`을 프로덕션에서 import하지 않는 규약)
  - `productType`이 `{"4","5","6"}`(중고)이면 드롭
  - 결과 아이템은 항상 `is_used=False`
- `build_retail_source(key=None)` 팩토리

### 3. 순차 호출

LLM 웹검색이 이미 7~15초 걸리는데 네이버는 177ms다 — 병렬화해서 아끼는 시간이 전체의
2% 미만이라 이득이 없다. `service.py`의 `estimate()`에서 comps 처리 뒤 순차로 한 번 더
호출한다.

### 4. 실패는 절대 job을 죽이지 않는다 — 이중 방어

`RetailSource.fetch()`는 **예외를 던지지 않는 게 계약이다.** 키 없음·HTTP 오류·타임아웃
전부 `NaverRetailSource` 내부에서 잡아 빈 `RetailFetch(items=[], notes=[...])`로
변환한다. `service.py`(`_fetch_retail`)에서도 한 번 더 `try/except Exception`으로 감싼다
(구현 버그 방어용 이중 안전장치).

comps는 인프라 오류(`CompsUnavailable`)면 여전히 job을 `failed`로 만들지만, 신상품가는
부가 정보일 뿐 가격 산정의 필수 입력이 아니므로 **어떤 실패든 무조건 빈 배열**로
떨어져야 한다. `CompsUnavailable`을 재사용하지 않고 "안 던진다"로 계약 자체를 다르게
못박는다.

### 5. 스키마 확장 (`schemas.py`)

- `RetailSourceKey(str, Enum)` — `mock` / `naver`
- `PricingModelInfo.retail_source: RetailSourceKey` 추가 — `comps_source`와 같은 이유
- `PricingResult.retail_items: list[CompItem]` — `comps_used`와 나란히, 독립
- `PricingResult.retail_notes: list[str]` — 기존 `notes`(comps 한계 문구)와 분리
- **안 만든 것**: `RetailStats`(median 등 요약통계) — 스코프 밖(YAGNI)

### 6. registry / config / CI 안전장치

- `registry.py` — `RetailSourceConfig(TypedDict)`(display_name/max_items/timeout_seconds),
  `RETAIL_BACKENDS = {"mock": {...}, "naver": {...}}`, **`ACTIVE_RETAIL_SOURCE = "mock"`**
  (기본값), `retail_config()` 헬퍼 — `comps_config()`와 동일 패턴.
- `app/core/config.py` — `naver_client_id`/`naver_client_secret` 추가. `gms_api_key`
  주석과 같은 톤("비어 있으면 mock으로 폴백, 서비스는 정상 기동").
- `AI/.env.example` / 루트 `.env.example` — "validation 전용, 서비스 런타임에는 불필요"
  주석을 GMS_API_KEY 때와 같은 패턴으로 갱신("서비스 런타임에서도 씀, 비어 있으면 mock
  폴백, 무료지만 쿼터 있음").
- `docker-compose.yml`의 `ai:` 서비스 — `GMS_API_KEY` 아래에 `NAVER_CLIENT_ID`/
  `NAVER_CLIENT_SECRET` env 전달 추가.
- `AI/requirements.txt` — `retail.py`가 프로덕션에서 처음으로 `httpx`를 직접 import한다
  (지금은 anthropic의 전이 의존성으로만 존재). `requirements-dev.txt`와 같은 버전
  (`0.28.1`)으로 명시 고정.
- `AI/CLAUDE.md` 하드 룰 — `llm_web_search` 불릿과 같은 형식으로 `naver` retail 백엔드
  불릿 추가: `ACTIVE_RETAIL_SOURCE` 기본값은 항상 `mock`, Claude가 이 값을 바꾸거나 그
  상태로 서버·pytest를 실행하는 것 금지.

---

## 구현 목록

- [x] `app/pricing/schemas.py` — `RetailSourceKey`, `PricingModelInfo.retail_source`,
      `PricingResult.retail_items`/`retail_notes`
- [x] `app/pricing/registry.py` — `RetailSourceConfig`/`RETAIL_BACKENDS`/
      `ACTIVE_RETAIL_SOURCE`/`retail_config()`
- [x] `app/core/config.py` — 네이버 키 필드
- [x] `app/pricing/retail.py`(신규) — 인터페이스 + Mock + Naver 구현체
- [x] `app/pricing/service.py` — `retail_source` 주입, `estimate()`에 순차 fetch 통합
      (`_fetch_retail`로 이중 방어), `get_pricing_service()` 갱신
- [x] `test/pricing/test_pricing_retail.py`(신규) + `test_pricing_service.py`/
      `test_pricing_router.py` 갱신
- [x] `.env.example`(AI/·루트) 주석 갱신, `docker-compose.yml` env 추가, `requirements.txt`에
      `httpx` 명시
- [x] `AI/CLAUDE.md` 하드 룰 불릿 추가
- [x] `PricingRequest.include_retail` 추가 — 신상품가 조회를 **기본 꺼짐**으로 바꾸고
      요청 단위로 켜게 함(아래 "호출 조건(트리거) — 미정" 참고)
- [ ] 실네이버 전환 후 재검증 — **사용자가 직접 실행**(AI/CLAUDE.md 하드 룰)

---

## 호출 조건(트리거) — 아직 미정

처음 설계에서는 `estimate()`가 comps 처리 뒤 매번 무조건 `_fetch_retail()`을 호출했다.
`ACTIVE_RETAIL_SOURCE=naver`로 전환하면 **요청마다 쿼터가 소모**되므로, 임의로 항상 켜 두는
것은 원치 않는다는 피드백을 받아 `PricingRequest.include_retail: bool = False`로
기본 꺼짐 스위치를 추가했다. `estimate()`는 이 값이 `True`일 때만 `_fetch_retail()`을 부르고,
`False`(기본)면 `retail_items=[]` + 사유 note만 채운다.

**"언제 켤지"는 아직 정해지지 않았다** — BE/FE 팀과 트리거 기준(예: 판매자가 "미착용/새 상품"
태그를 달았는가 등)을 논의한 뒤 결정한다. 지금은 함수 분리 + 스위치만 준비된 상태이고,
그 판단 결과를 `include_retail`에 담아 보내는 쪽(BE) 또는 AI가 다른 필드로 내부 판단하는
쪽 중 무엇을 택할지도 그때 정한다. 트리거가 정해지면 이 섹션과 스키마 docstring을 갱신한다.

---

## 범위 밖 (명시적 배제)

- `pricer.py` 수정(가격 계산에 신상품가 반영) — 다음 라운드
- `RetailStats`(요약 통계)
- BE `retail_price`(요청 필드)와 네이버 결과의 병합·우선순위 로직
- BE/FE 연동(이미 `-338` 스코프 밖으로 확인됨)
- `include_retail`의 실제 트리거 기준 확정 — BE/FE 협의 후 별도 결정

---

## 검증

```bash
cd AI && ruff check . && black --check . && pytest -q
```
기본값이 `mock`/`mock`이라 네트워크·GMS·네이버 호출 없이 전부 통과해야 한다(CI 안전 확인).

실네이버 전환·실행은 하드 룰대로 **사용자가 직접**: `registry.ACTIVE_RETAIL_SOURCE = "naver"`
+ `.env`에 `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET` 채운 뒤 재실행.
