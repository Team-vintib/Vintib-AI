# [답변] 라이브 영상 송출/재생 미디어 서버 스펙

- 요청자 파트: BE (FE → BE 요청 "라이브 영상 송출/재생 미디어 서버 스펙 확인"에 대한 회신)
- 대상 파트: FE

## 요약

미디어 서버는 **LiveKit**(OpenVidu v3의 미디어 코어)이고, 운영 서버에 이미 배포·구성되어 있다.
FE는 `livekit-client` SDK만 붙이면 되고, **BE 쪽 추가 API나 스펙 변경은 필요 없다.**
`serverUrl`/`token`을 그대로 `Room.connect()`에 넘기면 된다.

단, 운영 서버 미디어 경로(공인 IP·UDP 포트)의 **실제 동작 검증은 BE가 아직 하지 않았다.**
FE 통합과 병행해 BE가 확인하겠다(아래 "BE 쪽 후속 작업" 참고).

---

## 1. 미디어 서버 종류와 FE가 쓸 SDK

**LiveKit이다.** OpenVidu v3가 LiveKit 기반이라 BE 코드·설정 이름은 `openvidu.*`로 남아 있지만,
실제로 뜨는 컨테이너와 프로토콜은 전부 LiveKit이다. **`openvidu-browser`는 쓰지 않는다.**

| 항목 | 값 |
| --- | --- |
| 미디어 서버 | `livekit/livekit-server:v1.9.1` (`docker-compose.yml`) |
| BE 서버 SDK | `io.livekit:livekit-server:0.14.0` (`BE/build.gradle:35`) |
| **FE 클라이언트 SDK** | **`livekit-client` 2.x** (`npm i livekit-client`) |

> OpenVidu v3 공식 번들(자체 Caddy·Redis·MinIO·대시보드 포함)은 443 포트 충돌과 메모리 예산 때문에
> 쓰지 않고 미디어 코어만 올렸다. 판단 근거는 `BE/docs/infra/ec2.md` "WebRTC 미디어 서버" 절.
> 클라이언트 SDK·room 개념은 OpenVidu v3와 동일하므로 `livekit-client`로 붙으면 된다.

최소 연결 코드는 아래와 같다. **`serverUrl`에 `/rtc`를 직접 붙이지 않는다** — SDK가 알아서 붙인다.

```ts
import { Room, RoomEvent, Track } from 'livekit-client';

const { roomName, token, serverUrl, role } = res.data; // POST /lives/{liveId}/video-token
const room = new Room({ adaptiveStream: true, dynacast: true });

room.on(RoomEvent.TrackSubscribed, (track) => {
  if (track.kind === Track.Kind.Video || track.kind === Track.Kind.Audio) {
    track.attach(videoEl);
  }
});

await room.connect(serverUrl, token);           // serverUrl 그대로
if (role === 'PUBLISHER') {
  await room.localParticipant.enableCameraAndMicrophone();
}
```

`roomName`은 참고용이다. 방 결정은 토큰 안의 grant로 이뤄지므로 `connect()`에 따로 넘기지 않는다.

## 2. 운영 배포 상태와 외부 접근

**배포되어 있다.** 구성은 다음과 같다.

```
브라우저 ──wss://i15a108.p.ssafy.io/rtc──▶ Caddy(443) ──▶ livekit:7880   (시그널링)
브라우저 ──────────UDP 7885 / TCP 7881──────────────────▶ livekit        (미디어, 직통)
백엔드   ──http://livekit:7880/twirp/*──────────────────▶ livekit        (room 관리)
```

- `serverUrl`은 운영에서 **`wss://i15a108.p.ssafy.io`** 로 내려간다
  (CI/CD 변수 `PROD_OPENVIDU_SERVER_URL` → `infra/ci/deploy.sh:114`).
  SSAFY가 호스트를 하나만 주기 때문에 서브도메인 대신 **같은 도메인의 `/rtc` 경로**로 나눴다.
  Caddy가 `/rtc`·`/rtc/*`·`/twirp/*`만 LiveKit으로 프록시한다(`infra/caddy/Caddyfile:23-26`).
