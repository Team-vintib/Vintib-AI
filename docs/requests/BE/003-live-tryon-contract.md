# 003 Live/TryOn API 요청 (AI 시착만 남음)

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: **AI 시착 생성 API**를 요청한다. 라이브 쪽 항목은 전부 반영돼 이 문서에서 뺐다.
- 우선순위: P0
- 시연 필수 여부: AI 시착 시연 범위에 따라 결정

> **2026-08-04 정윤 정리** — 3.5의 선택 필드까지 전부 반영됐다. 라이브 쪽은 AI 시착을 빼면
> 남은 게 없다. 반영 내용은 `docs/requests/FE/022-pre-auction-batch-handoff.md`,
> `027-live-optional-fields-and-notifications.md` 참고.
>
> | 원래 항목 | 결과 |
> | --- | --- |
> | 3.1 생성용 연결 가능 상품 조회 | **기존 API로 충족** — `GET /api/users/{userId}/products`(본인 상품 전체, DRAFT 포함). 새 엔드포인트를 만들지 않았다 |
> | 3.5 `LiveProductResponse` 필드 보강 | **반영 완료** — brandName·price·thumbnailUrl·saleType·conditionGrade |
> | 3.5 `LiveDetailResponse.currentProductId` | **반영 완료** |
> | 3.5 `LiveDetailResponse.hostProfileImageUrl` | **반영 완료** |
> | 3.5 `LiveDetailResponse.description` | **반영 완료** — 개설 요청에도 `description`(선택, 1000자)이 추가됐다 |
> | 3.5 `material`/`measurements`/`defectSummary` | **반영 완료(2026-08-04)** — `LiveProductResponse`에 추가. 하자는 목록이 아니라 쉼표로 이어붙인 한 줄 요약(`defectSummary`)이다 |
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

### 3.5 라이브 시청 화면 상품/상세 필드 보강 (LIVE-005) — 전부 반영 완료

`LiveProductResponse`(필수 4개 + 선택 3개 전부 반영, 이름 2개는 다름):
- `brandName`: string | null — 반영됨
- `price`: number | null — 반영됨
- `thumbnailUrl`: string | null — 반영됨
- `saleType`: 반영됨. 단 값이 `AUCTION | FIXED_PRICE`가 아니라 **`AUCTION | DIRECT_SALE`**이다 (`FIXED_PRICE`는 이 프로젝트에서 안 쓰는 이름 — PROD-005 상시 판매 표기와 통일)
- `condition`(선택) → **`conditionGrade`**라는 이름으로 반영됨(등급 체계 미확정이라 자유 문자열, enum으로 굳히지 말 것)
- `material`(선택): string | null — 반영됨
- `measurements`(선택): 키-값(cm) | null — 반영됨
- `defectSummary`(선택): string | null — 반영됨. **목록이 아니라 한 줄 요약이다** — 등록된 하자 항목을 쉼표로 이어 붙인 문자열(예: `"밑단 오염, 우측 소매 실밥 풀림"`). 상세 목록이 필요하면 상품 상세(`GET /api/products/{id}`)를 연다

`LiveDetailResponse`:
- `currentProductId`: number | null — 반영됨
- `hostProfileImageUrl`(선택): string | null — 반영됨
- `description`(선택): string | null — 반영됨

- **필요 없는 것(FE 미사용)**: `LiveProductResponse`의 `addedAt`, `liveId`, 연결 `id`는 시청 화면에서 쓰지 않는다 → 유지/제거는 BE 판단(우선순위 낮음). 그대로 유지됨.

### 3.6 상품 상세 AI 시착 생성 (TRYON-003)

- 대상: 상품 상세(`ProductDetailView`)의 AI 시착 팝업 (라이브 밖, 상품 단위 시착)
- 요청
  - **전신 사진 조회**: `GET /api/users/{userId}/tryon`(시착 프로필, 구현 완료 — `docs/requests/FE/015-tryon-profile-presigned-upload.md` 참고)로 회원 전신 사진 URL을 내려주면 팝업 초기 이미지로 사용한다.
  - **상품 시착 생성(비 라이브)**: `POST /api/users/{userId}/tryons` 또는 `POST /api/products/{productId}/tryons` — 상품 이미지 + 회원 전신 사진 합성 결과를 생성한다. 3.3(라이브 시착 생성)과 같은 합성이나 라이브 컨텍스트가 아니다.
  - 응답: `tryonId`, `status`(`PENDING|PROCESSING|DONE|FAILED`), `resultImageUrl`(null 가능). polling vs STOMP push 방식은 3.3과 동일 정책을 따른다.
- 참고: 시착 결과 저장(TRYON-005)은 "추가" 우선순위로 이번 범위 밖. 결과 조회/삭제(`GET`/`DELETE /api/users/{userId}/tryons`)는 이미 존재한다.

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용
  - 3.5 필수·선택 필드 전부 반영 완료. 남은 것은 AI 시착 생성(3.3, 3.6)뿐 — 정윤 파트가 아니다
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

- AI 시착 결과 polling 또는 STOMP push 방식
- 시착 실패 사유 응답 구조
