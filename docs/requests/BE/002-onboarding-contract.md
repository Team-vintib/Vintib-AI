# 002 Onboarding API 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: FE 온보딩 화면에서 입력한 기본 정보, 관심 정보, AI 시착 프로필, 회원 유형을 BE에 저장할 수 있도록 API 계약을 정리한다.
- 우선순위: P0
- 시연 필수 여부: 온보딩 진입을 시연하면 필수. Auth 시연만 진행하면 mock-success 유지 가능.

## 2. 현재 연동 상태

- 연동 완료 API: 기본 정보(3.1), 관심 정보(3.2), 온보딩 완료/회원 유형(3.4) — 확정 계약은 각 절 참고
- 미연동: AI 시착 프로필 저장(3.3)
- FE 구현 완료 범위
  - `OnboardingBasicInfoView.vue`: 닉네임, 성별, 연락처, 주소 입력 화면
  - `OnboardingInterestsView.vue`: 관심 브랜드/카테고리 선택 화면
  - `OnboardingTryOnView.vue`: 전신 사진과 신체 치수 입력 화면
  - `OnboardingMemberTypeView.vue`: 일반/사업자 회원 유형 선택 화면
- 현재 임시 처리 또는 Mock 사용 여부
  - `VITE_ONBOARDING_API_ENABLED !== 'true'`이면 FE가 `ApiResponse<null>` mock-success를 반환한다.
  - 실제 저장 API가 없어 새로고침 또는 재로그인 후 온보딩 진행 상태 복원은 불가하다.

## 3. 추가 구현 요청

### 3.1 기본 정보 저장 — 구현 완료, 계약은 다르게 확정됨

실제 엔드포인트는 `PATCH /api/me/onboarding`이 아니라 `PATCH /api/users/{id}`다. 확정 계약은
`docs/requests/FE/004-onboarding-basic-info-contract.md` 참고.

### 3.2 관심 정보 저장 — 구현 완료, 계약은 다르게 확정됨

실제 엔드포인트는 `PUT /api/me/interests`가 아니라 `GET`/`PUT /api/users/{id}/interests`다.
확정 계약은 `docs/requests/FE/005-onboarding-interests-contract.md` 참고.

### 3.3 AI 시착 프로필 저장

- Method / Endpoint: `PUT /api/me/tryon`
- 요청 목적: AI 시착에 사용할 전신 사진과 신체 치수를 저장한다.
- FE 사용처: `OnboardingTryOnView.vue`, 라이브 시착 패널
- 요청 데이터
  - Header: `Authorization: Bearer {accessToken}`
  - `multipart/form-data`
    - `bodyPhoto`: image file | null
    - `heightCm`: number | null
    - `weightKg`: number | null
    - `chest`: number | null
    - `waist`: number | null
    - `hip`: number | null
- 응답 데이터: 저장된 시착 프로필 요약 또는 `null`
- 응답 예시

```json
{
  "success": true,
  "data": {
    "tryonProfileId": 1,
    "bodyPhotoUrl": "https://cdn.example.com/body/1.jpg",
    "heightCm": 170,
    "weightKg": 60
  },
  "error": null
}
```

### 3.4 온보딩 완료 — 구현 완료, 계약은 다르게 확정됨

실제 엔드포인트는 `POST /api/me/onboarding/complete`가 아니라 `PATCH /api/users/{id}/member-type`다.
응답에 `nextStep`은 내려주지 않는다 — `memberType` 값으로 FE가 직접 분기한다. 확정 계약은
`docs/requests/FE/006-onboarding-member-type-contract.md` 참고.

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용: 없음
- 추가할 필드: 없음
- 변경 영향 범위: 없음

## 5. 보류 또는 시연 제외 범위

- 현재 구현하지 않아도 되는 기능
  - Auth 시연만 진행하면 온보딩 API는 mock-success 유지 가능
  - 전신 사진 저장 정책이 미확정이면 `PUT /api/me/tryon`은 보류 가능
- 추후 구현 예정 기능
  - 온보딩 진행 단계 조회
  - 관심 정보 수정 화면
  - 시착 프로필 다중 관리

## 6. 협의 필요 사항

3.1/3.2/3.4(기본 정보 분리 여부, 관심 브랜드·카테고리 numeric id, `memberType` 저장 시점,
응답을 `null` 대신 저장 결과로 내려줄지, `postalCode` 필수 여부)는 모두 확정·구현됐다 —
각 확정 계약 문서 참고. 3.3(AI 시착)만 아직 남았다.

- FE·BE 간 결정이 필요한 내용
  - 전신 사진 multipart 필드명과 저장 URL 반환 여부
- 아직 확정되지 않은 응답 구조나 정책
  - 신체 치수 단위와 허용 범위

## 7. 추가 요청 없음

- 이미 정상 연동된 API: 없음
- 기존 규격을 유지하면 되는 기능: 없음
