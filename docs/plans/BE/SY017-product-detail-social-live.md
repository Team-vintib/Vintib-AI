# 상품 상세조회 확장 — 찜/판매자통계/연결라이브 (PROD-006)

## 배경/목표

`.codex/requests/be/007-product-detail-view-contract.md`(FE 요청)가 `GET /api/products/{id}` 응답에 이미지, 연결 라이브, 찜, 판매자 상세(팔로워수·판매상품수), 판매자 고지 하자, AI 품질 분석을 요구한다. 이미지는 이미 `images` 필드로 제공 중이다. 나머지 중 **AI 품질 분석은 이번 스코프에서 제외**한다(AI 쪽이 아직 발표된 비동기 계약(job_id+polling)대로 코드가 바뀌지 않아 크로스팀 리스크가 있음 — 별도 Jira 이슈로 분리해 AI 파트와 일정을 맞춘 뒤 진행). 이 계획은 나머지(브랜드/카테고리 표시명, 찜 여부, 판매자 통계, 판매자 하자, 연결 라이브)를 다룬다.

색상/소재/실측/하자 필드 자체는 `SY015`에서 추가한다. 이 계획은 그 값들을 상세 응답에 포함시키는 것과, 찜/팔로워/연결라이브처럼 **다른 도메인 데이터를 끌어와야 하는 부분**을 다룬다.

## 아키텍처 결정 — 대칭 포트 패턴

`product` 도메인이 `live`(연결 라이브)와 `social`(찜/팔로워)의 데이터를 읽어야 하는데, 두 패키지 모두 이미 `product`를 참조하고 있다(`live/port/ProductQueryAdapter`가 `product.repository.ProductRepository` 등을 import, `social/entity/Wish`가 `product.entity.Product`를 FK로 참조). `product`가 `live`/`social`을 직접 import하면 순환 의존이 생긴다.

기존 `live`가 이미 쓰는 패턴(`live/port/ProductQueryPort` 인터페이스를 `live`가 소유하고, 구현체 `ProductQueryAdapter`가 `product` 쪽을 import)을 대칭으로 뒤집어 적용한다: **`product`가 포트 인터페이스를 소유**하고, **구현체는 `live`/`social` 패키지에 둔다**(그 구현체만 반대쪽을 import). 이러면 `product` 패키지 자체는 여전히 `live`/`social`을 import하지 않는다.

## 작업 내용

### 1. 판매자 통계용 최소 Follow 엔티티

- 신규 `social/entity/Follow.java`: `id, follower(Member FK), following(Member FK), createdAt`. `(follower_id, following_id)` 유니크 제약, `follower_id <> following_id` 체크 제약.
- 신규 `social/repository/FollowRepository.java`: `long countByFollowing_Id(Long memberId)`.
- 이번엔 팔로우/언팔로우 API(컨트롤러)는 만들지 않는다 — FOLLOW-001 전체 기능은 별도 스코프, 카운트 조회에 필요한 최소 구조만 추가.
- DB: 신규 `follow` 테이블.

### 2. 상품→라이브 역방향 조회

- 신규 `product/port/LiveQueryPort.java`: `Optional<LinkedLiveSummary> findLinkedLive(Long productId)`. `LinkedLiveSummary`(`product` 패키지 소유 값 객체): `liveId, title, status, scheduledAt/startedAt, thumbnailUrl`.
- 구현체 `live/port/LiveQueryAdapter.java`(`product.port.LiveQueryPort` 구현) — 기존 `live/port/ProductQueryAdapter.java`와 대칭 위치.
- `live/repository/LiveProductRepository.java`에 신규 메서드 `findByProductIdAndRemovedAtIsNull(Long productId)` 추가(현재 live→product 방향만 있음) — `Live`까지 조인해 값 객체로 변환.

### 3. 상품→찜/팔로우 대칭 포트

- 신규 `product/port/SocialQueryPort.java`: `boolean isWishedBy(Long productId, Long memberId)`, `long countFollowers(Long sellerId)`.
- 구현체 `social/port/SocialQueryAdapter.java` — `WishRepository.existsById(new WishId(memberId, productId))`(기존 메서드 재사용, 신규 불필요), `FollowRepository.countByFollowing_Id(sellerId)`(위 1번) 사용.

### 4. 상세조회 조립

- `ProductDetailResponse`에 필드 추가: `categoryName`, `brandName`, `color`, `material`, `measurements`, `sellerDefects: List<String>`, `isWished: Boolean`(비로그인 viewer면 null), `sellerFollowerCount`, `sellerProductCount`, `linkedLive: LinkedLiveSummaryResponse | null`.
- `ProductService.getProductDetail`:
  - `categoryRepository.findById(...)`/`brandRepository.findById(...)`(상속 메서드, 신규 불필요)로 표시명 조회.
  - `SocialQueryPort`로 찜 여부·팔로워수.
  - 신규 `ProductRepository.countBySeller_IdAndSaleStatusNot(sellerId, SaleStatus.DRAFT)`로 판매상품수.
  - `LiveQueryPort`로 연결 라이브.
