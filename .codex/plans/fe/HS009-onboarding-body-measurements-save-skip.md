# S15P11A108-254 신체 정보 입력·저장 및 건너뛰기 구현 계획

## 배경/목표

S15P11A108-252에서 배치한 ONBOARD-003 신체 정보 필드를 실제로 입력할 수 있게 만들고,
S15P11A108-253에서 선택한 전신 사진과 함께 저장한 뒤 ONBOARD-004로 이동한다.

모든 항목은 선택 사항이다. 사용자는 아무 정보도 입력하지 않고 건너뛸 수 있으며, 일부
신체 정보만 입력하거나 사진만 선택해 저장할 수도 있다.

## 확인한 기준

- `FE/docs/notion/화면 기반 개발 요구 문서.md`는 ONBOARD-003 입력 항목을 키, 몸무게,
  가슴, 허리, 엉덩이로 정의한다.
- 같은 문서는 다음 또는 건너뛰기 후 ONBOARD-004로 이동하도록 정의한다.
- `FE/docs/notion/기능 정의서.md`는 사진과 신체 정보가 모두 선택 입력이며 신체 정보
  없이도 AI 시착을 사용할 수 있다고 정의한다.
- `APIs.md`에는 `PUT /users/{id}/tryon` 후보가 있으나 FE는 신뢰할 수 있는 회원 ID
  Store가 없으므로 인증 사용자용 endpoint가 필요하다.
- 현재 BE Swagger와 Controller에는 시착 프로필 API가 없고 DB 초안의
  `member_body_profile`에는 `body_photo_url`, `height_cm`, `weight_kg`만 존재한다.
- 가슴·허리·엉덩이 DB 컬럼과 단위, 모든 숫자 필드의 허용 범위는 미확정이다.
- `ONBOARD_MEMBER_TYPE` 라우트 이름과 경로 상수는 있지만 실제 라우트와 페이지가 없다.

## 사용자 동작

### 신체 정보 입력

- 키, 몸무게, 가슴, 허리, 엉덩이는 각각 독립적인 선택 입력이다.
- 빈 값은 정상 상태로 처리한다.
- 값을 입력한 경우에만 양의 정수인지 확인한다.
- 범위 정책이 없으므로 키 100~250 같은 임의 범위는 적용하지 않는다.
- 잘못된 값을 입력하고 필드에서 벗어나면 해당 필드 아래에 오류를 표시한다.
- 제출 시 전체 필드를 다시 검증하고 첫 번째 오류 필드로 포커스를 이동한다.

### 다음 단계

1. 입력한 신체 정보를 검증한다.
2. 사진 또는 신체 정보가 하나라도 있으면 저장 API를 호출한다.
3. 서버가 `success: true`를 반환한 경우에만 ONBOARD-004로 이동한다.
4. 아무 사진과 신체 정보도 없으면 저장할 값이 없으므로 건너뛰기와 동일하게 바로 이동한다.
5. 요청 중에는 이전·건너뛰기·다음과 사진 변경·삭제를 모두 비활성화한다.
6. 저장 실패 시 현재 사진과 입력값을 유지하고 다시 시도할 수 있게 한다.

### 건너뛰기

- 저장 API를 호출하지 않고 ONBOARD-004로 바로 이동한다.
- 현재 화면에서 선택한 사진과 입력한 신체 정보는 저장하지 않고 버린다.
- BE API가 준비되지 않아도 온보딩 흐름을 확인할 수 있다.

## 선행 API 계약

```http
PUT /api/me/tryon
Authorization: Bearer {accessToken}
Content-Type: multipart/form-data
```

선택 가능한 multipart 항목:

| 필드 | 타입 | 의미 |
| --- | --- | --- |
| `bodyPhoto` | image file | 전신 사진 |
| `heightCm` | integer string | 키(cm) |
| `weightKg` | integer string | 몸무게(kg) |
| `chest` | integer string | 가슴 치수, 단위 미확정 |
| `waist` | integer string | 허리 치수, 단위 미확정 |
| `hip` | integer string | 엉덩이 치수, 단위 미확정 |

