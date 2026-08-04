# SY028 — 공개 회원/판매자 프로필

## 배경/목표

`docs/requests/BE/011-user-mypage-contract.md` §3.3이 요청한 공개 프로필 API를 구현한다.
상품 상세 판매자 영역, 검색 회원 결과, 라이브 호스트 정보처럼 **다른 사용자가 어떤 회원을 볼 때**
쓰는 비회원도 조회 가능한 API다. 이미 있는 `GET /api/users/{id}`(MY-001, 본인 전용·인증 필수·전화번호
등 민감정보 포함)와는 목적이 다르다.

## 작업 내용

### 경로 — 기존 `GET /api/users/{id}`와 분리

FE가 요청한 경로는 기존 자기 정보 조회와 동일한 `GET /api/users/{userId}`이지만, 이미 그 경로는
본인 전용(인증 필수, 403 IDOR 방지, 민감정보 포함)으로 확정돼 있어 그대로 재사용하면 인증 여부에
따라 응답 타입 자체가 달라지는 하나의 엔드포인트가 된다 — Swagger 계약이 애매해지고, 기존 자기
정보 조회의 보안 모델(permitAll 아님)을 건드리는 위험한 변경이라 피한다. 대신 별도 경로로 만든다:

- `GET /api/users/{userId}/profile` — 공개 프로필(비회원 조회 가능)

FE 계약 문서(`docs/requests/FE/018-mypage-contract.md`)에 경로 변경 사유를 명시해 전달한다.
(이번 요청 범위 내 MY-005 `hostId` 쿼리 파라미터, MY-007 `points`/`logs` 명칭처럼, 계획 대비 실제
경로가 조정되는 전례를 따르는 것.)

### 인증 — `FollowController.getFollowers`와 동일 패턴

`SecurityConfig.PUBLIC_ENDPOINTS`엔 패턴 매칭이 안 돼(`{userId}`가 끼어 있어 static 문자열
whitelist로 못 넣음) 기존 `GET /api/users/{userId}/followers`처럼 `authorizeHttpRequests`에
`.requestMatchers(HttpMethod.GET, "/api/users/{userId}/profile").permitAll()` 한 줄을 추가한다.
컨트롤러는 `Authentication authentication`을 받되 `null`을 허용하고,
`viewerId = authentication != null ? (Long) authentication.getPrincipal() : null`로 뽑는다
(`FollowController.getFollowers/getFollowings`와 동일 패턴).

### 응답 필드 — 스키마에 없는 2개 필드는 이번 범위에서 뺀다

FE 요청 필드: `id`, `nickname`, `profileImageUrl`, `coverImageUrl`, `description`, `followerCount`,
`followingCount`, `productCount`, `liveCount`, `isFollowing`, `businessVerified`.

`member` 테이블(`docs/db/schema.sql`)에 `cover_image_url`/`description` 컬럼이 아예 없다 —
`docs/requests/BE/011` §5도 "소개글/커버 이미지 수정"을 추후 구현 예정으로 명시해 지금 범위가
아님을 이미 인정하고 있다. 이번 스토리는 **읽기 전용 조회 API**라 스키마 변경까지 벌이지 않고,
이 두 필드는 이번 응답에서 뺀다(추후 소개글/커버 이미지 기능이 생기면 그때 필드를 추가한다).
나머지 9개 필드만 구현한다.

- `id`, `nickname`, `profileImageUrl` — `Member`에서 그대로.
- `followerCount` — `FollowRepository.countByFollowing_Id`(기존).
- `followingCount` — `FollowRepository.countByFollower_Id`(신규 추가, `countByFollowing_Id`와 대칭).
- `productCount` — `ProductRepository.countBySeller_IdAndSaleStatusNot(sellerId, DRAFT)`(기존 —
  상품 상세 판매자 통계가 쓰는 것과 동일한 메서드를 그대로 재사용, 신규 코드 없음).
- `liveCount` — `LiveRepository`에 `countByHost_IdAndStatusIn(hostId, statuses)` 신규 추가,
  `LiveService.PUBLIC_STATUSES`(SCHEDULED/LIVE)로 호출.
- `isFollowing` — `viewerId`가 없으면 `false`(팔로워 목록 API와 동일 정책, `docs/requests/BE/011`
  §6 "비회원 공개 프로필의 isFollowing 값 정책" 미결 사항을 이 전례로 확정). 있으면
  `FollowRepository.existsByFollower_IdAndFollowing_Id(viewerId, targetId)`(기존).
- `businessVerified` — `BusinessInfoRepository.findById(targetId)`의
  `verificationStatus == APPROVED` 여부(boolean). `MemberProfileResponse`가 문자열 4종을 그대로
  노출하는 것과 달리, 공개 프로필은 PENDING/REJECTED/NONE을 구분해 노출할 필요가 없어(다른 사용자
  입장에서 "인증됐는지 여부"만 의미 있음) boolean으로 단순화한다.

### 코드 위치

기존 `UserController`/`UserService`에 이어 붙인다(마이페이지 요약과 같은 이유 — 회원 조회
도메인이라 별도 컨트롤러를 만들 필요 없음).

- `member/dto/response/PublicProfileResponse` 신규.
- `UserService.getPublicProfile(viewerId, targetId)` 신규 — `requireSelf` 체크 없음(공개),
  대상 회원 없으면 `USER_NOT_FOUND`만 확인.
- `UserController GET /{id}/profile` 신규.
- `FollowRepository.countByFollower_Id`, `LiveRepository.countByHost_IdAndStatusIn` 신규 메서드.
- `SecurityConfig`에 permitAll 패턴 1줄 추가.

## 구현 목록

- [x] `FollowRepository.countByFollower_Id` 추가
- [x] `LiveRepository.countByHost_IdAndStatusIn` 추가
- [x] `PublicProfileResponse` DTO
- [x] `UserService.getPublicProfile`
- [x] `UserController GET /{id}/profile` + Swagger 문서화
- [x] `SecurityConfig` permitAll 추가
- [x] `UserServiceTest`에 단위 테스트 추가(정상 조회/비회원 isFollowing=false/로그인 회원
      isFollowing=true/사업자 인증 승인·대기 구분/대상 회원 없음 404)
- [x] `docs/APIs.md`, `docs/requests/BE/011`, `docs/requests/BE/006`(인덱스) 갱신, 신규
      `docs/requests/FE/020-public-profile-contract.md` 작성(마이페이지 계약과 성격이 달라 `018`에
      합치지 않고 별도 번호로 분리)
- [x] `./gradlew build` 통과

## 확인이 필요한 미결정 사항

- `coverImageUrl`/`description`은 스키마에 없어 이번엔 응답에서 제외 — 프로필 이미지 업로드·소개글
  기능이 생기면 그때 컬럼과 함께 추가한다.
