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

## 진행 상황 (2026-07-31) — 남은 항목

**구현 완료.** `GET`/`PUT /api/users/{id}/interests`로 구현했다(`.claude/plans/be/SY020-onboard-interests.md`
참고). 브랜드·카테고리 마스터 조회(`GET /api/brands`/`categories`, 숫자 ID)는 이미 SY007에서
해소돼 있었고, 이번에 전체 교체(full-replace) 저장, 빈 배열=건너뛰기/삭제 의미, 존재하지
않는 ID에 대한 400(`BRAND_NOT_FOUND`/`P009`, `CATEGORY_NOT_FOUND`/`P008`), 중복 ID 처리,
Swagger 문서화까지 반영했다. 엔드포인트 경로 결정과 실제 계약은
`.claude/requests/fe/005-onboarding-interests-contract.md`로 FE에 전달했다 — 아래 항목만
남았다.

- **완료 시점**(구 "BE 확인 필요 5"): 이 API 자체는 `onboardingCompleted`를 건드리지 않는다.
  001·004 요청과 공통으로 걸린 이슈라 `.claude/plans/be/SY019-onboarding-enforcement.md`로
  옮겨 한 곳에서 추적한다.
