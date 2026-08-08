# 005 가격 책정 내부 호가 소스 — BE 답변 (CH016 §1/§2 대응)

- **요청자 파트**: BE
- **대상 파트**: AI
- **원본 요청**: AI가 전달한 "가격 책정: 정찰제 호가를 시세 근거로 쓰기 위한 확인·요청"
  (`S15P11A108-494`, 설계 `CH016-internal-comps-hedge.md`)에 대한 답변.
- **요약**: §1-A는 코드로 전부 확인됨(아래). §1-B는 로컬 DB를 직접 조회했고, **의미 있는 실사용
  데이터는 사실상 0건**이다(이유는 §1-B 참고). §2는 BE 의견을 냄 — **뷰 + 읽기 전용 계정**(직접
  조회 방식)을 권장. §3(뷰·계정·계약 문서·`PricingResult` 변경)은 새 스키마/권한 변경이라
  바로 만들지 않고, 이 답변에 대한 AI/사용자 확인 후 `docs/plans/BE/`에 계획을 세워 별도로
  진행한다 — 이 문서에서 API를 만들거나 DB 계정을 발급하지 않았다.

---

## §1-A 코드로 답할 수 있는 것

### 1. 정찰제 상품 엔티티 컬럼

`Product` 엔티티(`BE/src/main/java/com/ssafy/backend/product/entity/Product.java`), 테이블명 `product`:

```java
@Entity
@Table(name = "product")
public class Product extends BaseTimeEntity {   // createdAt, updatedAt 포함 (아래 4번)
    Long id;
    Member seller;             // seller_id FK
    Long categoryId;           // NOT NULL, category FK (구조화됨 — 아래 5번)
    Long brandId;               // nullable, brand FK (구조화됨 — 아래 6번, 자유입력 아님)
    String title;               // NOT NULL, 200자
    String description;         // TEXT, nullable
    String conditionGrade;      // nullable, 20자 자유 문자열 (아래 3번 — 세부 설명 있음)
    String sizeLabel;           // nullable, 50자
    String color;                // nullable, 50자
    String material;            // nullable, 50자
    Map<String,Integer> measurements; // JSONB, nullable
    SaleType saleType;           // DIRECT_SALE | AUCTION, nullable(DRAFT일 땐 미정)
    SaleStatus saleStatus;       // NOT NULL — 아래 2번
    Long price;                  // 정찰제가(원). AUCTION이면 null
    boolean aiModelEnabled;      // 이번 라운드에 추가된 필드, pricing과 무관
    AiModelGender aiModelGender; // 위와 동일
    LocalDateTime deletedAt;     // soft delete, NOT NULL이면 삭제된 상품
}
```

**브랜드/모델명 질문에 대한 답**:
- **브랜드는 이미 구조화 필드다.** `brandId`는 자유 텍스트가 아니라 `brand` 마스터 테이블
  FK다 — §4에서 AI가 제안한 "브랜드를 선택형으로"는 **등록 화면에서는 이미 그렇게 되어 있다**
  (`ProductCreateRequest.brandId: Long`). 다만 §1-B에서 보듯 **실제로 채워지는 비율이 0%다** —
  선택 UI 자체는 있지만 필수 입력이 아니라서 안 채워지는 것으로 보인다(FE 확인 필요, 이 문서
  범위 밖).
- **모델명/품번 전용 컬럼은 없다.** `title`(자유 텍스트) 안에 섞여 들어갈 수밖에 없다
  ("리바이스 501 빈티지"처럼). CH016 §3.2가 가정한 "모델번호 패턴 추출"은 `title` 파싱에
  의존해야 한다 — 전용 필드를 새로 만드는 건 이번 답변에 포함하지 않았다(필요하면 별도 요청
  부탁).

### 2. 판매 상태 enum

`SaleStatus`(`BE/src/main/java/com/ssafy/backend/product/entity/SaleStatus.java`):

