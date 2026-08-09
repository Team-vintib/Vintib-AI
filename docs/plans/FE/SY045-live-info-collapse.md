# 라이브 진행 중 경매/라이브 정보 영역 접기·펴기

## 배경/목표

라이브 시청·방송 화면에서 영상 아래에 고정으로 붙는 상품/경매 정보 영역이 항상 노출돼 있어 화면을 많이 차지한다. 이미 채팅 패널(`LiveChatOverlay`)에 구현된 접기/펴기 토글과 동일한 방식으로, 구매자·판매자 화면 모두에서 이 정보 영역을 접었다 펼 수 있게 한다.

## 작업 내용

- `LiveChatOverlay.vue`의 기존 패턴을 그대로 재사용한다: 로컬 `ref`(`isInfoCollapsed`)로 상태를 두고 `v-show`로 본문을 토글. 펼친 상태엔 우측 상단 `×` 버튼으로 접고, 접힌 상태엔 우측 하단에 `i`(정보) 버튼만 남아 다시 누르면 펼쳐진다. 새로고침 시 초기화(영속화하지 않음), 부모로 emit하지 않고 각 페이지 로컬 상태로 관리.
- **구매자** `LiveWatchPage.vue`: `.live-watch-page__details`(상품 요약 `LiveSelectedProduct` + `LiveDirectSalePanel`/`LiveAuctionPanel`) 전체를 감싸는 wrapper에 토글 적용.
- **판매자** `LiveBroadcastPage.vue`: `.live-broadcast-page__details`(`SellerAuctionPanel` + `LiveBroadcastInfo`) 전체를 감싸는 wrapper에 토글 적용.
- 두 화면은 컴포넌트를 공유하지 않으므로(기존 구조 그대로) 공통 컴포넌트로 추출하지 않고 각 페이지 파일에 개별 구현한다.
- 접힌 상태에서는 정보 영역이 차지하던 grid row/영역이 얇은 바 높이로 줄어들도록 CSS를 조정한다(영상 스테이지 크기 자체는 건드리지 않음).
- 아이콘은 별도 아이콘 라이브러리 없이 기존 관례대로 텍스트 문자(`×`, `i`)를 사용한다.
- "정보 탭"의 범위는 상품 요약 + 판매/경매 패널 전체(하단 블록 전체)로 확정.

## 구현 목록

- [x] `LiveWatchPage.vue`: 상세 정보 영역 wrapper(`-body`) + `isInfoCollapsed` ref + `×` 닫기 / `i` 재오픈 버튼
- [x] `LiveBroadcastPage.vue`: 상세 정보 영역 wrapper(`-body`) + `isInfoCollapsed` ref + `×` 닫기 / `i` 재오픈 버튼
- [x] 접힌/펼친 상태 CSS(grid-template-rows 전환, 버튼 스타일)를 `LiveChatOverlay`와 톤 맞춰 작성
- [ ] 두 화면 각각 판매자/구매자 계정으로 접기·펴기 동작 수동 확인 (브라우저 테스트 필요)
