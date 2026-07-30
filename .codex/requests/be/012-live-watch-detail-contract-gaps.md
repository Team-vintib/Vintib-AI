# Figma 라이브 시청 화면 API 비교 및 잔여 계약 요청

- 요청 파트: FE
- 대상 파트: BE
- 관련 작업: `S15P11A108-419` 및 후속 채팅·경매 패널 UI
- 관련 화면: `/lives/:liveId`
- 기준: `origin/develop-BE@dd6a0b6`, `.codex/requests/be/009-live-list-api-contract.md`

## 비교 범위

Figma 라이브 시청 화면에서 사용하는 방송 정보, 영상, 상품 큐, 선택 상품 정보, 판매자 팔로우,
상품 찜, 채팅, 반응 이모지와 경매 패널을 저장소 전체의 현재 API와 비교한다.

- 다른 화면이나 기능에서 이미 구현된 API도 재사용 가능한지 확인한다.
- 재사용 가능한 API는 새로 요청하지 않는다.
- 구현 예정 Jira가 확인된 항목은 작업 번호와 필요한 최종 계약만 기록한다.
- 현재 API와 예정 작업 모두에 없는 항목만 잔여 요청으로 정리한다.
- 구성이 변경된 AI 시착 영역은 이번 비교에서 제외한다.

## 확인 결과

`009-live-list-api-contract.md`의 최종 확정 내용을 확인했다.

- 공개 목록 `GET /api/lives`는 구현 완료됐다.
- 현재 시청자 수는 `S15P11A108-450` 전까지 `viewerCount: null`이다.
- `VIEWERS_DESC` 정렬은 현재 허용하지 않는다.
- 라이브 카테고리는 편성 상품에서 유도한 복수 `categories[]`로 제공한다.
- 시청 상세 `GET /api/lives/{liveId}`에도 `categories[]`가 반영됐다.
- 영상 접속 토큰은 별도 작업 `S15P11A108-449`가 담당한다.

아래는 Figma 화면의 각 영역을 현재 API로 구성할 수 있는지 대조한 결과다.

## 현재 API로 바로 구성 가능한 항목

| Figma 표시·동작 | 재사용 API 또는 필드 | 판단 |
| --- | --- | --- |
| 방송 ID·제목·상태 | `GET /api/lives/{liveId}` | 추가 요청 없음 |
| 판매자 닉네임 | `LiveDetailResponse.hostNickname` | 추가 요청 없음 |
| 방송 썸네일·영상 placeholder | `LiveDetailResponse.thumbnailUrl` | 실제 영상 연결 전까지 사용 가능 |
| 방송 경과 시간 | `startedAt`, 종료 방송은 `endedAt` | FE 계산 가능 |
| 최고 시청자 수 | `peakViewerCount` | 종료 방송에서만 사용 |
| 상품 큐 ID·제목·정렬 | `products[].productId`, `productTitle`, `sortOrder` | 추가 요청 없음 |
| 상품 이미지·가격·판매 유형·상태 | `GET /api/products/{productId}` | 상품별 상세 조회로 재사용 가능 |
| 브랜드명 | 상품 상세의 `brandId` + `GET /api/brands` | 기존 API 조합 가능 |
| 상품 찜 목록·등록·해제 | `GET/POST /api/users/{userId}/wishes`, `DELETE /api/users/{userId}/wishes/{productId}` | 기존 API 재사용 |
| 상품 상세 이동 | 기존 `/products/:productId` route와 상품 상세 조회 | 추가 요청 없음 |
| 라이브 카테고리 | `categories[].id`, `categories[].name` | 추가 요청 없음 |

상품 큐의 각 상품마다 상세 API를 호출하면 요청 수가 늘어난다. 기능 구현은 가능하므로 새 API가
반드시 필요한 것은 아니지만, 편성 상품 수가 많아질 수 있다면 라이브 상세 응답 보강이나 batch
조회 중 어느 방식을 사용할지 BE 성능 기준 확인이 필요하다.

## 현재 시청 상세 응답

```http
GET /api/lives/{liveId}
```

현재 `LiveDetailResponse`:

