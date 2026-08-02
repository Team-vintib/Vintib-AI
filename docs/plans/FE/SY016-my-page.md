# SY016 - 마이페이지

## 배경/목표

`/my` route는 현재 placeholder이고, 기능 정의서의 `MY-001~009`는 필수 범위다. 마이페이지를 프로필·거래·판매·소셜·사업자·포인트 관리 허브로 만들고, 이미 구현된 `/points` 화면과 아직 BE 계약이 부족한 주문/배송/환불/정산 영역을 구분해 단계적으로 연결한다.

## 현재 상태 분석

- FE
  - `/my`는 `RoutePlaceholder`에 연결되어 있다.
  - `domains/my` 폴더는 구조만 있고 실제 페이지, 타입, API adapter가 없다.
  - 공통 헤더 프로필 드롭다운은 `/my`, `/my?section=orders`, `/my?section=sales`, `/my?section=wishlist`, `/points`로 이동하도록 이미 연결되어 있다.
  - `/points`, `/points/history`는 `domains/point` 실제 화면으로 구현되어 있고 `VITE_POINT_API_ENABLED=false` 기본값에서 mock fallback을 사용한다.
  - `MY-002~006`에서 재사용할 상품/라이브 카드 UI는 홈·검색·상품·라이브 도메인에 이미 존재하지만, 마이페이지 전용 액션과 상태 배지는 별도 조정이 필요하다.
- BE
  - 구현 확인됨: `PATCH /api/users/{id}` 기본 정보 등록·수정, `GET/PUT /api/users/{id}/interests`, `PATCH /api/users/{id}/member-type`, `GET/POST/DELETE /api/users/{userId}/wishes`, 알림 API.
  - 미구현 또는 계약 대기: `GET /api/me`, `PATCH /api/me`, `GET /api/users/{userId}/mypage`, 공개 프로필, 팔로우 목록, 사업자 정보 조회/수정, 주문/배송/환불, 포인트/출금, 마이페이지용 판매 상품/라이브 필터.
  - `docs/requests/BE/011-user-mypage-contract.md`가 내 정보·공개 프로필·마이페이지 요약 계약을 추적 중이다.
  - `docs/requests/BE/010-commerce-wallet-contract.md`가 주문·배송·환불·포인트/출금 계약을 추적 중이다.

## 화면 구성

마이페이지 첫 구현은 `/my` 단일 페이지 안에서 `section` query로 탭/패널을 전환한다. 별도 상세 화면은 API와 라우트가 확정된 뒤 분리한다.

- 메인 요약
  - 사용자 카드: 프로필 이미지 fallback, 이름/닉네임, 이메일, 회원 유형, 사업자 인증 상태
  - 카운터: 구매/낙찰, 판매, 찜, 팔로워, 알림
  - 개인 홈 요약: 구매/낙찰, 찜, 팔로워, 사용 가능 포인트
- `seller`
  - 판매 대시보드: 판매 완료 건수, 누적 판매/순수익, 평균 판매가, 정산 완료, 월별 수익 추이
  - 운영 대기: 배송 대기, 환불 요청, 예약 라이브
  - 상품 상태 분포: 판매중, 경매 예정, 판매 완료
  - 포인트 요약: 사용 가능 포인트와 `/points` 이동 CTA
  - 빠른 메뉴: 상품 등록, 라이브 시작, 알림센터, 사업자 인증/관리
- `profile` 또는 기본 섹션
  - MY-001 회원 정보: 이름/이메일 읽기 전용, 닉네임/전화번호/주소/성별 수정
  - 관심 브랜드·카테고리 조회/수정 진입
  - AI 시착 신체 정보는 현 BE 계약이 별도이므로 이번 범위에서는 표시/진입만 두고 저장 연동은 후속으로 둔다.
