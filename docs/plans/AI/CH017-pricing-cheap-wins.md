# CH017 — 가격 검색 저비용 개선 (프롬프트·후처리·자체 로그)

> 대상 티켓: `S15P11A108-494 [PROD-010 | AI] 가격 검색 로직 고도화`. 브랜치 미정.
>
> 선행: `CH016`(내부 호가 비교 — BE 데이터 0건이라 보류 중) / `-494` 점검 보고서(B1~B4)
>
> 산출 범위: **설계 + 구현.** BE·DB 의존 없이 지금 바로 완결 가능한 항목만 다룬다.
> 실제 GMS 실호출 검증(구조화 출력 지원 여부, 사이트 비교)은 스크립트만 준비하고
> **실행은 사용자가 직접 한다**(`AI/CLAUDE.md` 하드 룰).
>
> **2026-08-04 구현 완료** — §1~4(신뢰도 결함·잘린 응답 복구·규칙 필터·관측 로그)는 코드+테스트
> 완료(`ruff`/`black`/`pytest` 전부 통과, 105/105 pricing 테스트). §5·6(사이트 A/B/C 비교,
> 구조화 출력 스모크)은 스크립트 작성까지 완료 — **GMS 실행은 사용자 몫**:
> ```bash
> python validation/PRICE/pricing-model-check/site_scope_comparison.py --limit 1
> python validation/PRICE/pricing-model-check/smoke_gms.py --structured-output
> ```

---

## 배경

'요즘 당근 AI 개발' 인사이트 — *"때로는 프롬프트 엔지니어링 정도와 후처리를 추가하는 것만으로도
개선된다"*. CH016(내부 DB 연동)은 BE 실데이터가 0건이라 지금 착수해도 효과를 측정할 수 없다.
반면 `-494` 점검에서 발견된 결함 3건(B1·B2·B4)은 설계까지 끝났지만 구현되지 않은 채 남아 있고,
BE·DB 의존이 전혀 없다. 이걸 먼저 한다.

## 구현 항목

### 1. 신뢰도 계산 결함 수정 (B1)

`pricer.py`의 `_confidence()` 분산 항이 `1 - (p75-p25)/median`인데 comps 1건이면 분산 항이
만점이 된다. **표본이 최소 개수 미만이면 분산 항을 0으로 둔다**(신뢰도를 깎는 방향으로만
작동하게). 임계치는 `registry.CONFIDENCE_DISPERSION_MIN_COMPS`로 노출한다(임의값 부채,
기존 계수들과 같은 성격).

### 2. 잘린 응답 부분 복구 (B2)

`gms.py`에 `generationConfig.maxOutputTokens`를 명시한다(설정 가능, `registry.py`의
`CompsSourceConfig`에 `max_output_tokens` 추가). `comps.py`는 `finishReason`을 읽어
`CompsFetch`에 진단 필드로 남기고, 배열이 완결되지 않았을 때 **완결된 객체만 부분 복구**한다
(잘린 마지막 항목만 버리고 나머지는 살린다). `groundingChunks`에서 가격을 추출하는 폴백은
넣지 않는다 — 청크에는 가격이 구조화돼 있지 않아 추측이 된다.

### 3. comps 규칙 필터 (신규, 기본 off)

`app/pricing/filters.py` — 순수 함수. 브랜드 키워드 미포함 제거 + 가격 MAD 기반 이상치 제거.
`registry.ACTIVE_COMPS_FILTER = "none"`(기본) / `"keyword_mad"`로 스왑. 기본이 꺼져 있으므로
지금 이 커밋으로 산정 결과가 바뀌지 않는다 — 실측(§4·§5) 이후에 켤지 결정한다.

### 4. 자체 검색 결과 로그 (신규)

`app/pricing/store.py` — `app.core.db.get_vector_engine()`(AI 소유 postgres-vector, BE와
무관)을 재사용해 실제 GMS 검색 결과를 적재한다. `app/chat/rag_store.py`와 같은 패턴
(자체 `Base`, `init_schema()`, 저장/조회 함수). 벡터 컬럼은 쓰지 않는다 — 유사도 검색이
목적이 아니라 캐시·사후 검수용 원장이다.

`service.py`에서 comps 백엔드가 `mock`이 아닐 때(실제 검색일 때만) 결과를 적재한다.
**적재 실패가 가격 산정을 막지 않는다** — `RetailSource`와 같은 계약(예외를 삼키고
로그만 남긴다).

효과: (a) 같은 쿼리 재검색 비용·지연 절감(캐시), (b) 파싱 실패·이상값 사후 검수 가능
(당근의 BigQuery 뷰 테이블과 같은 역할, BE 의존 없이), (c) CH016의 관측 저장소를 실데이터로
채우는 시작점.

### 5. 사이트 비교 실험 스크립트 (신규, 실행은 사용자)

`validation/PRICE/pricing-model-check/site_scope_comparison.py` — 후르츠패밀리 / 번개장터 /
당근마켓 세 곳을 **각각 별도 쿼리로 한정 검색**해 A/B/C 비교군을 만든다. `comps_sources.py`와
같은 지표(평균 comps·중고 비율·지연)를 사이트별로 집계하고, 세 사이트의 가격 분포(중앙값·IQR)를
나란히 출력해 겹침 여부를 눈으로 볼 수 있게 한다.

⚠️ 쿼리 1건당 GMS 호출이 **3회**로 늘어난다(하드 룰 — 기본 쿼리 수를 작게 잡고 비용 경고를
스크립트 상단에 명시한다). 지금 프로덕션 프롬프트("후르츠패밀리·번개장터·중고나라")와 실측
스크립트("번개장터·당근마켓·중고나라")의 사이트 목록 불일치(B4)를 이 실측으로 해소한다.

### 6. 구조화 출력 실측 스크립트 (신규, 실행은 사용자)

`smoke_gms.py`에 Gemini `responseSchema` 지원 여부를 확인하는 실험을 추가한다. **프로덕션
`comps.py`는 건드리지 않는다** — GMS가 이 파라미터를 통과시키는지 미확인 상태에서 프로덕션에
넣으면 400이 원인 파악 없이 전체 검색을 막는다. 통과가 확인되면 별도로 프로덕션 반영을 검토한다.

## 범위 밖

- B3(브랜드 선택형 전환), B4의 사이트 목록 **확정** — §5 실측 결과가 나온 뒤
- `PricingResult`(BE 계약) 필드 추가 — 필터 결과·진단 정보는 이번 라운드에 내부 로그로만 남김
- CH016 §4 2차(BE DB 연동) — 그대로 보류

## 검증

```bash
cd AI && ruff check . && black --check . && pytest -q
```

`store.py` 테스트는 인메모리 SQLite로 스키마를 검증한다(라이브 postgres 불필요) — sqlalchemy·
psycopg·pgvector는 이미 `requirements.txt`(프로덕션 의존성)에 있어 CI에서 그대로 설치된다.
