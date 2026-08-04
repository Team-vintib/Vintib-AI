# 라이브/경매 확정 계약 3건

**요청자 파트**: BE
**대상 파트**: FE

## 배경

`007-live-tryon-contract.md`(영상 토큰), `009-auction-chat-contract.md`(경매 조건 설정), `013-live-seller-control.md`(방송 종료)가 요청한 것 중 이미 구현된 3건을 정리한다.

## 1. 영상 접속 토큰 발급 — `POST /api/lives/{liveId}/video-token`

요청한 그대로지만 두 가지가 다르다:
- `role`은 body로 안 받는다. **서버가 호스트 여부로 직접 정한다**(본인 라이브면 `PUBLISHER`, 그 외/비회원이면 `VIEWER`).
- 응답 필드: `roomName`(요청한 `roomId` 대응), `token`, `serverUrl`(LiveKit wss 주소, 신규 — 환경별 서버 주소를 FE가 관리할 필요 없음), `role`(`PUBLISHER`/`VIEWER`), `expiresAt`.

## 2. 경매 생성·조건 설정(AUCT-001, 판매자) — `POST /api/lives/{liveId}/auctions`

Body `{ productId, startPrice, bidUnit, durationSeconds }` → 생성된 경매(`status: "READY"`) 반환.
- **생성/설정과 시작은 분리**로 확정 — 시작(`/start`)은 아직 미구현.
- `durationSeconds`: 초 단위 정수, 상한 없이 양수만(프리셋 강제 없음).
- `bidUnit`: 양수 자유 입력(프리셋 없음).

## 3. 방송 종료(호스트) — `PATCH /api/lives/{liveId}/status`

전용 엔드포인트(`POST .../end`) 대신 범용 상태 전이 API로 처리한다: body `{ "status": "ENDED" }`.
- 호스트 본인만 허용(아니면 403).
- 이미 종료·취소된 방송은 전이 자체가 막혀 400(멱등 아님 — 재요청 시 에러).
- **시청자 실시간 전파(STOMP)는 아직 없다** — 필요하면 별도 요청.

## 관련 자료

- Swagger: `/swagger-ui/index.html` — "라이브(Lives)", "경매(Auctions)" 태그

## 처리 결과

(FE 반영 후 기입)
