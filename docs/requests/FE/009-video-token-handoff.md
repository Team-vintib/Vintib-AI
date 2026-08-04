# 영상 접속 토큰 인계 — Phase 4 (코드 완료 / 서버 대기)

- **요청 파트**: BE
- **대상 파트**: FE
- **관련 이슈**: `S15P11A108-449`(연동·토큰), `-448`(서버 구축, 정윤 진행 중)
- **상태**: 🟡 **API는 완성. 미디어 서버가 아직 없어 지금은 503이 온다**

---

## 1. 지금 상태를 먼저 알아야 한다

**API는 다 만들어졌고 스펙은 확정이다. 그런데 지금 호출하면 `503 L012`가 온다.**
OpenVidu 서버(`-448`)가 아직 구축 전이기 때문이다.

그래서 이렇게 진행하면 된다.

- **지금** — 응답 타입·어댑터·에러 분기를 이 문서 기준으로 확정해 둔다. 스펙은 바뀌지 않는다
- **서버가 올라간 뒤** — 같은 호출이 그대로 200을 준다. FE 코드 변경 없음

`503 L012`를 "아직 영상 준비 중"으로 표시하면 서버가 붙기 전까지도 화면이 자연스럽다.

## 2. 요청

```http
POST /api/lives/{liveId}/video-token
Authorization: Bearer {accessToken}   // 선택 — 없으면 시청자로 발급
```

**본문 없음.** 비회원도 호출할 수 있다.

## 3. 응답

```json
{
  "success": true,
  "data": {
    "roomName": "live-101-a3f9c1e2",
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "serverUrl": "wss://i15a108.p.ssafy.io",
    "role": "VIEWER",
    "expiresAt": "2026-08-01T22:00:00Z"
  },
  "error": null
}
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `roomName` | `String` | LiveKit room 이름. 방송마다 다르다 |
| `token` | `String` | 접속 토큰(JWT). 그대로 LiveKit 클라이언트에 넘긴다 |
| `serverUrl` | `String` | 미디어 서버 주소. **FE가 환경변수로 따로 관리하지 않아도 된다** |
| | | 운영은 `wss://i15a108.p.ssafy.io` — **서비스와 같은 도메인이다.** 서브도메인을 쓸 수 없어(호스트가 하나뿐) 시그널링을 `/rtc` 경로로 프록시한다. LiveKit 클라이언트가 알아서 붙이므로 FE는 이 값을 그대로 넘기면 된다 |
| `role` | enum | `PUBLISHER` / `VIEWER` |
| `expiresAt` | instant | 토큰 만료 시각(UTC) |

### `serverUrl`을 함께 내리는 이유

FE가 환경별 미디어 서버 주소를 따로 들고 있으면 배포 환경이 늘 때마다 BE 설정과 FE 빌드 변수
두 곳을 맞춰야 한다. 어긋나면 **"토큰은 유효한데 접속이 안 되는"** 형태로 드러나 원인 찾기가
어렵다. 토큰과 주소는 한 쌍으로 움직이므로 함께 준다.

## 4. ⚠️ 역할은 서버가 정한다 — 요청할 수 없다

**송출용/시청용 endpoint를 따로 두지 않았다.** 하나를 호출하면 서버가 판단한다.

| 호출자 | `role` | 권한 |
| --- | --- | --- |
| 방송 호스트 본인 | `PUBLISHER` | 발행 + 구독 |
| 그 외 회원 | `VIEWER` | **구독만** |
| 비회원 | `VIEWER` | **구독만** |

나누면 FE가 "나는 호스트니까 송출 토큰을 달라"고 요청하는 모양이 되는데, 그 판단은 서버가
해야 한다. **FE는 호스트 여부로 분기할 필요가 없다** — 받은 `role`을 보고 화면만 정하면 된다.

토큰이 새어 나가도 `VIEWER`로는 남의 방송에 영상을 밀어 넣을 수 없다.

## 5. 에러

| HTTP | 코드 | 상황 | FE 처리 제안 |
| --- | --- | --- | --- |
| 503 | `L012` | **영상 서버 미구성 (지금 상태)** | "영상 준비 중" 표시. 재시도 유도하지 않기 |
| 400 | `L013` | 진행 중(`LIVE`)인 방송이 아님 | 예약 방송은 대기 화면, 종료 방송은 다시보기 안내 |
| 404 | `L001` | 라이브 없음 | 목록으로 이동 |