- `products`
  - MY-002 판매 상품 관리: 상태 탭(전체, 판매중, 판매 완료), 상품 카드, 상품 등록/수정/상세 진입
  - 실제 목록 API가 없으면 명시적 mock view model로 표시한다.
- `orders`
  - MY-003 구매/낙찰 내역: 주문 상태, 상품, 판매자, 금액, 배송/구매확정/환불 가능 상태
  - 010 계약 확정 전까지 주문 생성·구매 확정·환불 액션은 비활성 또는 준비 상태로 둔다.
- `sales`
  - MY-004 판매/배송/환불/정산 내역: 구매자, 판매 가격, 배송 상태, 정산 상태, 송장 등록 진입
  - 배송/환불 endpoint 미확정이므로 목록 shell과 상태 표시 중심으로 시작한다.
- `lives`
  - MY-005 라이브 관리: 예약, 진행 중, 종료 라이브 목록과 연결 상품 수, 방송/상세 이동
  - 기존 `GET /api/lives`에 host filter가 없으므로 mock 또는 전체 목록 보조 필터는 사용하지 않고 BE 요청 대기로 둔다.
- `wishlist`
  - MY-006/MY-009 찜 목록: 구현된 `GET /api/users/{userId}/wishes`를 우선 연동 가능
  - 찜 해제는 구현된 `DELETE /api/users/{userId}/wishes/{productId}` 사용 가능
  - 팔로워/팔로잉 목록은 API 미구현이므로 별도 탭 shell과 요청 대기로 둔다.
- `business`
  - MY-008 사업자 정보·인증 상태: 현재 BIZ 제출 화면과 연결하고, 조회/수정 API 전까지 상태는 사용자 정보 또는 mock fallback으로 처리한다.

## 작업 내용

1. `domains/my`에 마이페이지 view model, mock data, API adapter, page/component를 만든다.
2. `/my` route를 `MyPage.vue`로 교체하고 `section` query를 읽어 탭/패널을 전환한다.
3. BE가 있는 API는 adapter에 실제 호출 후보를 분리하고, 미구현 API는 `VITE_MY_API_ENABLED` 같은 플래그 또는 명시적 mock fallback으로 둔다.
4. 프로필 수정은 현재 구현된 `PATCH /api/users/{id}`가 전체 필수 필드 방식이므로 저장 전 기존 값을 채워 보내는 형태로 설계한다. `GET /api/me`가 없으면 로그인 세션의 최소 정보와 mock profile을 병합한다.
5. 찜 목록은 실제 BE 구현을 기준으로 먼저 연결 가능한 영역으로 분리한다.
6. 주문/배송/환불/포인트/출금은 010 요청 문서의 확정 전까지 화면 shell과 준비 상태를 두고, `/points`는 기존 구현 화면으로 이동시킨다.
7. 구현 후 `FE/docs/frontend/screens/screen-inventory.md`, `FE/docs/frontend/flows/route-map.md`, `FE/docs/frontend/implementation/status.md`, `FE/docs/frontend/implementation/current-structure.md`를 갱신한다.

## 구현 목록

