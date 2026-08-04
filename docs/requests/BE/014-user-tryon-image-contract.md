# 사용자 AI 시착용 기본 사진 API 요청

## 요청 파트 / 대상 파트

- 요청 파트: FE
- 대상 파트: BE

## 배경/이유

온보딩에서 사용자의 AI 시착용 기본 사진을 받고, 이후 마이페이지 `내 정보 변경`에서 같은 사진을 조회/변경/삭제할 수 있어야 한다. 이 사진은 프로필 표시용 사진과 별개이며, 사용자가 추후 별도로 프로필 사진을 선택하지 않는 한 `profileImageUrl`로 사용하지 않는다.

## 남은 요청 내용

프로필 사진/시착 기본 사진 API 자체는 아래 "확인 결과"에 정리된 대로 이미 있다. 남은 건 하나뿐이다.

- 마이페이지 요약 응답(`GET /api/users/{userId}/mypage`)에 현재 시착 기본 사진 URL을 포함해달라.
  - 필드 제안: `user.bodyPhotoUrl: string | null` (기존 `user.profileImageUrl`과 같은 레벨)
  - `TryOnProfileController`의 `bodyPhotoUrl`과 같은 값을 내려주면 된다.

## 2026-08-03 확인 결과 — 실제로는 대부분 구현되어 있음(경로가 `/me/*`가 아닐 뿐)

`/api/me/*` 경로로는 없지만, 이 프로젝트 전체 컨벤션대로 `/api/users/{userId}/*`(본인 확인은 JWT
principal과 대조) 경로에 이미 구현돼 있다. FE가 `/me` 계열로만 찾아서 "미구현"으로 판단한 것으로 보인다.

- 프로필 표시 사진: `POST /api/users/{id}/profile-image/upload-url`(presigned 발급) →
  `PUT /api/users/{id}/profile-image`(확정) → `DELETE /api/users/{id}/profile-image`
  (`UserController`, `docs/APIs.md` 회원 섹션에 이미 문서화됨 — 2단계 presigned 업로드다,
  `{profileImage}` 단일 파일 필드로 바로 PUT하는 방식이 아니다).
- AI 시착용 기본 사진: `GET/PUT/DELETE /api/users/{userId}/tryon`(`TryOnProfileController`) —
  응답 필드명은 `defaultTryOnImageUrl`이 아니라 `bodyPhotoUrl`이다.
- 두 API는 서로 다른 리소스라 요청서에서 우려한 "한쪽이 다른 쪽을 건드리는" 문제는 애초에 없다.

**여전히 없는 것**: `GET /api/users/{userId}/mypage`(`MypageSummaryResponse.User`)에
`bodyPhotoUrl`(또는 `defaultTryOnImageUrl`) 필드가 없다 — `profileImageUrl`만 있다. 마이페이지 요약에
시착 기본 사진을 같이 보여주려면 이 필드 추가가 필요하다(아래 요청 내용 중 이 항목만 남는다).
