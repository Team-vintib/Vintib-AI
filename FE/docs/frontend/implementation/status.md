# 구현 상태

확인일: 2026-07-27

| 영역            | 상태   | 비고                                                                                                                                   |
| --------------- | ------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| 프로젝트 초기화 | 완료   | Vue/Vite/TS 구성 존재                                                                                                                  |
| src 도메인 구조 | 완료   | 기능 ID prefix 기준 `domains/*`, 공통 `shared/*`, 앱 조립 `app/*` 생성                                                                 |
| Tailwind CSS    | 완료   | Vite 플러그인 연결, `src/assets/tailwind.css` import                                                                                   |
| 디자인 토큰     | 완료   | `src/assets/main.scss`에 색상/간격/radius/버튼 높이/오류 변수 선언                                                                     |
| 라우터          | 부분   | 인증·ONBOARD-001~004·BIZ-001·BIZ-001-2·HOME·FOLLOWING_HOME placeholder·LIVE placeholder·공개 PROD-008 route 등록, 인증 guard 구현                               |
| Pinia           | 부분   | 앱 등록 완료, AUTH-002 인증 store와 BIZ-001 더미 제출 화면 간 상태 구현                                                               |
| Axios           | 부분   | `shared/api/http.ts` 공통 인스턴스, ApiResponse envelope 정규화, 인증 토큰 interceptor, AUTH-001·002·ONBOARD-001~004 FE 선행 계약 연동 |
| 스타일          | 부분   | Tailwind와 전역 SCSS 기반 완료, 온보딩 UI 컴포넌트 및 회원가입·로그인·SSO 화면 스타일 구현                                             |
| 레이아웃        | 부분   | 공통 슬롯 레이아웃, 인증 레이아웃, 온보딩 단계 레이아웃 구현. `DefaultLayout`은 화면별 콘텐츠 최대 폭 지정 지원                       |
| 인증 화면       | 부분   | AUTH-001 이메일 회원가입, 가입 방식 선택, AUTH-002 이메일 로그인, AUTH-003 SSAFY 로그인·가입 진입, SSO callback·계정 연결 안내 FE 완료, BE 메일/로그인/SSO 환경에서 E2E 재검증 필요 |
| 온보딩 화면     | 부분   | ONBOARD-001~004 FE 구현 완료, ONBOARD-003 사진 선택·촬영·미리보기·삭제 완료, ONBOARD-003·004 저장은 BE API 대기                        |
| 사업자 인증 화면 | 부분   | BIZ-001 필수값·숫자 10자리·이미지 MIME 검증, 제출 활성화·중복 방지와 BIZ-001-2 더미 인증 대기 및 HOME 이동 연결 완료, BE API 대기                    |
| 홈 화면         | 부분   | HOME 공개 route, 로그인별 Guest/Member 홈 분기, 검색 패널·섹션·라이브 카드·상품 카드·empty·loading/error/retry 상태와 mock adapter 구현, 실제 HOME API 대기 |
| 상품 목록 화면   | 부분   | PROD-008 공개 route, 검색·필터·판매 방식 탭·정렬·mock 카드·페이지네이션 껍데기 완료, 실제 조회·찜·상세 이동 API 대기             |
| 상품 상세 화면   | 부분   | S15P11A108-408 상품 이미지·구매 요약·판매자·연결 라이브·상세 정보와 AI 감정 원본/검수 이미지 비교 정적 UI 구현, 410 상호작용·412 상태 화면 대기 |
| 공통 컴포넌트   | 부분   | 온보딩 도메인에 BaseButton, BaseInput, BaseField, 단계 표시 구현                                                                       |
| API 타입        | 부분   | 공통 응답/에러/pagination, 인증 회원가입·로그인 요청/응답 타입, 온보딩 필드 오류·회원 유형 타입 구현                                   |
| Mock 데이터     | 부분   | 홈·상품 목록·상품 상세 화면 확인용 mock 데이터 구현, 홈·상품 상세는 mock adapter를 통해 주입하며 실제 API 전환 시 adapter 내부 교체 필요    |
| 테스트/검증     | 부분   | lint, type-check, build, AUTH-001·002·003·ONBOARD-001~004 검증 완료, HOME·BIZ-001·BIZ-001-2 수동 검증 대기                           |
