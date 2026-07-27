# S15P11A108-250 관심 정보 저장·건너뛰기 및 단계 이동 구현 계획

## 배경/목표

S15P11A108-244와 S15P11A108-245에서 구현한 ONBOARD-002 관심 브랜드·카테고리
선택 화면에 저장, 건너뛰기, 다음 온보딩 단계 이동을 연결한다.

선택값을 저장한 경우와 건너뛴 경우 모두 서버 처리가 성공한 뒤에만 ONBOARD-003으로
이동하며, 요청 중 중복 제출과 실패 시 선택값 유실을 막는다.

## 확인한 기준

- `FE/docs/notion/화면 기반 개발 요구 문서.md`는 ONBOARD-002의 관심 정보가 선택
  입력이며 `다음`과 `건너뛰기`를 모두 제공하도록 정의한다.
- 같은 문서는 `다음`을 관심 정보 저장, `건너뛰기`를 미입력 상태 저장/스킵으로 정의하고
  두 동작의 성공 목적지를 ONBOARD-003으로 지정한다.
- `APIs.md`는 관심 정보 등록·수정을 `PUT /users/{id}/interests` 후보로 정의하지만,
  현재 FE에는 로그인 회원 ID를 신뢰성 있게 제공하는 인증 Store가 없다.
- BE Swagger와 관심 정보 API가 아직 없으므로, FE는 인증 토큰에서 회원을 식별하는
  `PUT /api/me/interests`를 선행 계약으로 사용하고 BE 파트에 구현 요청 문서를 남긴다.
- 건너뛰기는 별도 endpoint를 만들지 않고 같은 PUT 요청에 빈 배열을 전달한다. 이 방식은
  재진입 사용자의 기존 관심 정보까지 명확히 비우며 저장과 스킵을 멱등하게 처리할 수 있다.
- 현재 화면의 브랜드·카테고리 ID는 임시 UI 식별자이다. 실제 마스터 데이터 API가
  확정되면 서버 ID로 교체해야 하며, 이번 FE 선행 계약에서는 문자열 식별자를 그대로
  전달한다.

## 선행 API 계약

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

성공 응답:

```json
{
  "success": true,
  "data": null,
  "error": null
}
```

- HTTP 성공이어도 `success: false`이면 실패로 처리한다.
- 검증 오류와 일반 API 오류는 `error.message`를 우선 표시한다.
- 네트워크 오류 또는 응답 형식이 없으면 FE 기본 오류 문구를 표시한다.

## 작업 내용

### API 계층

- `FE/src/api/onboarding.ts`에 `SaveOnboardingInterestsRequest` 타입을 추가한다.
- 같은 파일에 `saveOnboardingInterests()`를 추가하고 공통 `httpClient`로 선행 계약을
  호출한다.
- `FE/docs/frontend/api/api-index.md`에 endpoint, 요청/응답, 임시 식별자 제약을 기록한다.
- `.codex/requests/BE/`에 관심 정보 저장 API와 마스터 ID 계약 확정을 요청하는 문서를
  추가한다. BE 코드는 수정하지 않는다.

### 공통 온보딩 레이아웃

- `OnboardingLayout.vue`에 선택적으로 노출하는 건너뛰기 버튼 props와 `skip` emit을
  추가한다.
- 기본값은 건너뛰기 미노출로 두어 ONBOARD-001 동작을 변경하지 않는다.
- 버튼 영역은 `이전 단계 / (건너뛰기, 다음 단계)` 구조로 배치한다.
- 저장 중에는 이전, 건너뛰기, 다음 버튼을 모두 비활성화해 화면 이탈과 중복 요청을 막는다.

### ONBOARD-002 화면

- `isSubmitting`과 `submitError`를 컴포넌트 로컬 상태로 관리한다.
- 다음 단계 선택 시 현재 `selectedBrandIds`, `selectedCategoryIds`를 복사해 저장한다.
- 건너뛰기 선택 시 두 배열을 변경하지 않고 API에 빈 배열을 전달한다. 요청 실패 시
  사용자의 기존 화면 선택 상태는 그대로 유지한다.
- 요청 성공 시에만 이름 기반 라우팅으로 `onboarding-try-on`에 이동한다.
- 요청 실패 시 선택 영역 아래에 접근 가능한 공통 오류 문구를 표시하고 재시도를 허용한다.
- 처리 중 버튼 문구를 `저장 중`으로 변경한다.

### 다음 단계 이동 대상

- 라우터에 `/onboarding/try-on`, `onboarding-try-on` 라우트를 추가한다.
- ONBOARD-003 본 기능을 임의 구현하지 않고, 3단계 표시와 “AI 시착 정보 화면 준비 중”
  안내 및 ONBOARD-002로 돌아가는 동작만 가진 임시 화면을 추가한다.
- 후속 ONBOARD-003 작업에서 임시 화면을 실제 화면으로 교체할 수 있게 파일을 분리한다.

### 상태 문서

- `FE/docs/frontend/implementation/status.md`와
  `FE/docs/frontend/screens/screen-inventory.md`에서 ONBOARD-002를
  `저장·건너뛰기·이동 완료` 상태로 갱신한다.

## 구현 목록

- [x] 관심 정보 저장 요청 타입과 API 함수 추가
- [x] API 후보 문서와 BE 구현 요청 문서 추가
- [x] 공통 레이아웃의 선택적 건너뛰기 액션 추가
- [x] 저장 중 중복 제출 및 화면 이탈 방지
- [x] 선택값 저장과 빈 배열 건너뛰기 처리
- [x] API 오류/네트워크 오류 표시와 선택 상태 유지
- [x] 성공 시에만 ONBOARD-003 이동
- [x] ONBOARD-003 임시 라우트와 이동 확인 화면 추가
- [x] 구현 상태 문서와 화면 목록 갱신
- [x] `npm run type-check` 검증
- [x] `npm run build` 검증
- [x] 브라우저 수동 검증

## 검증 시나리오

1. 브랜드·카테고리를 선택하고 다음 단계를 누르면 선택 ID가 한 번만 전송된다.
2. 선택값 없이 다음 단계를 눌러도 빈 배열 저장 요청 후 ONBOARD-003으로 이동한다.
3. 선택값이 있는 상태에서 건너뛰기를 누르면 빈 배열이 전송된다.
4. 저장 또는 건너뛰기 요청 중 모든 하단 액션이 비활성화되고 중복 요청되지 않는다.
5. API가 `success: false`를 반환하면 이동하지 않고 서버 오류 메시지를 표시한다.
6. 네트워크 오류가 발생하면 이동하지 않고 기본 오류 메시지를 표시한다.
7. 실패 뒤 선택값이 유지되며 다시 시도할 수 있다.
8. 성공한 경우에만 `/onboarding/try-on`으로 이동한다.
9. ONBOARD-003 임시 화면에서 이전 단계를 누르면 ONBOARD-002로 돌아온다.
10. ONBOARD-001의 기존 이전/다음 버튼과 저장 동작에는 변화가 없다.

## 범위 제외 및 후속 확인

- 실제 브랜드·카테고리 마스터 조회 API 연동
- 임시 문자열 식별자를 DB의 숫자 ID로 교체하는 작업
- ONBOARD-003 AI 시착 정보 입력 UI와 저장/건너뛰기 로직
- 인증 Store 및 라우트 가드
- BE 관심 정보 저장 로직 직접 구현

BE Swagger가 먼저 확정되면 endpoint, 요청 필드 타입과 오류 규격은 Swagger를 우선해
이 계획과 FE 코드를 맞춘다.