- AI 품질분석 필드는 이번 응답에 포함하지 않는다.
- Swagger `@Schema` 예시 갱신.

### 5. 문서 정리

- `../../../../../APIs.md` 238 행 갱신(신규 응답 필드 반영).
- `.codex/requests/be/007-product-detail-view-contract.md`: 반영된 항목(이미지·브랜드/카테고리명·찜·판매자통계·하자목록·연결라이브) 제거, AI 품질분석 항목만 남기고 "별도 Jira 이슈로 분리, AI 비동기 계약 코드 반영 후 진행 예정"이라는 사유를 적는다 — 일부만 반영이므로 파일은 삭제하지 않는다.
- 새 Jira 이슈 생성(사용자 승인 후): "AI 품질분석(PROD-009/010) BE 연동" — 에픽 211 하위, 이 브랜치에는 포함하지 않음.

## 구현 목록

- [x] `social/entity/Follow.java`, `social/repository/FollowRepository.java` 신규
- [x] `product/port/LiveQueryPort.java`, `product/port/dto/LinkedLiveSummary` 값 객체 신규
- [x] `live/port/LiveQueryAdapter.java` 신규, `live/repository/LiveProductRepository.java`에 `findByProductIdAndRemovedAtIsNull` 추가
- [x] `product/port/SocialQueryPort.java` 신규
- [x] `social/port/SocialQueryAdapter.java` 신규
- [x] `product/dto/response/ProductDetailResponse.java` 필드 확장(+ `LinkedLiveSummaryResponse`) —
      **`categoryName`/`brandName`도 추가**(원래 계획엔 있었는데 실제 구현에서 빠져 있어 검증 중 발견,
      이번에 `CategoryRepository`/`BrandRepository` 조회로 채워 넣었다)
- [x] `product/service/ProductService.java` — 포트 주입, 상세조회 조립 로직
- [x] `BE/docs/db/schema.sql`/`comments.sql`(follow 테이블) 수정 → `regen.sh` 실행
- [x] `../../../../../APIs.md` 238 행 — 이미 구현 완료 ✓ 표시돼 있었음(필드 목록 컬럼은 없음)
- [x] `docs/requests/BE/006-product-contract.md` 3.2절 반영 정리(`similarProducts`/`priceDistribution`만 남김)
- [ ] Jira에 "AI 품질분석 BE 연동" 신규 이슈 생성(에픽 211 하위) — 아직 안 함, 사용자 승인 필요
- [x] `ProductServiceTest`에 포트를 목(mock)으로 주입한 상세조회 조립 케이스 추가(`categoryName`/`brandName` 포함)
- [x] `BE:verify` 통과 확인

## 검증 중 발견/정리한 문제

- **`categoryName`/`brandName` 누락**: 위 구현 목록대로 추가해 해결.
- **`follow` 테이블 스키마 중복 정의**: `BE/docs/db/schema.sql`에 이 계획이 추가한 버전(복합 PK,
  `follower_id`+`following_id`)과, `develop-BE`에 이미 있던 버전(서로게이트 `id` PK +
  `ux_follow` UNIQUE 제약)이 **동시에** `CREATE TABLE follow`로 두 번 선언돼 있었다 — 실행하면
  "relation already exists" 에러가 난다. `Follow` 엔티티(`social/entity/Follow.java`)는 이미
  서로게이트 `id` 버전과 맞게 작성돼 있었으므로, 이 계획이 추가한 구버전(복합 PK) 선언을 삭제하고
  `develop-BE`의 기존 정의만 남겼다. `comments.sql`도 동일하게 중복 제거.
  이건 develop-BE에 FOLLOW-001이 (스키마 차원에서는) 이미 독립적으로 존재하고 있었다는 뜻이다 —
  `home/service/FollowingService`가 아직 mock이라 애플리케이션 레벨에서는 충돌하지 않았을 뿐이다.
- **`isWished` 비회원 정책**: `SocialQueryAdapter.isWishedBy`가 `memberId == null`이면 `false`를
  반환하도록 이미 구현돼 있었다 — "비회원 isWished 값 정책" 미결정 사항을 `false`로 확정.
- **`seller` 중첩 객체 대신 평탄 필드**: FE 요청 문서는 `seller: { ... }` 중첩 객체를 제안했지만,
  실제 구현은 기존 `sellerNickname`과 같은 레벨에 `sellerFollowerCount`/`sellerProductCount`를
  평탄하게 추가했다 — 기존 응답 모양과의 일관성을 우선했다. `docs/requests/BE/006-product-contract.md`에
  이 결정을 반영해뒀다.

## 확인 필요한 미결정 사항

- 없음. (AI 품질분석 제외, Follow 최소 구현, 대칭 포트 패턴은 모두 사용자 확인 완료)

## 구현 순서 의존성

`SY015`(색상/소재/실측/하자 필드) → 이 계획(SY017, 1~4번 항목 병렬 가능 후 4번에서 조립). `SY016`(목록 필터)은 독립적이라 아무 때나 진행 가능.
