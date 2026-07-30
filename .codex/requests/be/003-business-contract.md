# 사업자 도메인 API 계약 요청

## 요청자 파트 / 대상 파트

- 요청자: FE
- 대상: BE

## 배경/이유

FE는 BIZ-001 사업자 정보 입력/검증과 BIZ-001-2 인증 대기 화면을 구현했다. 현재 BE에는 사업자 인증 제출/상태 조회 API가 없어 FE는 Pinia 메모리 상태와 지연 mock으로 동작한다. 실제 저장, 파일 제한, 심사 상태 계약 확정을 요청한다.

## 현재 구현 확인

- BE에 business verification 관련 컨트롤러/서비스/엔티티가 없다.
- FE는 `businessRegistrationNumber`, `businessName`, `representativeName`, `certificateFile`을 메모리에 저장한다.
- FE 임시 규칙은 사업자등록번호 하이픈 없이 숫자 10자리, 인증서 파일 1개, MIME `image/*` 확인이다.

## 요청 API

### 사업자 인증 제출

```http
POST /api/business-verifications
Authorization: Bearer {accessToken}
Content-Type: multipart/form-data
```

multipart 필드 규칙:

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `businessRegistrationNumber` | string | 필수 | 숫자 10자리. 하이픈 허용 여부 확정 필요 |
| `businessName` | string | 필수 | 상호명 |
| `representativeName` | string | 필수 | 대표자명 |
| `certificate` | image file | 필수 | 사업자등록증 1개 |

성공 응답 후보:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "PENDING",
    "submittedAt": "2026-07-27T17:00:00+09:00"
  },
  "error": null
}
```

### 사업자 인증 상태 조회

```http
GET /api/business-verifications/me
Authorization: Bearer {accessToken}
```

응답 후보:

```json
{
  "success": true,
  "data": {
    "id": 1,
    "businessRegistrationNumber": "1234567890",
    "businessName": "빈티브상사",
    "representativeName": "홍길동",
    "status": "PENDING",
    "submittedAt": "2026-07-27T17:00:00+09:00",
    "reviewedAt": null,
    "rejectionReason": null
  },
  "error": null
}
```

상태 enum 후보:

| 값 | 의미 |
| --- | --- |
| `NONE` | 제출 내역 없음 |
| `PENDING` | 심사 대기 |
| `APPROVED` | 승인 |
| `REJECTED` | 반려 |

## 요청 사항

- 인증 토큰에서 현재 회원을 식별하고 클라이언트가 회원 ID를 보내지 않도록 한다.
- 사업자등록번호, 상호명, 대표자명과 사업자등록증을 한 요청으로 저장한다.
- 사업자등록번호 하이픈 허용, 숫자 길이, 체크섬 검증 주체를 확정한다.
- 사업자등록증 허용 확장자/MIME, 최대 용량, 최소 해상도를 확정한다.
- 중복 제출, 이미 승인된 회원, 반려 후 재제출 정책을 확정한다.
- 제출 완료와 온보딩 완료 상태의 관계를 확정한다. FE 흐름상 BUSINESS 회원은 온보딩 완료 후 사업자 인증 화면으로 이동한다.
- 검증 실패는 공통 `ApiResponse` 오류와 필드별 오류로 반환한다.
- Swagger에 multipart 필드, 성공 응답, 오류 응답, 상태 enum을 문서화한다.

## 오류 응답 필드명

FE가 필드별 표시할 수 있도록 아래 필드명을 사용 요청한다.

- `businessRegistrationNumber`
- `businessName`
- `representativeName`
- `certificate`

## FE 관련 파일

- `FE/src/domains/biz/pages/BusinessVerificationPage.vue`
- `FE/src/domains/biz/pages/BusinessVerificationPendingPage.vue`
- `FE/src/domains/biz/stores/businessVerificationStore.ts`
- `FE/src/domains/biz/constants/businessVerification.ts`
- `FE/docs/frontend/api/api-index.md`
- `FE/docs/frontend/screens/BIZ-001/requirements.md`
