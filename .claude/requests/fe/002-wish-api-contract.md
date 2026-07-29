# 상품 찜/해제/목록 API 연동 요청

**요청자 파트**: BE
**대상 파트**: FE

## 배경/이유

`FE/docs/frontend/api/api-index.md`의 "찜" 후보 엔드포인트가 `/api/products/{id}/wish`로 적혀 있는데, 실제 구현은 그 경로가 아니다(`APIs.md` "팔로우 / 찜(Socials)" 섹션 스펙을 그대로 따름). FE 연동 시 경로 불일치로 바로 막힐 수 있어 실제 계약을 공유한다.

## 요청 내용

- **찜 등록** — `POST /api/users/{userId}/wishes`
  - 요청: `{ "productId": number }`
  - 성공(201) 응답: `{ "productId": number, "createdAt": string(ISO-8601) }`
- **찜 해제** — `DELETE /api/users/{userId}/wishes/{id}` (`{id}`는 찜 자체 ID가 아니라 **상품 ID**)
  - 성공: 204, 바디 없음
- **찜 목록 조회** — `GET /api/users/{userId}/wishes?page=&size=`
  - 페이지네이션(0-base `page`, 기본 `size=20`), 정렬은 찜한 시각 최신순 고정(sort 파라미터 무시)
  - 응답: 공용 `PageResponse` 래퍼(`content`, `page`, `size`, `totalElements`, `totalPages`, `hasNext`) 안에 `content: [{ product: {...기존 상품 목록 DTO와 동일 필드...}, wishedAt: string }]`
  - **찜한 뒤 상품이 판매완료(SOLD)·비공개(PRIVATE)로 바뀌어도 목록에서 빠지지 않는다** — `product.saleStatus`를 보고 화면에서 상태 배지를 띄워야 한다(기능 정의서 MY-009: "판매 완료 또는 비공개 상품은 현재 상태를 함께 표시한다").

`{userId}`는 항상 로그인한 본인 ID와 같아야 한다(다르면 403). 모든 엔드포인트 인증 필요.

에러 코드(`error.code`): `P001`(상품 없음/비공개 상품 찜 시도), `S001`(이미 찜한 상품), `S002`(찜하지 않은 상품 해제 시도), `S003`(본인 외 사용자의 찜을 조작하려 함).

## 관련 자료

- Swagger: `/swagger-ui/index.html` — "팔로우 / 찜(Socials)" 태그
- `BE/src/main/java/com/ssafy/backend/social/controller/WishController.java`