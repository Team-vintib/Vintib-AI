# 공통 컴포넌트 후보

출처: `docs/notion/화면 기반 개발 요구 문서.md`, `docs/notion/프론트엔드 디자인 구현 규칙.md`

| 컴포넌트 | 우선순위 | 사용 화면 | 주요 상태 |
| --- | --- | --- | --- |
| BaseButton | 1 | 전체 | default, hover, pressed, focus, disabled, loading |
| BaseInput | 1 | AUTH, ONBOARD, BIZ, POINT | default, focus, error, disabled |
| BaseCheckbox | 1 | AUTH 약관, ONBOARD 선택 | checked, disabled, error |
| BaseField | 1 | 폼 화면 | label, help, error |
| AuthLayout | 1 | AUTH-* | guestOnly 화면 레이아웃 |
| StepIndicator | 2 | ONBOARD, PROD, LIVE | current, complete, pending |
| StatusBadge | 2 | 상품, 주문, 배송, 사업자, 라이브 | status enum |
| Toast | 2 | 전체 | success, error, info |
| ConfirmModal | 2 | 구매, 비공개, 환불, 송장 등록 | open, loading |
| EmptyState | 2 | 목록 화면 | action 있음/없음 |
| ProductCard | 3 | HOME, SEARCH, MY | 판매중, 판매완료, 경매, 찜 |
| LiveCard | 3 | HOME, SEARCH, MY | 예정, 진행중, 종료 |
| ImageUploader | 3 | PROD, BIZ, ONBOARD, TRYON, REFUND | uploading, failed, complete |
| AuctionPanel | 4 | LIVE, AUCT | 진행중, 종료, 포인트 부족, 재접속 |

## 인증 화면 우선 컴포넌트

첫 구현 묶음에서는 `BaseButton`, `BaseInput`, `BaseCheckbox`, `BaseField`, `AuthLayout`부터 만들면 중복을 줄일 수 있습니다.
