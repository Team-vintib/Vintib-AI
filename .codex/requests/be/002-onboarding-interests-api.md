# S15P11A108-250 온보딩 관심 정보 저장 API 구현 요청

## 요청 배경

FE의 ONBOARD-002 관심 브랜드·카테고리 검색과 선택 UI가 구현되어 저장·건너뛰기 및
ONBOARD-003 이동을 연결했다.

현재 BE Swagger에는 관심 정보 저장 API와 브랜드·카테고리 마스터 조회 계약이 없어
아래 FE 선행 계약에 맞춘 BE 구현과 실제 ID 타입 확정을 요청한다.

## 요청 API

```http
PUT /api/me/interests
Authorization: Bearer {accessToken}
Content-Type: application/json
```

선택 저장:

```json
{
  "brandIds": ["brand-a", "brand-c"],
  "categoryIds": ["outer", "top"]
}
```

건너뛰기:

```json
{
  "brandIds": [],
  "categoryIds": []
}
```

## 필드 규칙

| 필드          | 타입     | 필수 | 규칙                                         |
| ------------- | -------- | ---- | -------------------------------------------- |
| `brandIds`    | string[] | 필수 | 중복 없는 브랜드 식별자 배열, 빈 배열 허용   |
| `categoryIds` | string[] | 필수 | 중복 없는 카테고리 식별자 배열, 빈 배열 허용 |

- PUT 요청은 회원의 기존 관심 브랜드·카테고리를 요청 배열 전체로 교체한다.
- 두 배열이 모두 비어 있으면 관심 정보 없이 건너뛴 상태로 저장한다.
- 인증 토큰에서 현재 회원을 식별하며 클라이언트가 회원 ID를 전달하지 않는다.

## 응답 규격

성공:

```http
200 OK
```

```json
{
  "success": true,
  "data": null,
  "error": null
}
```

검증 실패:

```http
400 Bad Request
```

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "C001",
    "message": "관심 정보가 올바르지 않습니다.",
    "errors": null
  }
}
```

## FE 처리

- 선택 저장은 현재 화면의 브랜드·카테고리 ID를 전달
- 건너뛰기는 두 ID 배열을 모두 비워 전달
- 요청 중 이전·건너뛰기·다음 액션 비활성화 및 중복 요청 방지
- `success: true` 응답에서만 `/onboarding/try-on` 이동
- 실패 시 선택 상태 유지, 오류 문구 표시 및 재시도 허용

## BE 확인 필요

1. DB의 `brand.id`, `category.id`는 bigint인데 현재 FE 화면 데이터는
   `brand-a`, `outer` 같은 임시 문자열 식별자를 사용한다. 실제 저장 전 브랜드·카테고리
   마스터 조회 API와 숫자 ID 응답 계약을 확정해야 한다.
2. 상위 `APIs.md`의 후보는 `PUT /users/{id}/interests`이지만 FE에는 신뢰할 수 있는
   회원 ID Store가 없다. 인증 사용자 전용 `/api/me/interests` 사용 여부를 확정해야 한다.
3. 존재하지 않거나 비활성화된 브랜드·카테고리 ID, 중복 ID의 오류 규격을 확정해야 한다.
4. 빈 배열 PUT이 기존 관심 정보를 삭제하는 건너뛰기 의미인지 확인해야 한다.
5. 실제 온보딩 완료 처리는 ONBOARD-004까지 마친 시점에 수행되어야 한다.
6. 구현 후 Swagger에 요청 DTO, 응답, 오류 응답과 빈 배열 의미를 문서화해야 한다.

## FE 관련 파일

- `FE/src/domains/onboard/api/onboarding.ts`
- `FE/src/domains/onboard/pages/OnboardingInterestsView.vue`
- `FE/docs/frontend/api/api-index.md`

## 진행 상황 (2026-07-29)

**저장 API는 미구현.** `PUT /api/me/interests` 엔드포인트는 아직 없다.

- 다만 "BE 확인 필요 1"에서 요청한 **브랜드·카테고리 마스터 조회 API는 이미 구현되어 있다** — `GET /api/brands`, `GET /api/categories` (SY007에서 구현, 인증 불필요). 응답이 `{ id: number, name: string, ... }` 형태로 **숫자 ID**를 내려주므로, FE가 우려한 `brand-a`/`outer` 같은 임시 문자열 식별자 문제는 이 조회 API로 해소할 수 있다. Swagger "상품(Products)" 태그에서 확인 가능.
- 회원 관심 브랜드·카테고리를 저장하는 도메인(테이블/엔티티)은 아직 없다 — `PUT /api/me/interests` 자체와 "BE 확인 필요 2~4"는 여전히 미해결.

착수 시 CLAUDE.md 규율상 신규 API라 `.claude/plans/be/`에 설계 계획부터 세우고 승인받아야 한다.
