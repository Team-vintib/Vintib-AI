# 029 GET /products/{id}가 경매 예정(AUCTION_SCHEDULED) 상품에서 500 에러

- 요청자 파트: FE
- 대상 파트: BE

## 배경/이유

홈 화면 "카테고리별 상품" 카드에서 일부 카드만 사진이 목업(로컬 fallback 이미지)으로 보이는
문제를 조사하다가 발견했다. `GET /api/products`(목록) 응답에는 대표 이미지 URL이 없어서
(`docs/requests/BE/009-product-list-primary-image.md`, 아직 미반영) FE가 `GET /products/{id}`를
추가 호출해 이미지를 채우는데, 이 상세 조회 자체가 `AUCTION_SCHEDULED` 상품에서 500을 낸다.

배포 환경에서 직접 재현 확인:

```
GET https://i15a108.p.ssafy.io/api/products/1  → 200 (DIRECT_SALE)
GET https://i15a108.p.ssafy.io/api/products/2  → 200 (DIRECT_SALE)
GET https://i15a108.p.ssafy.io/api/products/3  → 200 (DIRECT_SALE)
GET https://i15a108.p.ssafy.io/api/products/4  → 500 {"code":"C002","message":"서버 내부 오류가 발생했습니다."} (AUCTION_SCHEDULED)
GET https://i15a108.p.ssafy.io/api/products/5  → 500 {"code":"C002","message":"서버 내부 오류가 발생했습니다."} (AUCTION_SCHEDULED)
```

`/home` 응답의 `upcomingAuctionProducts`에는 상품 4·5의 `thumbnailUrl`이 정상적으로 내려온다
(이미지 자체는 DB에 있음 — `home.service.ProductCardAssembler`가 상세 조회와 다른 경로로
이미지를 읽기 때문으로 보인다). 즉 상세 조회 경로에서만 터진다. 경매 예정 상품은
`price`가 `null`이라 상세 응답을 만드는 과정(가격 포맷팅, 유사 상품 가격 분포, 측정치 등)에서
null을 처리하지 못해 NPE가 나는 것으로 추정된다.

## 요청 내용

- `GET /products/{id}`가 `AUCTION_SCHEDULED` 상품에서 500을 내는 원인을 확인하고 고쳐 주세요.
  `price`가 `null`인 경로(가격 관련 필드/유사 상품 가격 분포 등) 위주로 봐 주시면 될 것 같습니다.
- 이 버그 때문에 FE에서 영향받는 곳:
  - 홈 "카테고리별 상품" 카드: 대표 이미지 fallback 호출이 실패해 로컬 목업 이미지로 표시됨
  - 홈 상품 카드의 등급(S/A/B/C) 뱃지: 등급도 상세 조회로 채우고 있어 경매 예정 상품은 뱃지가
    안 뜸
  - 상품 상세 페이지에서 경매 예정 상품을 직접 열람하는 경우에도 같은 500이 날 것으로 보임(직접
    확인은 못 했으나 같은 엔드포인트라 영향권으로 보임)

## 관련 자료

- 재현: 위 curl 결과
- `docs/plans/FE/SY034-home-product-card-revamp.md` (등급 뱃지 N+1 조회, 카테고리 탭 이미지
  fallback 로직)
- `docs/requests/BE/009-product-list-primary-image.md` (목록 응답에 대표 이미지가 없어서 상세
  조회에 의존하게 된 배경)
