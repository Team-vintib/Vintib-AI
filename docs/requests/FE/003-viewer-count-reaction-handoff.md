# 시청자 수 · 반응 이모지 인계 — Phase 3 완료

- **요청 파트**: BE
- **대상 파트**: FE
- **관련 이슈**: `S15P11A108-450`(시청자 수), `-471`(반응 이모지)
- **상태**: ✅ **구현 완료, 바로 붙일 수 있다**
- **계약 상세**: `001-live-stomp-contract.md` 8·9번 절 (이 문서는 "무엇이 되고 어떻게 확인하는가")

---

## 1. 한 줄 요약

**라이브 시청자 수가 실시간으로 오고, 반응 이모지를 주고받을 수 있다.** 그리고 라이브 목록의
`viewerCount`가 드디어 실제 값이 됐다 — **이 필드의 타입이 바뀌었으니 아래 2번을 꼭 봐 달라.**

## 2. ⚠️ 깨질 수 있는 변경 — `viewerCount`가 `null`을 주지 않는다

`.codex/requests/be/009-live-list-api-contract.md`에서 "`viewerCount`는 항상 `null`이니 표시를
생략해 달라"고 전달했었다. **그 안내는 이제 폐기다.**

| | 이전 | 지금 |
| --- | --- | --- |
| 타입 | `Integer` (항상 `null`) | `int` (**항상 값이 있다**) |
| 아무도 안 볼 때 | `null` | `0` |
| `sort=VIEWERS_DESC` | 400 | ✅ 200 |

`null` 체크로 "시청자 수 숨기기"를 하고 있었다면 **그 분기는 이제 절대 타지 않는다.** 0명인
방송은 `0`으로 표시하거나, 진행 전(`SCHEDULED`) 방송에서만 숨기는 쪽으로 바꿔 주면 된다.

`VITE_LIVE_LIST_API_ENABLED`를 켜는 데 남아 있던 마지막 걸림돌이 이것이었다. 이제 없다.

> 이로써 `.codex/requests/be/009-live-list-api-contract.md`의 마지막 잔여 항목이 해소되어 그
> 요청 문서는 삭제했다. 그 문서에 적혀 있던 계약 차이(카테고리 복수, `PageResponse` 규격,
> `productIds` 필수)는 이미 반영·전달된 내용이고 Swagger가 단일 기준이다.

## 3. 어디까지 구현됐는가

| 기능 | 상태 | 비고 |
| --- | --- | --- |
| 현재 동시 시청자 수 집계 | ✅ | 세션 단위. 한 사람이 여러 토픽을 구독해도 1명 |
| `/topic/lives/{liveId}/viewers` 브로드캐스트 | ✅ | 들어오거나 나갈 때 |
| 라이브 상세 `currentViewerCount` | ✅ | **화면 진입 시 초기값** |
| 라이브 목록 `viewerCount` | ✅ | 실제 값 |
| `sort=VIEWERS_DESC` | ✅ | 아래 6번의 제약 하나 있음 |
| 최고 시청자 수(`peakViewerCount`) 기록 | ✅ | 넘어설 때만 갱신되고 종료 후에도 남는다 |
| 반응 발행·구독 | ✅ | `HEART` / `FIRE` / `CLAP` / `WOW` |
| 반응 rate limit | ✅ | 초당 5건, 초과 시 `L011` |
| 반응 이력 조회 | ❌ **없다** | 저장하지 않기로 확정. 중간 입장자는 이전 반응을 못 본다 |
| 영상(OpenVidu) | ❌ Phase 4 | |
| 현재 소개 상품 `NOW` 배지 | ❌ Phase 5 | |
| 경매 | ❌ Phase 6~8 | |

## 4. 붙이는 순서

### 시청자 수

```ts
// 1) 화면 진입 — 초기값은 REST 에서
const { currentViewerCount } = await fetchLiveDetail(liveId);
viewerCount.value = currentViewerCount;

// 2) 이후 변화만 토픽으로
client.subscribe(`/topic/lives/${liveId}/viewers`, (frame) => {
  const { viewerCount: count } = JSON.parse(frame.body);
  viewerCount.value = count;
});

// 3) 화면 이탈 — 구독을 끊어야 시청자에서 빠진다
subscription.unsubscribe();
```

**2번만 하면 화면이 비어 있다.** 구독 직후 자기 세션에 브로드캐스트가 오는 것은 보장되지 않고,
다음 프레임은 다른 사람이 들고 날 때까지 오지 않는다.

### 반응

```ts
// 발행 (회원만)
client.publish({
  destination: `/app/lives/${liveId}/reactions`,
  body: JSON.stringify({ type: 'HEART' }),
});

// 구독 — 자기 것은 걸러낸다
client.subscribe(`/topic/lives/${liveId}/reactions`, (frame) => {
  const reaction = JSON.parse(frame.body);
  if (reaction.senderId === myMemberId) return; // 이미 낙관적으로 그렸다
  floatEmoji(reaction.type);
});
```

## 5. 테스트 가이드

### 준비

```bash
docker compose up -d postgres redis
```

```bash
cd BE && ./gradlew bootRun
```

Swagger: `http://localhost:8080/swagger-ui/index.html`

### 5-1. 시청자 수가 실제로 오르내리는지 (브라우저 콘솔 2개)

`wscat`이나 브라우저 콘솔에서 두 연결을 만든다. 아래는 콘솔용 최소 코드다.

