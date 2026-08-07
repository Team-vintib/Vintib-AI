# 상품 분류(카테고리·색상) 사전업로드 연동 — 방향 B 확정 + categoryId 조회표

- **요청자 파트**: AI
- **대상 파트**: BE
- **관련 문서**: `docs/requests/BE/042-product-registration-ai-pipeline.md`(방향 A/B 논의 원본),
  `docs/requests/AI/006-registration-category-color-autofill.md`(FE 원 요청)

## 배경/이유

`042`에서 논의한 "상품 생성 전 이미지 업로드" 문제를 **방향 B(상품과 무관한 독립 사전
업로드)** 로 확정했습니다. 분류(`POST /product-classifier/classify`)는 하자검수(`041`)와
달리 상품 생성 **전**에 트리거돼야 프리필 효과가 있습니다 — 카테고리를 사용자가 고르기
전에 채워주는 게 목적이라, 상품 생성 후에 트리거하면 이미 늦습니다.

## 요청 내용

### 1. AI 쪽 계약 변경 (이미 반영 완료, 참고용)

`ProductClassifyRequest.product_id`를 optional로 바꿨습니다(`int | None`, 기본값 `None`).
사전업로드 시점엔 진짜 상품 id가 없으니 그냥 생략하고 호출하시면 됩니다 — 응답도 `null`을
그대로 에코합니다.

### 2. categoryId 계산표 (요청하신 것)

분류 응답은 소분류 코드(`value`, 예: `"CARDIGAN"`)와 표시용 `path`만 줍니다. (성별 ×
소분류) → BE의 실제 `categoryId`(depth2/depth3)는 아래 표로 계산해 주세요.
`worker/models/product_classifier/taxonomy.py`의 `CATEGORY_ID_MAP`/`MAJOR_CATEGORY_ID_MAP`을
그대로 뽑은 것이라 BE 시드 기준으로 이미 assert 검산돼 있습니다(해당 파일 하단 참고).

**⚠️ 성별을 못 받은 상태(사전업로드 시점, 아직 폼에서 성별 선택 전)라면 MEN 행을 먼저
쓰고, 없으면(DRESS/JUMPSUIT) WOMEN 행을 쓰세요. UNISEX가 아닙니다** — 지금 FE 카테고리
드롭다운이 같은 한글 라벨을 가진 성별별 옵션 중 `id`가 가장 낮은 것(=MEN)만 남기고
나머지는 중복 제거해 버립니다(`ProductRegistrationPage.vue`의
`dedupeCategoryOptionsByLabel()`). UNISEX id를 주면 35개 소분류 중 33개에서 드롭다운에
해당 값 자체가 없어 자동채움이 조용히 실패합니다.

