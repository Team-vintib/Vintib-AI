# SY007 - 카테고리/브랜드 조회 API

## 배경/목표

`docs/db/schema.sql`에 `category`/`brand` 마스터 테이블은 이미 정의돼 있지만 엔티티/API가 없다. `Product.categoryId`/`brandId`(`PROD-001` 등록)와 `member_interest_category`/`member_interest_brand`(`ONBOARD-002`)가 이 마스터를 참조하므로, 상품 등록·온보딩 화면에서 선택지를 보여주려면 조회 API가 선행되어야 한다. 사용자가 제공한 빈티지·세컨핸드 플랫폼(후르츠패밀리류) 카테고리/브랜드 벤치마킹 자료를 반영해, 이번 작업에서 ①조회 API ②스키마 소폭 확장(브랜드 영문명) ③실제 카테고리/브랜드 시드 데이터까지 함께 넣는다.

사용자가 제시한 예시는 MySQL·복수형 테이블명(`categories`/`brands`)을 포함한 별도 제안이었으나, 우리 스키마는 이미 확정된 PostgreSQL 공유 계약(ERD/데이터 사전 자동 생성 대상)이라 테이블명은 그대로 두고 **선택적으로 필요한 것만** 반영한다:

- 반영: `brand.name_en` (한/영 브랜드명이 실제로 혼용 검색되는 도메인 특성 — 시드 데이터에도 한글/영문이 쌍으로 존재)

## 작업 내용

### 스키마 (`docs/db/schema.sql`, `docs/db/comments.sql`)

- `brand`에 `name_en VARCHAR(100)` 컬럼 추가(nullable — 영문명 없는 브랜드 대비). 기존 `name`(한글, UNIQUE)은 그대로 둔다.
- `comments.sql`에 `brand.name_en` 코멘트 추가.
- 변경 후 `bash docs/db/regen.sh`(data-dictionary.md 재생성) / `bash docs/db/export-erd.sh`(ERD 재생성) 실행 — 둘 다 로컬 `docker compose up -d postgres` 필요.

### 시드 데이터 (신규 `BE/src/main/resources/db/seed.sql`, 앱 기동 시 자동 실행)

`docs/db/seed.sql`(DDL 문서 옆)이 아니라 앱 classpath(`BE/src/main/resources/db/seed.sql`)에 둔다 — 기동 시 자동 실행하려면 Spring이 읽을 수 있는 위치에 있어야 한다.

자동 실행은 Flyway 등 마이그레이션 도구 도입 없이, `ApplicationRunner` 빈(`CategoryBrandSeeder`, `product` 패키지)으로 구현한다:

- 기동 시 `CategoryRepository.count() == 0`이면(카테고리 테이블이 비어 있으면) `ScriptUtils.executeSqlScript`로 `db/seed.sql`을 실행. 이미 데이터가 있으면 아무 것도 하지 않음 — 재기동/재배포 시 중복 삽입되지 않는다.
- 모든 프로파일(local/prod)에서 동일하게 동작. 마스터 데이터(카테고리·브랜드)는 dev 전용 픽스처가 아니라 실제 운영에도 필요한 데이터이므로 프로파일로 분리하지 않는다.
- 스크립트 실행은 하나의 트랜잭션으로 묶는다(`connection.setAutoCommit(false)` + 실패 시 `rollback`). auto-commit 상태로 두면 중간 실패 시 앞선 INSERT가 이미 커밋돼 `category`가 비어있지 않게 되고, 다음 재기동에서도 영영 재시도하지 못한 채 마스터 데이터가 반쪽 상태로 굳어버리기 때문.

- **카테고리** — 대분류 6개(패션 카테고리만) + 하위 소분류(대분류당 4~6개), `depth`=1/2, `parent_id`는 대분류 이름으로 서브쿼리 조회해 연결:
  아우터 / 상의 / 하의 / 신발 / 가방 / 액세서리
