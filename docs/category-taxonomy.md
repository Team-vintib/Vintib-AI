# 카테고리 분류 체계 (성별 → 대분류 → 소분류)

`category` 테이블의 실제 시드 데이터(ID·영문 코드 매핑). 컬럼 스펙 전체는
[`data-dictionary.md`](../BE/docs/db/data-dictionary.md), 히스토리는
`plans/BE/SY022-category-taxonomy.md`/`SY032-category-taxonomy-v2.md` 참고.

- 시드 원본: `../BE/src/main/resources/db/seed.sql`
- ID는 시드 삽입 순서에 고정(성별 → 대분류 → 소분류). 항목 추가/순서 변경 시 이 문서도 갱신.

## 컬럼

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | bigint | PK |
| `parent_id` | bigint | 상위 카테고리 (최상위는 NULL) |
| `name` | varchar(100) | 한글명 |
| `name_en` | varchar(100) NOT NULL | 영문 코드(`SCREAMING_SNAKE_CASE`) |
| `depth` | smallint | 1=성별, 2=대분류, 3=소분류 |

## depth·담당 주체

| depth | 의미 | 개수 | ID 범위 | 담당 |
| :---: | --- | :---: | --- | --- |
| 1 | 성별 | 3 | 1~3 | — |
| 2 | 대분류 | 20 (남 6 / 여 7 / 공용 7) | 4~23 | **AI 자동 판별** |
| 3 | 소분류 | 103 | 24~126 | **사용자 선택** |

`product.category_id`는 항상 depth=3(소분류) id — DB 제약은 없고 관례로만 지켜진다.
대분류 개수가 성별마다 다르다("원피스 및 점프슈트"는 여성·공용에만 있고 남성엔 없음).

## depth 1 — 성별

| id | name | name_en |
| :---: | --- | --- |
| 1 | 남성 | MEN |
| 2 | 여성 | WOMEN |
| 3 | 공용 | UNISEX |

## depth 2 — 대분류

| id | name | name_en | 성별 |
| :---: | --- | --- | :---: |
| 4 | 아우터 | OUTER | 남성 |
| 5 | 상의 | TOP | 남성 |
| 6 | 하의 | BOTTOM | 남성 |
| 7 | 신발 | SHOES | 남성 |
| 8 | 가방 | BAG | 남성 |
| 9 | 액세서리 | ACCESSORY | 남성 |
| 10 | 아우터 | OUTER | 여성 |
| 11 | 상의 | TOP | 여성 |
| 12 | 하의 | BOTTOM | 여성 |
| 13 | 신발 | SHOES | 여성 |
| 14 | 가방 | BAG | 여성 |
| 15 | 액세서리 | ACCESSORY | 여성 |
| 16 | 원피스 및 점프슈트 | DRESS_JUMPSUIT | 여성 |
| 17 | 아우터 | OUTER | 공용 |
| 18 | 상의 | TOP | 공용 |
| 19 | 하의 | BOTTOM | 공용 |
| 20 | 신발 | SHOES | 공용 |
| 21 | 가방 | BAG | 공용 |
| 22 | 액세서리 | ACCESSORY | 공용 |
| 23 | 원피스 및 점프슈트 | DRESS_JUMPSUIT | 공용 |

## depth 3 — 소분류 (`parent_id`=대분류 id, 성별마다 별도 id)

| 대분류 | 소분류 | name_en | 남성 id | 여성 id | 공용 id |
| --- | --- | --- | :---: | :---: | :---: |
| 아우터 | 자켓 | JACKET | 24 | 57 | 92 |
| | 코트 | COAT | 25 | 58 | 93 |
| | 가디건 | CARDIGAN | 26 | 59 | 94 |
| | 패딩 | PADDED_JACKET | 27 | 60 | 95 |
| | 후드집업 | HOOD_ZIPUP | 28 | 61 | 96 |
| 상의 | 티셔츠 | TSHIRT | 29 | 62 | 97 |
| | 셔츠 | SHIRT | 30 | 63 | 98 |
| | 니트 | KNIT | 31 | 64 | 99 |
| | 후드티 | HOODIE | 32 | 65 | 100 |
| | 맨투맨 | SWEATSHIRT | 33 | 66 | 101 |
| | 민소매 | SLEEVELESS | 34 | 67 | 102 |
| 하의 | 데님 | DENIM | 35 | 68 | 103 |
| | 슬랙스 | SLACKS | 36 | 69 | 104 |
| | 카고팬츠 | CARGO_PANTS | 37 | 70 | 105 |
| | 스커트 | SKIRT | 38 | 71 | 106 |
| | 숏팬츠 | SHORT_PANTS | 39 | 72 | 107 |
| | 트레이닝/조거 | JOGGER_PANTS | 40 | 73 | 108 |
| | 코튼팬츠 | COTTON_PANTS | 41 | 74 | 109 |
| 신발 | 스니커즈 | SNEAKERS | 42 | 75 | 110 |
| | 부츠 | BOOTS | 43 | 76 | 111 |
| | 구두 | DRESS_SHOES | 44 | 77 | 112 |
| | 샌들/슬리퍼 | SANDALS_SLIPPERS | 45 | 78 | 113 |
| 가방 | 백팩 | BACKPACK | 46 | 79 | 114 |
| | 숄더백 | SHOULDER_BAG | 47 | 80 | 115 |
| | 토트백 | TOTE_BAG | 48 | 81 | 116 |
| | 크로스백 | CROSS_BAG | 49 | 82 | 117 |
| | 파우치 | POUCH | 50 | 83 | 118 |
| 액세서리 | 모자 | HAT | 51 | 84 | 119 |
| | 벨트 | BELT | 52 | 85 | 120 |
| | 스카프 | SCARF | 53 | 86 | 121 |
| | 주얼리 | JEWELRY | 54 | 87 | 122 |
| | 시계 | WATCH | 55 | 88 | 123 |
| | 선글라스 | SUNGLASSES | 56 | 89 | 124 |
| 원피스 및 점프슈트 | 원피스 | DRESS | — | 90 | 125 |
| | 점프슈트 | JUMPSUIT | — | 91 | 126 |

## API

`GET /api/categories`(비회원 가능) — 전체 126개를 `id` 오름차순 평탄 리스트로 반환. 트리 구성은
FE/AI가 한다.

```json
{ "id": 29, "parentId": 5, "name": "티셔츠", "nameEn": "TSHIRT", "depth": 3 }
```

```bash
docker exec -i vintib-postgres psql -U postgres -d vintib \
  -c "SELECT id, name, name_en, depth, parent_id FROM category ORDER BY id;"
```

## 사용 방법

- **AI**: 대분류 id(4~23)로 결과를 준다. **성별도 함께 판별**해야 한다 — 대분류 이름·개수가
  성별마다 다르다(아우터가 3번 중복, 원피스는 남성에 없음).
- **FE**: 받은 대분류 id로 `parentId`가 일치하는 소분류만 필터링해 사용자에게 보여준다. 선택된
  소분류 id가 `POST /api/products`의 `categoryId`로 들어간다.
- **BE**: `product.category_id`는 항상 depth=3 id라고 가정하고 조회/필터를 짠다. `POST
  /api/products`는 지금 depth를 검증하지 않는다(관례로만 지켜짐).