- [x] `domains/my/types`에 마이페이지 요약, 프로필, 판매 상품, 주문, 판매/정산, 라이브, 찜/팔로우 view model 타입을 정의한다.
- [x] `domains/my/constants`에 mock profile, summary, 메뉴, 상태 라벨과 섹션 옵션을 둔다.
- [x] `domains/my/api`에 `getMyPageSummary`, `getMyProfile`, `updateMyProfile`, `getMyWishList` 등 adapter 함수를 만든다.
- [x] `/my` route를 `domains/my/pages/MyPage.vue`로 연결한다.
- [x] 마이페이지 레이아웃을 구현한다: 상단 사용자 요약, 포인트 카드, 카운터, 탭/사이드 메뉴, 섹션 콘텐츠.
- [x] 마이페이지 목록에 판매자 대시보드 섹션을 추가한다: KPI, 월별 수익, 처리 대기, 상품 상태 분포.
- [x] MY-001 프로필 조회/수정 UI를 구현하고, 저장 중/성공/검증 오류/권한 오류 상태를 처리한다.
- [x] MY-001 내 정보 관리에 관심 브랜드·카테고리 조회/수정 UI를 추가하고, `GET/PUT /api/users/{id}/interests` 계약에 맞춘 adapter를 연결한다.
- [ ] MY-002 판매 상품 관리 shell을 구현한다.
- [x] MY-003 구매/낙찰 내역 shell을 구현한다: 상태 필터, 카드형 목록, 별도 상세 페이지 이동을 제공한다.
- [x] MY-004 판매/배송/환불/정산 내역 shell을 구현한다: 상태 필터, 카드형 목록, 별도 상세 페이지 이동을 제공한다.
- [x] MY-005 라이브 관리 shell을 구현한다: 상태 필터, 카드형 목록, 라이브 송출/상세 화면 이동을 제공한다.
- [ ] MY-006/MY-009 찜 목록은 BE 구현된 wish API 우선 연동 또는 fallback으로 구현한다.
- [ ] MY-008 사업자 정보 관리는 BIZ 화면 이동과 인증 상태 표시 중심으로 구현한다.
- [ ] `section` query와 헤더 드롭다운 이동이 각 섹션을 정확히 열도록 처리한다.
- [ ] 빈 목록, 로딩, 오류, 권한 없음, API 미준비 상태를 섹션별로 제공한다.
- [ ] 문서 상태와 라우트 맵을 갱신한다.
- [ ] `npm run type-check`와 `npm run build`로 검증한다.

## BE 요청/확인 필요

- `011-user-mypage-contract.md`에서 우선 확정 필요
  - `GET /api/me`: 마이페이지와 auth guard가 최신 사용자 정보를 얻기 위해 필요
  - `GET /api/users/{userId}/mypage`: 첫 화면 카운터, 포인트 요약, 판매 KPI, 월별 수익, 처리 대기, 상품 상태 분포를 한 번에 받을지 결정 필요
  - `PATCH /api/me` 제공 여부: 현재 `PATCH /api/users/{id}`는 전체 필수 필드 방식이라 부분 수정 UX와 충돌 가능
  - 프로필 이미지 업로드 방식과 응답 필드
  - 사업자 인증 상태 필드 위치
- `010-commerce-wallet-contract.md`에서 우선 확정 필요
  - `GET /api/orders` 또는 `GET /api/users/{id}/orders` 중 마이페이지 목록 endpoint
  - 구매/판매 구분 query, 주문 상태 enum, 낙찰 주문 표시 필드
  - 배송/송장 조회·등록 endpoint와 택배사 enum
  - 구매 확정, 환불 요청, 환불 가능 조건
  - 포인트 잔액/내역/출금 endpoint 최종 경로와 응답 필드
- 추가 요청 후보
  - 판매 상품 관리용 `GET /api/users/{userId}/products?status=&keyword=&page=&size=`
  - 라이브 관리용 `GET /api/users/{userId}/lives?status=&page=&size=` 또는 기존 `/api/lives`의 `hostId` filter
  - 팔로워/팔로잉 목록 `GET /api/users/{id}/followers`, `GET /api/users/{id}/followings`
  - 사업자 정보 조회/수정 `GET/PATCH /api/users/{id}/business` 또는 기존 사업자 인증 endpoint와의 통합 방식

## 보류 범위

- 주문 생성, 결제, 실제 포인트 차감, 정산 자동화, 운영자 출금 승인
- 환불 증빙 이미지 업로드와 심사 플로우
- 공개 프로필 상세 화면
- AI 시착 결과 저장/비교 관리 화면
- 장바구니 기능: 기능 정의서와 API 목록에서 명확한 도메인 계약이 없어 헤더의 `cart` query는 준비 상태로만 처리