```java
public enum SaleStatus {
    DRAFT,                 // 등록 중(미공개) — 목록/검색/가격조회 전부에서 제외해야 함
    ON_SALE,                // 정찰제 중 — "안 팔린 호가"
    AUCTION_SCHEDULED,      // 경매 예정 — 정찰제 대상 아님(price가 null일 수 있음)
    AUCTION_IN_PROGRESS,    // 경매 진행 중 — 정찰제 대상 아님
    SOLD                    // 판매 완료(낙찰 포함) — "체결된 호가"
}
```

`SaleType`은 별도 enum: `DIRECT_SALE | AUCTION`. **CH016이 원하는 "정찰제 호가"는
`sale_type = 'DIRECT_SALE'`인 행 전체**(ON_SALE=안 팔림, SOLD=팔림 둘 다 포함)를 뜻한다.
`sale_status`만으로는 정찰제/경매를 못 가른다 — 반드시 `sale_type`과 함께 필터해야 한다
(경매 낙찰도 `SOLD`라서, `sale_status='SOLD'`만 보면 경매 낙찰가가 섞여 들어간다).

### 3. 품질검수 등급(condition_grade) 저장 위치 — ⚠️ 두 가지를 구분해야 함

AI 쪽 기록("검수 결과는 Redis에 TTL 1시간")은 **다른 개념과 혼동된 것으로 보인다**:

- **`product.condition_grade`**: `Product` 테이블의 **영구 컬럼**이다(위 1번). 값은 AI가 매긴
  등급이 아니라 **판매자가 등록 시 직접 입력한 자유 문자열**("A", "A급" 등 — 등급 체계
  미확정, `docs/plans/BE/SY015-product-fields.md` 참고)이다. `product` 테이블과 함께
  영구 저장되므로 **가중치·밴드 계산에 그대로 쓸 수 있다.**
- Redis TTL 1시간으로 남는 건 **AI 품질검수(하자 탐지) 결과**(보풀·오염 위치 등, bbox
  포함) 쪽 얘기일 가능성이 높다 — 이건 `condition_grade`와 별개 개념이고, 현재 BE에는 이
  결과를 영구 저장하는 테이블이 없다(`docs/requests/BE/019-product-quality-multi-image.md`,
  이번 정리에서 아직 미반영으로 남아 있음). **CH016이 쓰려는 건 `condition_grade` 쪽이고, 이건
  Redis가 아니라 DB에 영구 저장된다** — 우려한 문제는 없다.

### 4. 상품 등록일시

`BaseTimeEntity`(`BE/src/main/java/com/ssafy/backend/global/entity/BaseTimeEntity.java`)를
`Product`가 상속한다:

```java
@CreatedDate private LocalDateTime createdAt;   // 최초 등록(DRAFT 생성) 시각
@LastModifiedDate private LocalDateTime updatedAt; // 마지막 수정 시각(가격 변경 포함)
```

"가격 확정 시점"(정찰제 등록 API 호출 시점) 전용 컬럼은 없다 — `createdAt`은 DRAFT 생성
시각이라 정찰제 전환 이전일 수 있다. 정확한 가격 확정 시점이 필요하면 `updatedAt`을 근사치로
쓰거나, 별도 컬럼 추가를 요청해야 한다(이번 답변에 포함 안 함).

### 5. 카테고리 체계 — 3-depth, 성별×대분류×소분류

`Category` 엔티티: `id, parentId, name, nameEn, depth`. depth=1(성별 3개) → depth=2(대분류,
성별마다 6~7개) → depth=3(소분류, 총 103개). 시드 전체는
`BE/src/main/resources/db/seed.sql`에 있다. 요약:

- depth 1: 남성(4) / 여성(10) / 공용(17) — `id 1~3`
- depth 2 대분류(성별 공통 6종 + 여성·공용만 있는 "원피스 및 점프슈트"):
  아우터 / 상의 / 하의 / 신발 / 가방 / 액세서리 (+ 원피스 및 점프슈트)
