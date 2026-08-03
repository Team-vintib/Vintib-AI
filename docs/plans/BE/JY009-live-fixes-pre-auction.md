# Phase 6(경매) 진입 전 라이브 정합성 정리 계획

- 작성: 2026-08-03. 기준 `develop-BE` `c52b1c0`
- 근거: FE 요청 문서 `docs/requests/BE/004`·`007`·`009`·`012`·`013`, 정윤 현장 확인 2건
- 에픽: [-217](https://ssafy.atlassian.net/browse/S15P11A108-217) `[LIVE]`, [-27](https://ssafy.atlassian.net/browse/S15P11A108-27) `[INFRA]`
- **JY008 Phase 6(경매) 진입 전에 끼워 넣는 배치다.** 경매는 라이브 위에 얹히므로, 라이브의
  시각·호스트 판정이 틀린 상태에서 경매를 올리면 같은 버그를 경매에서 다시 만난다.

## 배경

Phase 5까지 끝낸 시점에서 두 갈래를 점검했다.

1. `docs/requests/BE/`의 FE 요청 문서 13건을 완료 코드와 대조했다.
2. 정윤이 실제 방송에서 발견한 라이브 오동작 2건을 재현·추적했다.

둘 다 **서버가 UTC로 도는 것**과 **홈이 아직 mock인 것**에서 대부분 파생됐다.

## 진단

### D1. 서버 시각이 UTC라 모든 시각이 9시간 어긋난다 (원인 확정)

- `Live.scheduledAt/startedAt/endedAt`과 `BaseTimeEntity.createdAt/updatedAt`은 `LocalDateTime`(존 없음)이고,
  DB 컬럼은 `TIMESTAMPTZ`다.
- 백엔드 컨테이너에 `TZ`가 없다. `eclipse-temurin:21-jre-jammy`는 UTC라 **`LocalDateTime.now()`가 UTC 벽시계**를 준다.
- 응답 JSON은 `"2026-08-03T01:30:00"`처럼 오프셋 없이 나가고, 브라우저는 이걸 KST로 읽는다 → **정확히 -9시간**.
- 파생 증상 두 가지가 정윤이 본 그대로다.
  - 개설 시각·시작 시각이 9시간 전으로 표시된다.
  - 경과 방송 시간 = `브라우저 now(KST)` − `startedAt(UTC를 KST로 오독)` = **9시간부터 시작**.
- 추가로 `LiveScheduleRequest.scheduledAt`의 `@Future`가 UTC now와 비교된다 → **KST 기준 과거 9시간 이내 예약이 통과**한다.
- 로컬(Windows JVM = KST)에서는 재현되지 않아 배포 후에야 드러났다.

### D2. 재입장 시 내 라이브인데 팔로우 버튼이 뜬다

- `GET /api/lives/{liveId}`는 `permitAll`이고 `Authentication`을 아예 받지 않는다. 응답에 `hostId`만 있고
  **"내가 호스트인가"를 서버가 알려주지 않는다.**
- 그래서 FE가 `hostId === authStore.me.id`로 직접 판정하는데, 새로고침·재입장 시 회원 정보 복원이
  라이브 상세 렌더보다 늦으면 `me.id`가 `undefined`라 판정이 뒤집힌다.
- **FE 타이밍 문제이기도 하지만, 판정 근거를 클라이언트에 맡긴 계약 자체가 원인이다.** 서버가
  `isHost`를 계산해 내려주면 경합 자체가 없어진다. 다른 응답(`isWished`)도 이미 서버 계산 방식이다.

### D3. 방송 종료가 시청자에게 실시간으로 전파되지 않는다

- 브로드캐스트 토픽은 `chat`·`reactions`·`viewers`·`product` 넷뿐이다. **상태 전이 토픽이 없다.**
- 호스트가 종료해도 시청 중인 사람 화면은 그대로다. 새로고침해야 404를 만난다.
- `docs/requests/BE/012` 인덱스가 "종료 시청자 실시간 전파"를 남은 요청으로 적고 있다.

### D4. 홈이 아직 전부 mock이다

- `HomeService`는 `liveId` 101·102를 하드코딩한다. FE가 `004 §3.3`에서 "홈에만 있고 상세는 404"라고
  보고한 정합성 버그의 **정체가 이것**이다. 실데이터로 바꾸면 함께 사라진다.
- `LiveCardResponse`에 `hostId`가 없다(`004 §3.1`).
- 홈 실데이터 전환에 해당하는 Jira 티켓이 없다(-279·-289는 mock 단계로 완료됨).

### D5. 좀비 라이브 — 호스트가 종료하지 않으면 영원히 LIVE다

- 상태 전이는 `PATCH /api/lives/{liveId}/status` 수동 호출뿐이고 스케줄러가 없다.
  호스트가 브라우저를 닫으면 방송이 `LIVE`로 남아 목록·홈 상단을 계속 차지한다.
- 예약 방송도 `scheduledAt`이 지나도 `SCHEDULED`로 남는다.
- 경매 마감 스케줄러(-466)에서 `@EnableScheduling`이 들어오므로, **그때 같이 처리하는 것이 싸다.**

## 결정

1. **시각은 컨테이너 타임존을 KST로 고정해서 고친다.** DTO를 `OffsetDateTime`으로 바꾸는 쪽이
   장기적으로 옳지만, 서윤 도메인 DTO까지 전부 건드려야 하고 FE 파싱도 같이 바꿔야 한다.
   수요일 마감 앞에서 취할 변경이 아니다. **`TZ=Asia/Seoul` 한 줄로 서버·DB·검증이 전부 KST로 정렬된다.**
   대신 "모든 datetime 필드는 오프셋 없는 KST 벽시계"라는 계약을 문서에 못박는다.
2. **`isHost`는 서버가 계산해 내려준다.** `GET /api/lives/{liveId}`에 선택 인증을 붙인다.
   비회원이면 `false`. FE 타이밍 수정은 별도로 요청 문서를 남긴다.
3. **`isFollowingHost`는 이번 범위에서 뺀다.** 팔로우는 서윤 도메인이고 FE가 이미 공개 프로필 API로
   팔로우 상태를 받고 있다. `isHost`만 고쳐지면 버튼이 뜨는 문제는 사라진다.
4. **좀비 라이브 정리는 -466(경매 마감 스케줄러)에 합친다.** 스케줄러 인프라가 거기서 처음 생긴다.
5. **통합 검색(`005`)과 예약 라이브 알림(`008 §3.2.1`)은 이번 주 범위에서 뺀다.** 둘 다 티켓이 없고,
   경매(Phase 6~8)가 시연 필수 경로다. 정윤 판단이 필요한 항목으로 남긴다.

## 작업 내용

### 1. 타임존 정렬 (D1)

- `docker-compose.yml` backend 서비스에 `TZ: ${TZ:-Asia/Seoul}` 추가. 컨테이너 하나만 고치면
  `LocalDateTime.now()`·`@Future`·auditing·pgjdbc 변환이 전부 같은 축으로 정렬된다.
- `BE/Dockerfile`에도 `ENV TZ=Asia/Seoul`을 둔다 — compose 없이 이미지를 직접 돌려도 같게 동작해야 한다.
- 서윤 도메인 시각(주문·알림·포인트)도 같이 고쳐지는 변경이라 **머지 후 공유한다.**
- 확인: 배포 후 `docker exec vintib-backend date`와 즉시 개설 라이브의 `startedAt`이 KST와 일치.

### 2. 라이브 상세 `isHost` (D2)

- `GET /api/lives/{liveId}`가 `Authentication`을 받는다(엔드포인트는 `permitAll` 유지 —
  토큰이 있으면 `JwtAuthenticationFilter`가 이미 채워 준다).
- `LiveDetailResponse`에 `isHost: boolean` 추가. `Live.isHostedBy(viewerId)` 재사용.
- FE에 요청 문서: `isHost`로 판정을 바꾸고 `hostId` 직접 비교를 제거.

### 3. 방송 상태 실시간 전파 (D3)

- `PATCH /api/lives/{liveId}/status` 성공 후 `/topic/lives/{liveId}/status`로 브로드캐스트.
- payload는 `{ liveId, status, endedAt }` 수준으로 얇게. 현재 소개 상품 전환과 같은 방식으로
  **커밋 이후**에 쏜다.
- 종료 시 시청자 Redis 집계도 함께 정리되는지 확인한다.

### 4. 홈 실데이터 전환 (D4)

- `HomeService`·`FollowingService`의 mock 조립부를 실제 조회로 교체.
  - 라이브 섹션: `LiveRepository`(진행 중·예약) — 내 도메인.
  - 상품 섹션: 서윤 도메인이라 **port로 읽는다**(`ProductQueryPort`와 같은 방식).
- `LiveCardResponse`에 `hostId` 추가(`004 §3.1`).
- 섹션별 정렬 기준·최대 개수·빈 섹션 정책을 Swagger 설명과 FE 요청 문서에 명시(`004 §3.2`).
- 상품 섹션 조회가 서윤 API에 막히면 **라이브 섹션만 먼저 실데이터로 돌린다** — `liveNow` 정합성
  버그(`004 §3.3`)는 그것만으로 해소된다.

## 구현 목록

- [ ] `docker-compose.yml`·`BE/Dockerfile`에 `TZ=Asia/Seoul` (D1)
- [ ] 타임존 계약을 `BE/README.md`와 FE 요청 문서에 명시 (D1)
- [ ] `LiveDetailResponse.isHost` + 컨트롤러 선택 인증 (D2)
- [ ] `isHost` 서비스 테스트 — 호스트/타인/비회원 3케이스 (D2)
- [ ] `/topic/lives/{liveId}/status` 브로드캐스트 (D3)
- [ ] 상태 전파 STOMP 테스트 (D3)
- [ ] `LiveCardResponse.hostId` (D4)
- [ ] `HomeService` 라이브 섹션 실데이터 전환 (D4)
- [ ] `FollowingService` 라이브 섹션 실데이터 전환 (D4)
- [ ] 홈 상품 섹션 실데이터 전환 — 서윤 port 확보 후 (D4)
- [ ] 홈 노출 정책 문서화 (D4)
- [ ] 처리 끝난 FE 요청 문서 정리 — `013` 삭제, `004`·`007`·`012` 반영분 축소
- [ ] FE 핸드오프 문서 — `isHost`, status 토픽, 타임존 계약, 생성용 상품 조회 안내

## 미결정 — 정윤 확인 필요

1. **통합 검색 `GET /api/search`(`005`)** — Jira 티켓이 없다. 이번 주에 넣을지, 시연 범위에서 뺄지.
2. **예약 라이브 알림 신청·스케줄러(`008 §3.2.1`)** — `live_reminder` 테이블·스케줄러가 필요하다.
   기능 정의서상 "추가" 우선순위. 이번 주 제외로 보고 있다.
3. **`LiveDetailResponse.description`(`007 §3.5` 선택)** — `live` 테이블에 설명 컬럼 자체가 없다.
   컬럼을 새로 파야 해서 이번 범위에서 뺐다.
