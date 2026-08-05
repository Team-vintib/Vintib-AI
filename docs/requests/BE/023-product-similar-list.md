# 023 상품 상세 유사 상품 추천 목록 API 요청

- **요청자 파트**: FE (김현수)
- **대상 파트**: BE
- **관련 이슈**: FE `S15P11A108-565` [PROD-006] 상세 하단 유사 상품 추천
- **작성일**: 2026-08-04

## 배경 / 이유

상품 상세 맨 아래(AI 분석 다음)에 "현재 상품과 유사한 상품"을 가로 캐러셀로 노출한다(FE 구현 완료,
현재 mock). 유사 판정 기준과 목록은 BE 소관(req 011에도 "유사 판정은 BE 결정"이라 명시)이라, 실제
데이터를 내려줄 엔드포인트가 필요하다.

## 요청 내용

현재 상품 기준 **유사 상품 목록 조회 API**. 예:

- `GET /api/products/{id}/similar?size=N`
- 응답: **기존 상품 목록 아이템과 동일 형태**의 배열 (id, title, brand, price, saleType,
  conditionGrade, primaryImageUrl, saleStatus, isWished 등 — `GET /api/products`와 같은 필드).
- **유사 판정 기준**(카테고리/브랜드/가격대/상태 등)은 BE에서 결정.
- 현재 상품(`{id}`)은 응답에서 제외(또는 FE가 자체 제외해도 됨).
- 공개 노출 범위는 목록 API와 동일 정책 적용(비공개 제외 등).

## 관련 자료

- FE: `getSimilarProducts` (`FE/src/domains/product/api/productApi.ts`) — 현재 mock, 확정 시 실제 호출로 교체
- FE: `ProductSimilarRecommendation.vue` — 가로 캐러셀 UI
- req 011 (유사 가격 분포) — 유사 판정 BE 결정 언급
