# 미낙찰 상품 처리 — 유찰 상품의 내용 수정 제약

- **요청자 파트**: FE
- **대상 파트**: BE (서윤 — 상품 도메인)
- **관련 이슈**: FE `S15P11A108-440`(미낙찰 상품 처리), 스토리 `-103`[AUCT-014], 에픽 `-209`[AUCT]
- **관련 기능**: PROD-005(판매 방식), PROD 상품 수정

## 처리 완료 (2026-08-05, Phase 8)

원래 이 문서의 **확인 요청 2건은 모두 답변됐고 코드로 확정됐다.** 계약은
`docs/requests/FE/030-auction-close-contract.md` §4 참고.

- 유찰이면 상품은 **`AUCTION_SCHEDULED`로 되돌아간다** — 별도 "복원" 선행 처리가 필요 없고,
  FE가 이미 연결한 `PATCH /products/{id}/status`·`/auction-schedule`을 그대로 쓰면 된다.
- `PATCH /products/{id}/status { price }`가 상시 판매 전환이 맞다.
- ⚠️ **`AUCTION_FAILED` 상태는 존재하지 않는다**(`SY013`에서 제거). 상품 상태로 유찰 여부를
  판단하지 말 것 — 유찰 이력은 `auction` 테이블에 `status='FAILED'` row로 남는다.

## 남은 요청 — 유찰 상품은 내용 수정이 막혀 있다 (서윤 판단 필요)

문서에 "상품 전체 수정 API가 없다"고 적혀 있었으나 **`PATCH /api/products/{id}`는 존재한다.**
다만 Swagger 설명대로 **`DRAFT`/`ON_SALE` 상태에서만 수정할 수 있다.**

유찰된 상품은 `AUCTION_SCHEDULED`에 머물기 때문에, 미낙찰 관리 화면에서 제목·설명·사진 등을
고치려 하면 **400이 난다.** 판매자 입장에서는 "안 팔렸으니 설명을 고쳐 다시 걸자"가 자연스러운
흐름이라 이 제약이 걸린다.

선택지는 둘로 보인다 — 어느 쪽이든 서윤 판단이 필요하다.

1. `PATCH /api/products/{id}` 허용 상태에 `AUCTION_SCHEDULED`를 추가한다. 단 **경매가 진행 중일
   때는 여전히 막아야 한다**(`AUCTION_IN_PROGRESS`).
2. FE가 "수정하려면 먼저 상시 판매로 전환하세요"로 안내한다(추가 구현 없음).

시연 필수는 아니다.
