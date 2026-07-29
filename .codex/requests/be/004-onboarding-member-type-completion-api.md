# S15P11A108-261 회원 유형 저장 및 온보딩 완료 API 구현 요청

## 요청 배경

FE의 ONBOARD-004 일반·사업자 회원 선택과 유형별 화면 분기를 구현했다. 회원 유형을
저장하면서 온보딩을 최종 완료하는 BE API가 없어 아래 FE 선행 계약을 기준으로 구현과
도메인 계약 확정을 요청한다.

현재 `Member.completeOnboarding()`은 기본 정보와 함께 `onboardingCompleted`를 `true`로
변경하지만, 화면 흐름상 최종 완료 시점은 ONBOARD-004 회원 유형 저장 성공 이후여야 한다.

## 요청 API

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

## 요청 규칙

- `memberType`은 `GENERAL | BUSINESS` 중 하나이며 필수다.
- 인증 토큰에서 현재 회원을 식별하고 클라이언트가 회원 ID를 전달하지 않는다.
- 회원 유형 저장과 `onboardingCompleted = true` 변경을 하나의 트랜잭션으로 처리한다.
- 이미 완료한 회원의 재요청을 멱등 성공으로 볼지 오류로 볼지 정책을 확정한다.

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
    "message": "회원 유형이 올바르지 않습니다.",
    "errors": [
      {
        "field": "memberType",
        "reason": "GENERAL 또는 BUSINESS 중 하나를 선택해 주세요."
      }
    ]
  }
}
```

## FE 처리

- 선택값이 없으면 API를 호출하지 않는다.
- 요청 중 회원 유형 변경, 이전 단계와 완료 버튼을 비활성화한다.
- `success: true` 응답에서만 유형별 목적지로 이동한다.
- `GENERAL`은 `ROUTE_PATHS.HOME`, `BUSINESS`는 `ROUTE_PATHS.BIZ_VERIFY`로 이동한다.
- 실패 시 ONBOARD-004에 남아 선택값을 유지하고 오류를 표시한다.

## BE 확인 필요

1. `member` 테이블의 `member_type`과 Java Entity enum 매핑을 확정해야 한다.
2. 기본 정보 저장 단계에서 조기 완료되는 현재 `Member.completeOnboarding()` 책임을
   ONBOARD-004 최종 완료 단계에 맞게 분리해야 한다.
3. 이미 완료한 회원의 재요청과 회원 유형 변경 허용 정책을 확정해야 한다.
4. 완료 이후 인증 응답 또는 내 정보 조회에서 `memberType`과
   `onboardingCompleted`를 제공할지 확정해야 한다.
5. 구현 후 Swagger에 요청, 응답과 오류 응답을 문서화해야 한다.

## FE 관련 파일

- `FE/src/domains/onboard/api/onboarding.ts`
- `FE/src/domains/onboard/pages/OnboardingMemberTypeView.vue`
- `FE/docs/frontend/api/api-index.md`

## 진행 상황 (2026-07-29)

**미구현.** `POST /api/me/onboarding/complete` 엔드포인트, 관련 컨트롤러/서비스 모두 아직 없다.

- `Member` 엔티티에 `memberType`(GENERAL/BUSINESS) 필드가 없다 — "BE 확인 필요 1" 미해결.
- `Member.completeOnboarding()`은 001번 요청(기본 정보 저장)이 아직 미구현이라 여전히 존재하지 않는 메서드 호출 지점 자체가 없는 상태 — "BE 확인 필요 2"는 001·004를 함께 설계해야 풀린다.

이 요청은 001(기본 정보), 002(관심 정보), 003(시착 프로필) 저장 흐름과 온보딩 완료 시점을 공유하므로, 네 요청을 한 번에 묶어서 `Member` 도메인 계획(`.claude/plans/be/`)을 세우는 게 나을 것 같다 — 순서대로 따로 구현하면 001에서 만든 완료 처리 로직을 004에서 다시 옮겨야 한다.