- 값이 없는 필드는 multipart에 포함하지 않는다.
- 인증 토큰에서 현재 회원을 식별하며 회원 ID를 요청에 포함하지 않는다.
- HTTP 성공이어도 `success: false`이면 실패로 처리한다.
- 서버 필드 오류는 `heightCm`, `weightKg`, `chest`, `waist`, `hip`, `bodyPhoto`를
  사용한다고 임시 정의한다.
- BE 계약 확정 시 endpoint, 필드명과 가슴·허리·엉덩이 단위를 우선 수정한다.

## 생성·수정할 파일

### 수정: `FE/src/domains/onboard/api/onboarding.ts`

- `SaveOnboardingTryOnProfileRequest` 타입을 추가한다.
- 선택된 값만 `FormData`에 넣는 `saveOnboardingTryOnProfile()`을 추가한다.
- 브라우저가 multipart boundary를 만들도록 `Content-Type`을 직접 하드코딩하지 않는다.

### 수정: `FE/src/domains/onboard/components/BaseInput.vue`

- 현재 `text | tel`만 가능한 `inputmode`에 `numeric`을 추가한다.
- 기존 ONBOARD-001·002 사용 방식과 기본값은 바꾸지 않는다.

### 수정: `FE/src/domains/onboard/components/FullBodyPhotoUploader.vue`

- 선택적인 `disabled` prop을 추가한다.
- 저장 중에는 파일 선택, 촬영, 변경과 삭제를 모두 막는다.
- 기존 사진 선택·미리보기·삭제 동작은 유지한다.

### 수정: `FE/src/domains/onboard/pages/OnboardingTryOnView.vue`

- 5개 신체 정보 값을 문자열로 관리하는 form 상태를 추가한다.
- 필드별 touched와 error 상태를 추가한다.
- 정적 disabled input을 `BaseField`, `BaseInput` 기반 실제 입력으로 교체한다.
- 선택 입력 검증, 첫 오류 포커스, 서버 필드 오류 매핑을 구현한다.
- 저장 중복 제출 방지와 요청 오류 문구를 구현한다.
- 건너뛰기와 다음 단계 이동을 연결한다.
- 저장 중 `FullBodyPhotoUploader`와 하단 액션을 비활성화한다.

### 새 파일: `FE/src/domains/onboard/pages/OnboardingMemberTypeView.vue`

- ONBOARD-004 본 기능을 구현하지 않고 4단계 이동 확인용 임시 화면을 만든다.
- “회원 유형 화면 준비 중” 안내와 ONBOARD-003으로 돌아가는 이전 단계만 제공한다.
- 일반/사업자 선택, 저장과 HOME/BIZ 이동은 후속 ONBOARD-004 작업 범위로 남긴다.

### 수정: 라우트

- `FE/src/router/routes.ts`에 `/onboarding/member-type` 라우트를 추가한다.
- 기존 `ROUTE_NAMES.ONBOARD_MEMBER_TYPE`과 `ROUTE_PATHS.ONBOARD_MEMBER_TYPE`을 재사용한다.

### 문서

- `FE/docs/frontend/api/api-index.md`에 임시 multipart 계약을 기록한다.
- `.codex/requests/BE/003-onboarding-tryon-profile-api.md`에 BE 구현과 DB 계약 확정을
  요청한다.
- `FE/docs/frontend/implementation/current-structure.md`에 임시 ONBOARD-004 페이지를
  추가한다.
- `FE/docs/frontend/implementation/status.md`와 화면 목록에 ONBOARD-003 FE 완료 상태를
  반영한다.
- `FE/docs/frontend/decisions/open-questions.md`에 신체 치수 단위·범위와 누락 DB 컬럼을
  구체적으로 기록한다.

## 입력 검증

```text
빈 값
  → 선택 입력이므로 정상

숫자가 아닌 값, 0, 음수
  → "0보다 큰 정수로 입력해 주세요."

양의 정수
  → 정상
```