**예정·종료 방송에는 토큰이 나오지 않는다.** 예정 방송은 아직 room이 없고, 종료된 방송은
정리된다. 시청 화면에서 `status === 'LIVE'`일 때만 호출해 달라.

## 6. 만료와 재발급

토큰 수명은 **기본 2시간**이다. 방송이 그보다 길어질 수 있다.

- `expiresAt` 전에 **같은 endpoint를 다시 호출**하면 새 토큰이 나온다. 재발급에 별도 제약 없음
- 재발급 시 `roomName`은 그대로다 — 재접속이 아니라 토큰만 갈아끼우면 된다
- 여유를 두고 갱신해 달라 (예: 만료 5분 전)

## 7. 같은 사람이 두 기기로 봐도 된다

LiveKit은 `identity`가 같은 참가자가 두 번 접속하면 **먼저 붙어 있던 쪽을 끊는다.**
그래서 서버가 이렇게 나눠 발급한다.

| 대상 | identity | 두 번 접속하면 |
| --- | --- | --- |
| 호스트 | `host-{memberId}` (고정) | **이전 송출이 교체된다** — 네트워크가 끊겼다 돌아왔을 때 유령 송출이 남지 않는다 |
| 시청자 | `viewer-{memberId}-{난수}` | 서로 끊지 않는다. 두 기기로 보는 것이 정상이다 |
| 비회원 | `guest-{난수}` | 위와 같음 |

## 8. 붙이는 순서

```ts
// 1) 방송이 진행 중일 때만
if (live.status !== 'LIVE') return;

// 2) 토큰 발급 (비회원도 그대로 호출)
const { token, serverUrl, roomName, role, expiresAt } = await issueVideoToken(liveId);

// 3) LiveKit 클라이언트 접속
const room = new Room();
await room.connect(serverUrl, token);

// 4) 호스트면 카메라·마이크 발행
if (role === 'PUBLISHER') {
  await room.localParticipant.enableCameraAndMicrophone();
}

// 5) 만료 전 재발급
scheduleRefresh(expiresAt);
```

클라이언트 라이브러리는 **`livekit-client`** 를 쓰면 된다. OpenVidu v3는 LiveKit 기반이라
LiveKit 표준 클라이언트가 그대로 동작한다.

## 9. 테스트 가이드

### 지금 (서버 없이) 확인할 수 있는 것

```bash
docker compose up -d postgres redis
```

```bash
cd BE && ./gradlew bootRun
```

1. **503이 오는지** — 진행 중인 라이브를 만들고 토큰을 요청한다

```bash
curl -X POST http://localhost:8080/api/lives/1/video-token
```

`{"error":{"code":"L012"}}`가 오면 정상이다. 서버 미구성 상태의 기대 동작이다.

2. **설정을 넣으면 200이 오는지** — 아무 값이나 넣어도 토큰은 만들어진다(로컬 서명이라서)

```bash
OPENVIDU_SERVER_URL=wss://localhost:7880 OPENVIDU_API_KEY=devkey OPENVIDU_API_SECRET=secret-that-is-long-enough ./gradlew bootRun
```

같은 호출이 `role`, `token`, `serverUrl`을 준다. **토큰 내용은 jwt.io에 붙여 확인할 수 있다** —
`video.room`, `video.canPublish`가 보인다.

3. **역할 분기** — 호스트 토큰으로 호출하면 `PUBLISHER`, 다른 회원/비회원이면 `VIEWER`

4. **상태 검증** — 예약 방송에 요청하면 `L013`

### 자동 테스트

```bash
cd BE && ./gradlew test --tests '*OpenViduClientTest' --tests '*LiveVideoControllerTest'
```

### 서버가 올라간 뒤 (`-448` 완료 후)

브라우저 두 개로 호스트/시청자를 띄워 실제 송수신을 확인한다. 이 단계는 아직 못 했다.

## 10. FE에서 확인 부탁

1. **`role`로 분기** — 호스트 여부를 FE가 판단하지 않기
2. `serverUrl`을 응답에서 쓰기 — 환경변수로 따로 두지 않기
3. `status === 'LIVE'`일 때만 토큰 요청
4. `503 L012`를 "영상 준비 중"으로 — 지금은 이 응답이 정상이다
5. `expiresAt` 기반 재발급 스케줄

바꿔야 할 부분이 있으면 이 문서에 이어서 적어 주시면 된다.
