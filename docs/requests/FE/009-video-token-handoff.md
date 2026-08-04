# 009 영상 접속 토큰 — 실제 LiveKit 연결 남음

- **요청 파트**: BE / **대상 파트**: FE
- **관련 이슈**: `S15P11A108-449`(연동·토큰), `-448`(서버 구축)

> 토큰 발급 연결은 반영 완료되어 덜어냈다. 실제 영상 송수신(LiveKit `Room` 접속)이 남았다.

## 남은 항목

1. `livekit-client` 도입 후, 응답의 `serverUrl` + `token`으로 `Room.connect()`. **`serverUrl`은 응답값을 그대로** 쓰고 환경변수로 따로 두지 않는다.
2. `role === 'PUBLISHER'`면 카메라·마이크 발행, `VIEWER`면 구독만.
3. `503 L012`는 "영상 준비 중"으로 표시(재시도 유도 X). 현재는 일반 "영상 토큰 발급 실패"로 처리한다.
4. `expiresAt` 기반 재발급 스케줄(만료 5분 전 재호출 → `roomName` 유지, 토큰만 교체).

## 참고 계약

- `POST /api/lives/{liveId}/video-token` (본문 없음, 비회원도 호출 가능) → `{ roomName, token, serverUrl, role, expiresAt }`
- `serverUrl` 운영 `wss://i15a108.p.ssafy.io`(`/rtc` 프록시). `role`은 서버가 결정(PUBLISHER/VIEWER).
- 에러: 503 `L012`(영상 준비 중) / 400 `L013`(LIVE 아님) / 404 `L001`(없음).
- 라이브러리: `livekit-client`.