- **미디어는 Caddy를 통과하지 않는다.** WebRTC 미디어는 HTTP가 아니라 브라우저↔서버 직통 UDP라
  리버스 프록시로 못 넘긴다. 그래서 `7885/udp`(미디어 mux)와 `7881/tcp`(UDP 차단 망 폴백)만
  호스트에 직접 발행한다(`docker-compose.prod.yml:95-97`). 방화벽에서 열려 있는 게 정상이다.
- **내장 TURN은 꺼져 있다.** 443/80을 요구해 Caddy와 충돌하기 때문이다. 대부분의 제한 망은
  TCP 7881 폴백으로 커버되지만, **443 외 모든 포트를 막는 극단적인 사내망에서는 연결이 실패한다.**
  시연 환경이 그런 망이면 미리 알려달라.

로컬 개발은 `docker compose up -d livekit`으로 띄우고 `serverUrl`이 `ws://localhost:7880`으로 내려온다
(7880/7885udp/7881 전부 호스트에 발행됨 — `docker-compose.override.yml:38-42`). 별도 설정은 없다.

## 3. room 자동 생성과 PUBLISHER 권한

**room은 자동 생성된다.** `livekit.yaml`의 `room.auto_create: true`이고, BE는 방송이 LIVE로 전환될 때
이름만 정해 둔다(`LiveVideoService.newRoomName`). **첫 참가자가 들어오는 순간 방이 생긴다** —
FE가 방을 미리 만들 필요도, 호스트가 먼저 들어와야 할 순서 제약도 없다.
(시청자가 먼저 들어오면 빈 방에 들어가 있다가 호스트 트랙이 올라오면 `TrackSubscribed`를 받는다.)

토큰 grant는 다음과 같다(`OpenViduClient.issueToken`).

| grant | PUBLISHER | VIEWER |
| --- | :---: | :---: |
| `roomJoin` / `roomName` | ✓ | ✓ |
| `canSubscribe` | ✓ | ✓ |
| `canPublish` (오디오·비디오) | ✓ | ✗ |
| `canPublishData` | ✓ | ✗ |

- **PUBLISHER는 오디오·비디오 publish 권한을 모두 가진다.** `canPublishSources`로 트랙 종류를
  제한하지 않았으므로 카메라·마이크·화면공유가 전부 허용된다.
- **VIEWER는 구독만 가능하다.** 토큰이 새어 나가도 남의 방송에 영상을 밀어 넣을 수 없다.
- **역할은 서버가 정한다.** 라이브의 호스트 본인이면 PUBLISHER, 그 외에는 VIEWER다.
  FE가 역할을 요청 파라미터로 고를 수 없다 — 그래서 송출용/시청용 엔드포인트를 나누지 않았다.

## 4. SFU 여부와 동시 시청 제한

**SFU가 맞다.** LiveKit은 SFU이므로 호스트는 업스트림을 **한 번만** 올리고 서버가 시청자 수만큼
복제해 내려보낸다. 시청자가 늘어도 호스트 업링크 부담은 늘지 않는다.

**동시 시청 인원 제한은 걸어두지 않았다.** `livekit.yaml`에 `max_participants`가 없고 BE에도 인원
체크가 없다. 다만 실질 한계는 있다.

- 단일 EC2 노드이고 LiveKit 컨테이너 `mem_limit: 1g`
- EC2 인스턴스 하나의 업링크 대역폭을 시청자 수가 그대로 나눠 쓴다
- FE에서 `adaptiveStream: true`, `dynacast: true`를 켜면 안 보이는 트랙 구독을 자동으로 줄여준다.
  **켜는 것을 권장한다.**

시연 규모(수십 명)에서는 문제없다. 특정 인원 상한이 정책적으로 필요하면 요청 주면 BE에서 건다.

## 5. `expiresAt` 만료와 재발급

**같은 엔드포인트를 다시 호출하면 된다. 횟수·간격 제약은 없다.** TTL은 기본 **2시간**(`OPENVIDU_TOKEN_TTL`).

다만 오해하기 쉬운 지점이 있다.