- 라이브: `id`, `hostId`, `hostNickname`, `title`, `thumbnailUrl`, `status`
- 시간: `scheduledAt`, `startedAt`, `endedAt`
- 시청자: `peakViewerCount`
- 상품: `products[].id`, `liveId`, `productId`, `productTitle`, `sortOrder`, `addedAt`
- 카테고리: `categories[].id`, `categories[].name`

`peakViewerCount`는 최고 시청자 수이므로 진행 중 화면의 현재 시청자 수로 사용하지 않는다.
`categories[]`는 FE DTO와 adapter에 반영한다.

## 잔여 요청 1. 현재 소개 상품 식별

상품 큐의 `NOW` 상태와 화면 진입 시 기본 선택 상품을 결정할 원천이 필요하다.

| 필드 후보 | 타입 | 규칙 확인 |
| --- | --- | --- |
| `currentProductId` | `Long/null` | 현재 소개 중인 상품. 예정·종료 또는 미선택이면 null |

별도 실시간 snapshot에서 제공할 예정이라면 해당 endpoint와 이벤트의 소유 작업을 알려 주기
바란다. FE는 계약 전까지 첫 상품을 화면 선택값으로만 사용하며 `NOW`로 확정하지 않는다.

## 잔여 요청 2. 상품 상세 표시 정보

상품 이미지·가격·판매 유형·상태 등급·사이즈는 기존 상품 상세 API로 조회할 수 있다. 다만
Figma 선택 상품 정보에 표시되는 아래 값은 현재 `ProductDetailResponse`와
`LiveProductResponse` 모두에 구조화된 필드가 없다.

실제로 부족한 필드:

| 항목 | 타입 후보 | 사용처 |
| --- | --- | --- |
| `material` | `String/null` | 선택 상품 정보 |
| `measurements` | object/null | 선택 상품 실측 |
| `defectSummary` | `String/null` | 하자 요약 |

`condition`은 기존 `conditionGrade`, 사이즈는 기존 `sizeLabel`을 재사용한다. 위 세 항목을
상품 설명에서 문자열로 파싱하지 않고 표시하려면 상품 상세 응답 또는 상품 등록 데이터에
구조화된 필드가 필요하다.

## 잔여 요청 3. 현재 판매자 팔로우 상태와 변경

Figma 헤더는 현재 방송 판매자의 팔로우 상태에 따라 `팔로우` 또는 활성 상태를 표시한다.
`APIs.md`에는 팔로우 후보 경로가 있지만 `origin/develop-BE`에는 팔로우 조회·등록·해제
controller가 확인되지 않았다.

필요한 동작:

- 현재 로그인 사용자가 `hostId`를 팔로우 중인지 확인
- 판매자 팔로우
- 판매자 팔로우 해제

아래 중 하나로 계약할 수 있다.

1. 라이브 상세 또는 판매자 조회 응답에 로그인 사용자 기준 `isFollowing`을 포함한다.
2. 별도 팔로우 상태 조회 API를 제공한다.

등록·해제는 공통 팔로우 API로 제공하고 라이브 전용 endpoint를 새로 만들 필요는 없다.
비회원, 본인 팔로우, 중복 팔로우와 팔로우하지 않은 판매자 해제 오류도 함께 확정이 필요하다.

## 구현 예정 계약 1. 실제 영상과 현재 시청자 수

현재 API에는 실제 영상 접속 토큰과 현재 동시 시청자 수가 없다. 아래 BE 작업이 이미 배정돼
있으므로 새 API 작업을 중복 요청하지 않는다.

| Jira | 내용 | FE 연결에 필요한 최종 정보 |
| --- | --- | --- |
| `S15P11A108-449` | OpenVidu 송출·시청 토큰 발급 | endpoint, room/session, viewer token, 만료·재발급, 상태별 오류 |
| `S15P11A108-450` | 실시간 시청자 수 집계 | 초기 `currentViewerCount`, 입장·퇴장 갱신 방식 |

`peakViewerCount`는 현재 시청자 수로 대체하지 않는다.

## 구현 예정 계약 2. 실시간 채팅

현재 Swagger와 BE 코드에는 시청자 채팅 API가 없지만 아래 작업이 이미 배정돼 있다.

- `S15P11A108-447`: WebSocket/STOMP 기반과 인증
- `S15P11A108-451`: 채팅 엔티티
- `S15P11A108-452`: 실시간 채팅 송수신
- `S15P11A108-453`: 과거 메시지 조회
- `S15P11A108-454`: 채팅 테스트

