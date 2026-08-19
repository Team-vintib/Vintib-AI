# SY048 — ProductService 책임 분리

## 배경/목표

`ProductService`(510줄)가 CRUD, 판매 채널 전환, 목록/검색, 상세 조회 조립, 시세 비교, AI 착용컷 상태 폴링, AI 품질검수 상태 폴링까지 서로 무관한 7개 책임을 한 클래스에 담고 있다. 특히 AI 착용컷/품질검수 상태 폴링 두 벌(`getAiModelCutStatus`+`refreshAiModelCutStatus`, `getQualityInspectionStatus`+`refreshQualityInspectionStatus`)은 "PENDING/PROCESSING이면 AI job을 다시 조회해 갱신"하는 동일한 셰이프를 반복한다.

DB 스키마(product 테이블 컬럼)는 건드리지 않는다 — 서비스 레이어만 책임별로 쪼개서 가독성·테스트 단위를 개선하는 게 목표다. 동작(엔드포인트 URL, 요청/응답 DTO, 트랜잭션 경계)은 바뀌지 않는다.

## 작업 내용

`ProductService`를 3개 서비스로 분리한다.

- **`ProductCommandService`**: `createProduct`, `updateProduct`, `deleteProduct`, `registerDirectSale`, `scheduleAuction`, `getOwnedEditableProduct`(private 헬퍼)
- **`ProductQueryService`**: `getProductList`, `getMyProducts`, `buildSort`, `getProductDetail`, `buildPriceEstimate`, `buildAiQualityAnalysis`, `asInt`, `getMarketPrice`, `toMarketPriceItem`
- **`ProductAiJobStatusService`**: `getAiModelCutStatus`, `refreshAiModelCutStatus`, `getQualityInspectionStatus`, `refreshQualityInspectionStatus`

각 서비스는 필요한 리포지토리/포트(`ProductRepository`, `MemberRepository`, `CategoryRepository`, `ProductImageService`, `SocialQueryPort`, `LiveQueryPort`, `OrderQueryPort`, `AiClient` 등)만 주입받는다. 기존 `ProductService` 클래스는 제거하고, 호출부(`ProductController`, `MyProductController`)의 필드/생성자 주입을 분리된 서비스로 교체한다.

`refreshAiModelCutStatus`/`refreshQualityInspectionStatus`는 동일한 try/catch·success/failed/processing 분기 구조를 반복하므로, `ProductAiJobStatusService` 안에서 공통 private 헬퍼로 통합할지 구현 중 판단한다(아래 미결정 사항 참고).

기존 테스트(`ProductServiceTest.java`)는 위 3개 서비스 기준으로 나눠 다시 작성한다.

## 구현 목록

- [ ] `ProductCommandService` 생성 — CRUD·판매 채널 전환 메서드 이동
- [ ] `ProductQueryService` 생성 — 목록/상세/시세 비교 메서드 이동
- [ ] `ProductAiJobStatusService` 생성 — AI 착용컷/품질검수 상태 폴링 메서드 이동
- [ ] `ProductController` 주입을 3개 서비스로 교체
- [ ] `MyProductController` 주입을 `ProductQueryService`로 교체
- [ ] 기존 `ProductService.java` 삭제
- [ ] `ProductServiceTest.java`를 3개 테스트 클래스로 분리(`ProductCommandServiceTest`, `ProductQueryServiceTest`, `ProductAiJobStatusServiceTest`)
- [ ] `.claude/skills/BE:verify`로 최종 검증

## 확인이 필요한 미결정 사항

- AI 상태 폴링 두 벌의 공통 로직을 헬퍼로 통합할지, 아니면 가독성을 위해 지금처럼 각자 두 메서드로 둘지 — 구현 중 코드 형태를 보고 판단
