# 018 방송 종료 요약(대시보드) 데이터 요청

**요청자 파트**: FE
**대상 파트**: BE

## 배경/이유
판매자 방송 종료 후 "방송 종료 대시보드"(FE `LiveBroadcastEndDashboard`, LIVE-003)가 판매 수·미낙찰 수·총 판매액·상품별 결과를 보여준다. 현재 이 값들이 FE에서 `0`/빈 배열로 **하드코딩**돼 있다(`LiveBroadcastPage.vue`의 `broadcastSummary` computed). 실데이터를 줄 API가 없어 요청한다.

## 요청 내용
- 방송 종료 요약을 주는 엔드포인트(방식은 BE 판단 — 예: `GET /api/lives/{liveId}/summary`, 또는 종료 `PATCH /api/lives/{liveId}/status` 응답에 포함).
- FE가 필요한 필드(현재 컴포넌트 `BroadcastEndSummary` 기준):
  ```jsonc
  {
    "soldCount": 3,        // 판매(낙찰/구매)된 상품 수
    "unsoldCount": 2,      // 미판매/미낙찰 상품 수
    "totalSales": 452000,  // 총 판매액(포인트)
    "results": [           // 상품별 결과
      { "productId": 2001, "status": "SOLD",   "finalPrice": 89000 },
      { "productId": 2002, "status": "UNSOLD", "finalPrice": null }
    ]
  }
  ```
  - `status`: 판매/미판매 구분(값 이름은 BE 확정). `finalPrice`: 낙찰가/판매가(미판매면 `null`).
  - 미낙찰 상품 목록은 FE가 `results`의 `UNSOLD`로 걸러 "남은 상품 관리"에 쓴다.
- 권한: 방송 host(판매자) 본인만.

## 일정/상태
- FE는 종료 대시보드 UI 구현 완료(현재 mock 값). API가 나오면 매핑만 하면 됨.
- 판매/낙찰 확정 로직과 얽히므로 경매 API(016 §6-F, 진행 중)와 함께 확정돼도 무방.

## 관련 자료
- FE: `FE/src/domains/live/pages/LiveBroadcastPage.vue`(`broadcastSummary` 하드코딩), `FE/src/domains/live/components/LiveBroadcastEndDashboard.vue`, 타입 `BroadcastEndSummary`
- 기능: LIVE-003 판매자 방송 / 부모 스토리 `S15P11A108-86`

## 처리 결과
(BE 반영 후 기입)
