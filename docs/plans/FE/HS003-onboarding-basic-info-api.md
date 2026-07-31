# S15P11A108-241 기본 정보 저장 API 및 다음 단계 이동 구현 계획

## 배경/목표

S15P11A108-240에서 구현한 ONBOARD-001 입력 폼과 프론트 검증 뒤에 기본 정보 저장 요청을 연결한다.
BE 온보딩 API가 아직 없으므로 FE가 임시 계약을 먼저 정의하고, BE가 같은 계약으로 구현할 수 있도록 Jira 공유 문구와 BE 요청 문서를 함께 남긴다.

## 작업 범위

- 공통 Axios 인스턴스와 공통 API 응답/오류 타입을 추가한다.
- ONBOARD-001 기본 정보 저장 API 함수와 요청 타입을 추가한다.
- 전체 입력 검증 성공 후 저장 API를 한 번만 호출한다.
- 요청 중에는 다음 단계 버튼을 비활성화해 중복 제출을 막는다.
- 서버 필드 오류를 기존 입력 오류 영역에 연결한다.
- 저장 실패 시 입력값을 유지하고 화면 공통 오류를 표시한다.
- 저장 성공 시에만 `/onboarding/interests`로 이동한다.
- 아직 구현되지 않은 ONBOARD-002 화면 대신 이동 확인용 임시 화면을 추가한다.
- FE가 선행 정의한 계약을 `.Codex/requests/BE/`에 요청 문서로 남긴다.

## FE 선행 API 계약

### 요청

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

- `gender`: `MALE | FEMALE`
- `nickname`: 한글, 영문, 숫자 2~10자
- `phoneNumber`: 국내 전화번호 형식
- `address`, `detailAddress`: 필수
- `postalCode`: 주소 검색 시 우편번호를 보내고 직접 입력 시 `null`
- Kakao 우편번호 응답의 `zonecode`는 API 경계에서 `postalCode`로 변환한다.

### 성공 응답

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

FE는 HTTP 성공과 `success: true`를 확인한 뒤 ONBOARD-002로 이동한다.

### 검증 실패 응답

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

- FE가 필드에 직접 매핑하는 이름: `nickname`, `gender`, `phoneNumber`, `postalCode`, `address`, `detailAddress`
- `postalCode` 오류는 화면의 주소 오류 영역에 표시한다.
- 알 수 없는 필드 오류와 일반 오류는 폼 공통 오류로 표시한다.

### 추가 오류

- `401`: 인증 토큰 없음 또는 만료. 인증 흐름 확정 전에는 현재 화면에 오류를 표시한다.
- `404 U001`: 사용자를 찾을 수 없음.
- `409`: 닉네임 중복. BE 오류 코드가 확정되기 전까지 HTTP 상태와 메시지를 기준으로 닉네임 오류로 표시하지 않고 공통 오류로 처리한다.
- `500 C002`: 서버 오류. 입력값을 유지하고 재시도할 수 있게 한다.

## 인증 토큰 처리

- 공통 Axios 인스턴스는 `localStorage`의 `accessToken`이 존재할 때만 `Authorization` 헤더를 추가한다.
- 현재 인증 Store와 토큰 저장 계약이 없으므로 241에서 Pinia 인증 Store를 새로 만들지 않는다.
- 인증 기능이 확정되면 토큰 조회 부분만 Store 기반으로 교체한다.
- 토큰이 없는 상태에서도 요청 자체는 수행하고 서버의 `401` 응답을 표시한다. 임의 성공 Mock으로 우회하지 않는다.

## 화면 상태와 이동

- `isSubmitting`: 저장 요청 동안 `true`
- `submitError`: 서버 또는 네트워크 공통 오류
- 제출 시작 시 이전 공통 오류를 지운다.
- 요청 중 재클릭은 무시한다.
- 실패 시 현재 화면과 입력값을 유지한다.
- 성공 시 `router.push({ name: 'onboarding-interests' })`를 실행한다.
- 현재 ONBOARD-001 경로 `/onboarding/basic-info`는 이번 작업에서 변경하지 않는다.
- 문서의 `/onboarding/profile`과 현재 경로 불일치는 별도 라우트 정리 작업으로 남긴다.

## 임시 ONBOARD-002 이동 대상

