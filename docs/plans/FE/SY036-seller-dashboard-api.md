# 판매자 대시보드 실 데이터 연동 + 월별 수익 그래프

## 배경/목표

마이페이지 "판매자 대시보드"(`selectedSection === 'seller'`) UI는 이미 있지만
`getMyPageViewData()`가 `salesPerformance`/`settlementSummary`/`monthlyRevenue`/
`todoCounts.shippingPending`을 항상 0/빈 값으로만 채워서 카드와 월별 수익 그래프가 항상
비어 있다. 전용 대시보드/정산 API가 없으므로, 이미 연동된 `GET /users/{id}/orders?role=SELLER`
(판매 내역)와 상품 목록을 클라이언트에서 조합해 채운다.

## 작업 내용

### 데이터 확인 결과 (조사 완료)

- 정산 완료 "시각"을 담는 필드가 BE 어디에도 없다(정산이 별도 절차 없이 주문 확정과 동시에
  끝나는 구조). 사용자 확인 후 **주문 생성일(`createdAt`)을 정산일 근사치로 사용**하기로
  했고, 실제 필드가 필요하다는 BE 요청 문서(`docs/requests/BE/030`)를 남겼다.
- 판매자 단위 환불 요청 집계 API가 없다(환불 API가 전부 주문 단위). 사용자 확인 후 **"환불
  요청" 카드는 이번 범위에서 제외**하기로 했다(`MyTodoCounts`에서 `refundRequests` 필드
  자체를 제거).

### 집계 로직 (`myApi.ts`)

- `GET /users/{id}/orders?role=SELLER`를 전체 페이지 순회해서 가져온다(현재는 첫 페이지
  100건만 가져와 있음 — 프로필 라이브 목록 전체 조회와 같은 페이지네이션 패턴 재사용).
- `SETTLED` 상태 주문으로: `salesPerformance`(soldCount/grossRevenue/netRevenue —
  수수료 데이터가 없어 gross와 동일/averageOrderAmount/sellThroughRate — 등록 상품 수 대비
  판매 수/repeatBuyerCount — 2회 이상 구매한 구매자 수), `settlementSummary.settledAmount`,
  `settlementSummary.lastSettledAt`(SETTLED 주문 중 가장 최근 createdAt)를 계산한다.
- `PAID`/`SHIPPING`/`DELIVERED`/`CONFIRMED` 상태 주문 합계로 `settlementSummary.pendingAmount`
  (화면에 아직 노출되진 않지만 타입 완전성을 위해 채움)를 계산한다. `withdrawableAmount`는
  이미 로드돼 있는 포인트 잔액(`pointBalance.available`)을 그대로 쓰면 되므로 여기서는
  건드리지 않는다(MyPage.vue가 이미 별도로 갖고 있음).
- `shippingPending`(`todoCounts`)은 `PAID`/`SHIPPING` 상태 주문 수로 계산한다.
- `monthlyRevenue`: 이번 달 포함 최근 12개월 각각에 대해 SETTLED 주문의 `createdAt` 월로
  묶어 합산한다. 데이터가 없는 달도 0으로 채워 12칸을 항상 유지한다. `month` 라벨은
  `"8월"`처럼 실제 달력상 월 숫자를 쓴다.

### 화면 (`MyPage.vue`)

- `todoCards`에서 "환불 요청" 항목 제거.
- 월별 수익 그래프를 6칸 → 12칸으로 바꾼다. 칸이 좁아지므로 막대 위/아래에 있던 금액·건수
  텍스트 라벨은 지우고(12칸에서는 겹쳐 보임), 대신 각 칸에 `title` 툴팁(월·금액·건수)을
  달아 정확한 값은 hover로 확인할 수 있게 한다. x축 라벨(월)은 그대로 막대 아래 유지한다.

## 구현 목록

- [x] `docs/requests/BE/030-order-settled-at-field.md` 작성
- [x] `my.types.ts`: `MyTodoCounts`에서 `refundRequests` 제거
- [x] `myApi.ts`: 판매자 주문 전체 페이지 조회, `buildSellerDashboardMetrics`/
      `buildMonthlyRevenue` 추가, `getMyPageViewData`에 연결
- [x] `MyPage.vue`: `todoCards`에서 환불 요청 제거, 월별 수익 그래프 12칸으로 변경(라벨 정리
      + 툴팁)
- [x] `npm run type-check`, `npm run lint` 통과 확인

## 확인이 필요한 미결정 사항

- 없음 — 정산일 근사(createdAt) 방식과 환불 요청 카드 제외는 사용자 확인 완료.
