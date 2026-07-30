# 실시간 채팅 인계 문서 (Phase 1~2 완료)

- **작성 파트**: BE (정윤)
- **대상 파트**: FE
- **관련 BE 이슈**: `S15P11A108-447`(WS 토대), `-451`~`-454`(채팅)
- **관련 FE 이슈**: `-419`, `-423`, `-430`, `-432`
- **계약 상세**: `.claude/requests/fe/001-live-stomp-contract.md` (destination·payload·에러 코드 전문)
- **이 문서**: 어디까지 됐고, 지금 무엇을 붙일 수 있고, 어떻게 직접 확인하는지

---

## 1. 한 줄 요약

**채팅은 지금 붙이면 동작합니다.** 영상·시청자 수·경매·반응 이모지는 아직입니다.

## 2. 구현 현황

| 기능 | 상태 | 비고 |
| --- | --- | --- |
| WebSocket(STOMP) 연결·인증 | ✅ 사용 가능 | 비회원 연결 허용 |
| 채팅 발행·구독 | ✅ 사용 가능 | 회원만 발행, 비회원 구독 가능 |
| 채팅 이력 조회 (커서) | ✅ 사용 가능 | 비회원 조회 가능 |
| 채팅 에러 통보 | ✅ 사용 가능 | `/user/queue/errors` |
| 반응 이모지 | ⏳ Phase 3 | destination만 예약 |
| 현재 시청자 수 | ⏳ Phase 3 | `viewerCount`는 계속 `null` |
| 영상(OpenVidu 토큰) | ⏳ Phase 4 | |
| 현재 소개 상품(`NOW` 배지) | ⏳ Phase 5 | `currentProductId` 아직 없음 |
| 경매 조회·입찰 | ⏳ Phase 6~8 | |

**아직 안 된 것에 대해 mock을 유지해 주세요.** 각 Phase가 끝날 때마다 이 문서와 같은 형식으로 다시 알립니다.

## 3. 시작하기

### 3-1. STOMP 클라이언트 설치가 필요합니다

확인해 보니 `FE/package.json`에 STOMP 클라이언트가 없습니다. 아래 하나만 설치하면 됩니다.

```bash
npm i @stomp/stompjs
```

> SockJS는 쓰지 않습니다. `sockjs-client`는 설치하지 마세요 — 서버가 plain WebSocket + STOMP로만 열려 있어 URL·프레임 규약이 맞지 않습니다.

### 3-2. 연결 코드

**아래 코드는 실제 서버에 붙여 동작을 확인한 것입니다.** 브라우저 환경 기준으로 정리했습니다.

```ts
import { Client } from '@stomp/stompjs';

const client = new Client({
  brokerURL: `${WS_BASE}/ws`,                 // 예: ws://localhost:8080/ws
  connectHeaders: accessToken
    ? { Authorization: `Bearer ${accessToken}` }
    : {},                                     // 비회원은 빈 객체
  reconnectDelay: 5000,

  onConnect: () => {
    // 구독은 onConnect 안에서 등록한다. 연결 전에 subscribe 하면 유실된다.
    client.subscribe(`/topic/lives/${liveId}/chat`, (frame) => {
      const message = JSON.parse(frame.body);
      appendMessage(message);
    });

    // 내 발언이 거부되면 여기로만 온다 (다른 시청자에게는 안 보인다)
    client.subscribe('/user/queue/errors', (frame) => {
      const { error } = JSON.parse(frame.body);
      showToast(error.code, error.message);
    });
  },

  onStompError: (frame) => {
    // 토큰이 잘못됐거나 만료된 경우 여기로 온다 — 연결 자체가 끊긴다
    console.error('STOMP error', frame.headers.message);
  },
});

client.activate();
```

**중요한 세 가지.**

1. **토큰은 `connectHeaders`에 넣습니다.** URL 쿼리스트링이 아닙니다. 브라우저 `WebSocket` API가 핸드셰이크 요청에 `Authorization` 헤더를 붙일 수 없어서, 서버가 STOMP CONNECT 프레임의 헤더에서 토큰을 읽습니다.
2. **잘못된/만료된 토큰이면 연결 자체가 거부됩니다.** 조용히 비회원으로 내려가지 않습니다. `onStompError`에서 토큰을 갱신하고 재연결해 주세요.
3. **구독은 `onConnect` 안에서** 등록합니다.

### 3-3. 발언

```ts
client.publish({
  destination: `/app/lives/${liveId}/chat`,
  body: JSON.stringify({
    content: text,
    clientMessageId: crypto.randomUUID(),   // 낙관적 렌더용 임시 ID
  }),
});
```

