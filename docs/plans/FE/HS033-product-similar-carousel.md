# HS033 — 상품 상세 하단 유사 상품 추천 캐러셀 (PROD-006)

- Jira: `S15P11A108-565` [PROD-006 | FE] (상세 하단 유사 상품 추천) / 에픽 `S15P11A108-211` [PROD]
- 브랜치: `feat/211-similar-products-carousel` (develop-FE 기준)

## 배경/목표

상품 상세 맨 아래(AI 분석 다음)에 **현재 상품과 유사한 상품을 가로로 넘기며 보는 캐러셀**을 넣는다.
탭 아님 — 좌우 화살표/스크롤로 넘기는 가로 리스트. 클릭하면 해당 상품 상세로 이동.

유사 상품 데이터는 **BE에서 받는다**(유사 판정 기준도 BE 소관, req 011에 명시). 실제 API가 없으므로
이번엔 **mock으로 UI를 구현**하고, 유사 상품 목록 엔드포인트를 `docs/requests/BE`에 요청한다.

## 작업 내용

1. `components/ProductSimilarRecommendation.vue` 신규
   - 제목 "유사 상품 추천" + 좌우 화살표.
   - 유사 상품 카드 가로 캐러셀(기존 `ProductCard` 재사용) → 클릭 시 상세 이동.
   - 로딩/빈 상태 처리.
2. `api/productApi.ts`(또는 productDetailApi)에 `getSimilarProducts(productId)` 추가 — 실제 API
   미구현이라 mock(기존 목록 mock에서 현재 상품 제외한 목록). BE 플래그 붙으면 실제 호출.
3. `pages/ProductDetailView.vue`: `AiQualityAnalysisPanel` 다음에 `ProductSimilarRecommendation` 배치.
4. `docs/requests/BE`에 유사 상품 목록 API 요청 문서(별도, main 대상).

## 구현 파일

- `components/ProductSimilarRecommendation.vue` (신규)
- `api/productApi.ts` — `getSimilarProducts` (mock)
- `pages/ProductDetailView.vue` — 하단 배치
- `docs/requests/BE/023-product-similar-list.md` (별도 커밋, main 대상)

## 검증

- vue-tsc / eslint 통과
- 로컬(mock): 상세 하단에 유사 상품 캐러셀 노출, 좌우 넘김, 카드 클릭 시 상세 이동

## 비고

- 실제 유사 판정·목록은 BE. 이번은 가로 캐러셀 UI + mock + 요청 문서.