- depth 3 소분류 103개(자켓/코트/가디건/패딩/후드집업, 티셔츠/셔츠/니트/후드티/맨투맨/민소매,
  데님/슬랙스/카고팬츠/스커트/숏팬츠/트레이닝조거/코튼팬츠, 스니커즈/부츠/구두/샌들슬리퍼,
  백팩/숄더백/토트백/크로스백/파우치, 모자/벨트/스카프/주얼리/시계/선글라스, 원피스/점프슈트)

`AI GarmentCategory`(니트/셔츠/자켓/코트/팬츠/스커트)는 이 소분류 이름과 **거의 1:1로 이미
겹친다**(성별 축만 추가로 있음). 매핑은 소분류 `name_en`(TSHIRT, SHIRT, KNIT, JACKET, COAT,
SLACKS, DENIM, SKIRT ...) 기준으로 하면 된다. 전체 카테고리 ID 매핑표는 저장소 루트의
`docs/category-taxonomy.md`에 있다(설계 배경은 `docs/plans/BE/SY032-category-taxonomy-v2.md`).

### 6. 브랜드 마스터 테이블 — 있음, 21개 고정

`Brand` 엔티티: `id, name, nameEn`. 시드 전체 목록(`seed.sql`):

```
꼼데가르송(Comme des Garçons), 메종 마르지엘라(Maison Margiela), 요지 야마모토(Yohji Yamamoto),
릭 오웬스(Rick Owens), 이세이 미야케(Issey Miyake), 장 폴 고티에(Jean Paul Gaultier),
비비안 웨스트우드(Vivienne Westwood), 베이프(A Bathing Ape), 슈프림(Supreme), 스투시(Stussy),
캐피탈(Kapital), 히스테릭 글래머(Hysteric Glamour), 크롬하츠(Chrome Hearts),
폴로 랄프로렌(Polo Ralph Lauren), 리바이스(Levi's), 칼하트(Carhartt), 버버리(Burberry),
아크테릭스(Arc'teryx), 나이키(Nike), 아디다스(Adidas), 프라다(Prada)
```

이 목록을 AI 쪽 별칭 테이블 시드로 그대로 써도 된다 — **한/영 표기 흔들림 자체는 이미 없다**
(한글명·영문명이 DB에 1:1로 고정돼 있음). §4에서 걱정한 "리바이스/Levi's/LEVIS" 표기 혼재는
`brand.name`/`brand.nameEn` 값이 아니라, `title` 자유 텍스트에 판매자가 브랜드명을 다시 적을 때만
발생한다.

### 7. BE가 `POST /pricing/estimates`에 실제로 보내는 값 — **아직 이 호출 자체가 없다**

BE 코드 전체에서 `pricing`을 검색해도 매치가 없다. AI 가격 추천/품질 분석 연동은 아직
BE에서 미구현 상태다(`docs/requests/BE/002-product-contract.md` §3.3, "BE 확정 필요"로 남아
있음). 즉 **지금은 BE가 그 엔드포인트를 호출하지 않으므로, brand/category가 채워져 오는지
자체가 아직 정의되지 않은 질문이다.** 이 연동이 실제로 만들어질 때 요청 스키마의 필수/선택
여부를 함께 정하는 게 맞을 것 같다.

### 8. job result 파싱 엄격도 — 위와 같은 이유로 **해당 없음**

`PricingResult`를 파싱하는 BE 코드가 없으므로 unknown 필드 거부 여부를 답할 수 없다. 연동
구현 시점에 Jackson `ObjectMapper`를 `FAIL_ON_UNKNOWN_PROPERTIES=false`(기본은 이미 false)로
두면 필드 추가는 안전하다 — 다만 지금은 확정할 대상 코드 자체가 없다는 게 정확한 답이다.

### 11 (연결성, §1-A 항목은 아니지만 코드로 바로 답 가능). AI 컨테이너 → BE DB 연결

