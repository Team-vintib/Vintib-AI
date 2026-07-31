# 카테고리 3-depth 분류 체계(성별 포함) 반영 완료

**요청자 파트**: BE
**대상 파트**: AI

## 배경/이유

`docs/requests/BE/category_schema.md`(성별→대분류→소분류 3-depth, ID 1~111 고정 매핑)를
BE가 시드 데이터에 그대로 반영했다. AI 라벨링이 이 ID를 그대로 결과로 쓸 수 있다.

## 반영 내용

- `BE/src/main/resources/db/seed.sql`의 카테고리 INSERT를 성별(depth=1) → 대분류(depth=2)
  → 소분류(depth=3) 순서로 재구성해, 요청 문서의 ID 매핑표와 정확히 일치하도록 시드했다.
- 로컬에서 실제로 시드를 실행해 `SELECT id, name, depth, parent_id FROM category ORDER BY id`로
  전수 확인함 — 111개 행, 경계값(51/52, 81/82, 111)까지 문서와 일치.
- 문서의 영문 코드(MEN/OUTER/JACKET 등)는 DB 컬럼으로 저장하지 않았다 — 이름은 한글만
  저장하고(`category.name`), ID로만 매핑한다. 영문 코드가 실제로 필요해지면(예: AI가
  코드 문자열로 조회해야 하는 경우) 별도 요청으로 알려달라.
- `GET /api/categories`(인증 불필요) 응답 형식은 그대로다 — `id`, `parentId`, `name`, `depth`
  평탄 리스트, `id` 오름차순.

## 참고

- `docs/plans/BE/SY022-category-taxonomy.md`
- `BE/src/main/resources/db/seed.sql`
