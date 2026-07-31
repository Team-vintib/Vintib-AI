# 007 Live/TryOn API 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 라이브 목록/상세/생성 연동 상태와 라이브 생성 보조, 영상 토큰, AI 시착 API 요청을 정리한다.
- 우선순위: P0
- 시연 필수 여부: 라이브 목록/상세/생성은 필수. 영상 토큰과 AI 시착은 실제 방송/시착 시연 범위에 따라 필수.

## 2. 현재 연동 상태

- 연동 완료 API
  - `GET /api/lives`
  - `GET /api/lives/{liveId}`
  - `POST /api/lives`
  - `POST /api/lives/schedule`
- FE 구현 완료 범위
  - 라이브 목록 화면
  - 라이브 상세/시청 화면
  - 라이브 즉시 생성/예약 생성 화면
  - 라이브에 연결할 상품 선택 UI
- 현재 임시 처리 또는 Mock 사용 여부
  - 생성용 상품 조회 전용 API가 없어 상품 선택 후보는 별도 연결이 필요하다.
  - 영상 송출 토큰과 AI 시착 생성은 실제 API가 없어 기능 연결이 보류되어 있다.
  - `thumbnailUrl`은 현재 FE에서 null 전송 가능하다.

## 3. 추가 구현 요청

### 3.1 생성용 연결 가능 상품 조회

- Method / Endpoint: `GET /api/lives/create/products`
- 요청 목적: 라이브 생성 시 현재 사용자가 연결할 수 있는 상품 목록을 조회한다.
- FE 사용처: `LiveCreatePage.vue`
- 요청 데이터
  - Header: `Authorization: Bearer {accessToken}`
  - Query: `page`, `size`, `keyword` 선택
- 응답 데이터: 기존 product card DTO 또는 간소 상품 DTO 목록
- 응답 예시

```json
{
  "success": true,
  "data": {
    "content": [
      {
        "productId": 1,
        "title": "빈티지 자켓",
        "thumbnailUrl": null,
        "saleStatus": "ON_SALE"
      }
    ],
    "page": 0,
    "size": 20,
    "totalElements": 1,
    "totalPages": 1,
    "hasNext": false
  },
  "error": null
}
```

### 3.2 영상 token 발급

- Method / Endpoint: `POST /api/lives/{liveId}/video-token`
- 요청 목적: 호스트 방송 송출 또는 시청 권한에 필요한 영상 서비스 토큰을 발급한다.
- FE 사용처: `LiveCreatePage.vue`, `LiveWatchPage.vue`
- 요청 데이터
  - Header: `Authorization: Bearer {accessToken}`
  - Path: `liveId`
  - Body: role 정책 필요 시 `role`: `HOST` | `VIEWER`
- 응답 데이터
  - `token`: string
  - `expiresAt`: string(datetime)
  - `roomId` 또는 `channelName`: string
- 응답 예시

```json
{
  "success": true,
  "data": {
    "token": "video-token",
    "roomId": "live-1",
    "expiresAt": "2026-07-31T13:00:00"
  },
  "error": null
}
```

### 3.3 라이브 AI 시착 생성

- Method / Endpoint: `POST /api/lives/{liveId}/products/{productId}/tryons`
- 요청 목적: 라이브 중 선택 상품에 대해 현재 사용자 시착 결과를 생성한다.
- FE 사용처: 라이브 시착 패널
- 요청 데이터
  - Header: `Authorization: Bearer {accessToken}`
  - Path: `liveId`, `productId`
- 응답 데이터
  - `tryonId`: number
  - `status`: `PENDING` | `PROCESSING` | `DONE` | `FAILED`
  - `resultImageUrl`: string | null
- 응답 예시

```json
{
  "success": true,
  "data": {
    "tryonId": 1,
    "status": "PENDING",
    "resultImageUrl": null
  },
  "error": null
}
```

### 3.4 사용자 시착 프로필 조회/저장

- Method / Endpoint: `GET /api/me/tryon`, `PUT /api/me/tryon`
- 요청 목적: AI 시착에 필요한 사용자 신체 프로필과 전신 사진을 조회/저장한다.
- FE 사용처: 온보딩 시착 단계, 라이브 시착 패널
- 요청 데이터: `002-onboarding-contract.md`의 `PUT /api/me/tryon`과 동일
- 응답 데이터: 시착 프로필 요약
- 응답 예시: `002-onboarding-contract.md` 참고

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용
  - 라이브 목록/상세 응답 필드는 현재 FE 연결 가능하므로 큰 변경 요청 없음
- 추가할 필드
  - 라이브 상세 `products[]`에 경매 가능 여부나 현재 경매 상태가 필요하면 추후 추가
- 변경 영향 범위
  - 라이브 상세 상품 큐
  - 경매 패널 초기화

## 5. 보류 또는 시연 제외 범위

- 현재 구현하지 않아도 되는 기능
  - 호스트 관리 UI가 없으면 `PATCH /api/lives/{liveId}/status` 연결 보류
  - 생성 후 상품 추가/삭제 UI가 없으면 관련 API 연결 보류
  - AI 시착 시연이 없으면 tryon 생성 API 보류
- 추후 구현 예정 기능
  - 방송 시작/종료/취소 관리
  - 라이브 상품 큐 편집
  - 시착 결과 목록/상세/삭제

## 6. 협의 필요 사항

- FE·BE 간 결정이 필요한 내용
  - 영상 token provider와 응답 필드명
  - 호스트/시청자 token 발급 정책
  - 생성용 상품 조회 필터 기준
  - AI 시착 결과 polling 또는 STOMP push 방식
- 아직 확정되지 않은 응답 구조나 정책
  - `thumbnailUrl` 필수 여부
  - 라이브 status enum 이름
  - 시착 실패 사유 응답 구조

## 7. 추가 요청 없음

- 이미 정상 연동된 API
  - `GET /api/lives`
  - `GET /api/lives/{liveId}`
  - `POST /api/lives`
  - `POST /api/lives/schedule`
- 기존 규격을 유지하면 되는 기능
  - 라이브 목록/상세 기본 렌더링
