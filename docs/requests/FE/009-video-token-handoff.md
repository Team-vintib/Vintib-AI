# 영상 접속 토큰 — 실제 LiveKit 연결 남음

- **요청 파트**: BE / **대상 파트**: FE
- **관련 이슈**: `S15P11A108-449`(연동·토큰), `-448`(서버 구축)

## 반영 현황 (2026-08-04 확인)

- ✅ **토큰 발급 연결**: `POST /api/lives/{liveId}/video-token` 호출, 인증 토큰 첨부, `status === 'LIVE'`일 때만 호출, 응답 `role` 기반 분기(호스트 판정 FE에서 안 함). (`liveControlApi.ts`, `LiveWatchPage.vue`, `LiveBroadcastPage.vue`)
- ⏳ **실제 영상 송수신 미구현**: 지금은 토큰을 받아 상태 라벨만 세팅하고 LiveKit `Room`에 접속하지 않는다. 아래가 남았다.

## 남은 항목

1. `livekit-client` 도입 후, 응답의 `serverUrl` + `token`으로 `Room.connect()`. **`serverUrl`은 응답값을 그대로 쓰고 환경변수로 따로 두지 않는다.**
2. `role === 'PUBLISHER'`면 카메라·마이크 발행, `VIEWER`면 구독만.
3. `503 L012`는 "영상 준비 중"으로 표시(재시도 유도 X) — 미디어 서버 미구성 시 정상 응답이다. 현재는 일반 "영상 토큰 발급 실패"로 처리한다.
4. `expiresAt` 기반 재발급 스케줄(예: 만료 5분 전, 같은 endpoint 재호출 → `roomName` 유지, 토큰만 교체).

## 참고 계약

### 요청
```http
POST /api/lives/{liveId}/video-token
Authorization: Bearer {accessToken}   // 선택 — 없으면 시청자로 발급
```
본문 없음. 비회원도 호출 가능.

### 응답
`{ roomName, token, serverUrl, role, expiresAt }`
- `serverUrl` — 미디어 서버 주소(운영 `wss://i15a108.p.ssafy.io`, `/rtc` 프록시). LiveKit 클라이언트가 알아서 붙인다.
- `role` — `PUBLISHER`(방송 호스트 본인) / `VIEWER`(그 외/비회원). **서버가 정한다.**

### 에러
| HTTP | 코드 | 상황 | 처리 |
| --- | --- | --- | --- |
| 503 | `L012` | 영상 서버 미구성 | "영상 준비 중" |
| 400 | `L013` | 진행 중(`LIVE`) 아님 | 예약=대기 화면, 종료=다시보기 안내 |
| 404 | `L001` | 라이브 없음 | 목록으로 이동 |

> 클라이언트 라이브러리는 `livekit-client`. OpenVidu v3는 LiveKit 기반이라 표준 클라이언트가 그대로 동작한다.