- 소수 허용 여부가 미확정이고 DB 초안이 `SMALLINT`이므로 이번 선행 구현은 정수만 허용한다.
- 값 범위는 서버 정책이 확정될 때 추가한다.
- 입력 중 사용자가 작성할 수 있도록 매 키 입력마다 강제로 문자를 삭제하지 않고,
  blur와 제출 시 검증한다.

## API 오류 처리

- `error.errors`의 필드명이 신체 정보 필드와 일치하면 입력 아래에 오류를 표시한다.
- `bodyPhoto` 오류와 매핑되지 않는 오류는 화면 하단 제출 오류 영역에 표시한다.
- 네트워크 연결 실패는 별도 안내 문구를 표시한다.
- 실패 시 사진, 입력값과 touched 상태를 유지한다.
- 성공 시에만 ONBOARD-004로 이동한다.

## 구현 목록

- [x] 신체 정보 form·touched·error 상태 추가
- [x] 선택 숫자 입력 UI와 단위 표시 연결
- [x] 양의 정수 검증과 첫 오류 포커스 구현
- [x] 시착 프로필 multipart 요청 타입·API 함수 추가
- [x] 저장 중 사진·화면 액션 비활성화
- [x] 서버 필드 오류·네트워크 오류 처리
- [x] 건너뛰기 직접 이동 구현
- [x] 값이 없을 때 다음 단계 직접 이동 구현
- [x] 저장 성공 시 ONBOARD-004 이동
- [x] ONBOARD-004 임시 페이지와 라우트 추가
- [x] API·BE 요청·구조·상태·미확정 문서 갱신
- [x] ESLint 검증
- [x] `npm run type-check` 검증
- [x] `npm run build` 검증
- [x] 브라우저 입력·검증·저장 실패·건너뛰기·반응형 검증

실제 저장 성공 E2E는 BE API가 없어 실행하지 못했다. 성공 응답 후 이동 분기는 코드와
타입 검사로 확인했으며, 브라우저에서는 API 실패 시 입력 유지와 화면 잔류를 확인했다.

## 검증 시나리오

1. 모든 신체 정보 필드를 비워둬도 오류가 없다.
2. 일부 필드만 입력해도 저장할 수 있다.
3. 문자, 0, 음수 입력 후 blur하면 해당 필드 오류가 표시된다.
4. 잘못된 입력으로 다음 단계를 누르면 API를 호출하지 않고 첫 오류 필드로 이동한다.
5. 사진 또는 신체 정보가 있으면 다음 단계에서 multipart 저장 요청을 한 번만 보낸다.
6. 요청 중 사진 변경·삭제와 모든 하단 액션이 비활성화된다.
7. 서버 오류가 발생하면 ONBOARD-003에 남고 현재 사진과 입력값이 유지된다.
8. 서버 필드 오류가 해당 입력 아래에 표시된다.
9. 건너뛰기는 API 호출 없이 ONBOARD-004로 이동한다.
10. 사진과 입력값이 모두 없는 다음 단계도 ONBOARD-004로 이동한다.
11. 저장 성공 후 ONBOARD-004 임시 화면으로 이동한다.
12. ONBOARD-004 임시 화면의 이전 단계로 ONBOARD-003에 돌아온다.
13. 데스크톱·태블릿·모바일에서 입력과 오류 문구가 겹치거나 가로로 넘치지 않는다.
14. ONBOARD-001·002와 기존 사진 선택·미리보기·삭제 동작에 회귀가 없다.

## 범위 제외

- ONBOARD-004 실제 일반/사업자 회원 선택과 저장
- HOME 또는 사업자 인증 화면 이동
- 서버에 저장된 시착 프로필 조회와 초기값 표시
- 확정되지 않은 숫자 최소·최대 범위와 소수 허용
- 가슴·허리·엉덩이 단위 확정
- 서버 DB migration과 Controller 구현
- 사진 압축·크롭·AI 전신 판별

BE 계약이 확정되면 Swagger를 기준으로 임시 multipart 계약과 FE 타입을 수정한다.
