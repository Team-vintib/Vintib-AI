# 상품 등록 — "AI 가격 추천" 그래프가 필요로 하는 데이터 형태

- **요청자 파트**: FE
- **대상 파트**: BE (AI ↔ BE 진행 중인 `034`/`005` 스레드의 소비처 확인 목적)

## 배경/이유

상품 등록 화면 `pricing` 스텝에 "AI 가격 추천" 섹션이 있습니다(`ProductRegistrationPage.vue`, `product-registration__price-chart`). 지금은 `priceRecommendationBuckets`/`recommendedPrices` 두 배열이 페이지 안에 하드코딩된 mock입니다 — 실제 API가 없습니다.

`docs/requests/BE/034-pricing-internal-comps-source.md`(AI↔BE, "상시판매 호가를 시세 근거로 쓰기 위한 확인·요청")를 보니 정확히 이 화면이 필요로 하는 것과 같은 데이터(동일 상품군의 실제 등록가 분포)를 다루고 있는데, 그 문서는 AI의 `PricingResult`(상품 1건 가격 추정) 계약 개선이 목적이라 저희가 화면에 그리려는 **히스토그램(가격대별 등록 상품 수)** 이나 **등급별 대표가**와는 응답 형태가 다를 수 있습니다. 이 문서는 그 스레드에 끼어들지 않고, FE가 실제로 필요로 하는 최종 형태만 별도로 남겨둡니다 — `034`의 인프라(뷰·통계) 작업이 진행될 때 참고해주세요.

## 요청 내용

`034`에서 정리 중인 데이터 소스가 실제로 준비되면, 아래 형태로 조회할 수 있으면 좋겠습니다(엔드포인트 경로·주체는 BE 판단):

```jsonc
{
  "priceBuckets": [
    { "label": "~3만", "min": 0, "max": 30000, "productCount": 6 }
    // 카테고리/사이즈 등 등록 중인 상품과 유사한 조건으로 필터링된 상시판매 상품의 가격대별 개수
  ],
  "recommendedPrices": [
    { "grade": "S", "price": 108000 }
    // 등급(S/A/B/C)별 대표(중간값 등) 가격
  ]
}
```

- 필터 기준(카테고리/브랜드/사이즈 등 어디까지 좁힐지)은 `034`의 §1 데이터 실태 확인 결과에 따라 BE/AI가 정하는 대로 따르겠습니다.
- `034`가 이미 밝힌 대로 실사용 데이터가 사실상 0건이라 지금 당장 되는 요청은 아닙니다 — **인프라(뷰·통계) 작업이 실제로 진행될 때, 최종 응답 형태를 정하실 때 이 문서를 참고 자료로 봐주시면 됩니다.**

## 참고 — 당장은 `044`로 같은 화면을 채울 수 있습니다

`docs/requests/BE/028-pricing-async.md`(AI 외부 시세 검색 기반 가격 추정)가 이미지·실제 상품 없이도 지금 연동 가능하다는 걸 확인했습니다. `docs/requests/BE/044-pricing-estimate-trigger.md`로 그 경량 트리거를 요청해뒀고, 등급별로 4번 호출해 얻은 결과로 이 화면(히스토그램+등급별 추천가)을 "우리 플랫폼 통계"가 아니라 "외부 시세 추정"으로 채우는 방식입니다. **이 문서(043)가 요청한 자체 통계 인프라가 급하지 않다면 044만으로 당분간 충분할 수 있습니다** — 우선순위는 낮춰도 됩니다.

## 관련 자료
- `docs/requests/BE/034-pricing-internal-comps-source.md`, `docs/requests/AI/005-pricing-internal-comps-source-answer.md`
- `FE/src/domains/product/pages/ProductRegistrationPage.vue`(`priceRecommendationBuckets`, `recommendedPrices`, `product-registration__price-chart`)
- `FE/src/domains/product/types/productRegistration.types.ts`(`ProductRegistrationPriceBucket`, `ProductRegistrationRecommendedPrice`)
