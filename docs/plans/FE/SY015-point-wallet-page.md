# SY015 - 포인트 지갑 화면

## 배경/목표

`/points` route는 존재하지만 현재 `RoutePlaceholder`에 연결되어 있고, `VITE_POINT_API_ENABLED=false`로 포인트 API 연동도 꺼져 있다. POINT-001~004 범위의 포인트 충전, 잔액/내역 조회, 출금 계좌/출금 신청 UI를 만들고 BE 계약이 준비되면 API로 전환 가능한 구조를 만든다.

## 작업 내용

FE는 `domains/point` 도메인을 신설하고 `/points`를 실제 페이지로 연결한다. BE 포인트 API가 아직 구현되지 않은 상태이므로 `VITE_POINT_API_ENABLED` 플래그를 기준으로 mock fallback을 유지하되, API 함수와 타입은 문서 후보 계약(`/api/points`, `/api/points/transactions`, `/api/points/withdrawals`) 및 `APIs.md`의 `/users/{id}/points` 계열을 비교해 `BE 확인 필요` 항목을 명확히 남긴다.

화면은 포인트 업무를 한 화면에서 처리하는 지갑형 관리 페이지로 구성한다.

- 상단 요약: 사용 가능 포인트, 입찰 보류, 거래 보관, 출금 가능, 최근 변동
- 충전 영역: 금액 직접 입력, 빠른 금액 버튼, 최소 금액 검증, 처리 중/성공/실패 상태
- 내역 영역: 전체/충전/사용/보류/해제/정산/환불/출금 필터, 페이지네이션 또는 더보기
- 출금 영역: 계좌 정보 표시/입력, 출금 금액 검증, 최소 출금 금액 안내, 신청 상태
- 빈/로딩/오류 상태: API 실패, 내역 없음, 계좌 없음, 포인트 부족

## 2026-08-01 UI 개선 반영

- [x] `/points` 진입 시 사용 가능 포인트를 가장 크게 노출한다.
- [x] 사용 가능 포인트 아래에 보유, 출금 가능, 정산 예정, 출금 처리 중 카드 4개를 배치한다.
- [x] 요약 아래에 내역, 충전, 출금 3개 버튼을 두고 선택한 기능만 표시한다.
- [x] 메인 내역은 최근 10개만 표시하고, 전체 내역 버튼으로 `/points/history`에 진입한다.
- [x] 전체 내역 페이지에서 전체, 출금, 입금 필터와 시작일/종료일 기간 필터를 제공한다.
- [x] 충전 화면은 충전 금액 선택, 결제 수단, 충전 금액 및 충전 후 잔액 순서로 구성한다.
- [x] 출금 화면은 출금 계좌 확인, 출금 가격 입력 및 출금 신청 순서로 구성한다.

## 구현 목록

- [x] `FE/src/domains/point/` 하위에 `pages`, `components`, `api`, `types`, `constants` 구조를 만든다.
- [x] `PointWalletPage.vue`를 만들고 `/points` route의 `RoutePlaceholder`를 실제 페이지로 교체한다.
- [x] 포인트 요약, 충전 패널, 거래 내역 목록, 출금 패널을 도메인 컴포넌트로 분리한다.
- [x] `point.types.ts`에 잔액, 거래 로그, 출금 내역, 계좌 정보, 충전/출금 요청 타입을 정의한다.
- [x] `pointApi.ts`에 조회/충전/출금 API 함수를 만들고 `VITE_POINT_API_ENABLED`가 `false`일 때 mock 데이터를 반환한다.
- [x] 인증 사용자 ID는 기존 `authStore` 세션에서 가져오고, 없으면 로그인 유도 상태를 보여준다.
- [x] 금액 입력 검증을 적용한다: 충전 최소 1,000P, 출금 최소 10,000P는 문서 기준 기본값으로 두되 `BE 확인 필요`로 표시한다.
- [x] API 오류는 `normalizeApiError`를 사용하고, `POINT_INSUFFICIENT` 또는 잔액 부족 계열 코드를 화면 메시지로 매핑한다.
- [x] `.env.example`에 `VITE_POINT_API_ENABLED=false`를 추가해 로컬 기본값을 명확히 한다.
- [x] `FE/docs/frontend/screens/screen-inventory.md`의 포인트 상태를 구현 범위에 맞게 갱신한다.
- [x] `FE/docs/frontend/implementation/current-structure.md`와 상태 문서가 있으면 `domains/point` 추가 사항을 반영한다.
- [x] `npm run type-check`로 타입 검증을 수행한다.

## API 계약 후보

현재 문서가 두 계열로 갈라져 있어 BE 확인이 필요하다.

- `FE/docs/frontend/api/api-index.md`: `/api/points`, `/api/points/transactions`, `/api/points/withdrawals`
- `APIs.md`: `/users/{id}/points`, `/users/{id}/points/logs`, `/users/{id}/points/charges`, `/users/{id}/withdrawals`

FE 구현에서는 `http`의 baseURL이 이미 `/api`를 포함하므로 코드 호출 경로는 BE 최종 계약에 맞춰 `/points` 또는 `/users/{id}/points` 중 하나로만 확정한다. 최종 계약 전에는 mock fallback을 기본으로 유지한다.

## BE 확인 필요

- 포인트 도메인 실제 구현 여부와 담당 일정
- 최종 endpoint 경로: `/points` 계열인지 `/users/{id}/points` 계열인지
- 응답 envelope와 필드명: available/held/escrow/withdrawable 포인트 구분 방식
- 거래 로그 enum: 충전, 사용, 입찰 보류, 보류 해제, 낙찰 차감, 정산, 환불, 출금
- 충전 API 실제 결제 방식: 외부 PG 연동 여부, MVP mock 충전 허용 여부
- 출금 계좌 등록/수정 endpoint 존재 여부
- 출금 최소 금액, 수수료, 처리 상태 enum

## 제외 범위

- 실제 PG 결제창 연동
- 구매/주문 생성과 연결되는 실 포인트 차감
- 경매 입찰의 포인트 보류/해제 트랜잭션
- 판매자 정산 자동화
- 운영자 출금 승인 화면

위 항목은 BE 거래/경매 도메인과 함께 별도 계획으로 진행한다.
