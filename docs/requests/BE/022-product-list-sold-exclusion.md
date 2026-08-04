# 022 상품 목록에서 판매완료(SOLD) 상품 제외 여부 결정 요청

- **요청자 파트**: FE (김현수)
- **대상 파트**: BE
- **관련 이슈**: FE `S15P11A108-562` [LIVE-003] 라이브 낙찰 상품 목록 반영 확인
- **작성일**: 2026-08-04

## 배경 / 이유

"라이브에서 낙찰된 상품이 상품 목록에서 빠지는지" 확인하다가, 현재 정책상 **빠지지 않는** 것을 확인했다.

- `docs/plans/BE/SY007-product-list.md`: 목록은 `DRAFT`/`PRIVATE`만 제외하고, `SOLD`를 포함한 나머지 상태는 **"판매 방식과 무관하게 모두 포함"** 이라고 명시. → 낙찰(SOLD) 상품도 목록에 계속 노출.
- FE 상품 카드는 `saleStatus`를 쓰지 않아 목록에 **"판매완료" 표기도 없음** → SOLD 상품이 판매중 상품과 구분 없이 노출됨(상세로 들어가야 "판매 완료"가 보임).
- 참고: `docs/plans/BE/JY008-live-screen-complete.md` 기준 낙찰 → `SOLD` 전이(Phase 8)가 아직 미구현으로 보임("낙찰 확정 → SOLD 누락"). 이 전이가 채워지는 것도 전제.

## 요청 내용

상품 목록(`GET /api/products`)에서 판매완료(`SOLD`) 상품 노출 정책을 결정해 주세요. 택1:

1. **목록에서 `SOLD` 제외** (기본 응답에서 빼기) — FE 별도 처리 불필요.
2. **`SOLD` 유지 + 상태값을 목록 응답에 포함** → FE가 카드에 "판매완료" 뱃지 표시(제거가 아니라 표기).
3. **상태 필터 파라미터 제공**(예: `?status=` / `excludeSold`) → FE가 판단해 호출.

FE 기대(사용자 요청)는 "낙찰 상품은 목록에서 안 보이게"라 **1번**이 맞습니다. 정책상 남겨야 하는 이유가 있으면 2번으로 가겠습니다(그 경우 목록 응답에 `saleStatus`가 실려야 함).

추가로, **낙찰 확정 시 상품이 실제로 `SOLD`로 전이되는지(Phase 8) 확정 시점**도 알려주시면 FE 검증에 반영하겠습니다.

## 관련 자료

- `docs/plans/BE/SY007-product-list.md` (목록 공개 범위 — SOLD 포함 명시)
- `docs/plans/BE/JY008-live-screen-complete.md` (낙찰 → SOLD 전이, Phase 8)
- FE: `getProductList` (`FE/src/domains/product/api/productApi.ts`) — 현재 status 필터 미전송