```js
// 탭 A — 관찰자
const a = new WebSocket('ws://localhost:8080/ws');
a.onmessage = (e) => console.log('A:', e.data);
a.onopen = () => {
  a.send('CONNECT\naccept-version:1.2\nhost:localhost\n\n\0');
  setTimeout(() => a.send('SUBSCRIBE\nid:sub-0\ndestination:/topic/lives/1/viewers\n\n\0'), 300);
};
```

```js
// 탭 B — 들어왔다 나가는 시청자
const b = new WebSocket('ws://localhost:8080/ws');
b.onopen = () => {
  b.send('CONNECT\naccept-version:1.2\nhost:localhost\n\n\0');
  setTimeout(() => b.send('SUBSCRIBE\nid:sub-0\ndestination:/topic/lives/1/chat\n\n\0'), 300);
};
// 나중에: b.close();
```

**확인할 것**

1. 탭 B가 구독하면 탭 A에 `{"liveId":1,"viewerCount":2}`가 온다
2. `b.close()` 하면 탭 A에 `viewerCount:1`이 온다
3. 탭 B에서 **같은 방송의 다른 토픽을 더 구독해도** 숫자가 안 오른다 (한 사람이 1명)
4. `GET /api/lives/1`의 `currentViewerCount`가 지금 붙어 있는 수와 같다

### 5-2. 최고 시청자 수가 기록되는지

1. 위 상태에서 2명까지 만들고 한 명을 끊는다 → `currentViewerCount`는 1
2. `GET /api/lives/1`의 `peakViewerCount`는 **2 그대로** 남아 있어야 한다

### 5-3. 반응

토큰이 필요하다. 로그인 응답의 access token을 CONNECT 헤더에 실는다.

```js
const c = new WebSocket('ws://localhost:8080/ws');
c.onmessage = (e) => console.log(e.data);
c.onopen = () => {
  c.send(`CONNECT\naccept-version:1.2\nhost:localhost\nAuthorization:Bearer ${TOKEN}\n\n\0`);
  setTimeout(() => {
    c.send('SUBSCRIBE\nid:r\ndestination:/topic/lives/1/reactions\n\n\0');
    c.send('SUBSCRIBE\nid:e\ndestination:/user/queue/errors\n\n\0');
  }, 300);
};
// 발행
const send = (type) =>
  c.send(`SEND\ndestination:/app/lives/1/reactions\ncontent-type:application/json\n\n{"type":"${type}"}\0`);
```

**확인할 것**

| 시도 | 기대 |
| --- | --- |
| `send('HEART')` | `/topic/.../reactions`로 `senderId`가 담긴 payload |
| `send('HEART')` 8번 연타 | 5건만 오고, `/user/queue/errors`에 `L011` |
| `send('MIDDLE_FINGER')` | `/user/queue/errors`에 `C001` (조용히 무시되지 않는다) |
| 토큰 없이 연결해 발행 | `L010` |
| 종료된 방송에 발행 | `L007` |

### 5-4. 목록 정렬

```bash
curl "http://localhost:8080/api/lives?sort=VIEWERS_DESC&size=12"
```

시청자가 붙어 있는 방송이 위로 온다. 전부 0명이면 `id` 내림차순이다.

### 5-5. 자동 테스트

```bash
cd BE && ./gradlew test --tests '*LiveViewerServiceTest' --tests '*LiveViewerCountStompTest' --tests '*LiveReactionStompControllerTest'
```

## 6. 알아 둘 제약

### `sort=VIEWERS_DESC`는 최대 500개 방송까지만 정렬한다

시청자 수는 Redis에만 있는 값이라 `ORDER BY`로 걸 컬럼이 없다. 서버가 후보를 읽어 메모리에서
세우고 페이지를 잘라낸다. 그래서 이 정렬에서는 **`totalElements`가 전체 개수가 아니라 정렬
대상이 된 수**다. 공개 목록에 나올 수 있는 방송(예정·진행 중)이 500개를 넘을 일이 없어 실제로는
차이가 없지만, 넘어서면 그때 스키마를 바꿔 SQL 정렬로 옮긴다.

### 서버 재기동 시 시청자 수가 0으로 리셋된다

Redis에만 있는 휘발성 값이다. 실제로 보고 있던 사용자는 재연결하면서 다시 집계되므로 몇 초 안에
복구된다. **배포 직후 잠깐 낮게 보이는 것은 정상이다.**

(반대로 이 초기화가 없으면 프로세스가 죽었을 때 "아무도 없는 방송에 300명"이 영구히 남는다.)

### 반응은 되돌아볼 수 없다

이력 API가 없다. 중간 입장자에게 이전 반응을 보여주는 UI는 만들 수 없다.

### 시청자 수는 "구독 중인 세션 수"다

같은 사람이 **다른 기기나 다른 탭에서** 보면 2명으로 잡힌다. 회원 단위로 세지 않는 이유는
비회원 시청자도 세야 하기 때문이다 — 비회원은 식별자가 세션뿐이다.

## 7. FE에서 확인 부탁

1. **`viewerCount`의 `null` 분기 제거** (2번) — 가장 중요하다
2. 시청자 수 초기값을 라이브 상세에서 받고 있는지
3. 화면 이탈 시 `unsubscribe()` 호출 — 안 하면 시청자 수가 줄지 않는다
4. 목록 화면에서 카드마다 토픽을 미리 구독하지 않는지
5. 반응에서 `senderId`로 자기 것을 걸러내는지
6. `L011`에 토스트를 띄우지 않는지 (하트 연타는 정상 사용이다)

바꿔야 할 부분이 있으면 이 문서에 이어서 적어 주시면 된다.
