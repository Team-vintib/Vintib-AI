# S15P11A108-261 회원 유형별 분기 및 온보딩 완료 처리 계획

## 배경/목표

S15P11A108-260에서 선택한 회원 유형을 서버에 저장하면서 온보딩을 최종 완료하고,
일반 회원은 HOME으로, 사업자 회원은 BIZ-001로 분기한다.

## 확인한 기준

- 화면 요구 문서는 일반 회원 선택 후 HOME, 사업자 회원 선택 후 BIZ-001 이동을
  요구하며 회원 유형 저장 성공을 이동 조건으로 둔다.
- FE에는 `ROUTE_PATHS.HOME`과 `ROUTE_PATHS.BIZ_VERIFY` 상수가 있지만 목적지 화면과
  실제 route record는 아직 구현되지 않았다.
- BE에는 `onboardingCompleted` 필드와 완료 메서드는 있지만 회원 유형 필드·저장 API와
  최종 온보딩 완료 endpoint가 구현되어 있지 않다.
- 기본 정보 저장 단계에서 온보딩을 완료하는 현재 BE 모델과 최종 단계에서 완료한다는
  화면 흐름 사이의 계약 정리가 필요하다.
- FE는 BE 코드를 수정하지 않고 `.codex/requests/BE/`에 계약 요청을 남긴다.

## FE 선행 API 계약

```http
POST /api/me/onboarding/complete
Authorization: Bearer {accessToken}
Content-Type: application/json
```

요청:

```json
{
  "memberType": "GENERAL"
}
```

- `memberType`은 `GENERAL | BUSINESS`만 허용한다.
- 서버는 회원 유형 저장과 `onboardingCompleted = true` 변경을 하나의 트랜잭션으로
  처리해야 한다.
- 공통 `ApiResponse` envelope의 `success: true`인 경우에만 완료로 판단한다.
- BE Swagger가 확정되면 endpoint와 요청·응답 필드명을 실제 계약에 맞춘다.

## 사용자 동작

### 다음 단계

1. 선택된 회원 유형이 있는지 확인한다.
2. 중복 제출을 막고 완료 API를 한 번 호출한다.
3. 성공 시 `GENERAL`은 `ROUTE_PATHS.HOME`으로 이동한다.
4. 성공 시 `BUSINESS`는 `ROUTE_PATHS.BIZ_VERIFY`로 이동한다.
5. 실패 시 ONBOARD-004에 남아 선택 값을 유지하고 재시도 안내를 표시한다.

### 요청 상태

- 요청 중에는 회원 유형 변경, 이전 단계와 다음 단계를 모두 비활성화한다.
- 서버 필드 오류와 일반 오류를 화면 오류 영역에 표시한다.
- 선택 없이 제출되는 방어 경로에서는 API를 호출하지 않는다.

## 생성·수정할 파일

### 수정: `FE/src/domains/onboard/api/onboarding.ts`

- `OnboardingMemberType`과 완료 요청 타입을 추가한다.
- `completeOnboarding()` API 호출 함수를 추가한다.

### 수정: `FE/src/domains/onboard/pages/OnboardingMemberTypeView.vue`

- 260의 선택 상태를 완료 API와 연결한다.
- 제출 중 상태, 중복 제출 방지와 오류 문구를 추가한다.
- 저장 성공 후 회원 유형별 경로로 분기한다.

### 새 파일: `.codex/requests/BE/004-onboarding-member-type-completion-api.md`

- 회원 유형 저장 필드와 enum을 요청한다.
- 최종 온보딩 완료 endpoint와 트랜잭션 경계를 요청한다.
- 기본 정보 단계에서 조기 완료되는 현재 모델의 정리를 요청한다.

### 문서

- `FE/docs/frontend/api/api-index.md`에 FE 선행 완료 계약을 기록한다.
- `FE/docs/frontend/decisions/open-questions.md`에 확정 대기 계약을 기록한다.
- `FE/docs/frontend/implementation/status.md`와 화면 목록에 ONBOARD-004 FE 완료 상태를
  반영한다.
- 목적지 화면이 구현되기 전까지 현재 경로 상수를 사용하며 HOME/BIZ 화면 자체는 이번
  작업에서 생성하지 않는다.

## 구현 목록

- [x] 회원 유형 완료 요청 타입·API 함수 추가
- [x] 선택값 저장과 최종 온보딩 완료 요청 연결
- [x] 요청 중 선택·이전·다음 액션 비활성화
- [x] 성공 시 일반 회원 HOME 분기
- [x] 성공 시 사업자 회원 BIZ-001 분기
- [x] 서버·네트워크 오류 표시와 선택 상태 유지
- [x] BE 회원 유형·완료 API 요청 문서 작성
- [x] API·미확정·구현 상태 문서 갱신
- [x] ESLint, type-check, build 검증
- [x] 브라우저 오류·중복 제출·유형별 분기 검증
- [x] 사용자 수동 화면·동작 검증

## 검증 시나리오

1. 유형을 선택하지 않은 방어 경로에서는 API를 호출하지 않는다.
2. 일반 회원을 선택하고 다음을 누르면 `GENERAL`로 완료 요청을 한 번 보낸다.
3. 사업자 회원을 선택하고 다음을 누르면 `BUSINESS`로 완료 요청을 한 번 보낸다.
4. 요청 중 카드와 이전·다음 버튼을 다시 조작할 수 없다.
5. API 실패 시 현재 선택을 유지하고 ONBOARD-004에 남는다.
6. 성공한 일반 회원은 `/`로 이동한다.
7. 성공한 사업자 회원은 기존 `ROUTE_PATHS.BIZ_VERIFY` 경로로 이동한다.
8. ONBOARD-001~003 흐름과 기존 API 함수에 회귀가 없다.

## 범위 제외

- BE entity, DB migration, Controller와 Service 직접 구현
- HOME 화면 구현
- BIZ-001 사업자 정보 제출 화면 구현
- 전역 인증 Store의 사용자 정보 갱신
- 온보딩 완료 사용자의 재진입 차단 route guard

## Git 작업 단위

- 브랜치: `feat/60-member-type-selection`
- 커밋: `[S15P11A108-261] feat: 회원 유형별 분기 및 온보딩 완료 처리`
- 자동 검증과 사용자 수동 검증 승인 후 261 변경만 커밋한다.
- 261 커밋 후 사용자가 같은 원격 스토리 브랜치에 다시 push한다.
- 두 작업의 커밋이 원격에 모두 반영된 뒤 스토리 단위 MR을 한 번 생성한다.
- MR 제목: `[ONBOARD] 회원 유형 선택 구현`
- MR 대상: `develop-FE`
