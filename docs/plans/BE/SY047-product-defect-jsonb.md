# product_defect 테이블 제거 → product.defects JSONB 컬럼으로 흡수

## 배경/목표

`product_defect`(id, product FK, content, sort_order)는 "판매자가 직접 입력한 하자 목록"을
표현하는 단순 순서 있는 문자열 리스트다. 그런데:

- 같은 `Product` 엔티티의 `measurements`(Map)·`excludedQualityFindingKeys`(List\<String\>)는
  이미 JSONB 컬럼인데 `defects`만 별도 테이블 — 같은 성격(가변 리스트, product 종속, 독립 조회
  없음)인데 저장 방식이 갈린다. SY015에서 별 이유 없이 자식 테이블로 도입된 것으로 보인다.
- `product_defect`는 product 없이 단독 조회되는 곳이 없다. `ProductDefectRepository`는 상품
  하나 기준 조회/삭제만 있고, `live` 도메인의 `ProductDefectQueryRepository`는 이미 로드한
  `Product` 목록에 대해 하자 요약 문자열만 만들려고 별도 쿼리를 또 던진다
  (`ProductQueryAdapter.findCards` → `defectSummaries`).
- API 응답(`ProductDetailResponse.defects: List<String>`) 형태는 그대로 유지 — **FE 계약 변경
  없음**, 순수 내부 리팩토링이다.

목표: `product_defect` 테이블/엔티티/레포지토리 2개(product, live)를 없애고 `product.defects`
JSONB(List\<String\>) 컬럼 하나로 합친다. 순서는 배열 순서 자체로 유지되므로 `sort_order` 컬럼은
불필요해진다.

## 작업 내용

- DB: `schema.sql`에서 `product_defect` 테이블 DROP, `product` 테이블에 `defects JSONB` 컬럼
  추가. `comments.sql` 갱신 후 `regen.sh`, `erd.md`에서 `product_defect` 관계 제거(테이블 수
  25→24) 후 `export-erd.sh`.
- `Product` 엔티티: `defects` 필드 추가(`measurements`/`excludedQualityFindingKeys`와 동일하게
  `@JdbcTypeCode(SqlTypes.JSON)` + `columnDefinition = "jsonb"`). 생성자(`@Builder`)와
  `update(...)`에 반영(update는 기존 컨벤션대로 null=미반영, non-null=전체 교체).
- `ProductDefect` 엔티티, `ProductDefectRepository`(product 도메인), `ProductDefectQueryRepository`
  (live 도메인) 삭제.
- `ProductService`: `saveDefects`/`productDefectRepository` 의존 제거. `createProduct`는
  `Product.builder().defects(...)`로, `updateProduct`는 `product.update(...)` 호출 인자로 그대로
  전달. `getProductDetail`은 별도 조회 없이 `product.getDefects()` 사용.
- `live/port/ProductQueryAdapter`: `defectSummaries`/`productDefectQueryRepository` 제거,
  `findCards`에서 `product.getDefects()`를 바로 `String.join(", ", ...)`로 조립(빈 리스트/`null`
  이면 `defectSummary`는 `null` — 현재 동작과 동일하게 유지).
- 테스트: `ProductServiceTest`의 `productDefectRepository` mock/verify를 `product.getDefects()`
  단언으로 교체. `ProductQueryAdapterTest`는 `productDefectRepository.save(...)` 대신
  `Product.builder().defects(List.of(...))`로 준비 데이터 구성.
- 배포 메모: `ddl-auto: update`는 새 컬럼만 추가할 뿐 `product_defect`의 기존 row를
  `product.defects`로 옮겨주지 않는다(그대로 두면 `defects`는 전부 `null`, `product_defect`는
  orphan으로 남는다). 실데이터 유무와 무관하게 안전하게 아래 순서로 백필한다(비용 거의 없음):
  1. 새 코드 배포 → 앱 기동 시 `ddl-auto: update`가 `product.defects` 컬럼을 자동 추가(값은 `null`).
  2. 배포 직후, `product_defect` row가 있는 상품에 한해 백필:
     ```sql
     UPDATE product p
     SET defects = sub.defects
     FROM (
         SELECT product_id, jsonb_agg(content ORDER BY sort_order) AS defects
         FROM product_defect
         GROUP BY product_id
     ) sub
     WHERE p.id = sub.product_id;
     ```
     (`product_defect` row가 없는 상품은 `defects`가 계속 `null` — 기존 "빈 리스트/null이면
     defectSummary는 null" 동작과 동일하므로 별도 처리 불필요.)
  3. 백필 결과를 확인한 뒤(`SELECT count(*) FROM product_defect;`와 위 UPDATE의 영향받은
     row 수가 일치하는지 등) `DROP TABLE product_defect;` 실행.

  로컬/운영 모두 같은 순서를 따른다. 운영 배포 단계에서는 안내만 하고 2·3단계 실제 실행은
  사용자 승인 후 진행한다.

## 구현 목록

- [x] `BE/docs/db/schema.sql` — `product_defect` DROP, `product.defects JSONB` 추가
- [x] `BE/docs/db/comments.sql` 갱신 → `regen.sh` 재생성 확인
- [x] `BE/docs/db/erd.md` 관계 제거 → `export-erd.sh`
- [x] `product/entity/Product.java` — `defects` 필드 추가(JSONB), builder/update 반영
- [x] `product/entity/ProductDefect.java` 삭제
- [x] `product/repository/ProductDefectRepository.java` 삭제
- [x] `product/service/ProductService.java` — `saveDefects` 제거, create/update/detail 조회 정리
- [x] `live/port/ProductDefectQueryRepository.java` 삭제
- [x] `live/port/ProductQueryAdapter.java` — `defectSummaries`를 `product.getDefects()` 기반으로 교체
- [x] `ProductServiceTest` — defect 관련 mock/verify를 필드 단언으로 교체
- [x] `ProductQueryAdapterTest` — defect 준비 데이터를 `Product.builder()`로 교체
- [x] `BE:verify` 통과 확인 (652 tests, 1 failed — tryon 도메인 기존 실패로 이번 변경과 무관, 아래 참고)
- [ ] 배포 후: 백필 SQL 실행 → row 수 확인 → `DROP TABLE product_defect;` (사용자 승인 후 실행, 다음 운영 배포 때)

## 확인 필요한 미결정 사항

- 없음 — API 응답 형태 불변이라 FE 요청 문서(`docs/requests/FE/`) 불필요.