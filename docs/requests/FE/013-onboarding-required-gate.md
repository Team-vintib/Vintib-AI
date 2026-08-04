# 온보딩 완료 강제 게이트 — 403 ONBOARDING_REQUIRED

**요청자 파트**: BE
**대상 파트**: FE

## 배경/이유

지금까지는 회원가입 직후 `onboardingCompleted = false`인 상태로도 다른 모든 API를 자유롭게
호출할 수 있었다(FE가 가입 직후 온보딩 화면으로 보내주는 것에만 의존). 이제 BE가 이를 실제로
막는 게이트를 추가했다(`docs/plans/BE/SY019-onboarding-enforcement.md`).

## 바뀌는 동작

- 로그인한 회원이 **온보딩을 완료하지 않은 상태**(`onboardingCompleted == false`)로
  아래 화이트리스트 밖의 API를 호출하면 **403**이 온다:
  ```json
  {
    "success": false,
    "data": null,
    "error": {
      "code": "U004",
      "message": "온보딩을 완료해야 이용할 수 있습니다.",
      "errors": null
    }
  }
  ```
- 화이트리스트(온보딩 미완료여도 허용):
  - `POST /api/auth/reissue`(토큰 재발급), `POST /api/auth/logout`
  - `PATCH /api/users/{id}`(ONBOARD-001), `PUT /api/users/{id}/interests`(ONBOARD-002),
    `PATCH /api/users/{id}/member-type`(ONBOARD-004), `PUT /api/users/{id}/tryon`과
    `POST /api/users/{id}/tryon/upload-url`(ONBOARD-003, 시착 프로필 — 이제 구현 완료·화이트리스트에
    포함됨. 엔드포인트는 `/api/me/tryon`이 아니라 `/api/users/{id}/tryon`이다 —
    `009-tryon-profile-presigned-upload.md` 참고)
- 그 외 상품/라이브/경매/채팅/찜/알림 등 나머지 API는 전부 차단 대상이다.

## ONBOARD-004에서 새로 추가된 오류

`PATCH /api/users/{id}/member-type` 호출 시 아직 `PATCH /api/users/{id}`(ONBOARD-001,
닉네임 등록)를 안 거쳤으면 400이 온다:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "U014",
    "message": "기본 정보를 먼저 등록해주세요.",
    "errors": null
  }
}
```

001→002→003→004 순서로 화면을 넘기는 흐름이라면 실무적으로 발생하지 않지만, 혹시 004로
바로 진입하는 경로가 있다면 이 오류를 대비해야 한다.

## FE 확인 필요

- 온보딩 미완료 상태에서 화이트리스트 밖 API를 호출하는 화면이 있는지(있다면 온보딩 화면으로
  리다이렉트하는 로직이 필요) 점검해달라.
- `403 U004`를 받으면 온보딩 미완료 회원을 온보딩 화면으로 보내는 공통 처리(axios 인터셉터 등)를
  추가하는 걸 권장한다 — 화면마다 개별 처리하면 빠뜨리기 쉽다.

## 참고

- `docs/plans/BE/SY019-onboarding-enforcement.md`
- `BE/src/main/java/com/ssafy/backend/auth/jwt/OnboardingRequiredFilter.java`
- `BE/src/main/java/com/ssafy/backend/global/exception/ErrorCode.java`
