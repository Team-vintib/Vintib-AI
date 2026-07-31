# 구현 상태

확인일: 2026-07-30

| 영역            | 상태   | 비고                                                                                                                                   |
| --------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| 프로젝트 초기화 | 완료   | Vue/Vite/TS 구성 존재                                                                                                                  |
| src 도메인 구조 | 완료   | 기능 ID prefix 기준 `domains/*`, 공통 `shared/*`, 앱 조립 `app/*` 생성                                                                 |
| Tailwind CSS    | 완료   | Vite 플러그인 연결, `src/assets/tailwind.css` import                                                                                   |
| 디자인 토큰     | 완료   | `src/assets/main.scss`에 색상/간격/radius/버튼 높이/오류 변수 선언                                                                     |
| 라우터          | 부분   | 인증·ONBOARD-001~004·BIZ-001·BIZ-001-2·HOME·FOLLOWING_HOME placeholder·LIVE_LIST·LIVE_CREATE·LIVE_WATCH 실제 화면·공개 PROD-008 route 등록, 인증 guard 구현 |
| Pinia           | 부분   | 앱 등록 완료, AUTH-002 인증 store와 BIZ-001 더미 제출 화면 간 상태 구현                                                               |
| Axios           | 부분   | `shared/api/http.ts` 공통 인스턴스, ApiResponse envelope 정규화, 인증 토큰 interceptor, AUTH-001·002·ONBOARD-001~004 FE 선행 계약 연동 |
| 스타일          | 부분   | Tailwind와 전역 SCSS 기반 완료, 온보딩 UI 컴포넌트 및 회원가입·로그인·SSO 화면 스타일 구현                                             |
| 레이아웃        | 부분   | 공통 슬롯 레이아웃, 인증 레이아웃, 온보딩 단계 레이아웃 구현. `DefaultLayout`은 화면별 콘텐츠 최대 폭 지정 지원                       |
| 인증 화면       | 부분   | AUTH-001 이메일 회원가입, 가입 방식 선택, AUTH-002 이메일 로그인, AUTH-003 SSAFY 로그인·가입 진입, SSO callback·계정 연결 안내 FE 완료, BE 메일/로그인/SSO 환경에서 E2E 재검증 필요 |
| 온보딩 화면     | 부분   | ONBOARD-001~004 FE 구현 완료, ONBOARD-003 사진 선택·촬영·미리보기·삭제 완료, ONBOARD-003·004 저장은 BE API 대기                        |
| 사업자 인증 화면 | 부분   | BIZ-001 필수값·숫자 10자리·이미지 MIME 검증, 제출 활성화·중복 방지와 BIZ-001-2 더미 인증 대기 및 HOME 이동 연결 완료, BE API 대기                    |
| 홈 화면         | 부분   | HOME 공개 route, 로그인별 Guest/Member 홈 분기, 공통 검색바 기반 검색 패널·섹션·라이브 카드·상품 카드·empty·loading/error/retry 상태 구현, `/api/home`·로그인 시 `/api/home/following` 부분 연동. BE 미제공 필드와 콘텐츠 카드는 FE 보조값 유지 |
| 상품 목록 화면   | 부분   | PROD-008 공개 route, 홈과 같은 공통 검색바의 통합 검색 상품 탭 이동, 실사형 로컬 이미지·최소/최대 가격 검증과 mock 목록 필터링·빈 상태·상품 카드→상세 route 이동 완료, 실제 조회·찜 API 대기 |
| 상품 상세 화면   | 부분   | S15P11A108-408 정적 UI, 410 상호작용, 412 로딩·오류·상품 없음·판매 완료 및 AI 분석 전·중·완료·결과 없음·실패 상태 화면과 유사 상품 가격대 분포·상품 상세 이동 구현. BE 상품 상세에 `images`는 추가 확인됐고, 찜 API 실제 경로도 확인됨. 판매자 상세·연결 라이브·AI 품질 분석·추천 API는 추가 계약 대기 |
| 상품 등록 화면   | 부분   | S15P11A108-409·411·414 `/products/new` route, 사진 등록·기본 정보·사이즈/소재·상태/하자와 AI 품질 검증·가격·검토·완료 7단계 UI 구현. 필수값·이미지·가격·등록 실패 상태와 mock 등록 adapter 구현 완료. BE presigned 이미지 업로드 3단계 계약은 FE 문서에 반영됐고, 실제 상품 등록·이미지 역할·AI 품질 검증·가격 추천·경매 등록 API 연결 대기 |
| 라이브 목록 화면 | 부분   | S15P11A108-413·415·418 카드·필터·정렬과 상태 화면, 홈과 같은 공통 검색바의 통합 검색 라이브 탭 이동 구현. `origin/develop-BE@dd6a0b6`에 `GET /api/lives`가 구현됐으며, 최종 009 계약의 복수 `categories[]`·공통 `PageResponse.content`·nullable `viewerCount`·`VIEWERS_DESC` 미지원 정책을 418 adapter에 반영하기 전까지 기본값은 mock |
| 라이브 개설 화면 | 부분   | LIVE-001/002 `/lives/new` route, 라이브 유형·방송 정보·판매 상품·예약 일정·장비 확인·완료 단계 UI, 필수값/과거 일정 검증, 상품 mock 검색/선택, `getUserMedia` 기반 카메라 미리보기와 마이크 순차 확인 구현. 실제 라이브 생성/예약 API와 방송 SDK 연동 대기 |
| 라이브 시청 화면 | 부분   | 419 방송 헤더·상품 큐·영상 stage·선택 상품·상태 화면, 423 채팅·반응·경매 패널, 425 사진 중심 AI 시착 패널과 등록 전·생성·결과·실패 mock 상태 구현. 실제 스트리밍·채팅 STOMP·경매·AI API 연동 대기 |
| 알림 화면        | 부분   | S15P11A108-420·421 `/notifications` 읽지 않은 알림 목록·탭 필터·전체 탭 더보기·단건/전체 읽음 처리와 공통 헤더 알림 팝업·unread badge 구현. 알림 mock data/query는 제거했고 실제 `/api/users/{userId}/alerts?unreadOnly=true`로 조회하며 읽음 처리된 알림은 목록에서 제거. 서버 카테고리 필터, 알림 `type/refType` enum 문서화, 일부 상세 route 매핑은 대기 |
| 공통 컴포넌트   | 부분   | 온보딩 도메인에 BaseButton, BaseInput, BaseField, 단계 표시 구현. shared에는 GlobalNavigation, RoutePlaceholder, 홈·상품·라이브가 재사용하는 AppSearchBar 구현 |
| API 타입        | 부분   | 공통 응답/에러/pagination, 인증 회원가입·로그인 요청/응답 타입, 온보딩 필드 오류·회원 유형 타입 구현                                   |
| Mock 데이터     | 부분   | 홈·상품 목록·상품 상세·유사 상품 가격 분포·상품 등록·라이브 채팅·경매·AI 시착 패널 확인용 mock 데이터 구현, 상품 목록은 로컬 WebP와 가격 필터 사용, 홈은 BE 미제공 회원 홈 보조 섹션·콘텐츠 카드·fallback 데이터에 mock 일부 유지. 알림 도메인 mock 데이터는 제거하고 실제 DB/API 확인으로 전환 |
| 테스트/검증     | 부분   | lint, type-check, build, AUTH-001·002·003·ONBOARD-001~004 검증 완료, 상품 목록→상세와 상세 408·410·412 상태 및 유사 상품 가격대 선택·이동 검증 완료, 상품 등록 409·411·414 type-check/build 완료, LIVE-001/002 type-check 완료, LIVE-005 목록→시청 이동·상품 선택·상태별 브라우저 검증 완료, HOME·BIZ-001·BIZ-001-2 일부 브라우저 수동 검증 대기 |