| 성별 | 소분류 코드(value) | 소분류(한글) | 대분류 | categoryId(depth3) | majorCategoryId(depth2) |
| --- | --- | --- | --- | --- | --- |
| MEN | JACKET | 자켓 | 아우터 | 24 | 4 |
| MEN | COAT | 코트 | 아우터 | 25 | 4 |
| MEN | CARDIGAN | 가디건 | 아우터 | 26 | 4 |
| MEN | PADDED_JACKET | 패딩 | 아우터 | 27 | 4 |
| MEN | HOOD_ZIPUP | 후드집업 | 아우터 | 28 | 4 |
| MEN | TSHIRT | 티셔츠 | 상의 | 29 | 5 |
| MEN | SHIRT | 셔츠 | 상의 | 30 | 5 |
| MEN | KNIT | 니트 | 상의 | 31 | 5 |
| MEN | HOODIE | 후드티 | 상의 | 32 | 5 |
| MEN | SWEATSHIRT | 맨투맨 | 상의 | 33 | 5 |
| MEN | SLEEVELESS | 민소매 | 상의 | 34 | 5 |
| MEN | DENIM | 데님 | 하의 | 35 | 6 |
| MEN | SLACKS | 슬랙스 | 하의 | 36 | 6 |
| MEN | CARGO_PANTS | 카고팬츠 | 하의 | 37 | 6 |
| MEN | SKIRT | 스커트 | 하의 | 38 | 6 |
| MEN | SHORT_PANTS | 숏팬츠 | 하의 | 39 | 6 |
| MEN | JOGGER_PANTS | 트레이닝/조거 | 하의 | 40 | 6 |
| MEN | COTTON_PANTS | 코튼팬츠 | 하의 | 41 | 6 |
| MEN | SNEAKERS | 스니커즈 | 신발 | 42 | 7 |
| MEN | BOOTS | 부츠 | 신발 | 43 | 7 |
| MEN | DRESS_SHOES | 구두 | 신발 | 44 | 7 |
| MEN | SANDALS_SLIPPERS | 샌들/슬리퍼 | 신발 | 45 | 7 |
| MEN | BACKPACK | 백팩 | 가방 | 46 | 8 |
| MEN | SHOULDER_BAG | 숄더백 | 가방 | 47 | 8 |
| MEN | TOTE_BAG | 토트백 | 가방 | 48 | 8 |
| MEN | CROSS_BAG | 크로스백 | 가방 | 49 | 8 |
| MEN | POUCH | 파우치 | 가방 | 50 | 8 |
| MEN | HAT | 모자 | 액세서리 | 51 | 9 |
| MEN | BELT | 벨트 | 액세서리 | 52 | 9 |
| MEN | SCARF | 스카프 | 액세서리 | 53 | 9 |
| MEN | JEWELRY | 주얼리 | 액세서리 | 54 | 9 |
| MEN | WATCH | 시계 | 액세서리 | 55 | 9 |
| MEN | SUNGLASSES | 선글라스 | 액세서리 | 56 | 9 |
| WOMEN | JACKET | 자켓 | 아우터 | 57 | 10 |
| WOMEN | COAT | 코트 | 아우터 | 58 | 10 |
| WOMEN | CARDIGAN | 가디건 | 아우터 | 59 | 10 |
| WOMEN | PADDED_JACKET | 패딩 | 아우터 | 60 | 10 |
| WOMEN | HOOD_ZIPUP | 후드집업 | 아우터 | 61 | 10 |
| WOMEN | TSHIRT | 티셔츠 | 상의 | 62 | 11 |
| WOMEN | SHIRT | 셔츠 | 상의 | 63 | 11 |
| WOMEN | KNIT | 니트 | 상의 | 64 | 11 |
| WOMEN | HOODIE | 후드티 | 상의 | 65 | 11 |
| WOMEN | SWEATSHIRT | 맨투맨 | 상의 | 66 | 11 |
| WOMEN | SLEEVELESS | 민소매 | 상의 | 67 | 11 |
| WOMEN | DENIM | 데님 | 하의 | 68 | 12 |
| WOMEN | SLACKS | 슬랙스 | 하의 | 69 | 12 |
| WOMEN | CARGO_PANTS | 카고팬츠 | 하의 | 70 | 12 |
| WOMEN | SKIRT | 스커트 | 하의 | 71 | 12 |
| WOMEN | SHORT_PANTS | 숏팬츠 | 하의 | 72 | 12 |
| WOMEN | JOGGER_PANTS | 트레이닝/조거 | 하의 | 73 | 12 |
| WOMEN | COTTON_PANTS | 코튼팬츠 | 하의 | 74 | 12 |
| WOMEN | SNEAKERS | 스니커즈 | 신발 | 75 | 13 |
| WOMEN | BOOTS | 부츠 | 신발 | 76 | 13 |
| WOMEN | DRESS_SHOES | 구두 | 신발 | 77 | 13 |
| WOMEN | SANDALS_SLIPPERS | 샌들/슬리퍼 | 신발 | 78 | 13 |
| WOMEN | BACKPACK | 백팩 | 가방 | 79 | 14 |
| WOMEN | SHOULDER_BAG | 숄더백 | 가방 | 80 | 14 |
| WOMEN | TOTE_BAG | 토트백 | 가방 | 81 | 14 |
| WOMEN | CROSS_BAG | 크로스백 | 가방 | 82 | 14 |
| WOMEN | POUCH | 파우치 | 가방 | 83 | 14 |
| WOMEN | HAT | 모자 | 액세서리 | 84 | 15 |
| WOMEN | BELT | 벨트 | 액세서리 | 85 | 15 |
| WOMEN | SCARF | 스카프 | 액세서리 | 86 | 15 |
| WOMEN | JEWELRY | 주얼리 | 액세서리 | 87 | 15 |
| WOMEN | WATCH | 시계 | 액세서리 | 88 | 15 |
| WOMEN | SUNGLASSES | 선글라스 | 액세서리 | 89 | 15 |
| WOMEN | DRESS | 원피스 | 원피스 및 점프슈트 | 90 | 16 |
| WOMEN | JUMPSUIT | 점프슈트 | 원피스 및 점프슈트 | 91 | 16 |
| UNISEX | JACKET | 자켓 | 아우터 | 92 | 17 |
| UNISEX | COAT | 코트 | 아우터 | 93 | 17 |
| UNISEX | CARDIGAN | 가디건 | 아우터 | 94 | 17 |
| UNISEX | PADDED_JACKET | 패딩 | 아우터 | 95 | 17 |
| UNISEX | HOOD_ZIPUP | 후드집업 | 아우터 | 96 | 17 |
| UNISEX | TSHIRT | 티셔츠 | 상의 | 97 | 18 |
| UNISEX | SHIRT | 셔츠 | 상의 | 98 | 18 |
| UNISEX | KNIT | 니트 | 상의 | 99 | 18 |
| UNISEX | HOODIE | 후드티 | 상의 | 100 | 18 |
| UNISEX | SWEATSHIRT | 맨투맨 | 상의 | 101 | 18 |
| UNISEX | SLEEVELESS | 민소매 | 상의 | 102 | 18 |
| UNISEX | DENIM | 데님 | 하의 | 103 | 19 |
| UNISEX | SLACKS | 슬랙스 | 하의 | 104 | 19 |
| UNISEX | CARGO_PANTS | 카고팬츠 | 하의 | 105 | 19 |
| UNISEX | SKIRT | 스커트 | 하의 | 106 | 19 |
| UNISEX | SHORT_PANTS | 숏팬츠 | 하의 | 107 | 19 |
| UNISEX | JOGGER_PANTS | 트레이닝/조거 | 하의 | 108 | 19 |
| UNISEX | COTTON_PANTS | 코튼팬츠 | 하의 | 109 | 19 |
| UNISEX | SNEAKERS | 스니커즈 | 신발 | 110 | 20 |
| UNISEX | BOOTS | 부츠 | 신발 | 111 | 20 |
| UNISEX | DRESS_SHOES | 구두 | 신발 | 112 | 20 |
| UNISEX | SANDALS_SLIPPERS | 샌들/슬리퍼 | 신발 | 113 | 20 |
| UNISEX | BACKPACK | 백팩 | 가방 | 114 | 21 |
| UNISEX | SHOULDER_BAG | 숄더백 | 가방 | 115 | 21 |
| UNISEX | TOTE_BAG | 토트백 | 가방 | 116 | 21 |
| UNISEX | CROSS_BAG | 크로스백 | 가방 | 117 | 21 |
| UNISEX | POUCH | 파우치 | 가방 | 118 | 21 |
| UNISEX | HAT | 모자 | 액세서리 | 119 | 22 |
| UNISEX | BELT | 벨트 | 액세서리 | 120 | 22 |
| UNISEX | SCARF | 스카프 | 액세서리 | 121 | 22 |
| UNISEX | JEWELRY | 주얼리 | 액세서리 | 122 | 22 |
| UNISEX | WATCH | 시계 | 액세서리 | 123 | 22 |
| UNISEX | SUNGLASSES | 선글라스 | 액세서리 | 124 | 22 |
| UNISEX | DRESS | 원피스 | 원피스 및 점프슈트 | 125 | 23 |
| UNISEX | JUMPSUIT | 점프슈트 | 원피스 및 점프슈트 | 126 | 23 |

이 표는 `worker/models/product_classifier/taxonomy.py`의 `CATEGORY_ID_MAP`/
`MAJOR_CATEGORY_ID_MAP`을 그대로 덤프한 것입니다 — 시드가 바뀌면 그 파일의 `assert`가
먼저 깨지므로, 재확인 없이 그대로 하드코딩하셔도 됩니다.

### 3. 실백엔드 상태 (참고)

카테고리·색상 둘 다 파인튜닝된 CLIP 체크포인트로 전환 작업 중입니다(로컬 테스트 단계).
색상은 정확도는 준수하지만(0.88대) 신뢰도 보정이 카테고리보다 약해 `action="autofill"`
빈도가 카테고리보다 낮게 나올 수 있습니다 — `action` 필드로 이미 구분되니 BE/FE 쪽에서
추가로 할 일은 없습니다.

## 요청하지 않는 것

- BE 트리거/폴링 엔드포인트 구현 자체는 요청하지 않습니다 — 같은 담당자가 진행 중입니다.
  이 문서는 그 구현에 필요한 계산표 전달용입니다.

## 처리 결과

(반영 후 기입)
