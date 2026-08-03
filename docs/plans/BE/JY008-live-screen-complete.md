# 라이브 시청 화면 전체 기능 개발 계획 (AI 시착 제외)

- 작성: 2026-07-30. 기준 `develop-BE` `dd6a0b6`
- 근거 문서: FE `012-live-watch-detail-contract-gaps.md`, `.codex/requests/be/009-live-list-api-contract.md`
- 에픽: [-217](https://ssafy.atlassian.net/browse/S15P11A108-217) `[LIVE]`, [-208](https://ssafy.atlassian.net/browse/S15P11A108-208) `[CHAT]`, [-209](https://ssafy.atlassian.net/browse/S15P11A108-209) `[AUCT]`, [-27](https://ssafy.atlassian.net/browse/S15P11A108-27) `[INFRA]`
- **JY006(실시간 라이브+채팅)을 흡수한다.** JY006은 이 문서의 Phase 1~4에 해당한다.
- 범위 제외: AI 시착(TRYON), AI 채팅 매니저(CHAT-002/003/004), 다시보기 타임라인(LIVE-008), STT(LIVE-007)

## 목표

FE Figma 라이브 시청 화면이 **mock 없이 전부 실제 API로 동작**하는 상태.

## 정윤 결정 (2026-07-30)

1. **입찰 동시성 = DB 비관적 락.** MQ·Redis 분산락 검토 결과는 아래 "설계 판단 1"에 남긴다.
2. **-448(OpenVidu 서버 구축)은 정윤이 직접 수행** — 에이전트가 인프라를 건드리지 않는다.
   라이브·채팅·경매 기능 구현도 전부 정윤 담당이다.
3. **반응 이모지는 실시간 기능이되 저장하지 않는다.**
4. **서윤 담당 영역(상품 구조화 필드, 팔로우 API)은 요청 문서로 넘긴다.**
5. **기존 스토리에 BE 작업 티켓을 새로 만든다.** 스프린트에는 넣지 않고 백로그.
6. **경매는 호스트가 버튼으로 시작한다.** 상품 전환과 분리 — 상품을 바꿔도 경매가 자동 시작되지 않는다.
7. **입찰 취소는 없다.** 누르면 낙찰 시 구매 의무가 확정된다.
8. **포인트는 서윤 미구현.** 완료 후 Phase 9에서 붙인다.

## 설계 판단

### 1. 입찰 동시성 — MQ를 검토했고 쓰지 않는다

정윤 요청으로 RabbitMQ·Kafka 같은 대규모 트래픽 기술을 실제로 따져봤다. **이점은 분명히 있지만 우리 조건에서는 손해가 크다.**

MQ가 주는 것 — `auctionId`로 파티셔닝하면 경매별 처리가 단일 소비자로 직렬화되어 **락 경합 자체가 사라진다.** 종료 직전 입찰 폭주도 큐가 흡수한다. 이건 실제 이점이고 대규모 경매 시스템이 실제로 쓰는 패턴이다.

그런데 우리 조건에서 대가가 이렇다.

| 대가 | 내용 |
| --- | --- |
| **응답이 비동기가 된다** | 가장 큰 문제. 입찰은 "내 입찰이 됐는지"를 즉시 알아야 한다. MQ를 끼우면 REST가 `202 Accepted`를 주고 결과는 STOMP로 따로 오므로, FE가 client message ID·결과 대기 UI·타임아웃까지 다뤄야 한다. **FE 요청서도 "입찰 → 성공 snapshot" 동기 응답을 기대하고 있다** |
| **메모리** | Kafka(KRaft) 1~2GB, RabbitMQ ~500MB. 현재 예산이 Spring 3 + PG 2 + Redis 1 + OpenVidu 2.5 + FastAPI 1 = 9.5GB / 15GB에 러너 3GB 버스트. OpenVidu가 아직 안 올라간 상태에서 MQ까지 넣으면 예산이 넘는다 |
| **유실·중복 처리** | 큐가 죽으면 입찰이 사라진다. at-least-once면 멱등키가 필요하다. 남은 일정에서 이건 새 실패 지점이다 |
| **아키텍처 확정과 충돌** | 루트 문서에 단일 EC2·no Kafka로 확정돼 있다 |

**결정적인 이유는 트랜잭션 경계다.** 입찰은 `bid` 삽입 + `auction.current_price` 갱신 + **포인트 보류**가 한 원자 단위여야 한다(`erd.md` §4). MQ든 Redis 락이든 DB 트랜잭션 밖에 있어서 "락은 풀렸는데 커밋은 안 된" 창이 생긴다. **DB 행 락은 트랜잭션과 생명주기가 같아서 그 창이 원리적으로 없다.**

게다가 스키마가 이미 안전망을 깔아뒀다.

```sql
CREATE UNIQUE INDEX ux_bid_auction_price ON bid (auction_id, bid_price);
CREATE UNIQUE INDEX ux_auction_live_running ON auction (live_id) WHERE status = 'RUNNING';
```

**같은 가격 단계는 DB가 두 번 성립시키지 않는다.** 락이 뭐가 됐든 최종 정합성은 여기서 보장된다. 그러면 락의 역할은 "`current_price`를 읽고 고치는 구간 직렬화"로 좁아지고, 그건 행 락이 가장 싸게 해결한다.

- 채택: `@Lock(PESSIMISTIC_WRITE)`로 경매 행을 잠그고, 판정·`bid` 삽입·가격 갱신·포인트 보류를 한 트랜잭션에서 처리
- **Redis는 락이 아니라 휘발성 카운터에만 쓴다** — 연속 입찰 제한, rate limit, 시청자 수
- `schema.sql`·`erd.md`의 "Redis 분산락이 1차 방어" 주석을 이 결정으로 정정한다
- **MQ가 정당해지는 지점을 명시해 둔다** — 실측 락 대기가 문제가 되거나 인스턴스를 늘릴 때. 교체 지점은 `AuctionBidService` 한 곳

### 2. 브로드캐스트는 반드시 커밋 후에

입찰 성공을 커밋 전에 쏘면 롤백 시 **유령 입찰이 모든 시청자 화면에 남는다.** `@TransactionalEventListener(phase = AFTER_COMMIT)`로 발행한다. 경매·채팅·큐레이션 전부 같은 규칙.

### 3. 경매 종료·자동 연장은 단일 스케줄러 폴링

`@Scheduled(fixedDelay = 1s)`로 `RUNNING` 경매만 훑어 `scheduled_end_at`이 지난 것을 마감한다. 스키마에 이미 `ix_auction_status ON auction (status) WHERE status = 'RUNNING'` 부분 인덱스가 있다 — **이 방식을 예상하고 만든 인덱스다.** 단일 인스턴스라 중복 실행 걱정이 없다.

자동 연장(AUCT-010)은 입찰 트랜잭션 안에서 처리한다. 종료 임박 입찰이면 `scheduled_end_at`을 밀고 `extension_count`를 올린다.

### 4. 현재 소개 상품은 `live`에 컬럼을 둔다

JY007에서 카테고리는 "편성 상품에서 유도"로 갔는데 **여기는 반대로 저장한다.** 카테고리는 편성 상품에서 계산할 근거가 있었지만, "지금 소개 중"은 **호스트의 현재 의도라 파생할 근거가 없다.**

- `live.current_product_id` (nullable, FK) 추가
- 편성된 상품이어야 한다 — `live_product`에 있는지 검증
- 방송 종료 시 `null`
- 전환 이력이 필요해지면(LIVE-008 다시보기) 그때 별도 이력 테이블을 만든다. `shown_at` 한 컬럼으로 현재와 이력을 겸하려 하면 상품을 되돌아갈 때 둘 다 깨진다

### 5. 경매 snapshot은 라이브 상세에 넣지 않는다

FE는 "라이브 상세에 현재 경매 ID 포함" 또는 "별도 snapshot API" 중 하나를 요청했다. **별도 endpoint로 간다.**

라이브 상세는 제목·호스트·편성 상품처럼 거의 안 바뀌는 값이고, 경매는 초 단위로 바뀐다. 섞으면 상세 응답을 캐시할 수도, 폴링 주기를 따로 잡을 수도 없다.

- `GET /api/lives/{liveId}/auctions/current` — 진행 중 경매 snapshot. 없으면 200 + `null`
- REST snapshot과 STOMP 이벤트는 **같은 enum·같은 필드명**을 쓴다 (FE 요청사항)

### 6. STOMP destination 최종 확정

| 방향 | destination | 인증 |
| --- | --- | --- |
| 발행 | `/app/lives/{liveId}/chat` | 회원만 |
| 발행 | `/app/lives/{liveId}/reactions` | 회원만 |
| 구독 | `/topic/lives/{liveId}/chat` | 비회원 허용 |
| 구독 | `/topic/lives/{liveId}/reactions` | 비회원 허용 |
| 구독 | `/topic/lives/{liveId}/viewers` | 비회원 허용 |
| 구독 | `/topic/lives/{liveId}/auction` | 비회원 허용 |
| 구독 | `/topic/lives/{liveId}/product` | 비회원 허용 (현재 소개 상품 전환) |
| 에러 | `/user/queue/errors` | — |

- 입찰은 **STOMP가 아니라 REST**(`POST`)로 받는다. 동기 응답이 필요하고 트랜잭션·인증이 REST에서 훨씬 단순하다. 결과 전파만 STOMP
- JWT는 **STOMP CONNECT 프레임 native header**로 받는다 — 브라우저는 WS 핸드셰이크에 `Authorization`을 붙일 수 없다
- SockJS 미사용 (plain WebSocket)

### 7. 시청자 수는 SUBSCRIBE로 센다

CONNECT 프레임에는 `liveId`가 없다. 어느 방송인지는 구독 시점에 드러난다.

- `SessionSubscribeEvent` → `sessionId → liveId` 매핑 저장 + 증가
- `SessionUnsubscribeEvent`/`SessionDisconnectEvent` → 매핑으로 찾아 감소
- **기동 시 `live:viewers:*` 정리** — 프로세스가 죽으면 세션은 끊기는데 Redis 값은 남아 "아무도 없는 방송에 300명"이 된다

### 8. 반응 이모지는 저장하지 않는다

허용 종류를 enum으로 고정하고(`HEART`, `FIRE`, `CLAP`, `WOW`), 회원당 rate limit을 Redis로 걸고 그대로 브로드캐스트한다. 초당 수십 건이 들어와도 DB 부하가 0이다.

### 9. 포인트 보류는 서윤 의존 — 입찰을 먼저 열고 나중에 붙인다

`point_account`·`point_transaction`·`point_hold` 테이블은 있는데 **`point` 패키지 코드가 없다.** 서윤 담당이고 스키마 주석에도 "입찰 트랜잭션의 핵심 의존"으로 적혀 있다.

- Phase 7(입찰)은 **포인트 보류 없이** 먼저 완성한다 — 입찰 판정·현재가·최고 입찰자·실시간 전파까지
- Phase 9(AUCT-007~009)에서 포인트를 붙인다. **서윤 포인트 도메인 완료가 선행**이다
- 그 전까지 잔액 검증이 없어 무한 입찰이 가능하다. **시연 전에는 반드시 닫아야 하는 구멍이라 문서에 명시하고 FE에도 알린다**

### 10. 상품 판매 상태 전이 — 경매가 `product.sale_status`를 움직인다

정윤이 2026-07-30에 확정한 정책이다.

- 라이브에서 **팔리면** → `SOLD`
- **안 팔리면** → 경매 예정 상태를 유지하고, 방송이 끝난 뒤 판매자가 둘 중 고른다
  - 그대로 두고 나중에 또 경매 (가격 없이 목록에 노출)
  - `ON_SALE`로 전환해 가격을 정하고 상시 판매

**`AUCTION_FAILED` 중간 상태는 유지한다.** 한때 없애기로 했다가 되돌렸다 — **서윤이 그 상태를 전제로 한 유찰 처리 API를 이미 머지해 뒀다**(`ProductService.resolveAuctionFailure`). 상태를 없애면 그 메서드가 도달 불가능한 상태를 검사하는 죽은 코드가 된다.

서윤 구현이 정윤 정책과 정확히 일치한다. `ProductAuctionResultRequest.NextStatus`가 `{ON_SALE, AUCTION_SCHEDULED}` 딱 둘이다.

```
경매 예정 등록  →  AUCTION_SCHEDULED   (서윤 `Product.scheduleAuction()`)
경매 시작       →  AUCTION_IN_PROGRESS
   ├ 낙찰       →  SOLD
   └ 유찰       →  AUCTION_FAILED  ─┬→ AUCTION_SCHEDULED (다시 경매, 가격 없음)
                                    └→ ON_SALE          (가격 정하고 상시 판매)
```

상태를 유지하면 **FE `-440`(미낙찰 상품 처리 UI)이 상태만으로 목록을 뽑을 수 있다**는 이점도 그대로 남는다.

> `PRIVATE` 상태는 서윤이 제거했다. `PROD-005`의 "비공개" 선택지도 함께 빠져 선택은 두 갈래뿐이다.

### 11. 이 정책 때문에 드러난 누락 5건

정책을 코드와 맞춰보니 **이미 머지된 것 하나를 포함해** 빠진 곳이 있었다.

| 지점 | 문제 | 처리 |
| --- | --- | --- |
| `AUCTION_SCHEDULED` 진입 | ~~어디서도 설정하지 않았다~~ | **서윤이 해결** — `Product.scheduleAuction()` + `POST` 경매 상품 등록(`-237`) |
| `-461` 경매 시작 | `AUCTION_SCHEDULED → AUCTION_IN_PROGRESS` 누락 | Phase 6 체크리스트 추가 |
| `-467` 낙찰 확정 | `→ SOLD` 누락. 낙찰자만 기록하고 상품은 그대로였다 | Phase 8 체크리스트 추가 |
| `-468` 유찰 | "상품 상태 복원"이라고만 적혀 무엇으로 되돌리는지 불명확 | **`AUCTION_FAILED`로 전이**로 명시 |
| 방송 후 판매 방식 선택 | ~~계획에 아예 없었다~~ | **서윤이 해결** — `ProductService.resolveAuctionFailure`. `-470`은 방송별 유찰 목록 조회만 남긴다 |

**`product`는 서윤 담당 영역이다.** 경매가 상품 상태를 바꾸는 것은 피할 수 없으니, 기존 `ProductQueryPort`처럼 **상태 변경도 포트로 격리**한다. 경매 서비스가 `ProductRepository`를 직접 잡지 않게 한다.

## 단계별 계획

각 Phase = 브랜치 1개, 커밋은 작업 단위. `develop-BE` 직접 커밋 금지.

### Phase 1 — 실시간 토대 · `-447` · 브랜치 `feat/27-websocket-base`

**여기가 어긋나면 채팅·시청자수·경매·큐레이션을 같이 고쳐야 한다.**

- [ ] `WebSocketConfig` — `@EnableWebSocketMessageBroker`, `/ws`, app prefix `/app`, SimpleBroker `/topic`
- [ ] `setAllowedOriginPatterns` — HTTP CORS와 별개
- [ ] `StompAuthChannelInterceptor` — CONNECT native header JWT 검증, principal에 `memberId`
- [ ] 토큰 없으면 **익명 통과**(비회원 시청), 잘못된 토큰만 거부
- [ ] `SecurityConfig`에 `/ws/**`
- [ ] 테스트 — 회원 CONNECT / 익명 CONNECT / 잘못된 토큰 거부

### Phase 2 — 채팅 · `-451` `-452` `-453` `-454` · 브랜치 `feat/208-live-chat`

- [ ] `-451` `chat` 패키지 + `ChatMessage` 엔티티. 정적 팩토리 `userMessage()`/`systemMessage()` — `@Builder`면 "USER인데 작성자 없음"이 만들어진다(DB `ck_chat_user_has_member`와 같은 규칙을 코드에서도)
- [ ] `-452` `@MessageMapping` 송수신 → 저장 → 커밋 후 브로드캐스트
- [ ] `-452` 비회원 발언 차단, 종료·취소 방송 발언 차단(`Live.isClosed()` 재사용), 길이 검증
- [ ] `-453` `GET /api/lives/{liveId}/chat-messages` — **`id` 커서 페이징.** `created_at`은 같은 밀리초 동률에서 경계 메시지가 밀린다. 비회원 조회 허용
- [ ] `-453` 실행계획 확인 후 필요하면 `(live_id, id DESC)` 인덱스
- [ ] `-454` STOMP 통합 테스트 + 권한 분기 + 커서 경계
- [ ] `BE/README.md` 디렉터리 구조에 `chat` 추가

**FE가 확정을 요청한 채팅 schema** — 이 Phase에서 함께 확정한다.

| 항목 | 결정 |
| --- | --- |
| 메시지 필드 | `messageId`, `senderId`, `senderNickname`, `senderProfileImageUrl`, `senderType`, `content`, `createdAt` |
| 전송 ack | `clientMessageId`를 그대로 되돌려준다. 낙관적 렌더 후 치환 |
| 차단 메시지 | `isBlocked=true`는 **응답에서 제외**한다. 숨김을 FE 판단에 맡기지 않는다 |
| 재접속 누락 보충 | 마지막 수신 `messageId`를 커서로 과거 조회 API 호출 |
| 종료 후 정책 | 읽기 허용, 쓰기 차단 |

### Phase 3 — 시청자 수 + 반응 이모지 · `-450` `-471` · 브랜치 `feat/217-live-realtime-signals` ✅ 완료

- [x] `-450` SUBSCRIBE/UNSUBSCRIBE/DISCONNECT 리스너 + `sessionId → liveId` 매핑
- [x] `-450` Redis 집계, 기동 시 stale 키 정리
- [x] `-450` 최대치 갱신 시에만 `live.peakViewerCount` — 매 접속마다 DB를 때리지 않는다
- [x] `-450` `/topic/lives/{liveId}/viewers` 브로드캐스트
- [x] `-450` `LiveListItemResponse.viewerCount` 실제 값 + `LiveListSort.VIEWERS_DESC` 개방
- [x] `-450` 라이브 상세에 `currentViewerCount` 추가 (`peakViewerCount`와 별 필드)
- [x] `-471` 반응 이모지 — `ReactionType` enum, rate limit, 브로드캐스트 (저장 없음)
- [x] `.codex/requests/be/009-live-list-api-contract.md` **삭제** — 잔여 항목이 해소됐다
- [x] FE 인계 문서 `003-viewer-count-reaction-handoff.md` + STOMP 계약 문서 갱신

**구현 중 계획과 달라진 것**

| 항목 | 계획 | 실제 | 이유 |
| --- | --- | --- | --- |
| 시청자 집계 자료구조 | Redis **카운터**(INCR) | Redis **Set**(세션 ID) | FE 한 명이 같은 방송의 여러 토픽을 구독한다. 구독마다 INCR 하면 한 사람이 네 명으로 잡힌다. `SADD`는 멱등해서 몇 번 구독해도 `SCARD`가 사람 수를 준다 |
| `sessionId → liveId` 매핑 | 단일 값 | `sessionId + subscriptionId → liveId` 해시 | UNSUBSCRIBE 프레임에는 destination 이 없다. 구독 단위로 남겨야 "채팅만 끊고 경매는 계속 보는" 경우에 시청자에서 잘못 빼지 않는다 |
| `peakViewerCount` 갱신 | 읽고 비교 후 저장 | 조건부 `UPDATE` 한 문장 | 동시 입장 시 두 스레드가 같은 최고치를 읽고 각자 덮어써 더 큰 값이 사라진다. 조건을 `WHERE`에 두면 원자적이다 |
| STOMP 예외 처리 | 컨트롤러별 핸들러 | `@ControllerAdvice`(`StompExceptionAdvice`) | 컨트롤러마다 복사하면 **새 STOMP 컨트롤러를 추가할 때 빼먹은 곳만 조용히 무응답**이 된다. 역직렬화 실패(`MessageConversionException`)도 여기서 잡는다 — 핸들러 실행 **전**에 터지므로 서비스 검증으로는 못 잡는다 |

**남은 빚**

- `VIEWERS_DESC`는 SQL 로 정렬할 수 없어 후보 500개까지만 메모리 정렬한다. 그 정렬에서
  `totalElements`는 전체 개수가 아니라 정렬 대상 수다. 규모가 커지면 `live` 에 현재 시청자 수
  컬럼을 두고 SQL 정렬로 옮긴다

### Phase 4 — 영상 · `-448`(인프라) → `-449`(코드) · 브랜치 `feat/217-live-openvidu`

**둘 다 정윤 담당이고 에이전트가 적극 관여한다**(2026-07-31 확정). 다만 손이 닿는 범위가 다르다 —
리포지토리 파일(compose·Caddyfile·문서·CI 변수)은 에이전트가 쓰고, **EC2 에 붙어서 하는 조작**
(설치 실행·UFW 적용·컨테이너 기동)은 정윤이 실행한다.

- [x] `-448` compose·Caddy·UFW·CI 변수·`ec2.md` — **파일 작성 완료.** 서버 적용은 정윤이 실행
- [ ] `-448` **EC2 적용** — `setup-ufw-media.sh` 실행 + CI/CD Variables 4개 등록 + 배포

**`-448` 판단 — 공식 번들을 쓰지 않고 미디어 코어만 올린다**

OpenVidu v3 Community 번들은 자체 Caddy·Redis·MinIO·MongoDB·대시보드를 함께 띄운다.
**443이 우리 Caddy와 정면 충돌하고**, Redis·MinIO는 이미 돌고 있으며, 메모리도 넘긴다
(현재 8.5GB + 러너 3GB / 15GB에 번들 4~6GB를 더한다).

OpenVidu v3는 LiveKit 기반이라 **미디어 코어(`livekit-server`)만 올려도 클라이언트·서버 SDK·room
개념이 전부 동일하다.** 번들이 더해주는 것은 관측·대시보드뿐이다. 단일 컨테이너 약 500MB로 간다.
STT용 오디오 추출이 필요해지면 LiveKit Egress를 추가로 붙인다 — 번들 전체를 되돌릴 필요가 없다.

| 항목 | 결정 |
| --- | --- |
| 시그널링 | 기존 Caddy가 `/rtc`·`/twirp` 프록시. **서브도메인을 못 쓴다**(호스트가 하나) |
| 미디어 | 호스트에 직접 publish — 프록시를 통과할 수 없는 UDP 스트림이다 |
| 미디어 포트 | UDP mux 단일 포트(7885) + TCP 폴백(7881). 기본 50000-60000 범위는 UFW 규칙이 만 개가 된다 |
| 공인 IP | `use_external_ip: false` + `NODE_IP` 주입. STUN 자동 탐지는 외부 UDP가 막히면 **서버가 아예 뜨지 않는다**(실제로 겪음) |

**로컬에서 실제로 확인한 것 (2026-07-31)** — 배포 후에야 드러나면 곤란한 것부터 앞당겨 봤다.

| 확인 | 방법 | 결과 |
| --- | --- | --- |
| 우리 토큰을 LiveKit이 수락 | `/rtc/validate` | 200 `success` |
| 시크릿 불일치 시 거절 | 틀린 secret으로 발급 | 거절됨 |
| Caddy `/rtc` → LiveKit | probe Caddy 경유 | 200 `success` |
| Caddy `/twirp` → RoomService | `livekit-cli room list` 경유 | 정상 응답 |
| `/`·`/api/*`가 백엔드로 | 같은 matcher로 확인 | 충돌 없음 |
| **WebSocket 업그레이드** | `Upgrade: websocket` | **101 Switching Protocols** |
| **실제 미디어 송수신** | `load-test` 송출 1 + 시청 2, 15초 | **1.1~1.2mbps, 패킷 손실 0%** |

미디어까지 흐르는 것을 봤으므로 `udp_port: 7885` mux 설정이 실제로 동작한다.
**남은 미확인은 "EC2 공인 IP 환경"뿐이다** — `NODE_IP`가 제대로 박히는지는 배포 후에만 볼 수 있다.

`OpenViduTokenAcceptanceTest` 3건은 서버가 없으면 자동으로 건너뛰므로 CI는 그대로 통과한다.
- [x] `-449` **선행 확인 완료 — 토큰 발급에 서버 호출이 없다.** 아래 참고
- [x] `-449` `OpenViduClient` — `global/client`에 `AiClient` 패턴대로
- [x] `-449` `SCHEDULED → LIVE` 전이 시 room 이름 배정 → `Live.assignOpenviduRoom()`. **즉시 개설 경로도 함께** (생성 시점에 이미 `LIVE`라 빠져 있으면 토큰을 못 받는다)
- [x] `-449` 송출 토큰(호스트) / 시청 토큰(**비회원도 발급**) API + 만료·재발급 규약
- [x] `-449` 종료 시 room 정리
- [ ] `-449` **브라우저 2개로 실제 송수신 확인 — `-448` 완료 후에만 가능**

**선행 확인 결과 (2026-07-31)**

계획서가 요구한 "토큰 발급에 서버 호출이 필요한가"의 답은 **필요 없다**이다. LiveKit 접속 토큰은
API key/secret 으로 로컬 서명하는 JWT다. `OpenViduClientTest` 8건이 **OpenVidu 서버가 없는
환경에서 통과하는 것**이 그 증거다 — CI 에도 서버가 없다.

room 도 미리 만들지 않는다. LiveKit 은 첫 참가자가 들어올 때 자동 생성하므로 방송 시작 시점에는
**이름만 정하면 된다.** 그래서 `-448` 없이도 여기까지 왔다. 남은 것은 실제 송수신 확인뿐이다.

**계획과 달라진 것**

| 항목 | 계획 | 실제 | 이유 |
| --- | --- | --- | --- |
| 토큰 endpoint | 송출용/시청용 분리 | **하나로 합침** (`POST /api/lives/{liveId}/video-token`) | 나누면 FE가 "나는 호스트니 송출 토큰 달라"고 요청하는 모양이 된다. 역할 판단은 서버 몫이다 |
| 종료 시 정리 | `LiveCleanupHook`에서 바로 삭제 | 훅은 **이벤트만 발행**, 삭제는 `AFTER_COMMIT` | 훅은 상태 전이 트랜잭션 안에서 돈다. 거기서 HTTP를 호출하면 미디어 서버가 죽었을 때 **방송 종료 자체가 느려지거나 실패한다.** 정리가 안 되는 것보다 종료가 안 되는 쪽이 훨씬 나쁘다 (설계 판단 2와 같은 이유) |
| room 이름 | `live-{liveId}` | `live-{liveId}-{난수8}` | 정리가 실패해 이전 room 이 남아 있어도 새 방송이 그 방에 섞이지 않는다 |

**설정이 없어도 애플리케이션은 뜬다.** `openvidu.*` 기본값이 비어 있고, 그때 영상 토큰만
`503 L012`로 거부된다. 이게 없으면 서버 구축 전까지 로컬·CI의 모든 `@SpringBootTest`가 깨진다.

**`-448`에서 정윤이 정해야 할 값** — BE는 아래 세 환경변수만 읽는다.

```
OPENVIDU_SERVER_URL   예: wss://openvidu.i15a108.p.ssafy.io
OPENVIDU_API_KEY
OPENVIDU_API_SECRET
OPENVIDU_TOKEN_TTL    선택, 기본 2h
```

### Phase 5 — 현재 소개 상품 큐레이션 · `-87`(LIVE-004) 신규 작업 · 브랜치 `feat/217-live-product-curation`

FE `NOW` 배지와 진입 시 기본 선택 상품의 원천이다. 지금은 없어서 FE가 배지를 못 띄운다.

- [x] `live.current_product_id` 컬럼 + `schema.sql`·`erd.md`·`comments.sql`·데이터 사전 갱신
- [x] `PATCH /api/lives/{liveId}/current-product` — 호스트만. 편성된 상품인지 검증
- [x] 라이브 상세·목록 응답에 `currentProductId` 추가
- [x] `/topic/lives/{liveId}/product` 전환 브로드캐스트 (커밋 후)
- [x] 방송 종료 시 `null`
- [x] 테스트 — 호스트 아님 403, 편성 안 된 상품 404, 종료 방송 400
- [x] **연결 상품 카드 필드 보강** — `brandName`·`price`·`saleType`·`conditionGrade`·`thumbnailUrl`
      (FE 요청 `docs/requests/FE/006`에서 "Phase 5에 온다"고 약속한 것)
- [x] FE 인계 문서 `docs/requests/FE/007-current-product-handoff.md`

**계획과 달라진 것**

| 항목 | 계획 | 실제 | 이유 |
| --- | --- | --- | --- |
| 편성 안 된 상품 | 400 | **404 `L006`** | 상품은 있지만 이 방송의 편성 목록에 없다는 뜻이라 기존 `LIVE_PRODUCT_NOT_FOUND`가 정확히 그 상황이다. 새 코드를 만드는 것보다 낫다 |
| 전환 허용 상태 | (명시 없음) | **진행 중에도 허용**, 종료·취소만 차단 | 편성 변경은 방송 시작 시 잠기지만 소개 상품 전환은 **방송 중에 하는 것이 본래 용도**다. `isOpenForEditing`이 아니라 `isClosed`로 막는다 |
| 상품 조회 | (명시 없음) | **배치 조회**(`ProductQueryPort.findCards`) | 편성 상품마다 상품·브랜드·이미지를 따로 읽으면 상품 수만큼 쿼리가 나간다. 시청 화면은 시청자가 들어올 때마다 열려 그 비용이 그대로 쌓인다 |
| 이미지 배치 조회 | (명시 없음) | `live/port/ProductImageQueryRepository` 신설 | 상품 도메인 리포지토리에는 상품 하나씩 읽는 메서드뿐이다. 거기에 메서드를 추가하면 서윤 영역을 고치게 되므로 **읽기 전용 조회를 라이브 패키지에** 뒀다 |

**`productId: null`은 오류가 아니라 해제다.** `@NotNull`을 걸지 않은 이유 — 호스트가 잡담 구간으로
넘어가면 아무 상품도 소개하지 않는 상태가 필요한데, 필수로 막으면 한번 지정한 뒤 되돌릴 방법이 없다.

### Phase 6 — 경매 조회·시작 · `-96`(AUCT-002) 신규 작업 · 브랜치 `feat/209-auction-start`

- [ ] `GET /api/lives/{liveId}/auctions/current` — snapshot. 없으면 200 + `null` (설계 판단 5)
- [ ] snapshot 필드 — `auctionId`, `productId`, `status`, `startPrice`, `bidUnit`, `currentPrice`, **`nextBidPrice`**, `topBidderId`, `topBidderNickname`, `scheduledEndAt`, `extensionCount`
- [ ] `POST /api/lives/{liveId}/auctions/{auctionId}/start` — `READY → RUNNING`, `scheduled_end_at` 계산
- [ ] `ux_auction_live_running` 위반을 400으로 변환 — 한 라이브에 진행 중 경매는 1개
- [ ] `/topic/lives/{liveId}/auction` 시작 이벤트
- [ ] **`ProductCommandPort` 신설** — 경매가 상품 상태를 바꾸는 통로. `product`는 서윤 영역이라 `ProductQueryPort`와 같은 방식으로 격리한다 (설계 판단 11)
- [ ] **경매 시작 시 `AUCTION_SCHEDULED → AUCTION_IN_PROGRESS`** (설계 판단 10)
- [ ] **`-394` 보완 — 경매 조건 설정 시 `AUCTION_SCHEDULED`로 전이.** 이미 머지된 코드에 빠져 있어 지금은 상품이 `DRAFT`·`ON_SALE`에 머문다
- [ ] Swagger + 테스트 (상태 전이 검증 포함)

### Phase 7 — 입찰 · `-97`(AUCT-003) `-98`(AUCT-004~006) 신규 작업 · 브랜치 `feat/209-auction-bid`

**이 계획의 핵심이자 가장 위험한 구간.** 설계 판단 1·2를 그대로 따른다.

- [ ] `AuctionRepository.findByIdForUpdate` — `@Lock(PESSIMISTIC_WRITE)`
- [ ] `POST /api/lives/{liveId}/auctions/{auctionId}/bids` — 동기 응답으로 성공 snapshot 반환
- [ ] 한 트랜잭션에서 — 경매 행 잠금 → 유효 입찰 판정 → `bid` 삽입 → `current_price`·`top_bidder_id` 갱신 → 자동 연장 판정
- [ ] 유효 입찰 판정 — `RUNNING` 상태, 종료 시각 전, `bidPrice == currentPrice + bidUnit`(첫 입찰은 `startPrice`)
- [ ] **연속 입찰 제한**(AUCT-006) — 직전 최고 입찰자가 본인이면 거부. Redis 불필요, `top_bidder_id`로 판정된다
- [ ] 중복 클릭(AUCT-004) — `ux_bid_auction_price` 유니크 위반을 409로 변환
- [ ] 밀린 입찰 `ACTIVE → OUTBID` 전이
- [ ] `GET /api/auctions/{auctionId}/bids` — 커서 페이징, `isMine` 포함
- [ ] 커밋 후 `/topic/lives/{liveId}/auction` 전파
- [ ] 테스트 — **동시 입찰 경합 테스트 필수**(스레드 2개 이상), 연속 입찰 거부, 종료 후 입찰 거부
- [ ] `schema.sql`·`erd.md`의 "Redis 분산락 1차 방어" 주석 정정

### Phase 8 — 자동 연장·낙찰·유찰 · `-100` `-101` `-103` 신규 작업 · 브랜치 `feat/209-auction-close`

- [ ] `@Scheduled(fixedDelay = 1s)` 마감 스캐너 — `RUNNING` + `scheduled_end_at` 경과 (설계 판단 3)
- [ ] 자동 연장(AUCT-010) — 종료 임박 입찰이면 `scheduled_end_at` 연장 + `extension_count++`. **입찰 트랜잭션 안에서**
- [ ] 낙찰(AUCT-012) — 경매 `SUCCESS`, `winner_id`·`final_price`, 최고 입찰 `WON`, 나머지 `LOST`
- [ ] **낙찰 시 상품 `→ SOLD`** (설계 판단 10). 티켓에 빠져 있던 항목이다 — 낙찰자만 기록하고 상품이 그대로면 같은 물건을 또 팔 수 있다
- [ ] 유찰(AUCT-014) — 경매 `FAILED`, **상품 `→ AUCTION_FAILED`**(판매자 선택 대기). 그 이후 처리는 서윤의 `resolveAuctionFailure`가 이미 담당한다 (설계 판단 10)
- [ ] `GET /api/auctions/{auctionId}/winner` — 결과 조회
- [ ] `/topic/lives/{liveId}/auction` 종료 이벤트
- [ ] 방송 종료 시 진행 중 경매 마감 — `LiveCleanupHook` 구현체
- [ ] 테스트 — 연장 경계, 입찰 0건 유찰, 방송 종료 시 강제 마감, **상품 상태 전이 검증**

#### Phase 8-b — 방송별 유찰 상품 목록 · `-89`(LIVE-006) · `-470`

**판매 방식 선택 자체는 서윤이 이미 구현했다** — `PATCH` + `ProductService.resolveAuctionFailure`. 상시 판매 전환과 다시 경매 둘 다 된다. 중복 구현하지 않는다.

남은 것은 **라이브 쪽 조회 하나**다. FE `-438`(방송 종료 대시보드)·`-440`(미낙찰 상품 처리 UI)이 "이 방송에서 안 팔린 상품"을 물어볼 곳이 없다.

- [ ] `GET /api/lives/{liveId}/unsold-products` — 이 방송의 유찰 상품. 호스트만
- [ ] 근거는 `auction` 테이블 — `live_id` + `status = 'FAILED'`. 상품 상태로 찾으면 "다른 방송에서 유찰된 것"까지 섞인다
- [ ] 응답에 판매자가 다음 행동을 고를 수 있을 만큼 담는다 — `productId`, `title`, `thumbnailUrl`, 마지막 경매의 `startPrice`
- [ ] Swagger + 테스트
- [ ] `-470` 티켓 범위를 이 조회로 축소 (판매 방식 선택 부분 삭제)

### Phase 9 — 포인트 보류·참여 제한 · `-99`(AUCT-007~009) 신규 작업 · **서윤 선행 필요**

- [ ] 서윤 `point` 도메인 완료 확인 (`point_account`·`point_hold` 코드)
- [ ] 입찰 시 포인트 보류 — **같은 트랜잭션**
- [ ] 밀린 입찰 보류 해제(AUCT-008) — `erd.md` §4의 순서 주의사항 준수
- [ ] 잔액 부족 시 입찰 거부(AUCT-009)
- [ ] 테스트

### Phase 10 — 문서·계약 정리 (각 Phase 완료 시점마다)

- [ ] Phase 2 직후 — `.claude/requests/fe/`에 **STOMP 계약 문서** (destination 표, CONNECT 인증, payload, 에러 규약, 비회원 제약). FE `-423`·`-432`가 이거 없이 못 움직인다
- [ ] Phase 7 직후 — **경매 계약 문서** (snapshot 필드, 입찰 요청/응답, 이벤트 payload, 에러 코드)
- [ ] **서윤 요청 문서 2건** (정윤 결정 4)
  - 상품 구조화 필드 — `material`, `measurements`, `defectSummary`
  - 팔로우 API — 상태 조회·등록·해제. `follow` 테이블만 있고 엔티티·컨트롤러가 없다. 비회원·본인 팔로우·중복 팔로우·미팔로우 해제 오류 규약 포함
- [ ] FE 요청서 `012-live-watch-detail-contract-gaps.md`를 잔여 항목만 남기고 정리

## 티켓 (2026-07-30 등록 완료)

전부 **작업 parent = 에픽, 스토리는 Relates 링크**. 스프린트에 넣지 않고 백로그.

| 티켓 | 내용 | 스토리 | Phase |
| --- | --- | --- | --- |
| [-457](https://ssafy.atlassian.net/browse/S15P11A108-457) | 현재 소개 상품 전환 API 및 실시간 전파 | `-87` | 5 |
| [-458](https://ssafy.atlassian.net/browse/S15P11A108-458) | 현재 소개 상품 전환 테스트 | `-87` | 5 |
| [-459](https://ssafy.atlassian.net/browse/S15P11A108-459) | 반응 이모지 실시간 브로드캐스트 | `-91` | 3 |
| [-460](https://ssafy.atlassian.net/browse/S15P11A108-460) | 진행 중 경매 snapshot 조회 API | `-96` | 6 |
| [-461](https://ssafy.atlassian.net/browse/S15P11A108-461) | 경매 시작 API 및 시작·조회 테스트 | `-96` | 6 |
| [-462](https://ssafy.atlassian.net/browse/S15P11A108-462) | 증액 버튼 입찰 API (DB 비관적 락) | `-97` | 7 |
| [-463](https://ssafy.atlassian.net/browse/S15P11A108-463) | 입찰 내역 조회 API (커서 페이징) | `-97` | 7 |
| [-464](https://ssafy.atlassian.net/browse/S15P11A108-464) | 유효 입찰·연속 입찰·중복 클릭 판정 | `-98` | 7 |
| [-465](https://ssafy.atlassian.net/browse/S15P11A108-465) | 동시 입찰 경합 테스트 | `-98` | 7 |
| [-466](https://ssafy.atlassian.net/browse/S15P11A108-466) | 경매 마감 스케줄러 및 자동 연장 | `-100` | 8 |
| [-467](https://ssafy.atlassian.net/browse/S15P11A108-467) | 낙찰 확정 및 결과 조회 API | `-101` | 8 |
| [-468](https://ssafy.atlassian.net/browse/S15P11A108-468) | 유찰 처리 및 방송 종료 시 경매 강제 마감 | `-103` | 8 |
| [-469](https://ssafy.atlassian.net/browse/S15P11A108-469) | 입찰 포인트 보류·해제 연동 | `-99` | 9 |

이미 있던 것 — `-447`, `-449`, `-450`, `-451`, `-452`, `-453`, `-454`. `-448`은 정윤이 직접(인프라).

### 추가 등록 완료 (2026-07-30)

상품 판매 상태 정책(설계 판단 10·11) 때문에 드러난 누락이다.

| 티켓 | 내용 | 스토리 | Phase |
| --- | --- | --- | --- |
| [-470](https://ssafy.atlassian.net/browse/S15P11A108-470) | 방송 후 판매 방식 선택 API (유찰 상품 재판매) | `-89` | 8-b |

나머지 4건(경매 설정·시작·낙찰·유찰의 상태 전이)은 **기존 티켓 `-461`·`-467`·`-468` 범위에 흡수**했다. 새로 만들지 않는다.

FE 계약 회신 문서는 별도 티켓으로 빼지 않고 `-462`(경매)·`-452`(채팅)의 산출물에 넣었다 — 기존 `-396` 패턴과 같다.

## 위험과 대응

| 위험 | 대응 |
| --- | --- |
| **포인트 도메인 미구현** | Phase 7을 보류 없이 먼저 열고 Phase 9에서 붙인다. 그 사이 무한 입찰이 가능하므로 시연 전 필수 마감 항목으로 관리 |
| **`-448` 리드타임** | Phase 4만 영상에 의존한다. Phase 1~3·5~8은 서버 없이 끝낼 수 있으니 막히면 순서를 미룬다 |
| **동시 입찰 회귀** | 스레드 경합 테스트를 Phase 7에 필수로 넣는다. 없으면 락을 잘못 걸어도 초록불이 뜬다 |
| **입찰 취소 불가 + 잔액 검증 없음** | 둘이 겹치면 "취소도 못 하는데 낼 수 없는 금액을 부를 수 있는" 상태가 된다. Phase 9까지는 **테스트·시연용 계정에만 노출**하고 FE에도 명시한다 |
| **스키마 변경** | `live.current_product_id` 추가. 로컬 `ddl-auto: update`는 컬럼 추가는 되지만, **빈 DB로 CI 검증을 반드시 한 번 돌린다**(지난 CI 실패 재발 방지) |
| **상품 상태가 어디서도 안 바뀌는 상태** | 현재 경매 관련 코드가 `sale_status`를 전혀 건드리지 않는다(설계 판단 11). Phase 6·8에서 채우기 전까지 **경매를 걸어도 상품은 계속 `DRAFT`·`ON_SALE`로 보인다** — 홈·목록의 "경매 예정" 표시가 나오지 않는다 |
| **서윤 영역 침범** | 상품 상태 전이는 `product` 도메인을 건드린다. `ProductCommandPort`로 격리하되, Phase 6 착수 전 서윤과 한 번 맞춘다 |

## 확정된 추가 결정 (2026-07-30)

1. **`-442`는 중복이 아니었다.** 작업이 아니라 **스토리**이고 완료된 `-390`·`-391`·`-392`가 그 아래 붙은 정상 구조였다. 삭제하지 않고 **완료로 전이**했다. Phase 8의 경매 마감 스케줄러는 AUCT 스토리에 붙인다
2. **경매는 호스트가 버튼으로 시작한다.** Phase 5(상품 전환)와 Phase 6(경매 시작)은 분리 유지. 상품을 바꿔도 경매가 자동으로 시작되지 않는다 — 호스트가 상품을 소개한 뒤 시점을 골라 시작한다
3. **입찰 취소는 없다.** 입찰 버튼을 누른 순간 낙찰 시 구매 의무가 확정된다. 그래서 **입찰 확정 전 프론트 확인 절차와 잔액 검증이 더 중요해진다** — Phase 9(포인트)가 시연 전 필수인 이유가 하나 더 늘었다
4. **포인트는 서윤이 아직 미구현.** 완료되면 Phase 9에서 붙인다. 그때까지 입찰은 잔액 검증 없이 동작한다

## 미결정

`AUCTION_FAILED`는 유지로 결론 났다(설계 판단 10). 남은 것은 하나뿐이다.

1. **`ProductCommandPort` 신설을 서윤과 맞출 것.** 경매가 상품 상태를 바꾸는 것은 피할 수 없으니, 직접 리포지토리를 잡는 대신 포트로 격리한다. **Phase 6 착수 전**에 정해지면 된다 — Phase 3~5는 영향이 없다.

## 공통 규율

- [ ] 각 Phase마다 `BE:verify` 통과 후 커밋 — **빈 DB로도 한 번**
- [ ] 새 엔드포인트는 Swagger 어노테이션 동반
- [ ] 브로드캐스트는 전부 커밋 후(설계 판단 2)
- [ ] push는 정윤이 직접