## 2026-07-28 검색 화면 상태

| 영역 | 상태 | 비고 |
| --- | --- | --- |
| 검색 결과 화면 | 부분 | SEARCH-001/002 `/search` 공개 route, 전체/상품/라이브/회원 탭, query 기반 탭 전환, 전체 탭 preview·전체보기, 개별 탭 페이지네이션, 상품/라이브/회원 mock 결과 카드, 카테고리·상태·가격·판매 유형 필터, 상품 결과 정렬, 검색어 기반 mock 필터링 구현. 실제 통합 검색 API 대기 |
| 검색 상태 화면 | 부분 | 초기 검색어 없음, loading, error, 검색 결과 없음, 필터 결과 없음, 가격 범위 오류 상태 구현. loading/error/empty는 `status` query로 mock 확인 가능 |
| 검색 액션 | 부분 | 상품 카드는 상세 route 이동, 라이브 카드는 시청 route 이동, 찜/팔로우는 로그인 필요 시 login redirect 처리. 실제 찜/팔로우 API와 회원 프로필 route 대기 |
| 스타일 토큰 | 부분 | 상품 목록/검색 필터가 공유하는 필터 패널 폭, 본문/캡션/버튼 글자 크기, font-weight, line-height CSS 변수 추가 |

## 2026-07-30 초기 진입 스플래시 상태

| 영역 | 상태 | 비고 |
| --- | --- | --- |
| 앱 초기 스플래시 | 완료 | 새 탭 최초 진입 시 `vintib_moving_logo.gif`를 1회 재생한 뒤 요청된 라우트 화면으로 전환. 같은 탭 내 이동에서는 재생하지 않도록 `sessionStorage` 기준 적용. |

## 2026-07-30 FE 요청 문서 반영

| 영역 | 상태 | 비고 |
| --- | --- | --- |
| 상품 이미지 업로드 계약 | 문서 반영 | `.claude/requests/fe/001-product-image-presigned-upload.md` 기준으로 `POST /api/products/{productId}/images/upload-url` → S3 `PUT` → `POST /api/products/{productId}/images` 3단계 흐름, 이미지 수정/삭제, 오류 코드 `P004`~`P007`을 API 문서에 반영 |
| 상품 찜 계약 | 문서 반영 | `.claude/requests/fe/002-wish-api-contract.md` 기준으로 실제 경로 `/api/users/{userId}/wishes`와 0-base 목록 pagination, 오류 코드 `P001`, `S001`~`S003`을 API 문서에 반영 |
| 인증 계약 | 문서 반영 | `.codex/requests/be/001-auth-contract.md` 기준으로 FE API 문서의 로그인 endpoint를 `/api/auth/signin`, 토큰 재발급을 `/api/auth/reissue`로 정정하고 현재 BE 응답/추가 필요 사항을 분리 |
