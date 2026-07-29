# [AI] 가격 책정 고도화 — 구글 검색 기반 등급별 시세 레퍼런스 (설계)

> 대상 티켓: 에픽 `S15P11A108-211 [PROD] 상품 등록·판매` → 스토리 `-313 [PROD-010] 가격 책정`
> → 고도화 작업(`-343`/`-344`, CH002가 남겨 둔 후속 티켓). 브랜치는 미정.
>
> 선행: `CH002-pricing-model-selection.md`(comps 백엔드 커버리지 실측) /
> `CH003-pricing-service-prototype.md`(서비스 프로토타입) /
> `CH004-naver-retail-price.md`(신상품가 병행 수집 — 같은 "부가 레퍼런스" 패턴의 선례)
>
> 산출 범위: **설계만.** `AI/CLAUDE.md`의 신규 도메인 로직 규율에 따라, 이 문서가 사용자
> 검토·승인을 받은 뒤에만 구현에 착수한다. 아래 "다음 단계"의 실측 라운드(CH002와 같은
> PoC 스파이크)가 먼저다 — 방식 A/B 중 무엇을 실제로 쓸지가 아직 결정되지 않았다.

---

## Context — 왜 구글 검색인가

사용자가 첨부한 예시(`Levis LVC 54501 시세` 구글 검색)에서, 구글의 "AI 개요"(AI Overview)가
번개장터·후루츠패밀리·중고나라를 이미 크롤링해서 **등급별(A+/A/B/C) 가격 범위**로
요약해 준다:

```
A+급 (택이 달린 미사용 새제품): 220,000원 ~ 260,000원
A급 (착용 횟수가 적고 수선/세탁 없는 상태): 150,000원 ~ 190,000원
B급 (자연스러운 워싱/페이딩 및 일반적인 중고 상태): 10,000원 ~ 140,000원
C급 (기장/통 수선 완료, 심한 오염 및 가랑이 폭파 등 하자 포함): 60,000원 ~ 90,000원
```

이건 `pricer.py`의 `condition_coefficient()`가 지금 **근거 없는 임의 계수**
(`clamp(1 + (score - 70) × 0.008, 0.60, 1.25)`, CH003 §임계치)로 흉내 내고 있는 것을
**실측 데이터로 대체할 잠재력**이 있다. LLM 웹검색 comps(CH002 V1)나 네이버 신상품가
(CH004)와 달리, 등급이라는 축을 이미 구조화해서 준다는 점이 다르다.

---

## 조사 결과 (2026-07 웹 검색으로 확인, 링크는 문서 하단 참고 자료)

- **구글은 "AI 개요"를 가져오는 공식 API를 제공하지 않는다.** 구글렌즈도 소비자용 공식 API가
  없다. 실무에서 이 데이터를 구조화된 JSON으로 얻는 경로는 SerpApi 같은 서드파티
  스크레이핑 대행 서비스뿐이다.
- **SerpApi `engine=google`** 응답에 `ai_overview` 필드가 있다. `text_blocks`
  (`paragraph`/`list` 타입)로 구조화돼 있어 스크린샷의 등급별 불릿을 그대로 파싱할 수
  있어 보인다. 다만 즉시 완성되지 않으면 `state: "deferred"`로 오고 `session_key`로
  별도 후속 요청이 필요하다 — "요청 1번 = 응답 1번"을 가정하는 지금 `comps.py`/`retail.py`
  구조와 다른 비동기 폴링이 새로 필요해진다.
- **SerpApi `engine=google_lens`** 는 이미지 + `q`(키워드) 파라미터를 함께 받는다 —
  사용자가 말한 "구글렌즈 + 키워드 검색"과 정확히 일치한다. Products/Visual matches
  섹션에서 title/price/source/link를 주는데, 이 모양은 `CompItem`과 거의 같다.
- **비용**: SerpApi Free 250건/월, 이후 Starter $25/월(1,000건)부터 유료다. 네이버(무료
  쿼터)나 GMS(팀 공용 쿼터)와 달리 **명시적으로 유료인 서드파티 서비스**라 팀 예산 승인이
  선행돼야 한다.
- **ToS/안정성 리스크**: 구글 SERP 스크레이핑은 구글 자체 정책상 회색지대이고(서드파티가
  이를 대행하는 형태), "AI 개요"는 실험적 UI 기능이라 형식이 바뀌거나 특정 쿼리에서
  아예 안 나올 수 있다. LLM 웹검색(comps.py)의 "모델이 검색을 안 했으면 응답 폐기"와
  비슷하게, **AI 개요가 안 나온 쿼리를 어떻게 처리할지**가 실패 계약 설계에 들어가야 한다.

---

## 사용자가 제시한 두 구현 방식 후보

### 방식 A — 가격 범주 건수 기반 (히스토그램)

`google_lens`(이미지+키워드) 또는 구글 오가닉 결과에서 원시 매물(title+price)을 모아,
가격 구간별로 몇 건이 몰려 있는지 집계한다. 등급 라벨은 없다 — "이 가격대에 매물이 N건
있다"는 밀집도만 본다.

데이터 모양이 LLM 웹검색 comps와 거의 같다(`title`/`price`/`url` → `CompItem`). **기존
`CompsSource` 인터페이스에 신규 백엔드로 추가**하는 쪽이 자연스럽다 —
`registry.COMPS_BACKENDS`에 `"google_lens"` 키를 더하는 정도의 확장.

