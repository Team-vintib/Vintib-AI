# 현재 소개 상품(NOW 배지) — 남은 FE 항목

- **요청 파트**: BE / **대상 파트**: FE
- **관련 이슈**: `S15P11A108-87` (LIVE-004)

## 반영 현황 (2026-08-04 확인)

- ✅ `currentProductId` 초기값(라이브 상세) + `/topic/lives/{id}/product` 구독으로 NOW 배지 이동, 호스트 `PATCH /api/lives/{liveId}/current-product`, `saleType`=`DIRECT_SALE`, `conditionGrade` 자유 문자열 — 모두 반영. (`LiveWatchPage.vue`, `LiveProductQueue.vue`, `liveControlApi.ts`, `liveWatchApi.ts`)
- ⏳ 아래 1건이 남았다.

## 남은 항목

- **삭제된 상품 표시**: 연결 후 판매자가 상품을 지우면 상품 관련 필드가 전부 `null`이 되고 연결 자체는 남는다. `productTitle`(FE `title`)이 `null`이면 "삭제된 상품"으로 표시할 것.
  - 현재 어댑터(`liveWatchApi.ts`)는 `title`을 non-null로 매핑하고, UI(`LiveProductQueue.vue`/`LiveSelectedProduct.vue`)에 삭제 상품 폴백이 없다.
