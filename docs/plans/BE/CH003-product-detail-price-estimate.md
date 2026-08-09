# CH003 — 상품 상세에 시세 조회 결과 노출 (LLM 재호출 없음)

## 배경/목표

등록 화면에서 확정 등급으로 계산된 AI 시세 추천(`PricingResult`, AI `/ai/estimates`)을 상품
상세에서도 그대로 보여준다. 상세 화면은 LLM을 다시 호출하지 않는다 — 등록 시 FE가 폴링해서
받은 결과를 그대로 BE에 전달해 저장해두고, 상세 조회 시 그 스냅샷을 그대로 돌려준다. `matchKey`
전달 패턴(047)과 동일한 방식이다.

## 작업 내용

- `Product`에 `priceEstimateResult`(jsonb, `Map<String,Object>`) 컬럼 추가 — AI
  `PricingResult` 원본을 그대로 저장(`qualityInspectionResult`와 같은 패턴). `matchKey`
  컬럼은 그대로 유지(용도가 다름 — 동일 상품 매칭용, 건드리지 않음).
- `ProductUpdateRequest`에 `priceEstimateSnapshot: Map<String, Object>` 필드 추가. FE가
  확정 등급의 `GET /ai/jobs/{jobId}` 결과를 그대로 전달한다. null=미반영.
- 신규 `ProductPriceEstimateResponse` — 원본에서 화면에 필요한 것만 추려 조립
  (`priced`, `priceRange{min,mid,max}`, `confidence`, `confidenceLevel`, `rationale`,
  `compsUsed[]{title,price,source,url}`, `notes[]`). CH002의 "원본 저장 + 읽을 때 조립"
  패턴을 그대로 따른다.
- `ProductDetailResponse`에 `priceEstimate: ProductPriceEstimateResponse | null` 필드 추가
  (스냅샷 없으면 null — 가격 산정 전 상품).

## 구현 목록

- [ ] `Product`: `priceEstimateResult` 컬럼 + `update()` 파라미터 + getter
- [ ] `ProductUpdateRequest`: `priceEstimateSnapshot` 필드 추가
- [ ] `ProductPriceEstimateResponse` 신규(원본 map → 응답 DTO)
- [ ] `ProductDetailResponse`/`ProductService.getProductDetail()`에 배선
- [ ] 컴파일 확인(테스트는 이번 라운드 생략 — 시연 우선)
