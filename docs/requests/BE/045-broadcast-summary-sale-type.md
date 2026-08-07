# 045 방송 종료 요약에 판매 방식·등록가 추가 요청

- **요청자 파트**: FE (김현수)
- **대상 파트**: BE
- **관련 이슈**: FE `S15P11A108-438` [AUCT-012/013] 방송 종료 대시보드
- **작성일**: 2026-08-07

## 배경 / 이유

판매자 방송 종료 대시보드에서 **미판매 상품이 정찰제인지 경매 예정인지 구분할 수 없고, 정찰제
미판매 상품의 가격도 알 수 없다.** `GET /api/lives/{id}/summary`의 `results`가 주는 값은
`productId`·`title`·`thumbnailUrl`·`status`·`finalPrice`·`soldVia`뿐이고, 안 팔린 상품은
`finalPrice`·`soldVia`가 둘 다 `null`이라 화면에 `—`만 남는다.

지금은 FE가 같은 화면에서 이미 들고 있는 편성 상품 목록(`GET /api/lives/{id}`의 `products`)을
`productId`로 이어 붙여 `saleType`·`price`를 채워 쓰고 있다. 동작은 하지만 **요약 API 하나만
보면 대시보드를 못 그리는 상태**라, 상품이 방송 후 수정·삭제되면 두 응답이 어긋난다.

## 요청 내용

`LiveBroadcastSummaryResponse.Result`에 아래 두 필드를 추가해 주세요.

- **판매 방식**: `DIRECT_SALE` / `AUCTION` (편성 시점 상품의 `saleType`). 상품 행을 못 찾으면 `null`
- **등록가**: 상품에 매겨진 가격(원). 경매 예정이라 가격이 없으면 `null`

`soldVia`(어느 경로로 팔렸는지)와는 다른 축입니다. `soldVia`는 판매된 상품에만 있고, 이번에
필요한 건 **안 팔린 상품이 원래 어떤 방식으로 걸려 있었는지**입니다.

필드가 들어오면 FE는 편성 상품 목록을 이어 붙이는 우회를 걷어내고 요약 응답만 씁니다.

## 관련 자료

- BE: `LiveBroadcastSummaryResponse`(`auction/dto/response`)
- FE: `LiveBroadcastEndDashboard.vue`, `docs/plans/FE/HS041-broadcast-end-dashboard-polish.md`
- 기존 계약 정리: `docs/requests/FE/031-broadcast-summary-unsold-contract.md`
