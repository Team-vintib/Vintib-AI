# 실시간 라이브(WebRTC) + 채팅 구현 계획

- Jira 에픽: [S15P11A108-217](https://ssafy.atlassian.net/browse/S15P11A108-217) `[LIVE]`, [S15P11A108-208](https://ssafy.atlassian.net/browse/S15P11A108-208) `[CHAT]`, [S15P11A108-27](https://ssafy.atlassian.net/browse/S15P11A108-27) `[INFRA]`
- 갱신: 2026-07-30 (JY007 머지 직후 `develop-BE` `dd6a0b6` 기준 재확인)
- **AI 채팅 매니저(CHAT-002/003/004)는 보류.** 이 계획은 사람 간 채팅과 영상 송출까지만 다룬다.
- ⚠️ **이 문서는 [JY008](JY008-live-screen-complete.md)에 흡수됐다.** 라이브 화면 전체 계획은 JY008을 본다 — 여기는 Phase 1~4에 해당한다.
- 티켓은 전부 기존 것(-447~-454)을 쓴다. **새로 만들지 않는다.**

## 목표

**"방에 들어가서 영상을 보며 채팅할 수 있는 상태"** 까지.

## 현황 (2026-07-30 재확인)

REST 토대는 끝났다. 실시간 계층은 여전히 코드가 0이다.

| 항목 | 상태 |
| --- | --- |
| 라이브 REST (개설·목록·상세·상태 전이·편성·정리 훅) | ✅ 완료 — `dd6a0b6`까지 머지 |
| CORS / Swagger `bearerAuth` / MinIO | ✅ 완료 |
| `spring-boot-starter-websocket` 의존성 | ✅ 있음 (`websocket-test`도 있음) |
| **WebSocket 설정·핸들러** | ❌ 없음 — 코드 0 |
| **chat 패키지** | ❌ 없음 — `chat_message` 테이블만 확정 |
| **OpenVidu** | ❌ 코드 0, **서버도 미설치** — compose에 서비스 없음 |
| `live.openviduRoom` / `assignOpenviduRoom()` | 🟡 컬럼·메서드만 있고 호출부 없음 |
| `LiveCleanupHook` | 🟡 인터페이스 + 로깅 구현체만. room 해제 구현체 자리 비어 있음 |
| `viewerCount` (목록 응답) | 🟡 항상 `null` — FE에 통보 완료 |

메모리는 문제없다. EC2 15GiB에 OpenVidu 2.5GB 예산이 이미 잡혀 있다. **실질 제약은 4 vCPU** — 방송 중 배포·빌드 금지.

## 설계 판단 (착수 전 확정할 것)

### 1. OpenVidu v3 = LiveKit이라 순서를 바꿀 수 있다

OpenVidu v3는 LiveKit 기반이고, **접속 토큰은 API key/secret으로 로컬 서명한다 — 서버에 요청하지 않는다.** room도 첫 참가 시 자동 생성된다.

즉 **-449(연동·토큰 발급)의 코드 대부분은 -448(서버 구축) 없이 쓸 수 있다.** 서버는 "실제로 영상이 오가는지" 검증할 때만 필요하다. 계획에서 -448이 유일한 병목이었는데, 이 사실이 위험을 크게 줄인다.

> ⚠️ 이건 문서 기반 판단이다. -449 착수 시 LiveKit Java SDK로 **먼저 확인**하고, 서버 호출이 필요하면 -448을 앞으로 당긴다.

### 2. 시청자 수는 CONNECT가 아니라 SUBSCRIBE로 센다

티켓 -450 설명에는 `SessionConnectedEvent`/`SessionDisconnectEvent`로 적어 뒀는데 **그대로는 안 된다. CONNECT 프레임에는 liveId가 없다.** 어느 방송을 보는지는 `/topic/lives/{liveId}/...` 구독 시점에 처음 드러난다.

- `SessionSubscribeEvent` → `sessionId → liveId` 매핑 저장 + 카운트 증가
- `SessionUnsubscribeEvent` / `SessionDisconnectEvent` → 매핑으로 liveId를 찾아 감소
- **매핑을 안 남기면 연결이 끊길 때 어느 카운터를 내릴지 알 수 없다**

### 3. Redis 시청자 수는 기동 시 비운다

프로세스가 죽으면 WS 세션은 전부 끊기는데 Redis 값은 남는다. 그대로 두면 **아무도 안 보는 방송이 시청자 300명으로 표시된다.** 기동 시 `live:viewers:*` 키를 정리한다. 단일 인스턴스라 가능한 단순화다.

### 4. JWT는 STOMP CONNECT 프레임 헤더로 받는다

브라우저 WebSocket API는 **핸드셰이크 HTTP 요청에 `Authorization` 헤더를 붙일 수 없다.** 그래서 핸드셰이크가 아니라 STOMP CONNECT 프레임의 native header에서 토큰을 읽는다. FE 계약에 명시해야 하는 항목이다.

### 5. SockJS는 쓰지 않는다 (제안)

FE가 Vue 3 + 최신 브라우저 대상이라 fallback이 필요 없다. SockJS를 끼우면 URL·프레임 규약이 바뀌고 테스트도 복잡해진다. **plain WebSocket + STOMP로 간다.**

### 6. 토픽 네임스페이스는 경매까지 보고 잡는다

경매 실시간(AUCT-002 이후)이 같은 채널을 쓴다. 나중에 갈아엎지 않도록 지금 확정한다.

| 방향 | destination | 인증 |
| --- | --- | --- |
| 발행 | `/app/lives/{liveId}/chat` | 회원만 |
| 구독 | `/topic/lives/{liveId}/chat` | 비회원 허용 |
| 구독 | `/topic/lives/{liveId}/viewers` | 비회원 허용 |
| 구독 | `/topic/lives/{liveId}/auction` | (다음 단계 예약) |

### 7. 커서 페이징 키는 `id`

`chat_message.id`는 IDENTITY 증가라 삽입 순서와 정확히 일치한다. `created_at`은 같은 밀리초에 두 건이 들어오면 동률이 생겨 경계에서 메시지가 밀리거나 중복된다. **커서는 `id`로 잡는다.** 인덱스가 `(live_id, created_at DESC)`라 `(live_id, id DESC)` 인덱스 추가가 필요한지는 -453에서 실행계획으로 확인한다.

## 실행 순서

브랜치는 에픽 기준, 커밋은 작업 단위(기존 방식과 동일). **`develop-BE`에 직접 커밋하지 않는다.**

```
[병렬 A: 인프라]  -448 OpenVidu 서버 ─────────────────┐
                                                      ↓
[병렬 B: 코드]    -447 WS 기반 ──┬─→ -450 시청자 수    -449 토큰·연동
                                 │
                  -451 엔티티 ───┴─→ -452 송수신 ─┬─→ -454 테스트
                                     -453 과거조회 ┘
```

### Step 1 — `-447` WebSocket(STOMP) 기반 · 브랜치 `feat/27-websocket-base`

채팅만의 것이 아니다. 시청자 수와 다음 단계 경매 이벤트가 전부 이 위에 올라간다. **여기가 어긋나면 세 기능을 같이 고쳐야 한다.**

- [ ] `WebSocketConfig` — `@EnableWebSocketMessageBroker`, 엔드포인트 `/ws`, 앱 prefix `/app`, SimpleBroker `/topic`
- [ ] `setAllowedOriginPatterns` — HTTP CORS와 **별개**다. 안 하면 핸드셰이크에서 막힌다
- [ ] `StompAuthChannelInterceptor` — CONNECT 프레임의 `Authorization` native header 검증, principal에 `memberId` 주입. `JwtTokenProvider` 재사용
- [ ] **토큰이 없으면 익명으로 통과시킨다.** 비회원도 시청·채팅 읽기가 가능해야 한다. 토큰이 *잘못된* 경우만 거부
- [ ] `SecurityConfig` `PUBLIC_ENDPOINTS`에 `/ws/**`
- [ ] 테스트 — 유효 토큰 CONNECT 성공 / 토큰 없이 CONNECT 성공(익명) / 잘못된 토큰 거부

### Step 2 — `-451` `ChatMessage` 엔티티 · `-447`과 병렬 가능

- [ ] `chat` 패키지 스캐폴딩 (`.claude/skills/scaffold`)
- [ ] `ChatMessage` 엔티티 — `schema.sql`의 `chat_message` 그대로. `senderType` enum(`USER`/`SYSTEM`/`AI`)
- [ ] 정적 팩토리 `userMessage()` / `systemMessage()` — `@Builder`를 쓰면 "USER인데 작성자 없음" 같은 잘못된 조합이 만들어진다. DB `ck_chat_user_has_member`와 같은 규칙을 코드에서도 막는다
- [ ] `ChatMessageRepository`
- [ ] 엔티티 단위 테스트
- [ ] `BE/README.md` 디렉터리 구조에 `chat` 추가

### Step 3 — `-452` 실시간 채팅 송수신 · 선행 `-447`, `-451`

- [ ] `@MessageMapping("/lives/{liveId}/chat")` 핸들러
- [ ] 저장 → `/topic/lives/{liveId}/chat` 브로드캐스트
- [ ] **비회원 발언 차단** — principal 유무로 판정. DB CHECK는 최후 방어선일 뿐, 여기서 먼저 막는다
- [ ] **종료·취소된 방송 발언 차단** — `Live.isClosed()` 재사용 (JY007에서 만든 것)
- [ ] 메시지 길이 검증, 빈 문자열 거부
- [ ] STOMP 에러 응답 규약 — `/user/queue/errors`. REST의 `ApiResponse`와 다르므로 FE와 맞춰야 한다

### Step 4 — `-453` 과거 메시지 조회 API · 선행 `-451`

- [ ] `GET /api/lives/{liveId}/chat-messages` — `id` 커서 페이징(위 판단 7)
- [ ] **비회원 조회 허용** — `SecurityConfig` 공개 경로 추가
- [ ] 인덱스 실행계획 확인 후 필요하면 `(live_id, id DESC)` 추가
- [ ] Swagger 문서화 (`.claude/skills/swagger`)

### Step 5 — `-454` 채팅 테스트 · 선행 `-452`, `-453`

- [ ] STOMP 통합 테스트 — 구독자가 브로드캐스트를 받는지, 저장이 함께 되는지
- [ ] 권한 분기 — 회원 발언 성공 / 비회원 발언 차단 / 비회원 구독 허용
- [ ] 종료된 방송 발언 차단
- [ ] 과거 조회 커서 경계, 비회원 200

> Spring Boot 4 함정 (이미 두 번 밟음): 테스트 컨텍스트에 `ObjectMapper` 빈이 없다(JSON 직접 조립), `@AutoConfigureMockMvc` 사용 불가(`MockMvcBuilders.webAppContextSetup`).

### Step 6 — `-450` 실시간 시청자 수 · 선행 `-447`

- [ ] `SessionSubscribeEvent`/`SessionUnsubscribeEvent`/`SessionDisconnectEvent` 리스너 (위 판단 2)
- [ ] Redis 카운터 + `sessionId → liveId` 매핑
- [ ] 기동 시 stale 키 정리 (위 판단 3)
- [ ] 최대치 갱신 시에만 `live.peakViewerCount` 반영 — 매 접속마다 DB를 때리지 않는다
- [ ] `/topic/lives/{liveId}/viewers` 브로드캐스트
- [ ] `LiveListItemResponse.viewerCount` 실제 값 연결 + `LiveListSort.VIEWERS_DESC` 개방
- [ ] **FE 회신** — `.codex/requests/be/009-live-list-api-contract.md` 잔여 항목 해소 후 문서 삭제

### Step 7 — `-448` OpenVidu v3 서버 구축 · 코드와 병렬, 지금 착수

**유일하게 코드로 해결되지 않는 항목이다.** 리드타임이 있으니 Step 1과 동시에 시작한다.

- [ ] OpenVidu v3 설치 + `docker-compose` 반영 (메모리 2.5GB 예산 내)
- [ ] 미디어 UDP 포트 UFW 개방 (TURN 포함)
- [ ] Caddy 정합 — 기존 `infra/caddy/Caddyfile`에 미디어 라우팅 추가 또는 OpenVidu 내장 Caddy로 일원화
- [ ] API key/secret을 GitLab CI/CD Variables로 (**레포 커밋 금지**)
- [ ] `BE/docs/infra/ec2.md` 갱신

### Step 8 — `-449` OpenVidu 연동·토큰 발급 · 선행 `-448`(검증 단계만)

- [ ] LiveKit Java SDK 의존성 추가 후 **판단 1을 먼저 검증** — 토큰 발급에 서버가 필요한가
- [ ] `OpenViduClient` — 기존 `AiClient`(Spring → FastAPI) 패턴대로 `global/client`에 배치
- [ ] 방송 시작(`SCHEDULED → LIVE`) 시 room 이름 생성 → `Live.assignOpenviduRoom()` 호출. **메서드는 이미 있고 부르는 곳만 없다**
- [ ] 호스트 송출 토큰 / 시청자 구독 토큰 발급 API. **시청 토큰은 비회원도 받을 수 있어야 한다**(LIVE-005 비회원 공개)
- [ ] 종료 시 room 정리 — `LiveCleanupHook` 구현체로 등록. **종료 로직 자체는 다시 열지 않는다**
- [ ] 실제 브라우저 2개로 영상 송수신 확인

### Step 9 — FE 계약 문서 (Step 3 직후)

FE 티켓 -423(채팅·경매 패널 UI)·-432가 이 계약 없이는 못 움직인다. **-452 완료 시점에 바로 낸다.**

- [ ] `.claude/requests/fe/`에 STOMP 계약 문서 — 엔드포인트 `/ws`, destination 표(판단 6), CONNECT 헤더 인증 방식(판단 4), 메시지 payload, 에러 규약, 비회원 제약

## 남은 미결정

1. **-448을 언제 착수하나.** 이 계획에서 유일한 외부 의존이다. 막히면 Step 1~6(채팅·시청자 수)을 먼저 끝낸다 — 영상에 의존하지 않는다.
2. **경매 실시간(AUCT-002 이후)은 이 계획 밖.** 입찰 동시성의 Redis 분산락 설계가 미확정이라 착수 전 사용자 확인이 필요하다(`BE/CLAUDE.md` 규칙).
3. **AI 채팅 매니저 보류.** 재개 시 "답변 전달 폴링→푸시", "답변 노출 화자", "비매너 판정 동기 차단 vs 비동기 숨김" 세 가지를 정해야 한다.

## 공통 규율

- [ ] 각 단계마다 `.claude/skills/BE:verify` 통과 후 커밋 — **빈 DB로도 한 번 돌린다**(CI 실패 재발 방지)
- [ ] 새 엔드포인트는 Swagger 어노테이션 동반
- [ ] push는 사용자가 직접