- **이미 연결된 세션은 `expiresAt`이 지나도 끊기지 않는다.** LiveKit 서버가 연결 중인 참가자에게
  주기적으로 갱신 토큰을 내려주고 SDK가 이를 재연결용으로 보관한다. 즉 2시간짜리 방송이라고
  FE가 타이머를 돌려 강제로 갱신할 필요는 없다.
- 재발급이 실제로 필요한 경우는 **새로 `connect()` 할 때**다. 발급받아 두고 오래 뒤에 붙거나,
  탭을 오래 방치했다가 재접속하는 경로에서 만료된 토큰을 쓰면 연결이 거부된다.
- 그래서 권장 흐름은 **"연결/재연결 직전에 항상 video-token을 새로 호출"** 이다.
  토큰을 스토어에 캐싱해 재사용하지 않는 편이 안전하다.

---

## FE 통합 시 반드시 알아야 할 것

1. **`roomName`을 캐싱하지 말 것.** 방송이 LIVE로 전환될 때마다 `live-{liveId}-{난수8자}` 형태로
   **새 이름이 배정된다.** 같은 방송을 껐다 다시 열면 이전 room과 섞이지 않도록 일부러 그렇게 했다.
   재접속 시 캐시된 room/token을 재사용하면 사라진 방에 붙으려 해 실패한다 — 항상 재호출.
2. **LIVE 상태에서만 발급된다.** 예정(SCHEDULED)·종료(ENDED) 방송에 호출하면 **400 (L013,
   `VIDEO_ROOM_NOT_READY`)** 이다. 라이브 상세의 `status`가 `LIVE`일 때만 호출하도록 가드를 둬야 한다.
3. **503 (L012)** 은 미디어 서버 미구성이라는 뜻이다. 로컬에서 livekit 컨테이너를 안 띄웠을 때 나온다.
4. **비회원도 발급 가능하다**(`permitAll`). 시청은 로그인 없이 열려 있다.
5. **호스트 identity는 `host-{memberId}`로 고정이다.** 같은 계정으로 송출 페이지를 두 개 열면
   **먼저 붙어 있던 쪽이 끊긴다.** 네트워크가 끊겼다 재접속했을 때 유령 송출이 남지 않게 한
   의도된 동작이다. 반대로 시청자 identity에는 난수가 붙어 다중 기기 시청이 정상 동작한다.
6. **채팅·시청자 수·반응은 지금처럼 STOMP(`/ws`)를 그대로 쓴다.** LiveKit DataChannel로 옮기지 말 것.
   VIEWER 토큰에 `canPublishData`를 열어두지 않은 이유이기도 하다.
7. 호스트가 잠깐 끊겨도 방은 60초(`departure_timeout`) 유지되고, 빈 방은 300초 뒤 자동 정리된다.
   즉 호스트 네트워크가 순간 끊겨도 시청자를 강제로 튕겨내지 않는다.

## BE 쪽 후속 작업 (BE가 진행)

FE 요청으로 스펙을 바꿀 것은 없고, **운영 환경 실검증**이 남아 있다.
FE가 SDK를 붙였는데도 화면이 검게 나온다면 아래가 원인일 가능성이 높으니, 통합 전에 BE가 먼저 확인한다.

- [ ] 운영 EC2에서 `vintib-livekit` 컨테이너가 실제로 떠 있고 **nodeIP가 공인 IP인지** 확인.
      사설 IP(`172.x`)면 브라우저가 미디어에 못 붙는데 **에러 없이 화면만 검게 나온다.**
- [ ] `PROD_OPENVIDU_SERVER_URL`이 정확히 `wss://i15a108.p.ssafy.io`인지 확인
      (`ws://`이거나 뒤에 `/rtc`가 붙어 있으면 FE 연결이 실패한다. `deploy.sh`는 비어 있는지만 검사한다).
- [ ] `infra/ec2/setup-udp-buffer.sh`·`setup-ufw-media.sh` 실행 여부 확인.
      UDP 버퍼가 작으면 시청자가 늘 때 영상이 끊기는데 애플리케이션 로그에는 아무것도 안 남는다.
- [ ] `curl -s "https://i15a108.p.ssafy.io/rtc/validate?access_token=<발급토큰>"` 이 성공하는지 확인.

검증이 끝나면 이 문서에 결과를 덧붙이거나 별도로 공유하겠다.
