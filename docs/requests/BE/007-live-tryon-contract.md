# 007 Live/TryOn API 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 라이브 목록/상세/생성 연동 상태와 라이브 생성 보조, 영상 토큰, AI 시착 API 요청을 정리한다.
- 우선순위: P0
- 시연 필수 여부: 라이브 목록/상세/생성은 필수. 영상 토큰과 AI 시착은 실제 방송/시착 시연 범위에 따라 필수.

## 2. 현재 연동 상태

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

### 3.5 라이브 시청 화면 상품/상세 필드 보강 (LIVE-005) — 필수 항목 구현 완료, 선택 항목 일부 남음

`LiveProductResponse`(필수 요청 4개 전부 반영, 이름 2개는 다름):
- `brandName`: string | null — 반영됨
- `price`: number | null — 반영됨
- `thumbnailUrl`: string | null — 반영됨
- `saleType`: 반영됨. 단 값이 `AUCTION | FIXED_PRICE`가 아니라 **`AUCTION | DIRECT_SALE`**이다 (`FIXED_PRICE`는 이 프로젝트에서 안 쓰는 이름 — PROD-005 상시 판매 표기와 통일)
- `condition`(선택) → **`conditionGrade`**라는 이름으로 반영됨(등급 체계 미확정이라 자유 문자열, enum으로 굳히지 말 것)
- `material`/`measurements`/`defectSummary`(선택) — 아직 없음

`LiveDetailResponse`:
- `currentProductId`: number | null — 반영됨
- `hostProfileImageUrl`(선택) — 아직 없음
- `description`(선택) — 아직 없음

- **필요 없는 것(FE 미사용)**: `LiveProductResponse`의 `addedAt`, `liveId`, 연결 `id`는 시청 화면에서 쓰지 않는다 → 유지/제거는 BE 판단(우선순위 낮음). 그대로 유지됨.

### 3.6 상품 상세 AI 시착 생성 (TRYON-003)

- 대상: 상품 상세(`ProductDetailView`)의 AI 시착 팝업 (라이브 밖, 상품 단위 시착)
- 배경: 상품 상세 "AI 시착" 버튼에 팝업(모달)을 구현했다. 등록 상품 이미지를 회원 전신 사진에 합성(TRYON-003). BE에 (a) 회원 전신 사진 조회, (b) 상품 단위 시착 생성 API가 없어 팝업은 mock으로 동작한다.
- 요청
  - **전신 사진 조회**: `GET /api/users/{userId}/tryon`(시착 프로필, 구현 완료 — `docs/requests/FE/009-tryon-profile-presigned-upload.md` 참고)로 회원 전신 사진 URL을 내려주면 팝업 초기 이미지로 사용한다.
  - **상품 시착 생성(비 라이브)**: `POST /api/users/{userId}/tryons` 또는 `POST /api/products/{productId}/tryons` — 상품 이미지 + 회원 전신 사진 합성 결과를 생성한다. 3.3(라이브 시착 생성)과 같은 합성이나 라이브 컨텍스트가 아니다.
  - 응답: `tryonId`, `status`(`PENDING|PROCESSING|DONE|FAILED`), `resultImageUrl`(null 가능). polling vs STOMP push 방식은 3.3과 동일 정책을 따른다.
- 참고: 시착 결과 저장(TRYON-005)은 "추가" 우선순위로 이번 범위 밖. 결과 조회/삭제(`GET`/`DELETE /api/users/{userId}/tryons`)는 이미 존재한다.

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용
  - 3.5 필수 필드는 반영 완료. 남은 건 선택 필드(호스트 프로필 이미지, 방송 설명, 상품 소재/치수/하자 요약)뿐
- 추가할 필드
  - 3.5 참고 — `LiveDetailResponse.hostProfileImageUrl`/`description`, `LiveProductResponse.material`/`measurements`/`defectSummary`
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
  - 생성용 상품 조회 필터 기준
  - AI 시착 결과 polling 또는 STOMP push 방식
- 아직 확정되지 않은 응답 구조나 정책
  - 라이브 status enum 이름
  - 시착 실패 사유 응답 구조

## 7. 추가 요청 없음

- 이미 정상 연동된 API: 없음
- 기존 규격을 유지하면 되는 기능: 없음