- `/onboarding/interests`
- 라우트 이름: `onboarding-interests`
- 임시 화면은 “관심 정보 화면 준비 중”과 현재 2단계 표시만 제공한다.
- 관심 브랜드/카테고리 선택 및 저장 로직은 구현하지 않는다.
- 실제 ONBOARD-002 구현 시 임시 화면을 교체한다.

## 예상 변경 파일

- `FE/src/api/httpClient.ts` 추가
- `FE/src/api/types.ts` 추가
- `FE/src/api/onboarding.ts` 추가
- `FE/src/views/onboarding/OnboardingBasicInfoView.vue` 수정
- `FE/src/views/onboarding/OnboardingInterestsPlaceholderView.vue` 추가
- `FE/src/router/index.ts` 수정
- `FE/docs/frontend/api/api-index.md` 수정
- `.Codex/requests/BE/001-onboarding-basic-info-api.md` 추가

## 검증

- 유효하지 않은 입력에서는 API를 호출하지 않는다.
- 유효한 입력에서는 정의한 요청 본문으로 API를 한 번만 호출한다.
- 요청 중 다음 단계 버튼이 비활성화된다.
- 서버 필드 오류가 해당 필드에 표시된다.
- 네트워크/서버 오류 뒤에도 입력값이 유지되고 다시 제출할 수 있다.
- 성공 응답에서만 `/onboarding/interests`로 이동한다.
- `npm run type-check`
- `npm run build`

## Jira S15P11A108-241 공유 문구

```text
[FE 선행 온보딩 기본 정보 API 계약]

BE 온보딩 API가 아직 없어 FE에서 아래 계약으로 먼저 연동합니다.

- Method/URL: PATCH /api/me/onboarding
- 인증: Authorization: Bearer {accessToken}
- Request:
  {
    "nickname": string,
    "gender": "MALE" | "FEMALE",
    "phoneNumber": string,
    "postalCode": string | null,
    "address": string,
    "detailAddress": string
  }
- Success: 200
  {
    "success": true,
    "data": null,
    "error": null
  }
- Validation error: 400 / C001
  error.errors[].field는 nickname, gender, phoneNumber, postalCode,
  address, detailAddress 중 하나로 내려주세요.
- 인증 실패: 401
- 사용자 없음: 404 / U001
- 서버 오류: 500 / C002

FE는 성공 응답에서만 /onboarding/interests로 이동합니다.
요청 중 중복 제출을 막고, 실패 시 입력값을 유지합니다.

[BE 확인 필요]
1. 현재 Member 엔티티는 주소 문자열 하나만 가지지만 FE는 우편번호/기본주소/
   상세주소를 분리해 전송합니다.
2. DB 데이터 사전의 member에는 gender와 회원 기본 주소 컬럼이 확인되지 않아
   저장 모델 확정이 필요합니다.
3. completeOnboarding()이 기본 정보 저장 즉시 onboardingCompleted=true로
   변경하지만 실제 온보딩은 ONBOARD-004까지 있으므로 완료 시점 조정이 필요합니다.
4. 닉네임 중복 오류 코드와 응답 규격을 확정해 주세요.
```

## 범위 밖

- BE 코드 직접 수정
- 실제 ONBOARD-002 관심 브랜드/카테고리 UI
- 인증 Store와 로그인/토큰 갱신 전체 구현
- 주소 DB 모델 결정
- 온보딩 완료 시점의 BE 도메인 로직 결정

## 구현 결과

- [x] 공통 Axios 인스턴스와 API 응답/오류 타입 추가
- [x] ONBOARD-001 기본 정보 저장 API 함수와 요청 타입 추가
- [x] 요청 중 중복 제출 방지와 저장 중 버튼 상태 적용
- [x] 서버 필드 오류 및 공통 오류 표시
- [x] 성공 시 `/onboarding/interests` 이동
- [x] ONBOARD-002 임시 이동 화면과 이전 단계 이동 추가
- [x] FE API 문서와 BE 요청 문서 작성
- [x] `npm run type-check`
- [x] `npm run build-only`
- [x] ESLint 검사
- [x] 브라우저에서 빈 입력, 성공, 서버 필드 오류, 서버 연결 실패 흐름 확인
