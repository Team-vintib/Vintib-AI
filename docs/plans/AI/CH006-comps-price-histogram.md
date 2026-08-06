# [AI] 가격 책정 — comps 가격 구간별 히스토그램 (설계)

> 대상 티켓: 에픽 `S15P11A108-211 [PROD] 상품 등록·판매` → 스토리 `-313 [PROD-010] 가격 책정`
> → 고도화 작업(`-343`/`-344`). 브랜치는 `feat/211-google-lens-pricing-check`.
>
> 선행: `CH003-pricing-service-prototype.md`(서비스 프로토타입, `RuleBaselinePricer`가 이미
> `comps_stats`를 조립한다) / `CH005-google-serp-grade-reference.md`(SerpApi 경로가 반려되며
> 남긴 "우리 comps로 직접 계산" 대안이 이 문서의 출발점)
>
> 산출 범위: **설계만.** `AI/CLAUDE.md`의 신규 도메인 로직 규율에 따라 이 문서가 사용자
> 검토·승인을 받은 뒤에만 구현에 착수한다.

---

## Context — 왜 필요한가

LAB-21(가격 책정 레퍼런스 비교, FE와 논의한 아이디어)에 "그래프로 보여주기 — x축 가격 범위,
y축 등록된 물품 수"가 있다. 지금 `PricingResult.comps_stats`는 중앙값·p25·p75 세 점만
주기 때문에, 이 그래프를 그리려면 FE가 원본 `comps_used`(가격 리스트)를 직접 구간별로 세어야
한다. **그 집계를 AI가 대신 해서 내려주면** FE 작업이 줄고, 구간 경계도 서버가 일관되게
관리할 수 있다.

**외부 API가 전혀 필요 없다** — 이미 `comps.py`(mock/`llm_web_search`)가 수집해 온
`CompItem` 가격을 구간별로 세는 순수 집계 로직이다. CH005가 SerpApi 경로를 반려하며 남긴
대안 중 실행 가능한 부분이 바로 이것이다.

---

## 핵심 설계 결정

### 1. 계산 위치 — `pricer.py`, `RuleBaselinePricer.price()` 안

`comps_stats`(median/p25/p75)를 조립하는 지점과 같은 곳에서 같이 계산한다. 별도 백엔드나
인터페이스가 필요 없다 — 이미 있는 가격 리스트를 구간별로 세는 순수 함수 하나
(`_price_buckets(prices, bucket_count)`)면 된다.

### 2. 어떤 표본을 쓰나 — **trim 이전의 `usable`**

`price()`는 이미 두 단계로 나뉘어 있다: `usable`(is_used=False만 제외한 전체) → `trimmed`
(표본 5건 이상이면 최고·최저 1건씩 제거, 중앙값 계산용). 히스토그램은 **`usable` 전체**로
그린다 — trim은 "중앙값이 이상치에 흔들리지 않게" 하려는 목적이고, 히스토그램은 반대로
"실제 분포가 어떻게 생겼는지"를 보여주는 목적이라 이상치도 눈에 보여야 의미가 있다. 최소
표본 기준(`min_comps_for_pricing`)은 그대로 따른다 — `priced=false`면 `comps_stats` 자체가
`None`이라 버킷도 자동으로 없다(추가 분기 불필요).

### 3. 버킷 정책 — 고정 개수, 균등 분할

절대 폭(예: "1만원 단위")이 아니라 **고정 버킷 개수**로 `min(usable)`~`max(usable)`를 균등
분할한다. comps 표본이 원래 적어서(mock 5건, `llm_web_search` 최대 10건) 절대 폭 방식은
가격대에 따라 버킷이 텅 비거나 한 칸에 다 몰리는 문제가 생기기 쉽다.

- `registry.PRICE_BUCKET_COUNT = 5` (상수, 근거는 표본 크기 상한과 맞춘 임의값 — 다른
  임계치들과 같은 성격의 부채로 남긴다)
- **모든 가격이 같은 값**이면 버킷 1개(`[price, price]`, count=전체)로 축소 — 폭 0으로
  나누기를 피한다.
- **표본이 2건 미만**이면 버킷을 만들지 않는다(`min_comps_for_pricing`이 이미 이보다 크게
  잡혀 있어 실제로는 발생하지 않지만, 순수 함수 자체의 방어로 넣는다).
- 경계값(정확히 구간 끝에 걸리는 가격)은 마지막 버킷에 포함시킨다(왼쪽 닫힘·오른쪽 닫힘,
  최상단 버킷만 양끝 포함) — `bisect`류 없이 나눗셈 인덱스 계산 + 마지막 버킷 clamp로 구현.

### 4. 스키마 확장 (`schemas.py`)

- `PriceBucket(BaseModel)` — `min: int`, `max: int`, `count: int`
- `CompsStats.buckets: list[PriceBucket] = Field(default_factory=list)` — 새 필드 하나만
  추가. `comps_stats`가 이미 "근거의 두께"를 숫자로 노출하는 자리이므로 그 안에 자연스럽게
  얹는다. 별도 최상위 필드(`PricingResult.price_histogram` 등)를 새로 만들지 않는다 —
  `comps_stats`가 `None`이면(`priced=false`) 버킷도 같이 사라지는 게 맞는 동작이라, 이미
  있는 nullable 관계를 재사용하는 쪽이 스키마를 더 단순하게 만든다.

### 5. FE 연동은 범위 밖

이번 라운드는 **AI 응답에 필드를 추가하는 것까지**다. FE가 이 필드로 실제 막대그래프를
그리는 것, "10~15 누르면 하이라이트" 같은 인터랙션은 FE 몫이고 이 문서의 범위가 아니다
(CH004가 신상품가 노출만 하고 `pricer.py` 반영을 다음 라운드로 미룬 것과 같은 패턴).

---

## 구현 목록

- [ ] `app/pricing/schemas.py` — `PriceBucket`, `CompsStats.buckets`
- [ ] `app/pricing/registry.py` — `PRICE_BUCKET_COUNT` 상수
- [ ] `app/pricing/pricer.py` — `_price_buckets()` 순수 함수 + `RuleBaselinePricer.price()`에서
      호출해 `CompsStats` 조립 시 채우기
- [ ] `test/pricing/test_pricing_pricer.py` — 균등 분포 표본 / 전부 동일 가격 / 경계값이
      버킷 끝에 걸리는 경우 케이스 추가
- [ ] `test/pricing/test_pricing_service.py` — 응답에 `buckets`가 실려 나오는지 스모크 확인

---

## 범위 밖 (명시적 배제)

- FE의 실제 그래프 렌더링·인터랙션
- 버킷 개수(`PRICE_BUCKET_COUNT`)의 근거 있는 값으로 교정 — 실판매가 정답셋 캘리브레이션
  대상이 되면 그때 같이 본다
- "구매자용 우리 데이터 기반 시세" — 자체 완료거래 데이터가 없어 이번에도 여전히 범위 밖
  (LAB-44가 이미 명시한 제약)

---

## 검증

```bash
cd AI && ruff check . && black --check . && pytest -q
```
순수 함수 추가라 네트워크·GMS·네이버 호출 없이 전부 통과해야 한다.
