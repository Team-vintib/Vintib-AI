# 020 AI 시착 결과 — 응답에 상품 카테고리 추가 요청

**요청자 파트**: FE
**대상 파트**: BE

## 배경/이유
AI 시착 페이지(TRYON-005)의 "저장된 시착 결과"를 **카테고리(상의/하의/아우터/원피스/신발/가방/액세서리 등)로 나눠 보는 탭**으로 구현했다. 그런데 현재 시착 결과 응답 `TryOnResultResponse`는 `{ id, productId, imageUrl, createdAt }`뿐이라 **결과가 어느 카테고리인지 알 수 없어** 탭 필터를 실데이터로 채울 수 없다. 지금은 mock 결과에 카테고리를 넣어 탭이 동작하게 해뒀다.

## 요청 내용
`GET /api/users/{userId}/tryons`(목록)·`/{id}`(상세) 응답에 **결과 상품의 카테고리 정보**를 추가해 달라. 시착 결과는 상품 1개 기준이므로 그 상품의 카테고리를 실으면 된다.

FE가 쓰기 좋은 최소 형태(둘 중 편한 방식):
```jsonc
// (a) 대분류 이름만
{ "id": 101, "productId": 1, "imageUrl": "...", "createdAt": "2026-08-03T14:20:00",
  "category": "아우터" }

// (b) id + 이름 (기존 카테고리 계약과 일관)
{ "id": 101, "productId": 1, "imageUrl": "...", "createdAt": "2026-08-03T14:20:00",
  "categoryId": 12, "categoryName": "아우터" }
```
- 탭은 **대분류 수준**(상의/하의/아우터/원피스/신발/가방/액세서리…)이면 충분하다. 소분류만 있으면 FE가 대분류로 올려서 묶을 수 있으니, 대분류를 특정할 수 있게만 주면 된다.
- `createdAt`은 기존대로 오프셋 없는 KST 벽시계 유지.

## 관련 자료
- FE: `FE/src/domains/tryon/components/TryOnResultGallery.vue`(카테고리 탭), `FE/src/domains/tryon/api/tryOnResultApi.ts`(`TryOnResultDto` → 현재 `category: null` 매핑), 타입 `TryOnResult`
- Mock(교체 대상): `FE/src/domains/tryon/constants/tryOnResultMockData.ts`
- 기능: TRYON-005 시착 결과 목록/상세

## 참고 — 함께 대기 중인 시착 생성/합성
시착 **생성**(`POST /users/{id}/tryons`) + AI 합성은 아직 미구현이라 결과가 실제로 쌓이지 않는다(입어보기는 mock). 이 건은 별도(TRYON-003/004, AI 합성 계약)로 이미 논의 중이며 본 문서 범위 밖이다. 카테고리 필드만 우선 요청한다.

## 처리 결과
(BE 반영 후 기입)
