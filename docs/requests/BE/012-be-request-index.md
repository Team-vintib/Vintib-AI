# 012 BE 요청 문서 인덱스

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 2026-07-31 기준 FE 화면/흐름과 BE controller를 대조한 요청 문서 목록을 한 곳에서 추적한다.
- 우선순위: P0
- 시연 필수 여부: 각 도메인 문서 기준을 따른다.

## 2. 현재 연동 상태

- FE 구현 완료 범위
  - Onboarding, Search, Auction, Commerce, MyPage는 mock 또는 미구현 범위가 남아 있음
  - Business는 BE 구현 완료(제출/조회/재제출) — FE는 아직 mock 사용 중(`docs/requests/FE/011-business-invoice-contract.md` 반영 필요)
- 현재 임시 처리 또는 Mock 사용 여부
  - Onboarding: mock-success fallback
  - Business: FE가 아직 `docs/requests/FE/011-business-invoice-contract.md` 미반영 — mock `PENDING` fallback 유지 중
  - Search: mock data 기반 화면
  - Auction: mock snapshot
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
| 004 | `004-home-contract.md` | Home | 홈/팔로잉 홈 연결 완료 | live card `hostId`, 정렬/노출 정책 문서화 |
| 005 | `005-search-contract.md` | Search | FE 화면/adapter 있음, BE `/api/search` 없음 | 통합 검색 API |
| 006 | `006-product-contract.md` | Product | 목록/상세/등록/이미지/찜 연결 완료 | AI 분석/가격 추천 |
| 007 | `007-live-tryon-contract.md` | Live/TryOn | 라이브 목록/상세/생성, 시착 프로필, 영상 토큰, 시청 화면 상품/헤더 필수 필드(brandName/price/thumbnailUrl/saleType/conditionGrade/currentProductId) 연결 완료 | 생성용 상품 조회, AI 시착 생성, 선택 필드(hostProfileImageUrl/description/material/measurements/defectSummary) |
| 008 | `008-social-notification-contract.md` | Social/Notification | 상품 상세 찜, 팔로우/팔로워·팔로잉 목록, 알림 목록/읽음 API 연동 완료. 알림 seed 제거 후 실제 생성 데이터 없음 | 알림 type/ref 문서화, 실제 알림 생성 이벤트, 예약 라이브 알림 신청/스케줄러, 탭별 bulk read |
| 009 | `009-auction-chat-contract.md` | Auction/Chat | 채팅/반응/시청자 수, 경매 조건 설정 연결 완료 | 경매 snapshot/start/bid/close/STOMP |

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용
  - 세부 내용은 각 도메인 문서의 4번 섹션을 따른다.
- 추가할 필드
  - Auth: `user`, `nextStep`
  - Home: live card `hostId`
  - Social/Notification: 알림 `type/refType/refId` 문서화, 도메인 이벤트별 알림 생성 정책, 예약 라이브 알림 신청/스케줄러, 탭별 읽음 처리 API
- 변경 영향 범위
  - route guard
  - 홈/상품/라이브 카드 이동
  - 검색/상품 필터
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
- `007-live-tryon-contract.md` §3.5(라이브 시청 화면 필드 보강)는 필수 필드 4개가 전부 반영돼 있었다
  (`saleType`은 `DIRECT_SALE`, `condition`은 `conditionGrade`로 이름이 다름). 선택 필드
  (`hostProfileImageUrl`/`description`/`material`/`measurements`/`defectSummary`)와 §3.1(생성용 상품
  조회)·§3.3/3.6(AI 시착 생성)은 아직 남아 있어 문서는 삭제하지 않고 갱신만 했다.
