# SY029 — 소개글/커버 이미지 수정

## 배경/목표

`docs/requests/BE/011-user-mypage-contract.md` §5가 추후 구현 예정으로 미뤄뒀던 "소개글/커버 이미지
수정"을 구현한다. `docs/plans/BE/SY028-public-profile.md`에서 공개 프로필 응답에 `description`/
`coverImageUrl`을 빼면서 "해당 기능이 생기면 함께 추가한다"고 적어둔 항목이 이거다.

**범위에서 뺀 것**: 같은 §5의 "프로필 이미지 업로드"(실제 이미지 파일을 올리는 presigned URL
플로우)와 "사용자 활동 내역"은 이번에 다루지 않는다. 전자는 상품/시착 이미지처럼 별도의 업로드
플로우가 필요한 완전히 다른 스토리고, 후자는 활동 로그 데이터 모델 자체가 없어 범위가 크다. 이번엔
텍스트 소개글과 커버 이미지 "URL 값" 저장/수정만 다룬다(`profile_image_url`이 지금도 그냥 문자열
컬럼이고 업로드 플로우가 없는 것과 동일한 수준).

## 작업 내용

### 스키마

`member` 테이블에 컬럼 2개 추가(`docs/db/schema.sql`/`comments.sql` 갱신, 로컬은
`ddl-auto: update`라 재기동 시 자동 반영):

- `description VARCHAR(500)` — 소개글
- `cover_image_url VARCHAR(500)` — 커버 이미지 URL (`profile_image_url`과 동일한 길이 컨벤션)

### 엔티티/DTO

- `Member`에 `description`/`coverImageUrl` 필드 추가, `updateBio(description, coverImageUrl)`
  메서드 추가(둘 다 nullable — 값이 없으면 `null`로 지운다. `updateBasicInfo`와 동일하게 "매번
  전체를 새로 받는" 방식이라 부분 patch가 아니다).
- 신규 요청 DTO `member/dto/request/UpdateBioRequest(description, coverImageUrl)` — 둘 다
  `@Size(max = 500)`, 필수 아님(자기소개를 안 쓰는 회원도 있을 수 있어 `@NotBlank` 없음).
- `MemberProfileResponse`(본인 조회, MY-001)에 `description`/`coverImageUrl` 필드 추가.
- `PublicProfileResponse`(공개 프로필, 011 §3.3)에 같은 필드 추가 — SY028에서 빼뒀던 부분을
  채운다. 두 응답 다 `Member`에서 직접 읽으므로 `from`/`of` 팩토리 시그니처는 안 바뀐다(호출부
  변경 없음).

### 서비스/컨트롤러

- `UserService.updateBio(requesterId, targetId, request)` 신규 — `requireSelf` 체크(기존
  `updateBasicInfo`와 동일 패턴), `Member.updateBio` 호출 후 `MemberProfileResponse` 반환.
- `UserController PATCH /{id}/bio` 신규.
- 주소/닉네임 등 "매번 필수"인 `UpdateMemberRequest`/`PATCH /{id}`와 별도 엔드포인트로 분리한다 —
  소개글/커버는 선택 입력이라 같은 요청에 섞으면 그 엔드포인트의 "전부 필수" 契약이 깨진다.

## 구현 목록

- [x] `docs/db/schema.sql`, `comments.sql`에 `description`/`cover_image_url` 컬럼 추가
- [x] `Member` 엔티티 필드 + `updateBio` 메서드
- [x] `UpdateBioRequest` DTO
- [x] `MemberProfileResponse`/`PublicProfileResponse`에 필드 추가
- [x] `UserService.updateBio`, `UserController PATCH /{id}/bio` + Swagger
- [x] `UserServiceTest`에 단위 테스트 추가
- [x] `docs/APIs.md`, `docs/requests/FE/012`(본인 조회 응답 필드 갱신), `docs/requests/FE/014`(공개
      프로필 응답 필드 갱신 — coverImageUrl/description 제외 문구 삭제), `docs/requests/BE/011` §5
      갱신
- [x] `./gradlew build` 통과
