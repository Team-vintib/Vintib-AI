# 003 Business Verification API 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 사업자 회원이 사업자등록증을 제출하고, 제출/승인/반려 상태를 조회할 수 있도록 API 계약을 정리한다.
- 우선순위: P0
- 시연 필수 여부: 사업자 회원 온보딩을 시연하면 필수. 일반 회원만 시연하면 보류 가능.

## 2. 현재 연동 상태

- 연동 완료 API
  - `POST /api/users/{userId}/business/upload-url`, `POST`/`GET /api/users/{userId}/business`(사업자 정보 제출/조회/재제출 — `docs/requests/FE/011-business-invoice-contract.md` 참고)
- FE 구현 완료 범위
  - `BusinessVerificationPage.vue`: 사업자등록번호, 상호명, 대표자명, 등록증 이미지 제출 화면
  - `BusinessVerificationPendingPage.vue`: 제출 후 대기 상태 화면
  - `businessVerificationStore`: 제출 결과를 로컬에 임시 저장
- 현재 임시 처리 또는 Mock 사용 여부
  - `VITE_BUSINESS_VERIFICATION_API_ENABLED !== 'true'`이면 FE가 제출 지연 후 mock `PENDING` 응답을 반환한다.
  - 새로고침 후 서버 상태 복원 API가 없어 로컬 저장 상태에 의존한다.

## 3. 추가 구현 요청

(3.1 사업자 인증 제출, 3.2 내 사업자 인증 상태 조회는 구현 완료 — 경로·업로드 방식·응답 필드가 요청과 다르게 확정되어 `docs/requests/FE/011-business-invoice-contract.md`에 확정 계약을 정리했다. 요약: 경로는 `/api/business-verifications`가 아니라 다른 온보딩류 API와 동일하게 `/api/users/{userId}/business`이고, `multipart/form-data` 한 번에 제출하는 대신 상품 이미지·시착 프로필과 동일한 presigned 2단계 업로드를 쓴다. 관리자 승인/거절 API는 이번 범위 밖이다.)

## 4. 기존 API 변경 요청

- 기존 요청·응답에서 변경할 내용
  - `GET /api/me`를 제공한다면 `businessVerificationStatus` 포함 요청
- 추가할 필드
  - `businessVerificationStatus`: `NONE` | `PENDING` | `APPROVED` | `REJECTED`
- 변경 영향 범위
  - 사업자 인증 CTA 노출
  - 상품 등록/라이브 생성 가능 여부 판단
  - 마이페이지 인증 상태 표시

## 5. 보류 또는 시연 제외 범위

- 현재 구현하지 않아도 되는 기능
  - 관리자 검토 화면은 FE 범위에 아직 없음
- 추후 구현 예정 기능
  - 관리자 승인/반려 API(이번 범위에 없어 승인은 현재 DB 직접 조작으로만 가능)
  - 인증 자료 상세 조회

## 6. 협의 필요 사항

- FE·BE 간 결정이 필요한 내용
  - 승인 후 `GET /api/me`에 사업자 인증 상태를 포함할지 여부(`GET /api/me` 자체가 아직 없음 — `docs/requests/BE/011-user-mypage-contract.md` 참고)
- 아직 확정되지 않은 응답 구조나 정책
  - 반려 사유 공개 문구(반려 사유 필드 자체가 아직 없음)

## 7. 추가 요청 없음

- 이미 정상 연동된 API
  - 사업자 정보 제출/조회/재제출 — `docs/requests/FE/011-business-invoice-contract.md` 기준
- 기존 규격을 유지하면 되는 기능: 없음
