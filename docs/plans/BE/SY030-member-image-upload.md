# SY030 — 프로필/커버 이미지 업로드

## 배경/목표

`docs/requests/BE/011-user-mypage-contract.md` §5가 추후 구현 예정으로 남겨뒀던 "프로필 이미지
업로드"를 구현한다. `SY029`에서 `coverImageUrl`을 문자열로 직접 받는 임시 계약을 만들었는데, 이제
실제 업로드 플로우로 대체한다.

## 재사용할 기존 패턴

상품 이미지(`ProductImageService`)·시착 프로필 사진(`TryOnProfileService`)이 이미 쓰는 **presigned
2단계**(발급 → 브라우저 직접 PUT → key 확인) 그대로 따른다. `global/storage/S3StorageService`,
`S3Config.AwsProperties`를 그대로 재사용 — 새 공용 컴포넌트는 만들지 않는다.

## 설계 결정

### 버킷 — public

프로필/커버 이미지는 마이페이지·공개 프로필에 상시 노출되는 비민감 이미지라 상품 이미지와 같은
`publicBucket` + 고정 `publicUrl`을 쓴다(시착 프로필의 `privateBucket`+매번 재발급 presigned GET과
다른 이유 — 그건 개인 신체 사진이라 비공개가 맞다).

### 저장값 — key가 아니라 최종 URL을 컬럼에 저장

상품 이미지는 `imageKey`를 저장하고 응답 시점에 `publicUrl(bucket, key)`로 변환한다. 회원
프로필/커버는 그 방식을 안 따르고 **컬럼에 완성된 URL을 그대로 저장**한다 — `MemberProfileResponse`/
`PublicProfileResponse`/`MypageSummaryResponse`가 이미 `member.getProfileImageUrl()`을 S3 의존성
없이 그대로 읽는 계약(FE에도 이미 "URL 문자열"로 안내됨, SY028/SY029)을 안 건드리기 위함이다.
서버 확정 엔드포인트(`PUT .../profile-image`)에서 key를 받아 `publicUrl`로 변환한 뒤 컬럼에 저장한다.

**트레이드오프**: 컬럼에 key를 안 들고 있으므로 이미지를 교체/삭제할 때 이전 S3 객체를 지우지
않는다(tryon은 지운다). public 버킷의 비민감 이미지라 orphan 객체가 남아도 실질적 문제가 없다고
판단해 여기까지는 안 한다 — 나중에 정리 배치가 필요해지면 별도로 다룬다.

### 엔드포인트 — `profile-image`/`cover-image` 하위 리소스로 분리

`Member`에 필드가 2개(단일 값)라 tryon처럼 하나의 upsert에 합치지 않고, 각각 발급/확정/삭제
3종으로 나눈다(상품 이미지의 "발급→등록" 2단계 + tryon의 "삭제" 엔드포인트를 합친 모양):

- `POST /api/users/{id}/profile-image/upload-url` — 발급
- `PUT /api/users/{id}/profile-image` — body `{key}`, key 확인 후 URL 저장, `MemberProfileResponse` 반환
- `DELETE /api/users/{id}/profile-image` — URL을 null로(S3 객체는 안 지움, 위 트레이드오프)
- `cover-image`도 동일하게 3종.

두 리소스가 요청/응답 모양이 완전히 같아 DTO(`MemberImageUploadUrlRequest/Response`,
`MemberImageKeyRequest`)는 공용으로 하나씩만 만든다.

### 코드 위치 — 신규 `MemberImageService`

`UserService`가 이미 커진 상태라, `ProductImageService`가 `ProductService`와 분리된 것과 같은
이유로 별도 서비스로 뺀다. 컨트롤러는 기존 `UserController`에 이어 붙인다(경로가
`/api/users/{id}/...` 그대로라 별도 컨트롤러를 만들 이유가 없음 — `MyProductController` 분리와는
다른 경우, 거긴 `/api/products` 고정 경로와 충돌해서 분리한 것).

본인 확인은 `UserService`의 기존 메서드들과 동일하게 서비스 내부에서
`requesterId.equals(targetId)` → `MEMBER_FORBIDDEN`으로 한다(TryOnProfileController처럼 컨트롤러
레벨 `requireSelf`를 새로 안 만든다 — 같은 컨트롤러의 다른 메서드들과 패턴을 맞춘다).

### `UpdateBioRequest` 변경 — coverImageUrl 필드 제거 (breaking change)

`SY029`에서 `PATCH /users/{id}/bio`가 `coverImageUrl`을 원시 URL 문자열로 직접 받게 만들어뒀는데,
이제 커버 이미지는 이 presigned 플로우로만 설정한다. `UpdateBioRequest`에서 `coverImageUrl` 필드를
빼고 `description`만 남긴다 — `Member.updateBio`도 `description`만 받도록 좁힌다.
FE는 마이페이지 화면이 아직 없어(011 §2 확인됨) 이 필드를 쓰고 있지 않으므로 안전한 변경이다.
`docs/requests/FE/012`에 변경 사항을 명시한다.

### 검증/에러코드

- content-type 화이트리스트(jpeg/png/webp)는 기존 `INVALID_IMAGE_TYPE`(P006) 재사용(tryon도 이미
  P006을 재사용한 전례를 따름 — 도메인 전용 코드를 새로 안 판다).
- key 확인 실패(prefix 불일치/미업로드/용량 초과 10MB)는 신규 `MEMBER_IMAGE_UPLOAD_NOT_CONFIRMED`
  (U015) 하나로 통일(profile/cover 공용 — `ProductImageService.verifyUploaded`/
  `TryOnProfileService.verifyUploaded`와 동일 패턴).
- key 네임스페이스: `member-profiles/{memberId}/`, `member-covers/{memberId}/`.

## 구현 목록

- [x] `ErrorCode.MEMBER_IMAGE_UPLOAD_NOT_CONFIRMED`(U015) 추가
- [x] `member/dto/request/MemberImageUploadUrlRequest`, `MemberImageKeyRequest` 신규
- [x] `member/dto/response/MemberImageUploadUrlResponse` 신규
- [x] `Member`에 `updateProfileImage(String)`/`updateCoverImage(String)` 메서드 추가,
      `updateBio`에서 `coverImageUrl` 파라미터 제거
- [x] `UpdateBioRequest`에서 `coverImageUrl` 필드 제거
- [x] `member/service/MemberImageService` 신규 — 발급/확정/삭제 6메서드(profile×3 + cover×3).
      업로드 URL 발급도 `requireSelf` 체크를 거치도록 함(초기 구현 누락을 구현 중 발견해 수정).
- [x] `UserController`에 6개 엔드포인트 추가 + Swagger
- [x] `MemberImageServiceTest` 신규(Mockito, 12개), `UserServiceTest`의 `updateBio` 관련 테스트에서
      `coverImageUrl` 인자 제거
- [x] 부수 발견: `MemberProfileResponse`(본인 조회)에 애초에 `profileImageUrl` 필드가 없던 버그를
      같이 고침 — 값을 저장할 수단이 없어 드러나지 않았을 뿐 응답 계약상 있었어야 하는 필드였다.
- [x] `docs/APIs.md`, `docs/requests/FE/012`(bio 계약 변경 + 이미지 업로드 API 추가),
      `docs/requests/BE/011` §5/§6 갱신
- [x] `./gradlew build` 통과