### 3-4. 낙관적 렌더 → 치환

**ack 채널이 따로 없습니다.** 발행자도 같은 토픽으로 자기 메시지를 받고, 거기에 `clientMessageId`가 그대로 담겨 옵니다.

```ts
// 1. 보내는 즉시 임시 말풍선을 그린다
const tempId = crypto.randomUUID();
appendMessage({ clientMessageId: tempId, content: text, pending: true });

// 2. 브로드캐스트가 돌아오면 그 값으로 찾아 실제 메시지로 바꾼다
client.subscribe(`/topic/lives/${liveId}/chat`, (frame) => {
  const message = JSON.parse(frame.body);
  const mine = message.clientMessageId
    && replacePendingMessage(message.clientMessageId, message);
  if (!mine) appendMessage(message);   // 남의 메시지
});
```

다른 사람의 메시지에는 `clientMessageId`가 없거나 내 것과 다릅니다.

## 4. 메시지 형태

브로드캐스트와 이력 조회가 **완전히 같은 형태**입니다. 어댑터를 하나만 만들면 됩니다.

```json
{
  "messageId": 1044,
  "senderId": 31,
  "senderNickname": "빈티지장인",
  "senderProfileImageUrl": null,
  "senderType": "USER",
  "content": "이 자켓 사이즈 M 맞나요?",
  "createdAt": "2026-07-30T14:02:11",
  "clientMessageId": "tmp-3f9c1e"
}
```

| 필드 | nullable | 처리 |
| --- | --- | --- |
| `messageId` | 아니요 | 재접속 후 누락분 보충 시 커서로 사용 |
| `senderId` | 가능 | `SYSTEM`·`AI`는 `null` |
| `senderNickname` | 가능 | 닉네임이 없으면 서버가 이름으로 대체해 보냅니다. `SYSTEM`은 `null` |
| `senderProfileImageUrl` | **항상 `null`** | 아래 6번 참고. 기본 아바타로 처리해 주세요 |
| `senderType` | 아니요 | `USER` / `SYSTEM` / `AI` |
| `clientMessageId` | 가능 | 이력 조회에서는 항상 `null` |

`senderType` 표시 방식:

- `USER` — 일반 말풍선
- `SYSTEM` — 입장·경매 안내. 작성자가 없으니 안내 스타일로
- `AI` — **현재 발생하지 않습니다.** AI 채팅 매니저가 보류 상태라 값만 열려 있습니다

## 5. 이력 조회

```http
GET /api/lives/{liveId}/chat-messages?cursor={messageId}&size=30
```

인증 헤더 없이도 200입니다.

```json
{
  "success": true,
  "data": { "content": [ /* 위와 같은 형태, 최신순 */ ], "nextCursor": 1043, "hasNext": true },
  "error": null
}
```

**`page` 번호가 아니라 `messageId` 커서입니다.** 채팅은 조회하는 동안에도 계속 쌓여서, offset 방식이면 경계에서 같은 메시지가 두 번 보이거나 빠집니다. `nextCursor`를 다음 요청에 그대로 넣고, `hasNext`가 `false`면 끝입니다.

- `content[0]`이 **가장 최신**입니다. 채팅창은 아래가 최신이니 뒤집어 쓰는 것을 전제로 했습니다.
- `totalElements`는 주지 않습니다. 매 요청마다 값이 바뀌는 전체 개수를 세는 것은 무한 스크롤에는 의미가 없습니다.
- **재접속 후 누락분 보충**: 마지막으로 받은 `messageId`를 `cursor`로 넣으면 그보다 오래된 것들이 옵니다. 반대로 "그 이후"를 받는 방법은 아직 없으니, 재접속 시에는 첫 페이지를 다시 받아 중복을 `messageId`로 걸러 주세요. 이 방식이 불편하면 알려주시면 `after` 커서를 추가하겠습니다.

## 6. 알려진 제약

### `senderProfileImageUrl`은 항상 `null`입니다

**회원 엔티티에 프로필 이미지 필드가 없습니다.** `member` 테이블 스키마에는 `profile_image_url`이 있는데 JPA 엔티티에 매핑이 빠져 있어서, 실제 DB 컬럼도 없는 상태입니다. 회원 도메인은 서윤 담당이라 요청 문서를 전달했습니다.

**필드는 미리 넣어 뒀으니 DTO·어댑터는 지금 확정해도 됩니다.** 값이 생기면 그대로 채워집니다. `viewerCount`와 같은 패턴입니다.

### 방송 종료 후

- 이력 **조회는 계속 됩니다**
- 발언은 `L007`로 거부됩니다 → 입력창을 비활성화해 주세요

