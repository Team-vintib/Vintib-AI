# SY024 — 팔로우(Follow)

- Jira 기능 ID: `FOLLOW-001`(팔로우/해제), `MY-006`(팔로워/팔로잉 목록), `HOME-002`(팔로잉 콘텐츠 실데이터 연동)

## 배경/목표

`social` 패키지에는 `Follow` 엔티티(서로게이트 PK, `follower`/`following` FK, DB `@Check`로 자기팔로우 방지)만 있고 CUD·조회 API가 없다. `APIs.md` "팔로우 / 찜 (Socials)" 섹션과 FE 계약 문서(`docs/requests/BE/008-social-notification-contract.md`, 반영 후 해당 섹션은 문서에서 제거됨)에 스펙이 이미 합의돼 있으므로 이를 API로 구현한다. 아울러 `home` 패키지 `FollowingService.getFollowingContent`가 전부 Mock인 것 중 "팔로우한 판매자"·"그 판매자들의 상품" 두 섹션을 실데이터로 전환한다.

## 작업 내용

### 1. Follow CUD API

- `POST /api/users/{userId}/followers`, `DELETE /api/users/{userId}/followers` — 인증 필요.
- **멱등(토글) 정책**: 사용자가 팔로우 버튼을 스위치처럼 연타해도 항상 안전하게 동작해야 한다는 요구에 따라, 이미 팔로우 중이어도 `POST`는 에러 없이 현재 상태를 `200 OK`로 반환하고(신규 저장 여부와 무관하게 항상 200 — "새 리소스 생성"을 뜻하는 201은 매 호출마다 성립하지 않으므로 쓰지 않는다), 팔로우 중이 아니어도 `DELETE`는 `204`로 반환한다. Wish의 엄격한 409/404 정책과 의도적으로 다르게 간다.
- 자기 자신 팔로우만 진짜 검증 실패로 취급해 `400 SELF_FOLLOW_NOT_ALLOWED`(신규, S004)를 던진다. 대상 회원이 없으면 기존 `USER_NOT_FOUND`(404) 재사용.
- 응답 `FollowResponse(targetUserId, isFollowing, followerCount)`.
- `FollowRepository`에 `existsByFollower_IdAndFollowing_Id`, `deleteByFollower_IdAndFollowing_Id`, `countByFollower_Id` 추가.

### 2. 팔로워/팔로잉 목록 API

- `GET /api/users/{userId}/followers`, `GET /api/users/{userId}/followings` — **인증 불필요**(공개 프로필). `WishController`의 `requireSelf`와 달리 본인 확인을 하지 않는다. `Authentication`을 nullable로 받아 `ProductController.getProductDetail`과 동일하게 `viewerId`를 뽑는다.
- 대상 회원이 존재하지 않으면 404.
- 정렬은 최신 팔로우순 고정(Wish와 동일 정책).
- 응답 `PageResponse<FollowUserResponse>` — `id, nickname, profileImageUrl, followerCount, productCount, isFollowing`. 비회원 조회 시 `isFollowing`은 **false**로 내린다(006 상품 상세 `isWished`와 동일 정책 — 최초에는 "안 팔로우함"과 "몰라서 못 채움"을 구분하려고 `null`로 설계했으나, FE 조사 결과 API 응답을 받는 지점에서 이미 `?? false`로 null을 뭉개 쓰고 truthy/falsy 체크만 하며 비회원 분기는 별도의 인증 상태 플래그로 하고 있어 `null`을 구분해서 얻는 실익이 없다고 판단해 `false`로 통일했다 — 아래 "구현 중 계획과 달라진 점" 참고).
- **N+1 방지**: 페이지 조회 1회 + 대상 회원들의 팔로워 수 배치 카운트(`GROUP BY`) 1회 + 상품 수 배치 카운트 1회 + 조회자의 isFollowing 배치 조회 1회, 총 4회 고정 쿼리로 페이지 크기와 무관하게 끝낸다. `ProductRepository`에 셀러 ID 목록 기준 배치 카운트 메서드를 추가한다(기존 `countBySeller_IdAndSaleStatusNot`은 단건이라 재사용 안 함).

### 3. ErrorCode

`// [소셜(팔로우/찜)]` 구역에 `SELF_FOLLOW_NOT_ALLOWED(400, S004)` 추가. 그 외 팔로우 전용 코드는 만들지 않는다(멱등 정책상 충돌/미존재 에러 불필요).

### 4. SecurityConfig

`ProductController`/`LiveController`가 쓰는 방식(정확 경로 화이트리스트가 아니라 `HttpMethod.GET` + 패턴 매칭)을 그대로 따라 팔로워/팔로잉 목록 GET 두 경로만 `permitAll()` 추가. `POST`/`DELETE`는 `anyRequest().authenticated()`에 자연히 걸린다.

### 5. 홈 화면 연동 (`home/service/FollowingService`)