`docker-compose.yml`의 `ai` 서비스는 이미 `postgres`와 같은 `vintib-net` 네트워크에 있고,
`DB_HOST=postgres`, `DB_PORT=5432`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD` 환경변수도 이미
주입돼 있다(BE와 동일한 계정). **네트워크·자격증명 경로는 이미 열려 있다** — 다만 지금
넘어가는 계정은 **BE와 같은 관리자 계정이라 읽기 전용이 아니다.** §3에서 요청한 읽기 전용
계정은 새로 만들어야 한다(아직 안 만듦).

---

## §1-B DB를 실제로 조회해야 아는 것

로컬 dev DB(`vintib-postgres`)를 직접 조회했다. **결론부터: 정찰제(`DIRECT_SALE`) 상품은
72건 있지만, 전부 통합 테스트가 남긴 데이터로 보이고 실사용 데이터로 볼 수 없다.**

### 근거

```sql
-- 전체/상태별 카운트
SELECT sale_status, sale_type, count(*) FROM product WHERE deleted_at IS NULL GROUP BY 1,2;
--      sale_status     |  sale_type  | count
-- ---------------------+-------------+-------
--  AUCTION_IN_PROGRESS |             |    45
--  AUCTION_SCHEDULED   | AUCTION     |    33
--  AUCTION_SCHEDULED   |             |    15
--  DRAFT                |             |   738
--  ON_SALE              | DIRECT_SALE |    72

-- brand/category/grade 채움 비율 (전체 903건 기준)
SELECT count(*), count(brand_id), count(category_id), count(condition_grade) FROM product WHERE deleted_at IS NULL;
--  total | with_brand | with_category | with_grade
--    903 |          0 |           903 |          0

