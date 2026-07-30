# 실시간 라이브(WebRTC) + 채팅 착수 계획

- Jira 에픽: [S15P11A108-217](https://ssafy.atlassian.net/browse/S15P11A108-217) `[LIVE]`, [S15P11A108-208](https://ssafy.atlassian.net/browse/S15P11A108-208) `[CHAT]`
- 선행: JY005(라이브 도메인 REST) — 오늘 -388~-392로 마무리
- **AI 채팅 매니저(CHAT-002/003/004)는 보류** (사용자 지시 2026-07-28). 이 계획은 사람 간 채팅과 영상 송출까지만 다룬다.

## 배경/목표

JY005로 "방을 만들고·조회하고·상태를 바꾸고·경매 조건을 거는" REST 토대가 끝난다. 하지만 **실시간 계층은 코드가 한 줄도 없다.** 방송 영상도, 채팅도, 경매 이벤트도 전부 그 위에 올라간다.

목표는 **"방에 들어가서 영상을 보며 채팅할 수 있는 상태"** 까지다.

## 최신 develop-BE 기준 현황 (2026-07-28 확인)

지난 점검 이후 서윤 쪽 작업으로 두 가지가 해소됐다.

| 항목 | 상태 |
| --- | --- |
| CORS | ✅ 해결 — `SecurityConfig`에 `CorsConfigurationSource` 빈 추가, 허용 오리진은 설정값 주입 |
| Swagger `Authorize` 버튼 | ✅ 해결 — `SwaggerConfig`에 `bearerAuth` SecurityScheme 추가(-311) |
| 파일 스토리지 | ✅ MinIO 도입 — 라이브 썸네일 업로드에 재사용 가능 |
| **WebSocket 설정** | ❌ 없음 — starter 의존성만 있고 config·핸들러·엔드포인트 전무 |
| **OpenVidu** | ❌ 없음 — 의존성·클라이언트·설정 전무. **서버도 미설치**(compose에 없음, Caddyfile·ec2.md에 "2주차에 붙인다" 메모만) |
| **chat 패키지** | ❌ 없음 — ERD `chat_message` 테이블은 확정, 코드는 0 |

**CORS가 풀린 것이 큰 변화다.** 지난 점검에서 이게 WebSocket 핸드셰이크까지 막는 선행 과제였는데 해소됐다. 다만 STOMP 엔드포인트는 `setAllowedOriginPatterns`를 따로 지정해야 하므로 그대로 통과되지는 않는다.

## 착수 전 필요한 작업

### 1. WebSocket 기반 (최우선 — 채팅·경매 공통 토대)

채팅만의 것이 아니다. 다음 주 경매 실시간 이벤트(현재가·최고입찰자·5초 연장)도 같은 채널을 쓴다. 여기를 먼저 세워야 두 기능이 갈라지지 않는다.

- `WebSocketConfig` — `@EnableWebSocketMessageBroker`, STOMP 엔드포인트 `/ws`, 브로커 `/topic`, 앱 prefix `/app`
- **핸드셰이크 JWT 인증** — `ChannelInterceptor`로 CONNECT 프레임의 `Authorization` 헤더를 검증해 principal에 `memberId`를 심는다. 기존 `JwtTokenProvider` 재사용
- `SecurityConfig` `PUBLIC_ENDPOINTS`에 `/ws/**` 추가 — **비회원도 시청·채팅 읽기가 가능**해야 하므로 핸드셰이크 자체는 열고, 발언 시점에 principal 유무로 막는다
- STOMP 엔드포인트에 `setAllowedOriginPatterns` 설정(HTTP CORS와 별개)

### 2. OpenVidu v3 — 인프라가 먼저다

**코드보다 서버가 없는 것이 문제다.** compose에 서비스가 없고 UFW·Caddy 정합도 안 돼 있다. 리드타임이 있으므로 **가장 먼저 착수**하되 코드 작업과 병렬로 굴린다.

- EC2에 OpenVidu v3 설치 + 미디어 UDP 포트 UFW 개방 + Caddy 정합(또는 OpenVidu 내장 Caddy로 일원화)
- `OpenViduClient` — 기존 `AiClient`(Spring → FastAPI) 패턴을 따라 `global/client`에 둔다
- 방송 시작 시 room 생성 → `live.openviduRoom` 저장 (컬럼은 이미 있고 채우는 코드만 없다)
- 호스트/시청자 토큰 발급 API
- 종료 시 room 정리 → **-391에서 만든 정리 훅에 구현체로 끼운다**

### 3. 채팅 (CHAT-001, 사람 간 채팅만)

- `chat` 패키지 + `ChatMessage` 엔티티·리포지토리 (ERD `chat_message` 그대로)
- STOMP 송수신 — 발행 `/app/lives/{liveId}/chat`, 구독 `/topic/lives/{liveId}/chat`
- 과거 메시지 조회 REST — `ix_chat_live_created (live_id, created_at DESC)` 인덱스에 맞춰 커서 페이징
- 발언 권한 — 회원만. ERD `ck_chat_user_has_member`가 DB에서도 막는다

### 4. 시청자 수 (LIVE-005 보완)

- WS 세션 연결/해제 이벤트로 현재 시청자 수 집계 → Redis
- 최대치 갱신 시 `live.peakViewerCount` 반영

## 확정 결정 (2026-07-28)

- **메시지 브로커는 Spring 내장 SimpleBroker.** 백엔드 1대라 Redis Pub/Sub의 이득이 없다. 교체 지점은 `WebSocketConfig` 한 곳.
- **새 티켓은 스프린트에 넣지 않는다** — 진행 중인 Sprint 3에 추가 금지. 전부 백로그로 생성했다.
- **작업의 parent는 에픽, 스토리는 Relates 링크** (기존 -388 패턴과 동일. 하위작업 미사용).

## 구현 목록

### Phase 0 — 오늘 (JY005 잔여, Sprint 3)

| 작업 | 내용 | SP |
| --- | --- | --- |
| [-388](https://ssafy.atlassian.net/browse/S15P11A108-388) | 시청 조회 API | 3 |
| [-389](https://ssafy.atlassian.net/browse/S15P11A108-389) | 시청 조회 테스트 | 1 |
| [-390](https://ssafy.atlassian.net/browse/S15P11A108-390) | 상태 전이 API·서비스 | 5 |
| [-391](https://ssafy.atlassian.net/browse/S15P11A108-391) | 종료 시 정리 훅 | 1 |
| [-392](https://ssafy.atlassian.net/browse/S15P11A108-392) | 상태 전이 테스트 | 1 |

브랜치 `feat/217-live-state-view` 하나에 커밋 5개. 순서는 -390 → -391 → -392 → -388 → -389 (시청 조회가 상태 전이 결과를 응답에 담으므로 뒤).

### Phase 1 — 실시간 기반 (백로그)

| 작업 | 내용 | SP | 연결 |
| --- | --- | --- | --- |
| [-447](https://ssafy.atlassian.net/browse/S15P11A108-447) | WebSocket(STOMP) 기반 구성 및 핸드셰이크 인증 | 3 | 에픽 -27 직속 |
| [-448](https://ssafy.atlassian.net/browse/S15P11A108-448) | OpenVidu v3 미디어 서버 구축 (EC2) | 3 | 에픽 -27 직속 |

**-448은 서버 작업이라 리드타임이 있다. 가장 먼저 착수한다.** 코드 작업(-447 이후)과 병렬로 굴린다.

### Phase 2 — 채팅 (백로그, CHAT-001 `-91`)

| 작업 | 내용 | SP |
| --- | --- | --- |
| [-451](https://ssafy.atlassian.net/browse/S15P11A108-451) | chat 패키지·ChatMessage 엔티티 | 2 |
| [-452](https://ssafy.atlassian.net/browse/S15P11A108-452) | 실시간 채팅 송수신 (STOMP) | 5 |
| [-453](https://ssafy.atlassian.net/browse/S15P11A108-453) | 과거 메시지 조회 API | 3 |
| [-454](https://ssafy.atlassian.net/browse/S15P11A108-454) | 실시간 채팅 테스트 | 3 |

-451은 선행 의존이 없어 -447과 병렬 가능하다.

### Phase 3 — 영상 송출 (백로그, LIVE-005 `-88`)

| 작업 | 내용 | SP |
| --- | --- | --- |
| [-449](https://ssafy.atlassian.net/browse/S15P11A108-449) | OpenVidu 연동 및 송출·시청 토큰 발급 | 5 |
| [-450](https://ssafy.atlassian.net/browse/S15P11A108-450) | 실시간 시청자 수 집계 | 3 |

-449는 -448(서버) + -390/-391(상태 전이·정리 훅)에 의존한다. -450은 -447에 의존한다.

### 의존 관계 요약

```
-448 (미디어 서버) ─────────────┐
                                ├─→ -449 (OpenVidu 연동)
Phase 0 -390/-391 (상태·훅) ────┘

-447 (WS 기반) ──┬─→ -452 (채팅 송수신) ─┬─→ -454 (채팅 테스트)
                 └─→ -450 (시청자 수)     │
-451 (엔티티) ───┴─→ -453 (과거 조회) ────┘
```

### 공통
- [x] Jira 티켓 신규 생성 — 8건(-447~-454), 전부 백로그
- [ ] 각 단계 BE 검증 하네스 통과 후 커밋
- [ ] `BE/README.md` 디렉터리 구조 갱신 (`chat` 패키지 추가 시)

## 확인이 필요한 미결정 사항

1. **OpenVidu v3 서버를 언제 누가 올리나** — 이 계획에서 유일하게 코드로 해결되지 않는 항목이다. 미설치 상태라 착수 시점을 먼저 잡아야 한다. 막히면 Phase 2(채팅)를 먼저 끝내고 영상은 뒤로 미룬다.
2. ~~Redis Pub/Sub을 쓸지~~ — **SimpleBroker로 확정**(2026-07-28). 로드맵에는 Redis Pub/Sub이 적혀 있으나 단일 인스턴스에서 이득이 없어 뒤집었다. 확장 필요 시 `WebSocketConfig` 한 곳만 교체한다.
3. **경매 실시간(AUCT-002 이후)은 이 계획 밖** — 입찰 동시성의 Redis 분산락 설계가 미확정이라 착수 전 별도 확인이 필요하다(BE/CLAUDE.md 규칙).
4. **AI 채팅 매니저 보류** — AI팀(-183·-192·-196·-197)은 완료 상태로 BE 협의를 기다리고 있다. 재개 시 "답변 전달 폴링→푸시", "답변 노출 화자", "비매너 판정 동기 차단 vs 비동기 숨김" 세 가지를 정해야 한다.