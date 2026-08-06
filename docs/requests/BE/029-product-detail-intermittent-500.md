# 029 GET /products/{id}가 상품에 따라 들쭉날쭉하게 500 에러

- 요청자 파트: FE
- 대상 파트: BE

## 배경/이유

홈/상품 목록/카테고리 탭에서 카드 클릭 시 상세로 못 넘어가고("상품 정보를 불러오지 못했습니다"
에러 패널), 카드 사진도 로컬 fallback(목업) 이미지로 보이는 상품이 있다는 리포트를 조사했다.
`GET /api/products`(목록) 응답에는 대표 이미지 URL이 없어서(`docs/requests/BE/009`, 미반영)
FE가 카드 이미지·등급을 채우려고 `GET /products/{id}`를 추가 호출하는데, 이 상세 조회 자체가
상품에 따라 500을 낸다. 상세 페이지 진입 실패도 같은 API라 같은 원인으로 보인다.

**2026-08-05에 처음 확인했을 때는 `AUCTION_SCHEDULED`(경매 예정) 상품만 500이 나서 "price가
null이라 NPE"로 추정했는데, 2026-08-06 재확인 결과 패턴이 달라졌다 — 이제는 판매 방식과 무관하게
들쭉날쭉하다.** 오늘 배포 환경에서 재현한 전체 매트릭스:

| id | saleType | saleStatus | conditionGrade | 상세 조회 |
| --- | --- | --- | --- | --- |
| 1 | DIRECT_SALE | ON_SALE | (빈 값) | **500** |
| 2 | DIRECT_SALE | ON_SALE | A | 200 (linkedLive 있음 — ENDED 라이브) |
| 3 | DIRECT_SALE | ON_SALE | A | **500** |
| 4 | AUCTION | AUCTION_SCHEDULED | (빈 값) | **500** |
| 5 | AUCTION | AUCTION_SCHEDULED | A | **500** |
| 6 | AUCTION | AUCTION_SCHEDULED | (빈 값) | 200 (linkedLive 없음/null) |

saleType, saleStatus, conditionGrade, linkedLive 유무 어느 것도 성공/실패를 깔끔하게 가르지
못한다(2·6은 linkedLive가 각각 있음/없음인데 둘 다 성공, 1·3·4·5는 이 값들이 제각각인데 전부
실패). 블랙박스 테스트로는 더 좁히기 어려워서, `ProductService.getProductDetail()`
(`BE/src/main/java/com/ssafy/backend/product/service/ProductService.java`) 쪽 서버 로그의
실제 스택트레이스를 봐야 원인이 잡힐 것 같다. 코드를 훑어봤을 때 의심 가는 지점은 없었다
(`isWishedBy`는 이미 `memberId == null` 가드가 있고, `ProductImageService.getImages`도
단순 매핑이라 특별한 문제가 안 보였다) — 그래서 직접 원인을 지목하기보다 재현 매트릭스만
남긴다.

## 요청 내용

- `GET /products/{id}`가 상품에 따라 500을 내는 원인을 서버 로그(스택트레이스)로 확인하고
  고쳐 주세요. 위 표의 실패/성공 조합이 힌트가 될 수 있을 것 같습니다.
- 이 버그 때문에 FE에서 영향받는 곳:
  - 홈/카테고리 탭/상품 목록 카드: 대표 이미지 fallback 호출이 실패해 로컬 목업 이미지로 표시됨
  - 홈 상품 카드의 등급(S/A/B/C) 뱃지: 등급도 상세 조회로 채우고 있어 안 뜨는 경우가 생김
  - **상품 상세 페이지 자체가 안 열림** — 해당 상품을 클릭하면 "상품 정보를 불러오지 못했습니다"
    에러 패널만 보임(`ProductDetailView.vue`가 500을 잡아서 보여주는 화면이라 白 화면은 아니지만,
    사용자 입장에선 "상세로 안 넘어간다"로 느껴짐)

## 관련 자료

- 재현: 위 표(2026-08-06 기준 실제 재현 결과)
- `docs/plans/FE/SY034-home-product-card-revamp.md` (등급 뱃지 N+1 조회, 카테고리 탭 이미지
  fallback 로직)
- `docs/requests/BE/009-product-list-primary-image.md` (목록 응답에 대표 이미지가 없어서 상세
  조회에 의존하게 된 배경)
