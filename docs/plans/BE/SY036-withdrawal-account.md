# SY036 - 출금 계좌 관리 (POINT-003)

## 배경/목표

포인트 현금화(POINT-004, `POST /users/{id}/withdrawals`)는 이미 있지만 금액만 받고 계좌 정보를
받지 않는다 — "환불(현금화)받을 계좌를 입력하면 그 계좌로 출금해주는" 흐름이 없다. 기능정의서
POINT-003("출금 계좌 관리")이 정의하는 대로, 계좌 정보를 등록/조회/수정하는 API를 추가하고
출금 신청 시 등록된 계좌가 있어야만 신청 가능하게 만든다.

- 실제 은행 송금 연동은 이번 범위 밖이다 — 지금 출금 신청도 "신청까지만 처리, 완료는 DB 직접 조작"
  방식인데(관리자 승인 체계 없음), 그 전제를 그대로 유지한다. 이번 작업은 **어느 계좌로 보내야 하는지
  정보를 남기는 것**까지다. 실제 송금은 여전히 사람이 계좌 정보를 보고 수동으로 처리한다.
- 은행명은 자유 문자열로 받는다(고정 코드 enum 아님) — `CourierCode`처럼 외부 API가 지원하는
  코드 집합에 맞출 필요가 없고, 은행명 표시용 문자열이면 충분하기 때문이다.
- 계좌번호는 평문 저장한다 — 코드베이스에 필드 암호화 유틸리티가 없고(`BusinessInfo`의 사업자번호도
  평문 저장), 이번 범위에서 새로 도입하지 않는다.

## 작업 내용

### 1. 계좌 등록/조회 (POINT-003)

`point.entity.WithdrawalAccount` 신규 — `PointAccount`/`OrderShipment`와 같은 공유 PK 1:1 구조
(PK=`member_id`). 필드: `bankName`, `accountNumber`, `accountHolderName`(예금주명), `updatedAt`.

- `PUT /api/users/{userId}/points/account`: 본인만 등록/수정 가능. 행이 없으면 생성, 있으면
  갱신(upsert) — `OrderService.registerAddress`와 같은 패턴.
- `GET /api/users/{userId}/points/account`: 본인만 조회 가능. 미등록이면 404
  (`WITHDRAWAL_ACCOUNT_NOT_FOUND`) — FE는 이 404를 계좌 입력 화면으로 유도하는 신호로 쓴다
  (기능정의서 POINT-003 비고와 일치).

두 엔드포인트 모두 기존 `PointController`(`/api/users/{userId}/points`)에 추가한다.

### 2. 출금 신청 시 계좌 필수화 (POINT-004)

`PointService.requestWithdrawal`에서 잔액 검증 전에 계좌 등록 여부를 먼저 확인한다 — 없으면
`WITHDRAWAL_ACCOUNT_REQUIRED`(400)로 거부한다. 출금 신청 자체의 요청/응답 바디는 바꾸지 않는다
(금액만 받는 기존 계약 유지) — 계좌는 별도로 등록해 두고 재사용하는 구조이기 때문이다.

### 3. 에러 코드

| 상황 | 코드 |
| --- | --- |
| 출금 신청 시 등록된 계좌 없음 | `WITHDRAWAL_ACCOUNT_REQUIRED`(W007) |
| 계좌 조회 시 등록된 계좌 없음 | `WITHDRAWAL_ACCOUNT_NOT_FOUND`(W008) |

## 구현 목록

- [ ] `point.entity.WithdrawalAccount` 엔티티(공유 PK 1:1) + `point.repository.WithdrawalAccountRepository` 추가
- [ ] `docs/db/schema.sql`에 `withdrawal_account` 테이블 추가
- [ ] `WithdrawalAccountRequest`(`bankName`/`accountNumber`/`accountHolderName`), `WithdrawalAccountResponse` DTO 추가
- [ ] `PointService`에 `registerWithdrawalAccount(memberId, ...)`, `getWithdrawalAccount(memberId)` 추가 + `requestWithdrawal`에 계좌 필수 검증 추가 + 테스트
- [ ] `PointController`에 `PUT/GET /api/users/{userId}/points/account` 추가 + Swagger 문서화
- [ ] `ErrorCode`에 W007~W008 추가
- [ ] `docs/APIs.md` 포인트/출금 섹션 갱신
- [ ] `docs/requests/BE/010-commerce-wallet-contract.md`의 "출금 계좌 관리(POINT-003)" 미반영 항목 반영 완료로 정리(반영된 부분 덜어내고, 남은 게 없으면 문서 자체를 검토해 필요 시 삭제)
- [ ] `.claude/skills/BE:verify`로 최종 검증

## 확인 필요 사항

- 최소 출금 금액/수수료/처리 기간은 여전히 미정(기능정의서 POINT-004에도 "추가 논의 필요"로 명시돼
  있음) — 이번 범위에서도 다루지 않는다.
- 계좌 1개만 등록 가능(공유 PK 1:1)으로 가정 — 여러 계좌를 등록해 두고 출금 시 선택하는 방식은
  요청받지 않아 이번 범위에서 제외한다.