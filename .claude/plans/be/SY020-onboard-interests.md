# SY020 - 관심 브랜드/카테고리 저장 API (ONBOARD-002, S15P11A108-228)

## 배경/목표

`APIs.md`에 정의된 ONBOARD-002 두 엔드포인트가 아직 미구현이다.

- `GET /users/{id}/interests` — 관심 정보 조회
- `PUT /users/{id}/interests` — 관심 정보 등록·수정

기능 정의: "관심 있는 브랜드와 의류 카테고리를 선택한다. 선택 입력이며 건너뛸 수 있다. 이후
마이페이지에서 수정할 수 있다." — 필수 우선순위 항목이지만 값 자체는 선택/스킵 가능하고,
등록(최초)과 수정(마이페이지)이 같은 엔드포인트를 쓴다는 점이 ONBOARD-001(`PATCH /users/{id}`,
SY018)과 동일한 모양이다.

DB 테이블은 `docs/db/schema.sql`에 이미 정의돼 있다(`member_interest_brand`,
`member_interest_category` — 둘 다 `(member_id, X_id)` 복합 PK만 있는 순수 매핑 테이블,
추가 컬럼 없음). 스키마 변경은 필요 없다.

## 설계

### 엔티티

`member` 패키지에 둔다(Wish가 `social` 패키지에서 `product.Product`를 `@ManyToOne`으로 참조하는
기존 선례와 동일하게, 회원이 소유하는 관계이므로 `member` 쪽에 둔다).

- `MemberInterestBrand` — `@EmbeddedId MemberInterestBrandId`(`memberId`+`brandId`), `@MapsId`로
  `Member`/`Brand` `@ManyToOne(LAZY)` — `Wish`/`WishId` 패턴 그대로.
- `MemberInterestCategory` — 동일하게 `MemberInterestCategoryId`(`memberId`+`categoryId`),
  `Member`/`Category` 참조.
- 생성/수정 시각 컬럼 없음(스키마에 없음) — `Wish`와 달리 `createdAt` 필드 자체를 두지 않는다.

### 레포지토리

- `MemberInterestBrandRepository extends JpaRepository<MemberInterestBrand, MemberInterestBrandId>`
  - `List<MemberInterestBrand> findByMember_Id(Long memberId)`
  - `@Modifying @Query("delete from MemberInterestBrand b where b.member.id = :memberId") void deleteAllByMemberId(...)`
    (`ProductDefectRepository.deleteAllByProductId` 패턴 — 전체 교체 전 선삭제)
- `MemberInterestCategoryRepository` — 동일한 모양.

### 요청/응답 DTO (`member/dto/request`, `member/dto/response`)

- `UpdateInterestsRequest(List<Long> brandIds, List<Long> categoryIds)` — 둘 다 `null` 불가,
  빈 리스트 허용(건너뛰기), `@NotNull` + 각 원소 `@NotNull`. 필수 필드 목록 자체를 통째로 교체하는
  전체 교체(full-replace) 방식 — 부분 추가/삭제 API가 아니다.
- `InterestsResponse(List<BrandResponse> brands, List<CategoryResponse> categories)` — 기존
  `product.dto.response.BrandResponse`/`CategoryResponse`를 재사용(새 DTO 만들지 않음).

### 서비스 — `UserService`에 메서드 추가 (새 서비스 클래스 만들지 않음, ONBOARD-001과 같은 클래스)

- `getInterests(Long requesterId, Long targetId): InterestsResponse`
  - `requesterId != targetId` → `MEMBER_FORBIDDEN`(본인만 조회 가능 — 다른 회원의 관심사 노출 방지)
  - 회원 없으면 `USER_NOT_FOUND`
  - `memberInterestBrandRepository.findByMember_Id` / category 동일 조회 후 응답 매핑
- `updateInterests(Long requesterId, Long targetId, UpdateInterestsRequest request): InterestsResponse`
  - `requesterId != targetId` → `MEMBER_FORBIDDEN`
  - 회원 없으면 `USER_NOT_FOUND`
  - `brandIds`/`categoryIds`에 존재하지 않는 ID가 섞여 있으면 400 — 새 에러코드 필요(아래 참고)
  - `deleteAllByMemberId` 후 요청받은 ID들로 재삽입(전체 교체) — `flush` 불필요(unique 제약 충돌
    가능성 없음, PK 자체가 중복 방지)
  - 재조회 없이 방금 저장한 `Brand`/`Category` 엔티티로 바로 응답 구성

### 존재 검증 & 새 에러코드

- 카테고리: 기존 `ErrorCode.CATEGORY_NOT_FOUND`(P008, 400) 재사용.
- 브랜드: 대응하는 에러코드가 없다 — `BRAND_NOT_FOUND(HttpStatus.BAD_REQUEST, "P009", "존재하지 않는 브랜드입니다.")`
  신규 추가(`CATEGORY_NOT_FOUND` 바로 다음 P009).
- 검증 방법: `brandRepository.findAllById(request.brandIds())`로 조회한 결과 수가 요청 ID 수와
  다르면 `BRAND_NOT_FOUND` 던짐(category도 동일하게 `categoryRepository.findAllById`).

### 컨트롤러 — `UserController`에 엔드포인트 추가

- `GET /api/users/{id}/interests` — `getInterests`
- `PUT /api/users/{id}/interests` — `updateInterests`
- 둘 다 `@SecurityRequirement(name = "bearerAuth")`, Swagger `@Operation`/`@ApiResponses`
  (200/400/401/403/404) — `.claude/skills/swagger` 컨벤션.

### 테스트

- `UserServiceTest`(기존 파일 있으면 추가, 없으면 신규)에 케이스 추가:
  - 정상 조회
  - 본인 아닌 회원 조회/수정 시도 → `MEMBER_FORBIDDEN`
  - 존재하지 않는 브랜드/카테고리 ID 포함 시 → `BRAND_NOT_FOUND`/`CATEGORY_NOT_FOUND`
  - 빈 리스트로 수정(스킵) → 기존 관심사 전체 삭제되고 빈 응답

## 구현 목록

- [ ] `ErrorCode`: `BRAND_NOT_FOUND`(P009) 추가
- [ ] `MemberInterestBrandId`/`MemberInterestCategoryId` (`member/entity`, `WishId` 패턴)
- [ ] `MemberInterestBrand`/`MemberInterestCategory` 엔티티 (`member/entity`)
- [ ] `MemberInterestBrandRepository`/`MemberInterestCategoryRepository` (`member/repository`)
- [ ] `UpdateInterestsRequest` (`member/dto/request`)
- [ ] `InterestsResponse` (`member/dto/response`, 기존 `BrandResponse`/`CategoryResponse` 재사용)
- [ ] `UserService.getInterests`/`updateInterests`
- [ ] `UserController`: `GET`/`PUT /api/users/{id}/interests` + Swagger
- [ ] `UserServiceTest` 케이스 4건 추가
- [ ] `.claude/skills/verify` 기준 빌드/테스트 통과 확인

## 확인이 필요한 미결정 사항

- 없음 — 스키마·응답 DTO·에러코드 컨벤션 모두 기존 패턴으로 확정 가능.