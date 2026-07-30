# 공개 라이브 목록 API 계약 요청 — 잔여 항목

- **요청 파트**: FE
- **대상 파트**: BE
- **관련 이슈**: `S15P11A108-413`, `S15P11A108-415`, `S15P11A108-418`
- **관련 화면**: 라이브 목록 `/lives`
- **상태**: 🟡 **대부분 반영 완료. `viewerCount` / `VIEWERS_DESC` 1건만 남음**

원 요청서의 나머지 항목은 `GET /api/lives` 구현으로 모두 반영되어 문서에서 덜어냈다.
아래는 **아직 못 준 것**과 **계약이 요청서와 달라진 부분**만 남긴 것이다.

---

## 아직 못 준 것 — `viewerCount`와 `VIEWERS_DESC` 정렬

현재 동시 시청자 수를 셀 수 있는 곳이 아직 없다. `live.peak_viewer_count`는 **최고치**이고
그마저 갱신하는 코드가 없다. 요청하신 "현재 동시 시청자 수"는 WebSocket 세션 집계가 있어야
나오는데, 그 작업이 [`S15P11A108-450`](https://ssafy.atlassian.net/browse/S15P11A108-450)로
아직 착수 전이다.

그래서 지금은 이렇게 나간다.

- 목록 응답의 `viewerCount`는 **항상 `null`**이다. 0으로 내리면 FE가 "시청자 0명"으로 표시해
  실제 값과 구분되지 않는다. **`null`이면 시청자 수 표시를 생략해 달라.**
- `sort=VIEWERS_DESC`는 **허용값에서 빠져 400**이 난다. 전부 `null`인 컬럼으로 정렬하면
  순서가 무의미해서, 값이 생긴 뒤에 여는 것이 맞다.

-450이 끝나면 `viewerCount`를 채우고 `VIEWERS_DESC`를 열면서 다시 알리겠다. 그때까지
FE 정렬 UI에서 "시청자 수 순"은 감춰 두시길 요청드린다.

## 계약이 요청서와 달라진 부분 (반영은 완료, 확인만 부탁드린다)

### 1. 카테고리가 단수 → 복수다

요청서의 `categoryId` / `categoryName`(단수)은 줄 수 없다. `live` 테이블에 카테고리 컬럼이
없고, 넣지 않기로 했다 — **편성 상품에서 유도한다.** 같은 사실을 두 군데 저장하면 반드시
어긋나기 때문이다(요청서 "BE에서 확정이 필요한 도메인 항목" 1번의 B안).

유도한 결과라 **라이브 하나가 카테고리를 여러 개 가진다.** 아우터·하의를 함께 파는 방송은
두 탭 모두에서 잡혀야 하므로 대표 하나를 뽑지 않았다. 요청서 2번에 적어 주신 대로 간다.

- 응답: `categoryId` + `categoryName` → **`categories: [{ id, name }]`**
- query: `categoryId` → **`categoryIds`(복수, 반복 파라미터)**
- 값은 항상 **대분류(depth 1)로 롤업**된다. 소분류 상품을 걸어도 응답에는 대분류가 나온다.
- 필터는 반대로 **대분류를 주면 하위 소분류 상품을 건 방송까지 잡힌다.** 소분류를 주면 정확 일치.
- `id`는 기존 `GET /api/categories`의 `id`와 같다 — 라이브 전용 endpoint는 만들지 않았다.

### 2. 페이지 응답은 `items`+`meta`가 아니라 공통 `PageResponse`다

프로젝트 공통 규격을 상품 목록 등에서 이미 쓰고 있어 라이브만 다르게 갈 수 없다.

```json
{ "content": [], "page": 0, "size": 12, "totalElements": 25, "totalPages": 3, "hasNext": true }
```

`items` → `content`, `meta.*` → 최상위 평탄화. FE adapter에서 흡수해 주시면 좋겠다.

### 3. 라이브 개설 요청에 `productIds`가 필수가 됐다

카테고리를 편성 상품에서 유도하므로, 상품 없는 방송은 카테고리도 없고 팔 것도 없는 빈 방이
된다. 그래서 **개설 시점에 판매할 상품을 반드시 고르게** 했다(예약·즉시 모두).
`POST /api/lives`, `POST /api/lives/schedule` 본문에 `productIds: [Long]`(최소 1개)가 추가됐고,
비어 있으면 400이다. **방송이 시작된 뒤에는 편성을 바꿀 수 없다.**

## 그대로 반영된 것

- 비회원 공개 — `SecurityConfig`에 `GET /api/lives` 추가
- 공개 목록은 `LIVE`·`SCHEDULED`만. `ENDED`·`CANCELED`는 **상태 query 허용값(400)과 결과 양쪽에서** 제외
- 빈 결과는 404가 아니라 200 + 빈 목록
- 잘못된 status/sort/범위 밖 page·size는 400 + 공통 에러 envelope
- 정렬 동률 시 마지막 기준 `liveId DESC`
- `LATEST`는 진행 중(시작 시각 내림차순)이 먼저, 그다음 예약(예정 시각 내림차순)
- `TITLE_ASC` 제공
- Swagger 문서화 + 통합 테스트(상태 필터·카테고리 필터·빈 목록·400)

## FE에서 확인 부탁

`VITE_LIVE_LIST_API_ENABLED`는 위 1~3의 adapter 수정 후 켜 주시면 된다.
`viewerCount`는 계속 `null`로 오므로, 플래그를 켜도 시청자 수만 비어 보이는 상태가 된다.