BE 계획에서 확인된 기본 경로:

- STOMP endpoint: `/ws`
- 메시지 발행: `/app/lives/{liveId}/chat`
- 메시지 구독: `/topic/lives/{liveId}/chat`
- 과거 메시지: cursor pagination REST
- 비회원은 읽기, 회원은 발언 가능

Figma 채팅 패널 연결 전에 아래 schema가 확정돼야 한다.

- 메시지 ID, 작성자 ID·닉네임·프로필 이미지, 본문, 생성 시각
- 과거 목록 cursor와 `hasNext`
- 전송 성공 ack 또는 client message ID
- 차단·삭제·숨김 메시지 처리
- 재접속 후 누락 메시지 보충 기준
- 방송 종료 후 읽기·쓰기 정책

## 잔여 요청 4. 경매 snapshot·입찰·실시간 event

현재 구현된 경매 API는 판매자가 조건을 설정하는
`POST /api/lives/{liveId}/auctions`뿐이다. Figma 시청자 경매 패널에 필요한 조회·입찰·결과
API는 아직 없다.

`APIs.md` 후보를 기준으로 필요한 계약:

| 화면 동작 | 후보 API | 필요한 값 |
| --- | --- | --- |
| 현재 진행 경매 조회 | `GET /api/auctions/{auctionId}` | 경매 ID, 상품 ID, 상태, 시작가, 현재가, 증액 단위, 다음 입찰가, 최고 입찰자, 종료 예정 시각 |
| 입찰 내역 | `GET /api/auctions/{auctionId}/bids` | cursor 목록, 입찰가, 입찰자 표시명, 생성 시각, 본인 입찰 여부 |
| 입찰 | `POST /api/auctions/{auctionId}/bids` | 요청 입찰가, 중복 클릭 방지 값, 성공 snapshot |
| 낙찰·유찰 결과 | `GET /api/auctions/{auctionId}/winner` | 결과 상태, 낙찰자, 낙찰가 |

라이브 진입 시 현재 `auctionId`를 얻는 방법도 필요하다. 라이브 상세에 현재 경매 ID를
포함하거나, `liveId` 기준 현재 경매 snapshot 조회 API가 필요하다.

STOMP event에는 최소한 아래 상태가 필요하다.

- 경매 시작과 현재 상품 변경
- 입찰 성공 후 현재가·최고 입찰자 변경
- 종료 임박 자동 연장과 변경된 종료 시각
- 낙찰·유찰·취소

REST snapshot과 STOMP event는 같은 경매 상태 enum과 필드명을 사용해야 한다.

## 조건부 잔여 요청 5. 반응 이모지

Figma 영상 영역의 하트·이모지가 사용자가 누르는 실시간 반응 기능이라면 reaction event가
필요하다. 단순 시각 효과라면 API는 필요하지 않다.

실제 기능일 경우 확인할 항목:

- 허용 reaction 종류
- STOMP 발행 destination과 구독 topic
- 사용자별 rate limit
- 서버 저장 또는 일시적 broadcast 여부

## 비교 제외

- AI 시착 진입 상태와 상세 팝업
  - Figma 구성이 변경됐고 `S15P11A108-419` 범위가 아니다.
  - 변경된 화면과 동작을 확인한 뒤 TRYON 작업에서 별도로 API를 비교한다.

## FE 처리

- `009`에서 확정한 `categories[]`를 시청 상세 DTO에 반영한다.
- 현재 시청자 수는 실제 API에서 `null`로 유지하고 최고 시청자 수로 대체하지 않는다.
- 실제 API에 `currentProductId`가 없으면 `NOW` 배지를 표시하지 않는다.
- 기존 상품 상세·브랜드·찜 API로 가져올 수 있는 값은 재사용한다.
- 구조화된 상품 정보, 팔로우, 경매·입찰 계약은 확정 전까지 mock view model로 표현한다.
- `S15P11A108-449` 영상 토큰과 `S15P11A108-450` 시청자 집계는 해당 작업 완료 후 별도로 연동한다.
- 채팅·경매 UI 구현은 각 스토리 브랜치에서 진행하며 이 문서는 공통 계약 기준으로 사용한다.
