# 006 BE 요청 문서 인덱스

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 2026-07-31 기준 FE 화면/흐름과 BE controller를 대조한 요청 문서 목록을 한 곳에서 추적한다.
- 우선순위: P0
- 시연 필수 여부: 각 도메인 문서 기준을 따른다.

## 2. 현재 연동 상태

- FE 구현 완료 범위
  - Onboarding, Commerce, MyPage는 mock 또는 미구현 범위가 남아 있음
  - Home/Search는 BE 구현 완료(팀원 쪽에서 반영) — `004-home-contract.md`/`005-search-contract.md`는
    반영 완료로 삭제됨
  - Business는 BE 구현 완료(제출/조회/재제출) — FE는 아직 mock 사용 중(`docs/requests/FE/017-business-invoice-contract.md` 반영 필요)
- 현재 임시 처리 또는 Mock 사용 여부
  - Onboarding: mock-success fallback
  - Business: FE가 아직 `docs/requests/FE/017-business-invoice-contract.md` 미반영 — mock `PENDING` fallback 유지 중
  - Commerce/Wallet, MyPage: FE 화면 없음

## 3. 추가 구현 요청

### 3.1 도메인별 요청 문서 확인

- Method / Endpoint: 해당 없음
- 요청 목적: BE 구현 시 도메인별 상세 요청 문서를 기준으로 우선순위와 필드를 확인한다.
- FE 사용처: FE-BE 계약 추적
- 요청 데이터: 없음
- 응답 데이터: 없음
- 응답 예시: 없음

| 번호 | 문서 | 도메인 | FE 기준 상태 | 남은 BE 요청 |
| --- | --- | --- | --- | --- |
| 001 | `001-auth-contract.md` | Auth | 이메일 auth API 연결 완료 | `GET /api/me`, auth 응답 `user/nextStep`, SSAFY SSO |
| 002 | `002-product-contract.md` | Product | 목록/상세/등록/이미지/찜 연결 완료 | AI 분석/가격 추천 |
| 003 | `003-live-tryon-contract.md` | Live/TryOn | 라이브 목록/상세/생성, 시착 프로필, 영상 토큰, 시청 화면 필드(필수+선택 전부: brandName/price/thumbnailUrl/saleType/conditionGrade/currentProductId/hostProfileImageUrl/description/material/measurements/defectSummary) 연결 완료 | AI 시착 생성만 남음(서윤/AI 파트) |
| 004 | `004-social-notification-contract.md` | Social/Notification | 상품 상세 찜, 팔로우/팔로워·팔로잉 목록, 알림 목록/읽음 API, 예약 라이브 알림 신청/스케줄러, `LIVE_STARTED`/`AUCTION_OUTBID` 알림 생성 연동 완료 | 알림 생성 이벤트 5종(낙찰/주문/배송/포인트)은 아직 — 낙찰은 Phase 8, 나머지는 서윤 확인 필요. unread count API, 탭별 bulk read API |
| 005 | `005-auction-chat-contract.md` | Auction/Chat | 채팅/반응/시청자 수, 경매 조건 설정, 경매 snapshot/시작/입찰/입찰내역, STOMP(`AUCTION_STARTED`/`BID_PLACED`) 연동 완료 | 경매 종료(`close`)·낙찰자 조회(`winner`)·`AUCTION_CLOSED` 이벤트·자동 종료 스케줄러 |
| 010 | `010-product-category-optional.md` | Product | 미반영 | `categoryId`가 여전히 `@NotNull`(`ProductCreateRequest`) — 선택 입력 전환 검토 |
| 011 | `011-product-similar-price-distribution.md` | Product | 미반영 | 상품 상세에 유사 상품 목록(`id`/`title`/`price`) 없음 |
| 012 | `012-product-ai-tryon-registration-fields.md` | Product | 미반영 | `aiModelEnabled`/`aiModelGender` 필드가 `ProductCreateRequest`에 없음 |

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용
  - 세부 내용은 각 도메인 문서의 4번 섹션을 따른다.
- 추가할 필드
  - Auth: `user`, `nextStep`
  - Social/Notification: 알림 `type/refType/refId` 문서화, 탭별 읽음 처리 API
- 변경 영향 범위
  - route guard
  - 홈/상품/라이브 카드 이동
  - 알림 클릭 이동

## 5. 보류 또는 시연 제외 범위

- 현재 구현하지 않아도 되는 기능
  - FE 화면이 없는 Commerce/Wallet 전체
  - FE 화면이 없는 MyPage/공개 프로필
  - 상품 수정/삭제/이미지 수정/삭제 API 연결
  - 라이브 상품 관리 UI
  - 찜 목록 UI
- 추후 구현 예정 기능
  - 각 도메인 문서의 5번 섹션을 따른다.

## 6. 협의 필요 사항

