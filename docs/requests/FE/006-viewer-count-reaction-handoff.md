# 시청자 수 · 반응 이모지 — 남은 FE 항목

- **요청 파트**: BE / **대상 파트**: FE
- **관련 이슈**: `S15P11A108-450`(시청자 수), `-471`(반응 이모지)
- **계약 전문**: `001-live-stomp-contract.md` 8·9번 절

## 반영 현황 (2026-08-04 확인)

- ✅ **시청자 수**: `viewerCount`가 non-null `int`로 반영, 초기값은 라이브 상세의 `currentViewerCount`(REST), 목록 카드 직접 표시, 화면 이탈 시 `unsubscribe`. (`LiveListCard.vue`, `LiveWatchPage.vue`, `LiveChatOverlay.vue`)
- ⏳ **반응 이모지**: 발행·구독은 연결됨. 아래 2건이 남았다.

## 남은 항목

1. **반응 `senderId` 자기 필터** — 발행자도 자기 반응을 브로드캐스트로 받는다. 지금 `LiveChatOverlay.vue`는 들어오는 모든 반응을 그리므로, 자기 반응을 낙관적으로 그린 뒤 브로드캐스트를 또 그리면 하나가 두 개로 보인다. `senderId === 내 회원 ID`인 프레임은 무시할 것.
2. **`L011`(반응 rate limit 초과)에 토스트를 띄우지 않기** — 현재 `/user/queue/errors`의 모든 에러를 토스트로 띄운다(`LiveChatOverlay.vue`). 하트 연타는 정상 사용이고, "너무 빠릅니다" 경고가 뜨면 사용자가 무엇을 잘못했는지 알 수 없다. `L011`만 조용히 무시(+버튼 쿨다운)할 것. 다른 에러 코드 처리는 그대로 둔다.

> 반응 payload·타입·rate limit 상세는 `001-live-stomp-contract.md` 9번 절 참고.
