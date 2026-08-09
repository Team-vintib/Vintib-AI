# HS042 라이브 선택 상품 정보 — "정보 준비 중" 제거

## 배경/목표

라이브 시청 화면의 "선택한 상품 정보" 패널이 값이 없는 항목마다 `정보 준비 중`을 띄운다.
실데이터로 확인해 보니(라이브 15 / 상품 23) BE 매핑 문제가 아니라 **값이 실제로 없는 것**이었고,
특히 하자는 `defects: []`(등록된 하자 없음)인데도 "준비 중"으로 표시돼 **구매자가 "아직 안 나온 정보"로
오해할 수 있는 잘못된 문구**다.

라이브 상품 응답(`LiveProductResponse`)이 담는 상품 필드는 `brandName / price / saleType / saleStatus /
conditionGrade / thumbnailUrl / material / measurements / defectSummary`뿐이라, 상품에는 있는
`sizeLabel`·`color`가 라이브에는 오지 않는다. BE에 필드 추가를 요청하는 대신 **이미 공개된
`GET /products/{id}`를 재사용**해 빈 칸을 채운다(BE 대기 없이 진행 — HS042 이전 계획들과 같은 판단).

## 작업 내용

### 1. 선택 상품 상세 조회 연결 (`LiveWatchPage.vue`)

`selectedProductId`를 watch해 바뀔 때마다 `getProductDetail(id)`를 1회 호출하고, 결과를
`Map<productId, ProductDetailViewData>`에 캐시한다. 같은 상품을 다시 선택하면 재호출하지 않는다.

- `GET /api/products/{id}`는 `permitAll`이라 **비회원 시청자도 호출 가능**하다(SecurityConfig 확인).
- 조회 실패는 무시하고 기존 라이브 응답 값으로 폴백한다 — 부가 정보 때문에 라이브 화면이 깨지면 안 된다.
- 라이브를 떠날 때(`onBeforeUnmount`, 시청 종료) 캐시를 비운다.
- 상품 전환 STOMP 이벤트·경매/구매 패널 로직은 건드리지 않는다.

### 2. 패널 표시 규칙 (`LiveSelectedProduct.vue`)

`정보 준비 중` 문구를 전부 걷어내고, 상품 상세에서 얻은 값으로 항목을 재구성한다.
표시 항목은 상품 상세 값 우선, 없으면 라이브 응답 값으로 폴백한다.

| 항목 | 출처 | 값이 없을 때 |
| --- | --- | --- |
| 브랜드 | 상세 `brand` | 항목 숨김 |
| 사이즈 | 상세 `sizeLabel` | 항목 숨김 |
| 색상 | 상세 `color` | 항목 숨김 |
| 소재 | 상세 `material` → 라이브 `material` | 항목 숨김 |
| 상태 | 상세 `conditionLabel` → 라이브 `condition` | 항목 숨김 |
| 실측 | 상세 `measurements` → 라이브 `measurements` | 항목 숨김 |
| 하자 | 상세 `sellerDisclosedDefects` → 라이브 `defectSummary` | **"없음"** |

- 상품 상세의 `specItems` 패턴과 동일하게, **값이 빈 항목은 행 자체를 만들지 않는다.**
- 하자만 예외로 "없음"을 명시한다 — 중고 거래에서 하자가 없다는 건 구매자에게 의미 있는 정보이고,
  BE 계약상 `defectSummary`가 null인 것은 "등록된 하자가 없음"을 뜻한다.
- 단, 상세 조회가 아직 안 끝났거나 실패했고 라이브 값도 없으면 "없음"을 단정하지 않고 숨긴다
  (BE가 "상품 행을 못 찾은 경우"에도 모든 필드가 null이 되므로 거짓 표시가 될 수 있다).
- **하자는 문장이 아니라 개수(`N개`)로 보여준다.** 다른 항목과 같은 좁은 칸에 들어가야 하고,
  판매자가 쓴 문장 전체는 상품 상세에서 읽으면 된다. 라이브 폴백일 때는 `defectSummary`가
  쉼표로 이어 붙인 한 줄이라 쉼표로 나눠 센다.
- AI 검수 이미지·findings는 이번 범위에서 제외한다. 이 패널에 넣을 공간이 없고, 상품 상세의
  `type`/`location` 미노출 문제가 아직 BE 대기 중이다.

### 2-1. 항목 배치

