# 상품 등록/수정 필드 확장 — 색상·소재·실측·하자 (PROD-001/007)

> **범위 축소**: 이 브랜치(`feat/179-register-product-info`)는 **등록(PROD-001, `S15P11A108-179`)만**
> 다룬다. 수정(PROD-007, `S15P11A108-233`)은 별도 브랜치·커밋으로 처리한다. 아래 작업 내용 중
> `ProductUpdateRequest`/`Product.update()`/수정 관련 항목은 이번 범위에서 제외했다.

## 배경/목표

기능 정의서 PROD-001은 "상품 이미지, 상품명, 카테고리, 브랜드, 색상, 사이즈, 소재, 상태와 설명을 등록한다. 실측과 하자 정보는 선택 입력이다"라고 명시하지만, 현재 `ProductCreateRequest`/`Product` 엔티티에는 색상(color)·소재(material)·실측(measurements)·판매자 고지 하자(defects) 필드가 전혀 없다. PROD-007(수정)도 같은 필드가 빠져 있다. 두 API에 이 4개 필드를 추가한다.

Jira: `S15P11A108-179`(등록), `S15P11A108-233`(수정). 에픽 `S15P11A108-211`.

## 작업 내용

- `Product` 엔티티에 `color`(String, nullable), `material`(String, nullable) 컬럼 추가.
- `measurements`는 상품마다 다른 치수 항목(총장/어깨너비/가슴단면/소매길이 등)을 담아야 해서 고정 컬럼 대신 `Map<String, Integer>`를 JSONB로 매핑한다. Hibernate 6 네이티브 지원(`@JdbcTypeCode(SqlTypes.JSON)` + `columnDefinition = "jsonb"`)을 쓴다 — 별도 라이브러리 불필요(Spring Boot 4.1 = Hibernate 6.x).
- 신규 엔티티 `ProductDefect`(`product/entity/ProductDefect.java`): `id, product(FK), content(TEXT), sortOrder`. "판매자가 직접 입력한 하자 목록"을 문자열 리스트로 표현. 신규 `ProductDefectRepository`.
- `ProductCreateRequest`/`ProductUpdateRequest`에 `color`, `material`, `measurements: Map<String,Integer>`, `defects: List<String>` 옵션 필드 추가.
  - Update는 기존 컨벤션대로 null=미반영. `defects`는 non-null이면 전체 교체(빈 리스트 `[]`면 전부 삭제) — PUT적 replace 의미.
- `Product.update(...)` 및 생성 관련 메서드 시그니처 확장.
- `ProductDetailResponse`/`ProductResponse`에 새 필드 반영(색상/소재/실측/하자).
- DB: `product` 테이블에 `color VARCHAR, material VARCHAR, measurements JSONB` 컬럼 추가, 신규 `product_defect` 테이블. `BE/docs/db/schema.sql`/`comments.sql` 수정 후 `regen.sh`, `erd.md` 수정 후 `export-erd.sh`.
- `../../../../../APIs.md`의 179/233 행에 새 필드 반영.

## 구현 목록

- [x] `product/entity/Product.java` — `color`, `material`, `measurements`(JSONB) 필드 추가
- [x] `product/entity/ProductDefect.java` 신규, `product/repository/ProductDefectRepository.java` 신규
- [x] `product/dto/request/ProductCreateRequest.java` — 4개 필드 추가
- [ ] ~~`product/dto/request/ProductUpdateRequest.java` — 4개 필드 추가~~ (별도 브랜치, PROD-007)
- [x] `product/service/ProductService.java` — 생성 로직에 반영(defects 저장), `getProductDetail`에서
      defects 조회 반영
- [ ] ~~수정 로직(defects 교체)~~ (별도 브랜치, PROD-007)
- [x] `product/dto/response/ProductDetailResponse.java` — 필드 반영(`ProductResponse`는 목록·최소
      응답 유지 — 아래 미결정 사항 참고)
- [x] `BE/docs/db/schema.sql`, `comments.sql` 수정 → `regen.sh`
- [x] `BE/docs/db/erd.md` 수정(`product_defect` 관계 추가, 테이블 수 24→25) → `export-erd.sh`
- [x] `APIs.md` — 확인 결과 필드 단위 내용은 Swagger가 담당하고 이 표는 엔드포인트 매핑만 있어서
      179 행 자체는 변경 불필요
- [x] `ProductServiceTest`에 새 필드 포함 등록 케이스 추가(색상/소재/실측/하자 저장, 하자 없을 때
      저장 스킵)
- [x] `BE:verify` 통과 확인 (`BUILD SUCCESSFUL`, ProductServiceTest 28개 전부 통과,
      `constraint-test.sql` 11/0)

## 완료 (등록만)

구현 완료. 수정(PROD-007, `S15P11A108-233`)은 이어서 별도 브랜치에서 진행한다 — `ProductUpdateRequest`에
4개 필드 추가, `Product.update()` 시그니처 확장, `defects` 전체 교체 로직(빈 리스트 `[]`면 전부 삭제)이
남은 작업이다.

## 확인 필요한 미결정 사항

- `ProductResponse`(목록 응답)에도 color/material을 넣을지는 FE PROD-008 카드 요구사항 확인 후 결정 — 우선 상세조회(SY017)만 확장하고 목록 응답은 이번엔 최소로 유지할 수 있음.
