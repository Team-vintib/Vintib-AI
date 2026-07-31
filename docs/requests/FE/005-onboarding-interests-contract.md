# 온보딩 관심 브랜드·카테고리 저장(ONBOARD-002) 실제 계약

**요청자 파트**: BE
**대상 파트**: FE

## 배경/이유

`.codex/requests/be/002-onboarding-interests-api.md`(FE 선행 계약)에 적힌 `PUT /api/me/interests`와
실제 구현이 다르다. `APIs.md`(공식 스펙)에 이미 명시된 대로 `/users/{id}/interests`로 구현했다 —
ONBOARD-001(`.claude/requests/fe/004-onboarding-basic-info-contract.md`)에서 같은 이유로
`/api/me/onboarding` 대신 `/api/users/{id}`를 쓰기로 한 것과 동일한 결정이다. `{id}`는
로그인한 본인 회원 ID로, 다르면 403이 온다 — FE가 우려했던 "신뢰할 수 있는 회원 ID
Store 부재" 문제는, 로그인 응답/`GET /api/users/{id}`(MY-001 조회)로 본인 ID를 이미
받는다는 전제로 해소된다고 보고 진행했다. 이 전제가 실제 FE 흐름과 안 맞으면 알려달라.

브랜드/카테고리는 숫자 ID다 — `brand-a`/`outer` 같은 임시 문자열 식별자가 아니라
`GET /api/brands`, `GET /api/categories`(SY007, 인증 불필요)가 내려주는 `id`(Long)를
그대로 쓰면 된다.

## 요청 내용

- **엔드포인트**:
  - 조회: `GET /api/users/{id}/interests`
  - 등록/수정: `PUT /api/users/{id}/interests`
- **요청 바디**(PUT) — FE 계약과 필드명은 동일, ID 타입만 문자열이 아니라 숫자다:
  ```json
  {
    "brandIds": [1, 3],
    "categoryIds": [2, 5]
  }
  ```
  - 둘 다 필수 필드(배열 자체는 항상 보내야 함)지만, 빈 배열은 허용한다(건너뛰기).
  - **전체 교체(full-replace) 방식** — 기존에 저장된 관심 브랜드/카테고리를 요청 배열로 통째로
    바꾼다. 부분 추가/삭제가 아니다. 빈 배열로 PUT하면 기존 관심 정보가 전부 삭제된다(질문
    4번에 대한 답: 맞다, 빈 배열 = 삭제/건너뛰기 의미).
  - 온보딩 최초 완료든 마이페이지 수정(MY-001)이든 같은 엔드포인트, 같은 규칙이다.
- **응답(200)**:
  ```json
  {
    "success": true,
    "data": {
      "brands": [{ "id": 1, "name": "리바이스", "nameEn": "Levi's" }],
      "categories": [{ "id": 2, "parentId": null, "name": "아우터", "depth": 1 }]
    },
    "error": null
  }
  ```
  (요청 계약의 `data: null` 대신 저장 결과를 그대로 돌려준다 — 다시 조회하지 않아도 화면
  갱신에 쓸 수 있게.)
- **에러**: `400`(존재하지 않는 브랜드/카테고리 ID 포함, `error.code`는 카테고리
  `CATEGORY_NOT_FOUND`/`P008`, 브랜드 `BRAND_NOT_FOUND`/`P009`), `401`(인증 필요),
  `403`(본인 아닌 회원 조회/수정 시도, `MEMBER_FORBIDDEN`/`U013`), `404`(회원 없음).
  - 존재하지 않거나 비활성화된 ID, 중복 ID 관련: 중복 ID는 정상 처리(같은 ID 여러 번
    보내도 한 번만 저장됨). 비활성화 브랜드/카테고리 개념 자체가 현재 스키마에 없다(전부
    활성 상태로 취급).

## 아직 확인되지 않은 것

- 실제 온보딩 완료(`onboardingCompleted`) 처리 시점 — ONBOARD-004(회원 유형 저장)까지 마친
  시점에 최종 완료로 처리해야 한다는 이슈가 `.codex/requests/be/001`, `002`, `004`에 공통으로
  남아 있다. 현재는 ONBOARD-001(기본 정보 저장) 시점에 바로 `onboardingCompleted = true`로
  바뀌는 예전 동작 그대로다 — 이 관심 정보 저장 API는 `onboardingCompleted`를 건드리지
  않는다. 완료 시점 재설계는 `.claude/plans/be/SY019-onboarding-enforcement.md`에서
  다룰 예정이며, 아직 미결정이다.

## 관련 자료

- Swagger: `/swagger-ui/index.html` — "회원(Users)" 태그, `GET`/`PUT /api/users/{id}/interests`
- `BE/src/main/java/com/ssafy/backend/member/controller/UserController.java`
- `BE/src/main/java/com/ssafy/backend/member/dto/request/UpdateInterestsRequest.java`
- `BE/src/main/java/com/ssafy/backend/member/dto/response/InterestsResponse.java`