- **브랜드** — 21개, `name`(한글)/`name_en`(영문) 쌍으로 INSERT:
  하이엔드·디자이너 아카이브(꼼데가르송, 메종 마르지엘라, 요지 야마모토, 릭 오웬스, 이세이 미야케, 장 폴 고티에, 비비안 웨스트우드) /
  스트릿·서브컬처(베이프, 슈프림, 스투시, 캐피탈, 히스테릭 글래머, 크롬하츠) /
  클래식·아메리칸 캐주얼(폴로 랄프로렌, 리바이스, 칼하트, 버버리) /
  고프코어·스포티(아크테릭스, 나이키, 아디다스, 프라다)
- 사용자 메시지에 있던 상세 취급 사유(검색량, 리셀가 등)는 시드 자체에는 반영하지 않는다(스키마에 그런 컬럼 없음) — 목록 선정 근거로만 참고.

### API

- 패키지: `product` 도메인 (README 담당 분배상 `category`/`brand`도 서윤 소유). `Category`/`Brand` 엔티티는 `product/entity`, 레포지토리는 `product/repository`.
- **`Category`**: `id`, `parentId`(자기참조 FK), `name`, `depth`. 조회 전용, `BaseTimeEntity` 미사용(스키마에 시간 컬럼 없음).
- **`Brand`**: `id`, `name`, `nameEn`(nullable). 조회 전용.
- **`GET /api/categories`**: 전체 카테고리 평탄 리스트(`id`, `parentId`, `name`, `depth`), `id` 오름차순(=시드 삽입 순서=의도한 표시 순서). 트리 구성은 FE 책임.
- **`GET /api/brands`**: 전체 브랜드 리스트(`id`, `name`, `nameEn`), `name` 오름차순. 키워드 검색/페이지네이션은 이번 범위 제외(요구사항 없음, 데이터 규모도 작음).
- 두 endpoint 모두 인증 불필요 → `SecurityConfig.PUBLIC_ENDPOINTS`에 `/api/categories`, `/api/brands` 추가.
- 컨트롤러 분리: `CategoryController`(`/api/categories`), `BrandController`(`/api/brands`) — `/api/products` 하위가 아니므로 `ProductController`에 얹지 않음. Swagger(`@Tag`/`@Operation`/`@ApiResponses`) 포함.
- 서비스: `CategoryService.getAllCategories()`, `BrandService.getAllBrands()` — 단순 조회, 예외 케이스 없음.
- 테스트: `CategoryServiceTest`/`BrandServiceTest`에 "전체 목록을 반환한다" 케이스 1건씩 (기존 `ProductServiceTest`처럼 Mockito 기반 — 이 리포의 서비스 테스트는 실제 DB 없이 레포지토리 목으로 검증).

## 구현 목록

- [x] `docs/db/schema.sql`: `brand.name_en` 컬럼 추가
- [x] `docs/db/comments.sql`: `brand.name_en` 코멘트 추가
- [x] `BE/src/main/resources/db/seed.sql` 신규: 카테고리 6개 대분류 + 소분류, 브랜드 21개(한/영) INSERT
- [x] `docs/db/regen.sh` / `export-erd.sh` 실행해 data-dictionary.md, ERD 이미지 갱신 (docker postgres 필요)
- [x] `Category` 엔티티/`CategoryRepository`
- [x] `Brand` 엔티티(`nameEn` 포함)/`BrandRepository`
- [x] `CategoryBrandSeeder`(`ApplicationRunner`): 카테고리 테이블 비어있을 때만 `db/seed.sql` 실행
- [x] `CategoryResponse`, `BrandResponse` (`product/dto/response`)
- [x] `CategoryService`/`BrandService`
- [x] `CategoryController`(`GET /api/categories`), `BrandController`(`GET /api/brands`) — Swagger 포함
- [x] `SecurityConfig.PUBLIC_ENDPOINTS`에 두 경로 추가
- [x] `CategoryServiceTest`/`BrandServiceTest` 작성
- [x] `.claude/skills/verify` 기준 빌드/테스트 통과 확인

## 확인이 필요한 미결정 사항

- 브랜드 키워드 검색/자동완성, 카테고리 트리 응답(중첩 구조)는 현재 요구사항이 없어 제외 — FE에서 필요해지면 별도 계획으로 추가.