- FE·BE 간 결정이 필요한 내용
  - FE axios `baseURL`은 `/api`이므로 FE API 함수에서는 `/auth/...`, `/home`처럼 `/api`를 제외하고 호출한다.
  - BE `PageResponse<T>`는 `content/page/size/totalElements/totalPages/hasNext` 구조다. FE adapter에서 `items/meta`로 변환한다.
  - FE 화면이 없는 API는 임의로 UI를 새로 만들지 않고 FE 설계 후 연결한다.
- 아직 확정되지 않은 응답 구조나 정책
  - 각 도메인 문서의 6번 섹션을 따른다.

## 7. 추가 요청 없음

- 이미 정상 연동된 API: 없음(완료된 항목은 각 도메인 문서에서 삭제하고 이 목록에도 남기지 않는다 — 반영 내용은 커밋/Jira에 남는다)
- 기존 규격을 유지하면 되는 기능
  - BE에는 있지만 FE 화면/진입점이 없어 아직 미연결인 API는 각 도메인 화면 설계 후 연결한다.

## 2026-08-03 정리

- `013-live-seller-control.md`는 완전히 반영돼(현재 소개 상품 전환 + STOMP 전파까지 확인) 삭제했다 — 위 표에서도 뺐다.

## 2026-08-04 정리

- `010-commerce-wallet-contract.md`는 남아 있던 환불(REFUND-001/002, 이슈 509)·출금 계좌·최소 충전/출금
  금액(10,000원)까지 전부 반영돼 삭제했다 — 위 표에서도 뺐다. 환불 승인 주체는 운영자가 아니라
  판매자로 확정했다(`docs/plans/BE/SY037-refund.md` 참고).
- `003-live-tryon-contract.md` §3.5(라이브 시청 화면 필드 보강)는 필수 필드 4개가 전부 반영돼 있었다
  (`saleType`은 `DIRECT_SALE`, `condition`은 `conditionGrade`로 이름이 다름). 선택 필드
  (`hostProfileImageUrl`/`description`/`material`/`measurements`/`defectSummary`)와 §3.1(생성용 상품
  조회)·§3.3/3.6(AI 시착 생성)은 아직 남아 있어 문서는 삭제하지 않고 갱신만 했다.

## 2026-08-04 Phase 8 진입 전 정리

- `003-live-tryon-contract.md` §3.5 선택 필드(hostProfileImageUrl/description/material/
  measurements/defectSummary) 전부 반영 완료. 남은 것은 AI 시착 생성뿐이라 표 상태를 "AI 시착
  생성만 남음"으로 정리했다.
- `004-social-notification-contract.md`에 `LIVE_STARTED`(팔로우한 판매자 방송 시작)·
  `AUCTION_OUTBID`(상위 입찰 발생) 알림 생성을 추가했다 — 둘 다 정윤 도메인 트리거라 서윤을
  기다리지 않고 반영했다. 계약은 `docs/requests/FE/027-live-optional-fields-and-notifications.md`.
- `007-unsold-product-disposition.md` 질문 1(미낙찰 상품 처리)에 DB 설계 기준 예비 답변을 남겼다
  — 최종 검증은 Phase 8 코드가 들어간 뒤.
- `018-live-broadcast-end-summary.md`(방송 종료 요약 API)는 Phase 8 작업(경매 종료·낙찰/유찰
  집계)과 데이터가 겹쳐 Phase 8에서 함께 처리한다 — 별도 반영하지 않았다.

## 2026-08-04 머지 정리 (경매/라이브 알림/검색/홈 대규모 반영)

- `004-home-contract.md`, `005-search-contract.md`는 팀원(정윤) 쪽에서 홈 `hostId`·통합 검색을
  구현하며 직접 삭제 처리했다 — 위 표에서도 뺐다.
- 경매 시작/입찰/입찰내역(AUCT-002~010), 라이브 예약 알림 신청/스케줄러가 이번 머지로 반영됐다 —
  008/009 문서를 코드와 대조해 갱신 완료(009 §3.1~3.3, 008 §3.1~3.2). 남은 것: 경매 종료/낙찰자
  조회(009), 알림 생성 이벤트 7종·unread count·탭별 bulk read(008).
- BE가 새로 요청한 문서 3개도 생겼다: `010-product-category-optional.md`,
  `011-product-similar-price-distribution.md`, `012-product-ai-tryon-registration-fields.md` —
  코드 확인 결과(categoryId `@NotNull` 그대로, similarProducts/aiModelEnabled·aiModelGender 필드 없음)
  전부 미반영 확인 후 표에 추가했다.
- 2026-08-04: 이 폴더 및 `FE`/`AI` 요청 문서 전체를 001부터 빈틈없이 재넘버링했다(팀원별로 독립적으로
  번호를 매겨 BE 014·016, FE 001·002·003·005·006·007·016·018, AI 002가 중복돼 있었음). 이 문서 자체도
  012 → 006으로 바뀌었다.
