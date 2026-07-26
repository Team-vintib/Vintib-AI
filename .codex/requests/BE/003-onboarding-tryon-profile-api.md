# S15P11A108-254 온보딩 AI 시착 정보 저장 API 구현 요청

## 요청 배경

FE의 ONBOARD-003 전신 사진 선택·촬영·미리보기·삭제, 선택형 신체 정보 입력, 검증,
건너뛰기와 ONBOARD-004 이동을 구현했다.

현재 BE Swagger와 Controller에는 AI 시착 프로필 저장 API가 없으며, 상위 `APIs.md`의
`PUT /users/{id}/tryon` 후보는 FE가 신뢰할 수 있는 회원 ID를 보유하지 않아 바로 사용할
수 없다. 아래 인증 사용자용 FE 선행 계약을 기준으로 BE 구현과 DB 계약 확정을 요청한다.

## 요청 API

```http
PUT /api/me/tryon
Authorization: Bearer {accessToken}
Content-Type: multipart/form-data
```

## multipart 필드 규칙

| 필드         | 타입           | 필수 | 현재 FE 규칙                 |
| ------------ | -------------- | ---- | ---------------------------- |
| `bodyPhoto`  | image file     | 선택 | MIME type이 `image/*`인 파일 |
| `heightCm`   | integer string | 선택 | 0보다 큰 정수, 단위 cm       |
| `weightKg`   | integer string | 선택 | 0보다 큰 정수, 단위 kg       |
| `chest`      | integer string | 선택 | 0보다 큰 정수, 단위 미확정   |
| `waist`      | integer string | 선택 | 0보다 큰 정수, 단위 미확정   |
| `hip`        | integer string | 선택 | 0보다 큰 정수, 단위 미확정   |

- 값이 없는 필드는 multipart 요청에서 생략한다.
- 사진만, 신체 정보 일부만 또는 사진과 신체 정보를 함께 저장할 수 있어야 한다.
- PUT은 전달된 값을 현재 회원의 AI 시착 프로필에 반영하는 멱등 요청으로 사용한다.
- 인증 토큰에서 현재 회원을 식별하며 클라이언트가 회원 ID를 전달하지 않는다.
- 건너뛰기와 모든 값이 빈 `다음 단계`는 FE가 API를 호출하지 않는다.

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
    "message": "AI 시착 정보가 올바르지 않습니다.",
    "errors": [
      {
        "field": "heightCm",
        "reason": "키는 0보다 큰 정수여야 합니다."
      }
    ]
  }
}
```

- 필드 오류명은 `bodyPhoto`, `heightCm`, `weightKg`, `chest`, `waist`, `hip`을 사용한다.
- 파일 오류와 공통 오류도 동일한 `ApiResponse<T>` envelope로 반환한다.

## FE 처리

- 입력값은 빈 값 또는 양의 정수인지 먼저 검증
- 사진이나 신체 정보가 하나라도 있으면 multipart PUT 호출
- 요청 중 이전·건너뛰기·다음, 사진 선택·촬영·변경·삭제와 신체 입력 비활성화
- `success: true` 응답에서만 `/onboarding/member-type` 이동
- 실패 시 선택한 사진과 입력값 유지, 필드 또는 화면 공통 오류 표시
- 건너뛰기는 사진 선택 여부와 무관하게 API 호출 없이 `/onboarding/member-type` 이동

## BE 확인 필요

1. DB 초안의 `member_body_profile`에는 `body_photo_url`, `height_cm`, `weight_kg`만 있고
   `chest`, `waist`, `hip` 저장 컬럼이 없다. 세 치수의 저장 여부와 컬럼을 확정해야 한다.
2. 가슴·허리·엉덩이 단위와 모든 숫자 필드의 최소·최대 범위, 소수 허용 여부를 확정해야 한다.
3. 사진 허용 형식, 최대 용량, 최소 해상도와 저장소 업로드 정책을 확정해야 한다.
4. 전신 사진 개인정보 동의, 보관 기간, 변경·삭제 정책을 확정해야 한다.
5. 기존 프로필에 일부 필드만 전달했을 때 미전달 값 유지 여부를 명시해야 한다.
6. 기존 사진 삭제는 이번 온보딩 저장과 별도 endpoint로 처리할지 확정해야 한다.
7. 실제 온보딩 완료 처리는 ONBOARD-004까지 마친 시점에 수행해야 한다.
8. 구현 후 Swagger에 multipart 요청, 응답과 오류 응답을 문서화해야 한다.

## FE 관련 파일

- `FE/src/domains/onboard/api/onboarding.ts`
- `FE/src/domains/onboard/pages/OnboardingTryOnView.vue`
- `FE/docs/frontend/api/api-index.md`