### 에러 코드

| 코드 | 상황 | 제안 |
| --- | --- | --- |
| `L008` | 비회원이 발언 시도 | 로그인 유도 |
| `L009` | 빈 메시지 또는 500자 초과 | 입력창에서 먼저 막고, 그래도 오면 토스트 |
| `L007` | 종료·취소된 방송에 발언 | 입력창 비활성화 |
| `L001` | 존재하지 않는 라이브 | 목록으로 이동 |

`L009` 기준은 **앞뒤 공백을 제거한 뒤 1~500자**입니다. FE에서 막아도 서버 기준과 어긋날 수 있으니 에러 처리는 남겨 두시는 편이 안전합니다.

### 허용 오리진

`cors.allowed-origins`를 따릅니다(로컬 기본값 `http://localhost:5173`). 다른 오리진에서 붙으면 핸드셰이크가 **403**입니다. HTTP CORS와 별개 설정이라 배포 시 함께 확인이 필요합니다.

## 7. FE에서 직접 확인하는 방법

### 7-1. 서버 띄우기

레포 루트에서:

```bash
docker compose up -d postgres redis minio
```

```bash
cd BE && ./gradlew bootRun
```

준비 확인 — `200`이 나오면 됩니다.

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/api/health
```

### 7-2. 테스트용 회원·라이브 만들기

회원가입은 이메일 인증 토큰이 필요해서, 확인용 데이터는 DB로 직접 넣는 편이 빠릅니다.

```bash
docker exec vintib-postgres psql -U postgres -d vintib -t -A -c "INSERT INTO member (email, password, name, nickname, onboarding_completed, created_at, updated_at) VALUES ('fe-check-'||gen_random_uuid()||'@example.com','encoded','FE검증','fe-'||substr(gen_random_uuid()::text,1,8),true,now(),now()) RETURNING id;"
```

출력된 회원 ID를 아래 `356` 자리에 넣으세요.

```bash
docker exec vintib-postgres psql -U postgres -d vintib -t -A -c "INSERT INTO live (host_id, title, status, started_at, peak_viewer_count, created_at, updated_at) VALUES (356,'FE 검증 라이브','LIVE',now(),0,now(),now()) RETURNING id;"
```

### 7-3. 이력 조회는 curl로 바로 확인

```bash
curl -s "http://localhost:8080/api/lives/193/chat-messages?size=5"
```

인증 헤더가 없어도 `"success": true`가 나옵니다. `193`은 위에서 만든 라이브 ID입니다.

### 7-4. 실시간 채팅 검증 스크립트

**FE가 쓸 라이브러리(`@stomp/stompjs`)로 동작을 확인하는 스크립트입니다.** 아래를 실행하면 8개 항목을 한 번에 봅니다.

```bash
mkdir -p /tmp/stomp-check && cd /tmp/stomp-check && npm init -y && npm i @stomp/stompjs ws
```

`fe-client.mjs`:

```javascript
// 브라우저에는 WebSocket 이 전역으로 있지만 Node 에는 없어서 ws 를 주입한다.
// FE 앱에서는 webSocketFactory 줄이 불필요하다.
import { Client } from '@stomp/stompjs';
import WebSocket from 'ws';
import { createHmac } from 'node:crypto';

const WS_URL = process.env.WS_URL ?? 'ws://localhost:8080/ws';
const SECRET = process.env.JWT_SECRET ?? 'local-dev-only-secret-key-please-change-in-prod-0123456789';
const LIVE_ID = process.env.LIVE_ID;
const MEMBER_ID = process.env.MEMBER_ID ?? '1';

const b64 = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
function mintToken(memberId) {
  const now = Math.floor(Date.now() / 1000);
  const head = b64({ alg: 'HS256', typ: 'JWT' });
  const body = b64({ sub: String(memberId), email: `fe-check-${memberId}@example.com`, iat: now, exp: now + 900 });
  const sig = createHmac('sha256', SECRET).update(head + '.' + body).digest('base64url');
  return head + '.' + body + '.' + sig;
}