- **`followedSellers`·`products` — 실데이터로 전환.** `products`는 `ON_SALE`(직접 판매 중) 상품만 최신순 상위 20개로 채운다 — `ProductCardResponse`의 `sellType`/`sellStatus` 허용값이 아직 `SaleType`/`SaleStatus`/경매 도메인과 1:1로 매핑 확정되지 않았고, 경매 예정 상품은 `auction` 패키지(정윤 소유) 조회가 별도로 필요해 이번 범위를 벗어난다.
- `FollowedSellerResponse.coverImageUrl`은 **항상 null**로 둔다 — `Member` 엔티티에 커버 이미지 컬럼 자체가 없다(프로필 커버 업로드 기능 미구현, 팔로우와 무관한 별도 작업).
- **`lives`는 이번 범위에서 Mock을 걷어내고 항상 빈 배열로 둔다** (직접 실데이터로 채우지 않음). 이유: `LiveRepository`에 host 기준 조회가 없고, `HomeService`(HOME-001)의 라이브 섹션도 아직 전부 Mock이라 라이브 카드 조회 로직(썸네일·시청자 수·상태 매핑) 자체가 정의된 적이 없다. 지금 임시로 설계하면 이후 정윤이 HOME-001을 실데이터로 옮기면서 다시 고쳐야 할 가능성이 높다. 다만 기존 `mockFollowingLives()`가 `memberId`와 무관하게 항상 라이브 1건을 반환해 `followedSellers`/`products`가 실데이터로 바뀐 뒤에는 `empty` 판정과 모순되므로, 이 부분만 빈 리스트로 고친다.
- 의존성 추가: `FollowRepository`, `ProductRepository`, `ProductImageRepository`, `CategoryRepository`, `BrandRepository`, `SocialQueryPort`, `S3StorageService`, `AwsProperties`. (Wish가 이미 `ProductRepository`를 직접 참조하는 것과 동일하게, `home`은 최상위 집계 도메인이라 하위 도메인 레포지토리를 포트 없이 직접 참조한다 — `product`/`live`가 서로를 참조할 때만 포트를 쓰는 기존 컨벤션과 일관됨.)

### 6. 테스트

- `FollowServiceTest`(Mockito 단위 테스트, Wish 스타일): 팔로우 성공 / 이미 팔로우 중이어도 멱등하게 현재 상태 반환 / 자기 자신 팔로우 시 예외 / 존재하지 않는 회원 팔로우 시 예외 / 해제 성공 / 팔로우 안 한 상태에서 해제해도 멱등하게 성공 / 팔로워 목록 최신순 반환 / 비회원 조회 시 isFollowing null / 로그인 조회 시 isFollowing 채워짐.
- `FollowingControllerTest`는 현재 Mock 하드코딩 assertion(`coverImageUrl` 값 존재 등)을 전제로 하므로, 실데이터 시드 기반으로 갱신한다.
- `FollowingServiceTest` 신규 작성.

### 7. 문서

`BE/README.md` 디렉터리 구조에 `social/` 새 파일, `home/`의 "Mock" 문구 갱신.

## 구현 목록

- [x] `ErrorCode`에 `SELF_FOLLOW_NOT_ALLOWED(S004)` 추가
- [x] `FollowRepository` 확장(존재확인/삭제/카운트/페이징 조회/배치 카운트/isFollowing 배치 조회)
- [x] `social/dto/response/FollowResponse.java`, `FollowUserResponse.java`
- [x] `social/service/FollowService.java`
- [x] `social/controller/FollowController.java` (Swagger 태그 `"팔로우 / 찜(Socials)"` 재사용)
- [x] `SecurityConfig`에 팔로워/팔로잉 목록 GET permitAll 추가
- [x] `ProductRepository`에 셀러별 배치 상품수 카운트, 셀러 목록 기준 ON_SALE 상품 조회 추가
- [x] `ProductImageRepository`에 대표이미지 배치 조회 추가
- [x] `home/service/FollowingService.java` 실데이터 연동(`followedSellers`/`products`), `lives`는 빈 배열로 정리
- [x] `FollowServiceTest` 작성 (9건: 팔로우 성공/멱등/자기팔로우 금지/대상없음, 해제 성공/멱등, 목록 최신순/비회원 null/로그인 isFollowing/대상없음 404)
- [x] `FollowingControllerTest` 갱신, `FollowingServiceTest` 신규
- [x] `BE/README.md` 갱신
- [x] Swagger 어노테이션(`@Tag`/`@Operation`/`@ApiResponses`/`@Schema`) 반영
- [x] BE 검증 하네스(`./gradlew build`, CI `be-test`와 동일) 통과 확인 — `BUILD SUCCESSFUL`, 전체 테스트 green

## 구현 중 계획과 달라진 점

- `FollowingService.toProductCards`에서 판매자 닉네임(`Member.getNickname()`)을 `Collectors.toMap`으로 모으면, 온보딩 전이라 닉네임이 `null`인 판매자가 있을 때 `Map.merge`가 NPE를 던진다는 걸 실제 DB 연동 테스트에서 확인했다. `HashMap`에 직접 채우는 방식으로 바꿔 null 값을 허용하도록 고쳤다(계획 대비 발견한 버그 수정, 범위 변경 아님).
- `FollowingControllerTest`는 실제 회원 row를 시딩하는 방식으로 바뀌면서 `OnboardingRequiredFilter`(SY019, `/api/home/following`은 화이트리스트 밖)에 걸려 온보딩 미완료 회원은 403을 받는다는 게 드러났다. 테스트 회원을 `completeOnboarding()`으로 처리한 뒤 시딩하도록 수정했다 — 실제 운영 동작과 일치하는 정상적인 제약이라 별도 대응 불필요.
- 머지 후 `isFollowing` 비회원 정책을 `null` → `false`로 재조정했다. `FollowUserResponse.isFollowing`을 `Boolean` → `boolean`으로, `FollowService.toResponse`의 분기를 `viewerId == null ? null : ...`에서 `viewerId != null && ...`로 바꾸고, 관련 테스트(`비회원이_조회하면_isFollowing이_null이다` → `...false다`)와 컨트롤러 Swagger 설명을 함께 갱신했다.