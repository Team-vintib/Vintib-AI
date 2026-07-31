# 홈/팔로잉 콘텐츠 조회 API (스켈레톤 + Mock)

- Jira: [S15P11A108-279](https://ssafy.atlassian.net/browse/S15P11A108-279) `[HOME-001|BE] 홈 콘텐츠 조회`, [S15P11A108-289](https://ssafy.atlassian.net/browse/S15P11A108-289) `[HOME-002|BE] 팔로잉 콘텐츠 조회`
- 로드맵: Phase 3 (3-1, 3-2)

## 배경/목표

홈 화면(HOME-001)과 팔로잉 탭(HOME-002)의 조회 API를 만든다. 두 API 모두 실데이터는 서윤 담당 도메인(상품·라이브·팔로우)에 의존하는데 이번 주엔 해당 테이블이 없다.
→ **이번 주 범위는 응답 스펙 확정 + 컨트롤러/서비스 스켈레톤 + Mock 응답 + Swagger 문서화까지.** FE가 Mock 기준으로 홈/팔로잉 화면 개발에 착수할 수 있게 하는 것이 완료 조건이다. 실데이터 조인(Repository/쿼리)은 2주차에 서윤 도메인 완성 후 연결한다.

## 작업 내용

새 `home` 도메인 패키지(`com.ssafy.backend.home.{controller,service,dto}`)를 신설한다. 이번 주엔 자체 `entity`/`repository` 없음(Mock). 두 API 모두 서비스는 하드코딩 Mock을 반환하되 **2주차 실데이터 교체가 국소적이도록** 응답 조립을 서비스 메서드 하나로 격리한다. 모든 응답은 기존 `ApiResponse<T>` 래퍼로 감싸고, Swagger는 `.claude/skills/swagger` 컨벤션(`@Tag`/`@Operation`/`@ApiResponses` + DTO `@Schema`)을 따르며 Mock 응답임을 `@Operation.description`에 명시한다.

**브랜치 완전 분리 결정에 따른 파일 소유권 분할** — 두 브랜치가 같은 파일을 *생성*하지 않도록 나눠 병합 충돌을 없앤다. 공유 카드 DTO(`LiveCardResponse`/`ProductCardResponse`)만 유일한 결합점이므로 **HOME-001이 소유**하고, HOME-002는 이를 새로 만들지 않는다(§확인 1 참조).

### HOME-001 (279)
- `home` 패키지 스캐폴딩 + 공유 카드 DTO 소유
- `GET /api/home` — **비회원 시청 가능 → public.** 섹션 구조 응답: `진행 중 라이브 / 예약 라이브 / 상시 판매 상품 / 경매 예정 상품`. 각 카드에 **판매 상태·방송 상태를 구분하는 필드** 포함(기능정의서 HOME-001 정책). 경매 예정 상품은 가격 대신 '경매 예정' 표시 필드.
- `SecurityConfig`의 `PUBLIC_ENDPOINTS`에 정확 경로 `/api/home` 추가.

### HOME-002 (289)
- `GET /api/home/following` — **로그인 회원만 → authenticated.** `Authentication`에서 `memberId`를 꺼내 사용. 응답은 팔로우 회원의 상품·라이브 목록 + 빈 결과 안내 플래그(`empty`). 팔로우 없음/결과 없음이면 빈 배열 + 플래그만. 추천 회원 제공은 이번 주 제외(여력 시 2주차).
- **별도 `FollowingController`로 분리**(HOME-001의 `HomeController`를 건드리지 않음 → 컨트롤러 충돌 없음). `/api/home/following`은 `/api/home` 정확 일치가 아니라 기본 인증 필요로 남으므로 **`SecurityConfig` 수정 불필요**(설정 충돌 없음).

## 구현 목록

### HOME-001 (279)
- [x] `home` 도메인 패키지 스캐폴딩 (entity/repository 제외)
- [x] 공유 카드 DTO: `LiveCardResponse`, `ProductCardResponse` (`@Schema`) — **HOME-001 소유**
- [x] `HomeContentResponse` (섹션별 목록) DTO
- [x] `HomeService.getHomeContent()` — Mock 반환, 실데이터 교체 지점 주석(TODO 2주차)
- [x] `HomeController` — `GET /api/home` (Swagger 어노테이션 포함)
- [x] `SecurityConfig`의 `PUBLIC_ENDPOINTS`에 `/api/home` 추가(정확 경로)
- [x] 컨트롤러 테스트(`@SpringBootTest` + `webAppContextSetup`, 프로젝트 관행) — 200/섹션 필드/경매예정 플래그/비회원 접근 4건
- [x] `BE/README.md` 디렉터리 구조 + 공개 엔드포인트 갱신
- [x] API 스펙 문서 반영 (FE 참고용) — Swagger 자동 생성 + `BE/docs/api/swagger-guide.md`(-294)로 대체
- [x] BE 검증 하네스 통과 확인 — `BUILD SUCCESSFUL`, 신규 4건 포함 전체 green

### HOME-002 (289) — HOME-001 머지 후 착수(공유 카드 DTO 재사용) ✅ develop-BE 머지 확인 후 분기
- [x] `FollowingContentResponse` (라이브/상품 목록 + `empty`) DTO
- [x] `FollowingService.getFollowingContent(Long memberId)` — Mock 반환, 실데이터 교체 지점 TODO
- [x] `FollowingController` — `GET /api/home/following` (별도 컨트롤러, Swagger 어노테이션 포함). HomeController·SecurityConfig 미수정 → 파일 충돌 없음
- [x] 컨트롤러 테스트(`@SpringBootTest`) — 미인증 401 / 인증 시 200·`empty` 플래그 (JwtTokenProvider로 실제 토큰 발급)
- [x] API 스펙 문서 반영 (FE 참고용) — Swagger 자동 생성 + `BE/docs/api/swagger-guide.md`(-294)로 대체
- [x] BE 검증 하네스 통과 — `BUILD SUCCESSFUL`, 신규 2건 포함 전체 25건 green

## 확인이 필요한 미결정 사항

1. **브랜치 전략 (확정: 완전 분리 + 순차)** — 두 티켓을 독립 브랜치로 진행하되 순서를 둔다: **HOME-001 → develop-BE 머지 → develop-BE에서 HOME-002 분기.** 유일한 결합점인 공유 카드 DTO는 HOME-001이 소유하고, 컨트롤러 분리 + `SecurityConfig` 무수정으로 파일 생성 충돌을 없앴다. Jira에서 289는 279에 "blocked by"로 연결한다.
2. **응답 DTO 필드 상세** — 이번엔 초안 필드로 Mock을 내리고, -53(초기 API 명세) 확정 및 FE 합의 시 조정한다는 전제. 지금 필드까지 못박을지, 명세 확정까지 열어둘지.
3. **페이지네이션** — 홈 섹션별 개수 제한/무한스크롤 여부. 이번 주 Mock은 고정 개수로 두고 명세 확정 시 반영 예정. FE가 초기부터 페이징을 원하면 응답에 커서/페이지 필드를 미리 넣을지.
4. **추천 회원(HOME-002 빈 결과 시)** — 이번 주 제외(빈 배열 + `empty` 플래그만). 동의 여부.
