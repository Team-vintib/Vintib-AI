# SY023 Profile Media Bio

## 배경/목표

Swagger 기준 공개 프로필 응답에 `profileImageUrl`, `coverImageUrl`, `description`이 존재하고, 본인 프로필에서 이미지와 소개글을 등록·수정·삭제할 수 있는 API가 구현되어 있다. 기존 공개 프로필/팔로우 기능을 유지하면서 프로필 이미지, 커버 이미지, 소개글을 실제 API 범위 안에서 연결하고 판매자 쇼룸형 디자인으로 재구성한다.

## Swagger 확인 결과

- 공개 프로필 조회: `GET /api/users/{id}/profile`
  - 응답: `id`, `nickname`, `profileImageUrl`, `description`, `coverImageUrl`, `followerCount`, `followingCount`, `productCount`, `liveCount`, `isFollowing`, `businessVerified`
- 본인 프로필 조회: `GET /api/users/{id}`
  - 응답: `profileImageUrl`, `description`, `coverImageUrl` 포함
- 소개글 등록·수정: `PATCH /api/users/{id}/bio`
  - body: `{ description: string }`, 최대 500자
- 프로필 이미지 업로드 URL 발급: `POST /api/users/{id}/profile-image/upload-url`
  - body: `{ contentType: string }`
  - 응답: `{ key, uploadUrl, expiresInSeconds }`
- 프로필 이미지 확정: `PUT /api/users/{id}/profile-image`
  - body: `{ key: string }`
- 프로필 이미지 삭제: `DELETE /api/users/{id}/profile-image`
- 커버 이미지 업로드 URL 발급: `POST /api/users/{id}/cover-image/upload-url`
  - body: `{ contentType: string }`
  - 응답: `{ key, uploadUrl, expiresInSeconds }`
- 커버 이미지 확정: `PUT /api/users/{id}/cover-image`
  - body: `{ key: string }`
- 커버 이미지 삭제: `DELETE /api/users/{id}/cover-image`

## 작업 내용

`domains/profile`의 API 모듈에 소개글 및 이미지 업로드 2단계 플로우를 추가한다. 공개 프로필 화면은 커버 이미지가 있으면 쇼룸 배너로 사용하고, 프로필 이미지는 작은 대표 이미지로 표시한다. 이미지가 없으면 빈 아바타나 닉네임 이니셜을 만들지 않고 텍스트 중심 레이아웃을 유지한다. 본인 프로필에서만 편집 컨트롤을 노출해 소개글 저장, 프로필 이미지 등록/삭제, 커버 이미지 등록/삭제를 처리한다.

## 구현 목록

- [x] `profileApi.ts`에 `updateBio`, 프로필/커버 이미지 upload-url 발급, S3 `PUT`, 확정, 삭제 함수 추가
- [x] 관련 request/response 타입 추가 및 기존 `PublicProfile` 타입의 실제 필드 사용 유지
- [x] 본인 프로필에서만 노출되는 간단한 편집 패널 또는 인라인 편집 UI 추가
- [x] 프로필 카드 디자인을 커버 이미지가 있을 때/없을 때 모두 자연스럽게 보이도록 재구성
- [x] 프로필 이미지가 없을 때 기본 아바타·이니셜 이미지를 만들지 않고 텍스트 중심 fallback 유지
- [x] 소개글은 값이 있을 때만 공개 영역에 표시하고, 본인 편집 시 빈 값 저장으로 삭제 가능하게 처리
- [x] 이미지 업로드는 기존 presigned 업로드 패턴을 따라 `contentType` 발급 → S3 업로드 → key 확정 순서로 처리
- [x] 업로드/삭제/저장 중 버튼 비활성화 및 실패 메시지 처리
- [x] 저장 성공 후 공개 프로필 데이터를 재조회하거나 로컬 상태를 실제 응답값으로 갱신
- [x] 기존 팔로우/언팔로우, 상품/라이브 탭, 페이지네이션 동작 유지
- [x] `npm run lint`, `npm run type-check`, `npm run build-only` 검증

## 미결정 사항

- 이미지 파일 용량 제한은 Swagger DTO에 명시되어 있지 않다. FE에서는 기존 업로드 UI 관례를 확인해 과도한 파일만 제한하거나, 명세 밖 제한을 추가하지 않는 방향 중 승인 후 결정한다.
- 프로필 편집 진입은 별도 모달 대신 프로필 카드 내부 접이식 편집 영역으로 우선 구현한다.
