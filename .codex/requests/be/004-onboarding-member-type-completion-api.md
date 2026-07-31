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

## BE 확인 필요 — 남은 항목

- **~~1. `member_type`과 Java Entity enum 매핑~~** — 해결됨. `MemberType`(GENERAL/BUSINESS)
  필드와 `schema.sql`의 `member_type VARCHAR(20)` + `ck_member_type` CHECK 제약까지 이미
  반영돼 있다(001/002 작업 중 회원 스키마를 다듬으면서 함께 정리됨).
- **~~4. 내 정보 조회에서 `memberType`/`onboardingCompleted` 노출~~** — 해결됨.
  `MemberProfileResponse`(ONBOARD-001/MY-001 조회 응답)가 이미 두 필드를 모두 내려준다.
- **2. `POST /api/me/onboarding/complete` 자체는 아직 미구현** — 회원 유형 저장 + 온보딩
  최종 완료를 하나의 트랜잭션으로 묶는 엔드포인트가 없다. 완료 시점을 ONBOARD-004로
  옮기는 설계는 001·002 요청과 공통 이슈라
  `.claude/plans/be/SY019-onboarding-enforcement.md`에서 함께 다룰 예정.
- **3. 이미 완료한 회원의 재요청/유형 변경 허용 정책** — 미결정.
- **5. Swagger 문서화** — 엔드포인트 구현 후 진행.

## FE 관련 파일

- `FE/src/domains/onboard/api/onboarding.ts`
- `FE/src/domains/onboard/pages/OnboardingMemberTypeView.vue`
- `FE/docs/frontend/api/api-index.md`

## 진행 상황 (2026-07-31)

`POST /api/me/onboarding/complete` 엔드포인트, 관련 컨트롤러/서비스는 여전히 없다 — 001(기본
정보)·002(관심 정보) 저장 API는 이번에 구현했지만, 이 요청(회원 유형 저장 + 온보딩 완료)은
아직 착수 전이다. `SY019` 계획에서 완료 시점 설계가 정해지면 그 계획에 따라 구현한다.