### 방식 B — AI 개요의 등급별 시세를 그대로 파싱 (스크린샷 예시)

구글이 이미 등급별로 계산해 준 가격 범위를 그대로 받는다. 이건 낱개 매물이 아니라
**"등급 → 가격대" 요약 테이블**이라 `CompItem`과 모양이 다르다. `retail.py`처럼 완전히
분리된 새 인터페이스가 필요할 것이다(가칭 `GradeReferenceSource`) — 새 값 객체
(가칭 `GradeBand(grade: ConditionGrade, price_min: int, price_max: int)`), 응답에는
`PricingResult.grade_bands: list[GradeBand]`로 노출한다(레퍼런스용 — `pricer.py`에 실제
반영하는 것은 CH004와 같은 이유로 이번에도 범위 밖).

### 권장(잠정) — 방식 B, 단 실측 전에는 확정하지 않는다

방식 B가 스크린샷과 정확히 일치하고, 지금 근거 없이 흉내 내는 "등급별 계수"를 실측
데이터로 대체할 잠재력이 방식 A보다 크다. 다만:

- `ai_overview`가 모든 쿼리에서 나오는 게 아니다(상품에 따라 아예 생성 안 될 수 있음) —
  CH002가 LLM comps 커버리지를 실측했던 것과 같은 실측이 필요하다.
- `deferred` 상태 처리 때문에 구현 난이도가 방식 A보다 높다.
- **방식 A/B는 배타적이지 않다** — 방식 A를 `CompsSource`에 얹고, 방식 B를 별도 레퍼런스로
  병행하는 것도 가능하다. CH004가 comps(중고 시세)와 retail(신상품가)을 분리했듯, 이번에도
  "등급별 레퍼런스"는 세 번째로 완전히 분리된 슬롯이 될 가능성이 높다.

**최종 채택은 CH002 스타일의 실측 라운드 이후에 결정한다.** 지금은 두 후보를 병기하는
수준이다.

---

## 아키텍처가 걸리는 지점

- **신규 도메인 로직이므로 이 문서가 사용자 승인을 받은 뒤에만 구현 착수**한다
  (루트 `CLAUDE.md`/`AI/CLAUDE.md` 규율).
- SerpApi 키도 `GMS_API_KEY`/`NAVER_CLIENT_ID`·`SECRET`과 같은 취급이 필요해 보인다 —
  `ACTIVE_*_SOURCE` 기본값은 `mock`, 실백엔드 전환은 사용자만, Claude는 실행 금지.
  구현 단계에 들어가면 `AI/CLAUDE.md` 하드 룰에 세 번째 백엔드로 추가한다.
- `ai_overview`의 `deferred` 상태(비동기 폴링)는 지금 `comps.py`/`retail.py`가 가정하는
  "요청 1번 = 응답 1번" 모델과 다르다. 폴링을 넣을지, `deferred`면 그냥 실패 취급(현재
  comps의 "검색 미호출"과 같은 패턴)할지는 실측 후 결정한다.
- 등급 라벨(A+/A/B/C)이 우리 `ConditionGrade`(S/A/B/C)와 정확히 대응하는지도 확인이
  필요하다 — 스크린샷은 A+/A/B/C 4단계이고 우리는 S/A/B/C 4단계라 이름이 다르다.

---

## 범위 밖 (이번 문서에서 결정하지 않는 것)

- 방식 A/B 중 최종 채택(또는 병행) 여부 — 실측 없이는 결정할 수 없다
- `pricer.py`에 등급별 가격대를 실제로 반영하는 로직
- SerpApi 예산·팀 승인 여부
- `GradeReferenceSource`/`registry`/스키마의 구체적인 필드 설계 — 방식이 정해진 뒤
  CH004와 같은 패턴으로 별도 문서화

---

## 다음 단계 제안

1. **(실측, 사용자가 직접 실행)** CH002 스타일로 SerpApi 무료 티어(250건)를 소량 써서
   `ai_overview` 커버리지(몇 %의 쿼리에서 등급별 요약이 나오는지)와 `google_lens` 매물
   품질을 실측한다. 유료 서드파티 키 발급·호출이라 `AI/CLAUDE.md` 하드 룰 대상 —
   **Claude는 이 실행을 하지 않는다.**
2. 실측 결과로 방식 A/B 중 무엇을(또는 둘 다) 프로덕션에 올릴지 결정한다.
3. 결정되면 CH004와 같은 패턴으로 인터페이스·스키마·registry·테스트 설계를 구체화해
   별도 승인을 받는다.

---

## 참고 자료 (2026-07 웹 검색)

- [Google AI Overview Results API — SerpApi](https://serpapi.com/ai-overview) — `ai_overview` 필드, `text_blocks`, `state: complete/deferred` 구조
- [Google AI Overview API — SerpApi](https://serpapi.com/google-ai-overview-api)
- [Google Lens API — SerpApi](https://serpapi.com/google-lens-api) — `engine=google_lens`, 이미지+`q` 키워드 조합
- [Google Lens Products API — SerpApi](https://serpapi.com/google-lens-products-api) — title/price/source/link 구조
- [SerpApi: Plans and Pricing](https://serpapi.com/pricing) — Free 250건/월, Starter $25/월 1,000건부터
