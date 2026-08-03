# 사용자 AI 시착용 기본 사진 API 요청

## 요청 파트 / 대상 파트

- 요청 파트: FE
- 대상 파트: BE

## 배경/이유

온보딩에서 사용자의 AI 시착용 기본 사진을 받고, 이후 마이페이지 `내 정보 변경`에서 같은 사진을 조회/변경/삭제할 수 있어야 한다. 이 사진은 프로필 표시용 사진과 별개이며, 사용자가 추후 별도로 프로필 사진을 선택하지 않는 한 `profileImageUrl`로 사용하지 않는다.

## 요청 내용

- 프로필 표시 사진과 AI 시착용 기본 사진을 분리한다.
  - `profileImageUrl`: 공개 프로필/헤더/판매자 카드 표시용. 온보딩에서는 받지 않는다.
  - `defaultTryOnImageUrl`: AI 시착 기본 입력 이미지. 온보딩에서 받고 마이페이지에서 관리한다.
- 마이페이지에서 프로필 표시 사진 조회/변경/삭제가 가능해야 한다.
  - 조회 대상: `GET /api/users/{userId}/mypage` 또는 `GET /api/me`
  - 필드: `profileImageUrl: string | null`
  - 업로드/수정 후보: `PUT /api/me/profile-image`
  - 파일 필드: `profileImage`
  - 삭제 후보: `DELETE /api/me/profile-image`
  - 이 API는 `defaultTryOnImageUrl`을 변경하지 않아야 한다.
- 온보딩 시착 프로필 저장 API의 사진 필드를 기본 시착 사진으로 저장한다.
  - 기존 후보: `PUT /api/me/tryon`
  - 파일 필드: `bodyPhoto`
  - 저장 결과가 이후 `defaultTryOnImageUrl`로 조회되어야 한다.
- 마이페이지에서 시착용 기본 사진 조회/변경/삭제가 가능해야 한다.
  - 조회 후보: `GET /api/me/tryon`
  - 업로드/수정 후보: `PUT /api/me/tryon`
  - 삭제 후보: `DELETE /api/me/tryon/image`
- 마이페이지 요약 응답에도 현재 기본 시착 사진 URL 포함이 필요하다.
  - 대상 후보: `GET /api/users/{userId}/mypage`
  - 필드: `summary.profile.defaultTryOnImageUrl: string | null`
- 허용 파일
  - `image/jpeg`, `image/png`, `image/webp`
  - 권장 제한: 5MB 이하

## 응답 예시

프로필 사진 변경:

```json
{
  "success": true,
  "data": {
    "profileImageUrl": "https://.../profile.jpg"
  },
  "error": null
}
```

AI 시착용 기본 사진 변경:

```json
{
  "success": true,
  "data": {
    "defaultTryOnImageUrl": "https://.../tryon-default.jpg"
  },
  "error": null
}
```

## FE 임시 처리

- API 확정 전까지 마이페이지는 선택한 이미지를 미리보기/mock 상태로 반영한다.
- 실제 저장 연동 시 `profileImageUrl`은 건드리지 않고 `defaultTryOnImageUrl`만 갱신해야 한다.
- 프로필 사진 변경 UI는 같은 저장 버튼 안에서 mock 상태로 반영하되, 실제 API 연동 시에는 `profileImageUrl` 전용 API만 호출해야 한다.

## 2026-08-02 확인 결과

- BE 컨트롤러 기준으로 `GET/PUT /api/me/tryon`, `DELETE /api/me/tryon/image`, `PUT/DELETE /api/me/profile-image` 구현은 확인되지 않았다.
- FE는 온보딩 AI 시착용 기본 사진과 마이페이지 프로필/시착용 사진 관리를 mock/local fallback으로 유지한다.
- `GET /api/users/{userId}/tryons`, `GET /api/users/{userId}/tryons/{id}`, `DELETE /api/users/{userId}/tryons/{id}`는 시착 결과 내역용 API로 확인되며, 기본 시착 사진 저장/조회 API와는 용도가 다르므로 이번 마이페이지 사진 관리에는 직접 연결하지 않는다.