항목은 2열 그리드에 행 방향으로 흐른다. 값이 없는 항목을 지우고 남은 것만 배치하므로
6개면 3·3, 5개면 3·2로 자동으로 균등해진다. 특정 항목이 열 전체를 차지하게 만들지 않는다 —
그러면 한쪽으로 쏠려 보인다.

라벨 열 너비는 46px에서 58px로 넓힌다. `브랜드:`·`사이즈:`처럼 3글자 라벨이 새로 들어와
기존 폭으로는 잘린다.

### 3. 상품 큐 브랜드 줄 (`LiveProductQueue.vue`) — 구매자 화면에만 적용

브랜드가 없을 때 `브랜드 정보 준비 중` 대신 그 줄 자체를 렌더링하지 않는다.
큐는 라이브 응답만 쓰므로 상세 조회를 붙이지 않는다 — 큐 항목 수만큼 호출이 늘어난다.

**이 컴포넌트는 시청자·판매자 두 화면이 공유하므로, 판매자 방송 화면은 현행(`브랜드 정보 준비 중`)을
그대로 유지한다.** `hideBrandWhenEmpty` prop(기본 `false`)을 추가하고 `LiveWatchPage`에서만 `true`를
넘겨 동작을 가른다. 기본값이 현행이라 `LiveBroadcastPage`는 호출부를 손대지 않아도 그대로 남는다.

## 구현 목록

- [x] `LiveWatchPage`: `selectedProductId` watch → `getProductDetail` 호출 + 캐시 + 실패 무시
- [x] `LiveWatchPage`: 라이브 이탈 시 캐시 초기화
- [x] `LiveSelectedProduct`: 상세/라이브 병합 props 수신, 항목 목록을 배열+필터 구조로 전환
- [x] `LiveSelectedProduct`: 브랜드·사이즈·색상 항목 추가, 빈 항목 숨김
- [x] `LiveSelectedProduct`: 하자를 개수(`N개`)로 표시, 0건이면 `없음`
- [x] `LiveSelectedProduct`: 라벨 열 46px → 58px (3글자 라벨 잘림 해결)
- [x] `LiveProductQueue`: `hideBrandWhenEmpty` prop 추가(기본 `false`), `LiveWatchPage`에서만 전달
- [x] 타입체크·린트 통과
- [x] 라이브 15(상품 23) 확인 — 사이즈 L·색상 BEIGE 표시, 브랜드·실측 숨김,
      큐 브랜드 줄 사라짐, `/api/products/23` 1회만 호출
- [x] 라이브 16 확인 — 6개 항목이면 3·3, 5개면 3·2로 균등 배치. 라벨 잘림 없음
- [x] 판매자 방송 화면 — `LiveBroadcastPage`가 prop을 넘기지 않아 기본값(현행)으로 유지됨을 코드로 확인

## 확인이 필요한 사항

- **추가 호출 1건**: 상품을 전환할 때마다 `GET /products/{id}`가 나간다. 응답에 `similarProducts`·
  `aiQualityAnalysis`·`images`·판매자 정보까지 실려 필요보다 무겁다. 라이브당 상품 수가 적고 캐시가
  있어 부담은 크지 않다고 봤지만, 문제가 되면 BE에 라이브 상품 응답으로 `sizeLabel`·`color` 추가를
  요청(`docs/requests/BE/`)해 이 호출을 없앨 수 있다.
- **하자 개수는 사실상 0 또는 1만 나온다.** 등록 화면(`resolveRegistrationDefects`)이 판매자가 쓴
  하자 설명을 통째로 배열 항목 **하나**에 담아 보내기 때문이다. 판매자가 하자를 세 가지 적어도
  `1개`로 표시된다. 실제 건수를 세려면 등록 화면에서 하자를 항목 단위로 입력받도록 바꿔야 하고,
  그건 등록 흐름 변경이라 별도 작업이다. 지금 서버 데이터는 하자를 등록한 상품이 아예 없어
  (상품 45건 확인) 전부 `없음`으로 나온다 — `N개` 경로는 실데이터로 확인하지 못했다.
- **판매자 화면은 이번 범위가 아니다(확정)**. `LiveSelectedProduct`는 시청자 전용이라 애초에 영향이
  없고, 공유 컴포넌트인 `LiveProductQueue`는 prop 기본값을 현행으로 둬서 판매자 화면이 그대로
  남도록 한다. 판매자 방송 화면에도 같은 정리가 필요해지면 별도 작업으로 잡는다.
