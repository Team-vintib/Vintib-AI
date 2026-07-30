# 003 Business Verification API 요청

## 1. 요청 개요

- 요청 파트: FE
- 대상 파트: BE
- 요청 목적: 사업자 회원이 사업자등록증을 제출하고, 제출/승인/반려 상태를 조회할 수 있도록 API 계약을 정리한다.
- 우선순위: P0
- 시연 필수 여부: 사업자 회원 온보딩을 시연하면 필수. 일반 회원만 시연하면 보류 가능.

## 2. 현재 연동 상태

- 연동 완료 API: 없음
- FE 구현 완료 범위
  - `BusinessVerificationPage.vue`: 사업자등록번호, 상호명, 대표자명, 등록증 이미지 제출 화면
  - `BusinessVerificationPendingPage.vue`: 제출 후 대기 상태 화면
  - `businessVerificationStore`: 제출 결과를 로컬에 임시 저장
- 현재 임시 처리 또는 Mock 사용 여부
  - `VITE_BUSINESS_VERIFICATION_API_ENABLED !== 'true'`이면 FE가 제출 지연 후 mock `PENDING` 응답을 반환한다.
  - 새로고침 후 서버 상태 복원 API가 없어 로컬 저장 상태에 의존한다.

## 3. 추가 구현 요청

### 3.1 사업자 인증 제출

- Method / Endpoint: `POST /api/business-verifications`
- 요청 목적: 사업자 인증 신청 자료를 제출하고 검토 대기 상태를 생성한다.
- FE 사용처: `BusinessVerificationPage.vue`
- 요청 데이터
  - Header: `Authorization: Bearer {accessToken}`
  - `multipart/form-data`
    - `businessRegistrationNumber`: string, 필수, 숫자 10자리
    - `businessName`: string, 필수
    - `representativeName`: string, 필수
    - `certificate`: image file, 필수
- 응답 데이터
  - `id`: number
  - `status`: `PENDING`
  - `submittedAt`: string(datetime)
- 응답 예시

```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "PENDING",
    "submittedAt": "2026-07-31T12:00:00"
  },
  "error": null
}
```

### 3.2 내 사업자 인증 상태 조회

- Method / Endpoint: `GET /api/business-verifications/me`
- 요청 목적: 현재 로그인 사용자의 사업자 인증 상태를 복원하고 화면 분기에 사용한다.
- FE 사용처: `BusinessVerificationPendingPage.vue`, 마이페이지, 사업자 기능 진입 guard
- 요청 데이터
  - Header: `Authorization: Bearer {accessToken}`
- 응답 데이터
  - `id`: number | null
  - `businessRegistrationNumber`: string | null
  - `businessName`: string | null
  - `representativeName`: string | null
  - `status`: `NONE` | `PENDING` | `APPROVED` | `REJECTED`
  - `submittedAt`: string(datetime) | null
  - `reviewedAt`: string(datetime) | null
  - `rejectionReason`: string | null
- 응답 예시

```json
{
  "success": true,
  "data": {
    "id": 1,
    "businessRegistrationNumber": "1234567890",
    "businessName": "빈티비상점",
    "representativeName": "홍길동",
    "status": "PENDING",
    "submittedAt": "2026-07-31T12:00:00",
    "reviewedAt": null,
    "rejectionReason": null
  },
  "error": null
}
```

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
  - 일반 회원만 시연하면 사업자 인증 제출/조회는 보류 가능
  - 관리자 검토 화면은 FE 범위에 아직 없음
- 추후 구현 예정 기능
  - 반려 후 재제출
  - 관리자 승인/반려 API
  - 인증 자료 상세 조회

## 6. 협의 필요 사항

- FE·BE 간 결정이 필요한 내용
  - 반려 후 재제출 가능 여부
  - 승인 후 `GET /api/me`에 사업자 인증 상태를 포함할지 여부
  - 사업자등록증 허용 MIME type, 최대 용량, 해상도
  - 사업자등록번호 서버 검증 범위
- 아직 확정되지 않은 응답 구조나 정책
  - `NONE` 상태에서 `id`와 사업자 정보 필드를 null로 줄지 생략할지
  - 제출 중복 처리 정책
  - 반려 사유 공개 문구

## 7. 추가 요청 없음

- 이미 정상 연동된 API: 없음
- 기존 규격을 유지하면 되는 기능: 없음