-- distinct 제목 수 (DIRECT_SALE 72건 중)
SELECT count(DISTINCT title), count(*) FROM product WHERE sale_type='DIRECT_SALE' AND deleted_at IS NULL;
--  distinct_titles | rows
--                26 |   72
```

- **`brand_id`가 903건 전부 NULL.** §1-A-1에서 말했듯 구조화 필드는 있는데 실제로 하나도
  안 채워졌다.
- **`condition_grade`도 903건 전부 NULL.**
- 정찰제 72건의 상품명 샘플(최근 10건, `title`은 마스킹 없이 원문 그대로 — 이미 테스트
  데이터라 개인정보 없음):

  ```
  zzsearch027e65a5 데님 자켓 | 45000원 | ON_SALE
  zzsearchb8257f48 데님 자켓 | 45000원 | ON_SALE
  zzsearch5c261daa 데님 자켓 | 45000원 | ON_SALE
  ... (zzsearch* 접두 8건, 전부 45000원 "데님 자켓")
  리바이스 501 빈티지         | 45000원 | ON_SALE   ← 여러 건 반복
  리바이스 501 빈티지         | 45000원 | ON_SALE
  ```

  `zzsearch...` 접두사는 `SearchControllerTest` 같은 통합 테스트가 검색 인덱싱 확인용으로
  찍어낸 픽스처다. "리바이스 501 빈티지" 45000원 반복도 여러 테스트 클래스의 공용 픽스처
  이름이다(72건 중 distinct 제목이 26개뿐 — 나머지는 같은 이름 반복). **판매자가 실제로
  등록한 행이 아니다.**

### 결론 및 제안

- **동일 브랜드+모델 조합 2건 이상 여부는 계산 불가**(brand_id가 전부 null이라 그룹화할 축이
  없음).
- 사실상 **0건**으로 취급하는 게 맞다. §1-B 안내대로 1-A(엔티티 정의)로 대체하고, FE 더미를
  BE 스키마에 맞춰 만드는 경로로 가는 걸 권장한다.
- `brand_id`가 실사용에서도 거의 안 채워질 가능성을 대비해야 한다 — 등록 폼에서 브랜드가
  선택 항목(optional)인지 FE 확인이 필요하다(이 문서 범위 밖, 별도 확인 요청 권장).

---

## §2 BE 의견 — 직접 DB 조회 vs 조회 API

**BE 권장: "뷰 + 읽기 전용 계정" (AI가 제안한 직접 조회 방향에 동의).** 단, 순수 테이블
직접 조회가 아니라 **뷰 하나만 노출 + 그 뷰에만 SELECT 권한을 준 별도 계정**으로 한정한다.

근거:

1. **뷰가 이미 "조회 API의 장점"을 상당 부분 흡수한다.** 뷰의 컬럼 계약은 BE가 내부 테이블
   구조를 바꿔도 그대로 유지할 수 있다 — API를 새로 만드는 것과 스키마 안전성 면에서 차이가
   크지 않다.
2. **사용 패턴이 배치/벌크다.** CH016 §3.9에 따르면 헷지는 요청 단위가 아니라 상품군별 배치로
   도는 백그라운드 작업이다. 이런 패턴은 HTTP API로 N번 호출하는 것보다 SQL 한 방으로 읽는
   게 훨씬 자연스럽고 빠르다. 시뮬레이션/실험(`validation/PRICE/`)에서도 임의 쿼리를 즉석에서
   날려볼 수 있어야 하는데, API로는 그때마다 새 엔드포인트가 필요해진다.
3. **BE 쪽 구현 비용이 적다.** 새 컨트롤러·인증·페이지네이션을 만들 필요 없이 `CREATE VIEW` +
   `CREATE ROLE ... NOSUPERUSER NOCREATEDB; GRANT SELECT ON view TO role;` 정도로 끝난다.
   지금 BE 인력이 1인이라 유지보수 표면을 늘리지 않는 쪽이 실질적으로 낫다.
4. **권한 수준 강제가 코드 신뢰보다 안전하다** — AI 쪽 요청대로, 계정 자체가 SELECT만 하도록
   막아두면 실수로 쓰기 코드가 들어가도 DB가 막아준다.

다만 이 방향을 택하면 지켜야 할 것:

- 뷰 컬럼을 바꿀 때는(예: 이번처럼 `product`에 컬럼이 자주 추가됨) **뷰 정의만 갱신하고
  컬럼 이름/타입 계약은 유지**해야 한다 — 계약이 깨지면 API 방식과 마찬가지로 통보가 필요하다.
  뷰 컬럼 계약을 `docs/APIs.md`나 별도 문서에 고정해 두는 건(§3-3 요청) 그대로 진행하는 게
  맞다.
- `ai` 컨테이너의 `db_*` 설정을 읽기전용 계정/뷰 전용으로 바꿔야 하고, 이건 **compose 환경변수
  변경 + DB 마이그레이션(role/view 생성)**이라 인프라 변경이다. 사용자 승인 후 진행한다.

---

## §3/§4 처리 방향

- §3(뷰 생성, 읽기전용 계정 발급, 컬럼 계약 문서화, `PricingResult` 계약 변경 예고 수신)은
  **이 답변 문서로 바로 처리하지 않았다.** 새 DB 객체·권한 발급은 인프라 변경이라 사용자
  확인 후 `docs/plans/BE/`에 계획을 세워 진행한다. AI 쪽에서 §1-B 결과(사실상 0건)를 보고도
  이 방향을 유지할지 먼저 확인해 주면 좋겠다 — 실사용 데이터가 쌓이기 전까지는 뷰를 만들어도
  비어 있는 뷰가 된다.
- §4(브랜드 선택형 전환)는 **이미 구조상 선택형이다**(brandId FK). 실제 입력률이 0%인 이유는
  기획/FE 쪽 확인이 필요한 부분이라 BE가 단독으로 답하지 않는다 — 필요하면
  `docs/requests/FE/`에 별도로 확인 요청을 남기는 걸 권장한다.