const line = (label, ok, detail) =>
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${label.padEnd(36)} ${detail ?? ''}`);

function connect({ token }) {
  return new Promise((resolve, reject) => {
    const client = new Client({
      brokerURL: WS_URL,
      webSocketFactory: () => new WebSocket(WS_URL, { headers: { Origin: 'http://localhost:5173' } }),
      connectHeaders: token ? { Authorization: `Bearer ${token}` } : {},
      reconnectDelay: 0,
      onConnect: () => resolve(client),
      onStompError: (frame) => reject(new Error('STOMP ERROR: ' + frame.headers.message)),
      onWebSocketClose: () => reject(new Error('closed')),
    });
    client.activate();
  });
}

const waitFor = (ms = 5000) => {
  let resolve;
  const promise = new Promise((r) => { resolve = r; });
  const timer = setTimeout(() => resolve(null), ms);
  return { promise, hit: (v) => { clearTimeout(timer); resolve(v); } };
};

if (!LIVE_ID) {
  console.error('LIVE_ID 환경변수가 필요합니다.');
  process.exit(1);
}

const member = await connect({ token: mintToken(MEMBER_ID) });
const chat = waitFor();
member.subscribe(`/topic/lives/${LIVE_ID}/chat`, (f) => chat.hit(JSON.parse(f.body)));
const errors = waitFor();
member.subscribe('/user/queue/errors', (f) => errors.hit(JSON.parse(f.body)));

await new Promise((r) => setTimeout(r, 300));
member.publish({
  destination: `/app/lives/${LIVE_ID}/chat`,
  body: JSON.stringify({ content: 'FE 방식 검증', clientMessageId: 'tmp-fe-1' }),
});

const received = await chat.promise;
line('회원 발언 후 브로드캐스트 수신', received?.content === 'FE 방식 검증');
line('clientMessageId 그대로 돌아옴', received?.clientMessageId === 'tmp-fe-1', received?.clientMessageId ?? '');
line('senderNickname 채워짐', typeof received?.senderNickname === 'string', received?.senderNickname ?? '');
line('senderProfileImageUrl 은 null', received?.senderProfileImageUrl === null);

member.publish({
  destination: `/app/lives/${LIVE_ID}/chat`,
  body: JSON.stringify({ content: '   ', clientMessageId: 'tmp-fe-2' }),
});
const err = await errors.promise;
line('공백 메시지는 개인 에러 큐로', err?.error?.code === 'L009', err?.error?.code ?? '무응답');
member.deactivate();

const guest = await connect({ token: null });
line('비회원도 연결된다', guest.connected);
const guestErrors = waitFor();
guest.subscribe('/user/queue/errors', (f) => guestErrors.hit(JSON.parse(f.body)));
await new Promise((r) => setTimeout(r, 300));
guest.publish({
  destination: `/app/lives/${LIVE_ID}/chat`,
  body: JSON.stringify({ content: '비회원 발언', clientMessageId: 'tmp-fe-3' }),
});
const guestErr = await guestErrors.promise;
line('비회원 발언은 L008 로 거부', guestErr?.error?.code === 'L008', guestErr?.error?.code ?? '무응답');
guest.deactivate();

let rejected = false;
try {
  await connect({ token: 'this.is.not.a.valid.jwt' });
} catch {
  rejected = true;
}
line('잘못된 토큰은 연결 거부', rejected);

process.exit(0);
```

```bash
LIVE_ID=193 MEMBER_ID=356 node fe-client.mjs
```

기대 출력 (BE에서 실행해 확인한 결과):

```
PASS  회원 발언 후 브로드캐스트 수신
PASS  clientMessageId 그대로 돌아옴              tmp-fe-1
PASS  senderNickname 채워짐                   fe-c770975c
PASS  senderProfileImageUrl 은 null
PASS  공백 메시지는 개인 에러 큐로                     L009
PASS  비회원도 연결된다
PASS  비회원 발언은 L008 로 거부                    L008
PASS  잘못된 토큰은 연결 거부
```

> 스크립트가 로컬 기본 시크릿으로 토큰을 만듭니다. **로컬 확인 전용**이고, 실제 앱에서는 로그인 응답의 accessToken을 쓰세요.

### 7-5. Swagger

`http://localhost:8080/swagger-ui/index.html` → **라이브 채팅(Chat)** 태그에서 이력 조회 파라미터와 응답 스키마를 볼 수 있습니다. WebSocket은 Swagger에 나오지 않으니 이 문서와 `001` 문서를 봐 주세요.

## 8. 확인 부탁드릴 것

1. `connectHeaders` 방식으로 토큰을 넣는 구조인지 (URL 쿼리 아님)
2. 잘못된/만료 토큰은 **연결 자체가 거부**되므로 갱신 후 재연결 로직이 필요합니다
3. 이력 조회는 `page`가 아니라 `cursor`
4. `senderProfileImageUrl`은 당분간 `null` — 기본 아바타
5. **재접속 후 누락분 보충 방식**(5번 마지막)이 불편하면 `after` 커서를 추가하겠습니다

계약을 바꿔야 하는 부분이 있으면 이 문서나 `001` 문서에 이어서 적어 주시면 됩니다.