# 마이페이지(MY-001~007) 확정 계약

**요청자 파트**: BE
**대상 파트**: FE

## 배경

마이페이지 API를 구현했다. `docs/requests/BE/011-user-mypage-contract.md`가 요청한 `/api/me`는 이 프로젝트 전례대로 `/api/users/{id}`로 확정했다. MY-006(찜/팔로우)·MY-008(사업자)·MY-009(찜/해제)는 이미 완료돼 있어 이번엔 다루지 않는다(각각 `docs/requests/FE/002`, `011`, `009` 참고).

## API 목록

| 기능 | Method | Endpoint | 비고 |
| --- | --- | --- | --- |
| 내 정보 조회 | GET | `/users/{id}` | `businessVerificationStatus` 포함 |
| 내 정보 수정 | PATCH | `/users/{id}` | 기존 API(온보딩과 겸용) |
| 판매 상품 관리 | GET | `/users/{id}/products` | 본인 전용, DRAFT 등 비공개 상태 포함 |
| 구매/판매 내역 | GET | `/users/{id}/orders?role=BUYER\|SELLER` | `role` 필수 |
| 주문 상세 | GET | `/orders/{orderId}` | 당사자만 |
| 라이브 관리 | GET | `/lives?hostId={id}` | 기존 목록 API 재사용. 본인 hostId면 종료·취소 이력까지 조회 |
| 포인트 잔액 | GET | `/users/{id}/points` | 없으면 0으로 자동 생성 |
| 포인트 사용 내역 | GET | `/users/{id}/points/logs` | 전체 원장 |
| 포인트 충전 | POST | `/users/{id}/points/charges` | **실결제 없는 테스트/데모 전용** |
| 출금 신청 | POST | `/users/{id}/withdrawals` | 신청까지만(관리자 승인 없음) |
| 출금 내역 | GET | `/users/{id}/withdrawals` | WITHDRAW만 필터링된 내역 |

모든 엔드포인트는 인증 필요(본인만), `products`/`orders`/`points`/`withdrawals`는 실패 시 403.

## 주의할 것

- **주문 데이터가 없다**: 주문 생성 API가 아직 없어(`docs/requests/BE/010-commerce-wallet-contract.md`), `orders`/판매 정산 화면은 실제 데이터가 없다.
- **공개 프로필용 아님**: `products`/`lives`는 본인 조회 시에만 전체 정보를 준다 — 판매자 공개 프로필(011 §3.3/§3.5)엔 못 쓴다.
- 마이페이지 요약(`GET /users/{id}/mypage`, 011 §3.4)은 이번 범위에서 제외했다.

## 관련 자료

- Swagger: `/swagger-ui/index.html` — "마이페이지(MyPage)", "주문(Orders)" 태그
- `docs/APIs.md` — 회원/상품/주문/라이브/포인트 섹션에 반영됨

## 처리 결과

(FE 반영 후 기입)
