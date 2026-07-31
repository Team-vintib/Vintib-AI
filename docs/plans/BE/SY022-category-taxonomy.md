# SY022 - 카테고리 3-depth 분류 체계 개편 (성별 포함)

## 배경/목표

docs/requests/BE/category_schema.md — AI 파트가 라벨링에 쓸 카테고리 분류 기준을 새로 정했다.
기존 카테고리는 대분류(depth=1, 6개)/소분류(depth=2, 대분류당 4~6개) 2단계였는데, 새 기준은
**성별(depth=1: 남성/여성/공용) → 대분류(depth=2, 성별당 6개) → 소분류(depth=3, 대분류당
4~6개)** 3단계다. 소분류까지 111개 ID 전체가 "1 Depth→2 Depth→3 Depth 순차 삽입" 전제로
고정 매핑되어 있고(AI 라벨링이 이 숫자 ID를 그대로 결과로 사용), BE가 그 순서를 정확히 지켜
시드해야 한다.

`Category` 엔티티(id/parentId/name/depth)는 이미 임의 깊이를 지원하는 범용 구조라 **엔티티·스키마
변경은 없다.** `BE/src/main/resources/db/seed.sql`의 카테고리 INSERT 블록만 통째로 교체하는
데이터 작업이다.

## 설계

### 시드 순서 (ID가 삽입 순서에 의존하므로 엄격히 지킨다)

1. **성별 3개** (depth=1, parent 없음): 남성 → 여성 → 공용 순서로 INSERT → id 1, 2, 3
2. **대분류 18개** (depth=2): 성별 순서(남성→여성→공용)로 묶고, 각 성별 안에서
   아우터→상의→하의→신발→가방→액세서리 순서로 INSERT, `parent_id`는 해당 성별의 id →
   남성 4~9, 여성 10~15, 공용 16~21
3. **소분류 90개** (depth=3): 마찬가지로 성별 순서로 묶고, 각 성별 안에서 대분류 순서
   (아우터5·상의5·하의5·신발4·가방5·액세서리6 = 30개)로 INSERT, `parent_id`는 해당 성별·해당
   대분류의 id → 남성 22~51, 여성 52~81, 공용 82~111

문서의 ID 매핑표(성별 1~3, 대분류 4~21, 소분류 22~111)와 정확히 일치한다 — 검증 삼아
직접 순서대로 세어봤다.

`parent_id`는 기존 방식대로 `(SELECT id FROM category WHERE name = ? AND depth = ? AND
parent_id = ?)` 서브쿼리로 연결한다 — 대분류 이름이 성별마다 중복되므로(남성 아우터/여성
아우터 모두 '아우터'), 소분류를 연결할 때는 대분류 이름만으로는 특정할 수 없고 **부모(대분류)의
parent_id(=성별 id)까지 함께 조건에 걸어야** 올바른 대분류를 가리킨다. 마찬가지로 대분류를
성별에 연결할 때도 성별 이름 조건이 필요하다.

### 문서의 "영문 코드"(MEN/OUTER/JACKET 등)는 저장하지 않는다

`category_schema.md`의 영문 코드는 AI 쪽 라벨 매핑표 가독성을 위한 표기로 보이고, 이 문서
자체가 " AI 라벨링 시 남성/여성/공용 ID를 결과로 산출"이라고만 요구한다 — BE가 영문 코드를
컬럼으로 저장해야 한다는 요구는 없다. `Brand.nameEn`과 달리 `Category`에 대응 컬럼도 없다.
필요해지면(FE가 영문 코드로 필터링해야 한다든지) 별도 계획으로 추가한다 — 이번엔 스킵.

### 기존 시드와의 차이 — 마이그레이션 주의

- `CategoryBrandSeeder`는 `category` 테이블이 **비어 있을 때만** 시드를 실행한다. 이미 구
  2-depth 데이터로 시드된 로컬/스테이징 DB는 재기동해도 자동으로 안 바뀐다 — 개발자가 직접
  `docker compose down -v`(볼륨 삭제 후 재기동) 하거나 `TRUNCATE category RESTART IDENTITY
  CASCADE` 후 재기동해야 새 시드가 들어간다. 이 안내를 PR/커밋 설명에 남긴다.
- 이 프로젝트엔 아직 실제 운영 데이터가 없고 `seed.sql`에 `product` INSERT도 없어(상품이
  카테고리를 참조하는 시드 데이터 자체가 없음) 데이터 손실 위험은 없다. 다만 각자 로컬에서
  API로 만들어본 테스트 상품이 있다면 그 상품의 `category_id`는 새 시드 후 의미가 달라지거나
  존재하지 않는 FK가 될 수 있다.

### API·엔티티·응답 DTO는 변경 없음

`GET /api/categories`(`CategoryResponse`: id/parentId/name/depth)는 depth 값의 의미를
모른 채 그대로 넘기는 범용 응답이라 depth가 1~2에서 1~3으로 늘어나도 코드 변경이 필요 없다.
트리 구성은 원래도 FE 책임(SY007에서 이미 그렇게 결정됨).

## 구현 목록

- [x] `BE/src/main/resources/db/seed.sql` — 카테고리 INSERT 블록을 3-depth(성별→대분류→소분류)
      구조로 전면 교체, 위 순서 규칙 그대로 적용
- [x] 로컬에서 `docker compose down -v && docker compose up -d postgres redis minio` 후 앱
      기동, 시드된 카테고리 111개 + ID 매핑이 문서와 정확히 일치함을 확인
      (`SELECT id, name, depth, parent_id FROM category ORDER BY id;` — 경계값 51/52/81/82/111까지 대조)
- [x] `docs/requests/BE/category_schema.md` — 반영 완료로 삭제
- [x] `docs/requests/AI/003-category-taxonomy-confirmed.md` — 반영 완료 안내 작성
- [x] `BE:verify` 통과 확인

## 확인이 필요한 미결정 사항

- 없음. ID 매핑은 문서에 이미 고정되어 있고, 그대로 따르면 된다.
