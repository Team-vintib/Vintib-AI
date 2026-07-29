# 구현 상태

확인일: 2026-07-27

| 영역            | 상태   | 비고                                                                                                                                   |
| --------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| 프로젝트 초기화 | 완료   | Vue/Vite/TS 구성 존재                                                                                                                  |
| src 도메인 구조 | 완료   | 기능 ID prefix 기준 `domains/*`, 공통 `shared/*`, 앱 조립 `app/*` 생성                                                                 |
| Tailwind CSS    | 완료   | Vite 플러그인 연결, `src/assets/tailwind.css` import                                                                                   |
| 디자인 토큰     | 완료   | `src/assets/main.scss`에 색상/간격/radius/버튼 높이/오류 변수 선언                                                                     |
| 라우터          | 부분   | 인증·ONBOARD-001~004·BIZ-001·BIZ-001-2·HOME·FOLLOWING_HOME placeholder·공개 LIVE 목록·공개 PROD-008 route 등록, 인증 guard 구현                               |
| Pinia           | 부분   | 앱 등록 완료, AUTH-002 인증 store와 BIZ-001 더미 제출 화면 간 상태 구현                                                               |
| Axios           | 부분   | `shared/api/http.ts` 공통 인스턴스, ApiResponse envelope 정규화, 인증 토큰 interceptor, AUTH-001·002·ONBOARD-001~004 FE 선행 계약 연동 |
| 스타일          | 부분   | Tailwind와 전역 SCSS 기반 완료, 온보딩 UI 컴포넌트 및 회원가입·로그인·SSO 화면 스타일 구현                                             |
| 레이아웃        | 부분   | 공통 슬롯 레이아웃, 인증 레이아웃, 온보딩 단계 레이아웃 구현. `DefaultLayout`은 화면별 콘텐츠 최대 폭 지정 지원                       |
| 인증 화면       | 부분   | AUTH-001 이메일 회원가입, 가입 방식 선택, AUTH-002 이메일 로그인, AUTH-003 SSAFY 로그인·가입 진입, SSO callback·계정 연결 안내 FE 완료, BE 메일/로그인/SSO 환경에서 E2E 재검증 필요 |
| 온보딩 화면     | 부분   | ONBOARD-001~004 FE 구현 완료, ONBOARD-003 사진 선택·촬영·미리보기·삭제 완료, ONBOARD-003·004 저장은 BE API 대기                        |
| 사업자 인증 화면 | 부분   | BIZ-001 필수값·숫자 10자리·이미지 MIME 검증, 제출 활성화·중복 방지와 BIZ-001-2 더미 인증 대기 및 HOME 이동 연결 완료, BE API 대기                    |
| 홈 화면         | 부분   | HOME 공개 route, 로그인별 Guest/Member 홈 분기, 검색 패널·섹션·라이브 카드·상품 카드·empty·loading/error/retry 상태와 mock adapter 구현, 실제 HOME API 대기 |
| 상품 목록 화면   | 부분   | PROD-008 공개 route, 실사형 로컬 이미지·최소/최대 가격 검증과 mock 목록 필터링·빈 상태·상품 카드→상세 route 이동 완료, 실제 조회·찜 API 대기 |
| 상품 상세 화면   | 부분   | S15P11A108-408 정적 UI, 410 상호작용, 412 로딩·오류·상품 없음·판매 완료 및 AI 분석 전·중·완료·결과 없음·실패 상태 구현, 실제 API 대기 |
| 라이브 목록 화면 | 부분   | S15P11A108-413 카드형 mock 목록, 진행 중·예정·종료 배지, 판매자·시청자 수와 시청 route 이동 구현. 필터·상태·실제 목록 API는 415·418 대기 |
| 공통 컴포넌트   | 부분   | 온보딩 도메인에 BaseButton, BaseInput, BaseField, 단계 표시 구현                                                                       |
| API 타입        | 부분   | 공통 응답/에러/pagination, 인증 회원가입·로그인 요청/응답 타입, 온보딩 필드 오류·회원 유형 타입 구현                                   |
| Mock 데이터     | 부분   | 홈·상품 목록·상품 상세 화면 확인용 mock 데이터 구현, 상품 목록은 로컬 WebP와 가격 필터 사용, 홈·상품 상세는 mock adapter를 통해 주입하며 실제 API 전환 시 adapter 내부 교체 필요 |
| 테스트/검증     | 부분   | lint, type-check, build, AUTH-001·002·003·ONBOARD-001~004 검증 완료, 상품 목록→상세와 상세 408·410·412 상태별 브라우저 검증 완료, HOME·BIZ-001·BIZ-001-2 수동 검증 대기                           |

## 2026-07-28 검색 화면 상태

| 영역 | 상태 | 비고 |
| --- | --- | --- |
| 검색 결과 화면 | 부분 | SEARCH-001/002 `/search` 공개 route, 전체/상품/라이브/회원 탭, query 기반 탭 전환, 전체 탭 preview·전체보기, 개별 탭 페이지네이션, 상품/라이브/회원 mock 결과 카드, 카테고리·상태·가격·판매 유형 필터, 상품 결과 정렬, 검색어 기반 mock 필터링 구현. 실제 통합 검색 API 대기 |
| 검색 상태 화면 | 부분 | 초기 검색어 없음, loading, error, 검색 결과 없음, 필터 결과 없음, 가격 범위 오류 상태 구현. loading/error/empty는 `status` query로 mock 확인 가능 |
| 검색 액션 | 부분 | 상품 카드는 상세 route 이동, 라이브 카드는 시청 route 이동, 찜/팔로우는 로그인 필요 시 login redirect 처리. 실제 찜/팔로우 API와 회원 프로필 route 대기 |
| 스타일 토큰 | 부분 | 상품 목록/검색 필터가 공유하는 필터 패널 폭, 본문/캡션/버튼 글자 크기, font-weight, line-height CSS 변수 추가 |
