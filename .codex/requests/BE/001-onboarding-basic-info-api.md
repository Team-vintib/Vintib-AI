# S15P11A108-241 온보딩 기본 정보 저장 API 구현 요청

## 요청 배경

FE의 ONBOARD-001 기본 정보 입력과 검증이 구현되어 저장 연동을 먼저 진행했다.
현재 BE Swagger에는 온보딩 API가 없어 아래 FE 선행 계약에 맞춘 BE 구현을 요청한다.

## 요청 API

```http
PATCH /api/me/onboarding
Authorization: Bearer {accessToken}
Content-Type: application/json
```

```json
{
  "nickname": "빈티지러버",
  "gender": "FEMALE",
  "phoneNumber": "010-1234-5678",
  "postalCode": "06236",
  "address": "서울 강남구 테헤란로 212",
  "detailAddress": "3층"
}
```

## 필드 규칙

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `nickname` | string | 필수 | 한글, 영문, 숫자 2~10자 |
| `gender` | enum | 필수 | `MALE`, `FEMALE` |
| `phoneNumber` | string | 필수 | 국내 전화번호 형식 |
| `postalCode` | string/null | 선택 | Kakao 주소 검색 결과. 직접 입력한 주소는 `null` |
| `address` | string | 필수 | 기본 주소 |
| `detailAddress` | string | 필수 | 상세 주소 |

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
    "message": "잘못된 입력값입니다.",
    "errors": [
      {
        "field": "nickname",
        "value": "!",
        "reason": "닉네임은 한글, 영문, 숫자 2~10자로 입력해주세요."
      }
    ]
  }
}
```

- `error.errors[].field`는 요청 필드명과 동일하게 전달한다.
- `postalCode` 오류는 FE에서 주소 필드 오류로 표시한다.
- 닉네임 중복 오류 코드와 HTTP 상태를 추가로 확정해 공유해 주어야 한다.

## FE 처리

- 요청 중 중복 제출 방지
- 성공 응답에서만 `/onboarding/interests` 이동
- 필드 오류를 해당 입력 영역에 표시
- 일반/네트워크 오류는 폼 공통 오류로 표시
- 실패 시 입력값 유지 및 재시도 허용

## BE 확인 필요

1. 현재 `Member` 엔티티는 주소 문자열 하나만 가지므로 우편번호, 기본 주소, 상세 주소의
   저장 모델을 결정해야 한다.
2. DB 데이터 사전의 `member`에는 `gender`와 회원 기본 주소 컬럼이 확인되지 않아
   스키마 정합성을 확인해야 한다.
3. 현재 `completeOnboarding()`은 기본 정보 저장 즉시 `onboardingCompleted=true`로
   변경한다. 실제 온보딩은 ONBOARD-004까지 있으므로 완료 시점을 조정해야 한다.
4. 닉네임 고유성 검증과 중복 오류 규격을 확정해야 한다.
5. 구현 후 Swagger의 요청 DTO, 응답, 오류 응답에 위 계약을 문서화해야 한다.

## FE 관련 파일

- `FE/src/api/onboarding.ts`
- `FE/src/views/onboarding/OnboardingBasicInfoView.vue`
- `FE/docs/frontend/api/api-index.md`
