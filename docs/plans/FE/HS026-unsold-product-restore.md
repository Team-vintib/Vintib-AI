# HS026 — AUCT-014 미낙찰 상품 처리

- Jira: `S15P11A108-440`(`[AUCT-014 | FE] 미낙찰 상품 처리 UI 구현`)
  / 스토리 `S15P11A108-103`[AUCT-014] 미낙찰 상품 복원 / 에픽 `S15P11A108-209`[AUCT]
- 브랜치: `feat/209-unsold-product-restore` (스토리 103, `origin/develop-FE` 기준 신규, 438 포함)

## 배경/목표

방송 종료 대시보드(438)의 **"남은 상품 처리" placeholder**를 실제 UI로 대체한다. 방송이 끝났을 때
낙찰되지 않은(미낙찰) 상품을 판매자가 **경매 다시 하기(`AUCTION`)** 또는 **상시 판매로 전환
(`DIRECT_SALE`)** 중 하나로 처리한다(AUCT-014 미낙찰 상품 복원). 실제 복원/재경매/판매방식 전환
API가 없어 **mock 처리**로 구현하고, 필요한 계약은 `docs/requests/BE/`에 요청한다.

## 기준 자료

- 방송 종료 대시보드 `LiveBroadcastEndDashboard.vue`(438, HS025) — `.broadcast-end__unsold` 섹션에
  미낙찰 상품 목록 + placeholder 버튼("남은 상품 처리하기")이 이미 있음. 이 섹션을 실제 처리 UI로 바꾼다.
- `saleType` enum: **`AUCTION` / `DIRECT_SALE`** (home·product·BE 006 공통). "상시 판매" = `DIRECT_SALE`.
- `SellerAuctionPanel.vue` 미낙찰(ENDED_FAILED) 상태의 "판매 방식 선택" placeholder(중복 개념 → 정합 정리).
- 사용자 결정([[auct-end-dashboard-leftover-disposition]]): 남은 상품을 경매 재시도 vs 상시 판매로 선택,
  다 팔렸으면 이 UI 없음(438에서 이미 미낙찰 없으면 섹션 숨김).
- BE: `POST /api/products/{id}/auction-schedule`(006, 재경매 후보) 존재. "미낙찰 복원/판매방식 전환"
  전용 계약은 없음.

## 작업 내용 (사용자 확정 플로우)

- **전부 낙찰**이면 대시보드만 보여주고 [라이브 목록으로].
- **미낙찰이 하나라도 있으면** 대시보드에 **[남은 상품 관리]** 버튼 → 방송 종료 페이지 안에서
  **"남은 상품 관리" 단계로 전환**(라우트 변경 없이 `endView` 전환).
- **남은 상품 관리 화면** — 미낙찰 상품마다 카드:
  - 등록된 상품 정보 표시(이미지·브랜드·상태·등록가). `GET /products/{id}`로 채우고, 조회 실패 시
    라이브 상품 데이터로 대체.
  - **[상시 판매로 전환]**: 가격 입력(등록가 기본값) → **가격을 넣어야 확정 가능** →
    `PATCH /products/{id}/status { price }`.
  - **[경매 예정]**: 입력 없이 바로 → `PATCH /products/{id}/auction-schedule`.
  - 처리되면 "처리 완료" 배지.
  - **모든 미낙찰 상품을 처리하면** 하단 [완료·라이브 목록으로] 활성.
- **API 연결(있는 것 다 연결)**: `getProductDetail`·`convertProductToDirectSale`·
  `scheduleProductAuction`(`productApi.ts`). 셋 다 상품 등록(publishProduct)과 동일 엔드포인트 →
  `publishProduct`도 이 함수를 재사용하도록 리팩터.
- 컴포넌트: `LiveUnsoldManage.vue`(관리 화면), `LiveUnsoldProductItem.vue`(상품 카드) 신규.

## API / mock 경계

- 미낙찰 처리에 필요한 API가 **전부 존재**해 실 API로 연결했다(006 §2 연동 완료). mock 처리 없음.
- **의미 확인 요청**: 경매 종료 상품에 `/status`·`/auction-schedule`를 그대로 호출해도 되는지, "복원"
  선행 단계가 필요한지 → `docs/requests/BE/014-unsold-product-disposition.md`.
- **등록 내용 전체 수정**(가격 외 필드) API는 없음 → 지금은 **가격만** 지정/수정. 필요 시 상품 수정 API
  요청(014에 명시).
- 미리보기/비로그인에서는 상품 API가 인증 필요라 실패 → 카드가 라이브 상품 데이터로 대체 표시(실제 처리
  성공은 로그인 상태에서).

## 구현하지 않는 범위

- 등록 상품 내용 **전체 편집**(제목·설명 등) — 상품 수정 API 없음(가격만 지정)
- `SellerAuctionPanel`의 방송 중 미낙찰(ENDED_FAILED) "판매 방식 선택" placeholder 정리(후속)
- STOMP 실시간, 미낙찰 외 상태 후처리

## 구현 목록

- [x] 대시보드 미낙찰 섹션 → [남은 상품 관리] 진입 버튼(`manage-unsold`), placeholder 제거
- [x] `LiveBroadcastPage` 종료 화면 단계 전환(`endView` 대시보드 ↔ 관리) + `unsoldProducts` 산출
- [x] `LiveUnsoldManage.vue`: 미낙찰 목록·진행률·전부 처리 시 [완료·목록으로] 활성
- [x] `LiveUnsoldProductItem.vue`: 등록 정보 표시 + [상시 판매 전환](가격 필수) / [경매 예정](입력 없이)
- [x] 상품 API 연결(`getProductDetail`·`convertProductToDirectSale`·`scheduleProductAuction`),
      `publishProduct` 리팩터로 재사용
- [x] BE 의미 확인·미보유(상품 수정) 요청 문서 `docs/requests/BE/014`
- [x] 변경/신규 파일 ESLint·`type-check`·`build-only` 통과
- [ ] 실행 화면에서 미낙찰 처리 흐름 사용자 확인(성공 처리는 로그인 필요)

## 확인 필요 (미결정)

- 경매 종료 상품에 `/status`·`/auction-schedule` 직접 호출 가능 여부 / "복원" 선행 필요 여부(014).
- 등록 내용 전체 수정은 상품 수정 API가 생기면 연결(지금은 가격만).

## Git / MR 단위

- 브랜치: `feat/209-unsold-product-restore`
- 커밋: `[S15P11A108-440] feat: 미낙찰 상품 처리 UI 구현` (작업 단위 한글)
- MR: 스토리 103 완료 시 `[AUCT] 미낙찰 상품 복원` → `develop-FE` (브랜치 다시 안 쓸 때 한 번)
- push는 사용자가 직접.
