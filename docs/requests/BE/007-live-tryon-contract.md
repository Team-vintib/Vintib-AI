# 007 Live/TryOn API 요청 (AI 시착만 남음)

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: **AI 시착 생성 API**를 요청한다. 라이브 쪽 항목은 전부 반영돼 이 문서에서 뺐다.
- 우선순위: P0
- 시연 필수 여부: AI 시착 시연 범위에 따라 결정

> **2026-08-03 정윤 정리** — 라이브 관련 요청은 모두 처리됐다. 무엇을 어떻게 반영했는지는
> `docs/requests/FE/016-pre-auction-batch-handoff.md`에 정리해 뒀다.
>
> | 원래 항목 | 결과 |
> | --- | --- |
> | 3.1 생성용 연결 가능 상품 조회 | **기존 API로 충족** — `GET /api/users/{userId}/products`(본인 상품 전체, DRAFT 포함). 새 엔드포인트를 만들지 않았다 |
> | 3.5 `LiveProductResponse` 필드 보강 | **반영 완료** — brandName·price·thumbnailUrl·saleType·conditionGrade |
> | 3.5 `LiveDetailResponse.currentProductId` | **반영 완료** |
> | 3.5 `LiveDetailResponse.hostProfileImageUrl` | **반영 완료** |
> | 3.5 `LiveDetailResponse.description` | **반영 완료** — 개설 요청에도 `description`(선택, 1000자)이 추가됐다 |
> | 3.5 `material`/`measurements`/`defectSummary` | **미반영** — 선택 항목이고 상품 상세(`GET /api/products/{id}`)에 이미 있다. 시청 화면 카드에 넣으면 편성 상품 수만큼 상세를 더 읽어야 한다 |
> | 3.5 불필요 필드(`addedAt`·`liveId`·연결 `id`) 제거 | **미반영(유지)** — 이미 쓰고 있는 FE 코드가 깨진다. 남아 있어도 무시하면 된다 |
> | 5. `PATCH /api/lives/{liveId}/status` | **연결 가능** — 전이 결과가 `/topic/lives/{liveId}/status`로 전파된다 |

## 2. 현재 연동 상태

- FE 구현 완료 범위: 라이브 목록/상세/생성, 상품 선택 UI, 라이브 시착 패널, 상품 상세 시착 팝업
- 현재 임시 처리: 시착 생성은 실제 API가 없어 mock으로 동작한다.

## 3. 추가 구현 요청

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

```json
{
  "success": true,
  "data": { "tryonId": 1, "status": "PENDING", "resultImageUrl": null },
  "error": null
}
```

### 3.6 상품 상세 AI 시착 생성 (TRYON-003)

- 대상: 상품 상세(`ProductDetailView`)의 AI 시착 팝업 (라이브 밖, 상품 단위 시착)
- 요청
  - **전신 사진 조회**: `GET /api/users/{userId}/tryon`(시착 프로필, 구현 완료)로 회원 전신 사진 URL을 내려주면 팝업 초기 이미지로 사용한다.
  - **상품 시착 생성(비 라이브)**: `POST /api/users/{userId}/tryons` 또는 `POST /api/products/{productId}/tryons`
  - 응답: `tryonId`, `status`(`PENDING|PROCESSING|DONE|FAILED`), `resultImageUrl`(null 가능)
- 참고: 시착 결과 저장(TRYON-005)은 "추가" 우선순위로 범위 밖. 결과 조회/삭제는 이미 존재한다.

## 6. 협의 필요 사항

- AI 시착 결과 polling 또는 STOMP push 방식
- 시착 실패 사유 응답 구조
