# S15P11A108-400 사업자 인증 제출 API 구현 요청

## 요청자 파트 / 대상 파트

- 요청자: FE
- 대상: BE

## 배경/이유

FE에서 BIZ-001 사업자 정보 입력·검증과 BIZ-001-2 인증 대기 화면을 구현했다. 현재는
실제 API 없이 화면 간 더미 상태만 사용하므로 사업자 정보 제출, 파일 제한과 심사 상태
계약 확정을 요청한다.

## 요청 API 후보

```http
POST /api/business-verifications
Authorization: Bearer {accessToken}
Content-Type: multipart/form-data
```

| multipart 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `businessRegistrationNumber` | string | 예 | 사업자등록번호 |
| `businessName` | string | 예 | 상호명 |
| `representativeName` | string | 예 | 대표자명 |
| `certificate` | image file | 예 | 사업자등록증 한 개 |

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

## 요청 내용

- 인증 토큰에서 현재 회원을 식별하고 클라이언트가 회원 ID를 보내지 않도록 한다.
- 사업자등록번호, 상호명, 대표자명과 사업자등록증을 한 요청으로 저장한다.
- 중복 제출의 멱등 처리 또는 오류 정책을 확정한다.
- BIZ-001-2에서 사용할 제출 상태 조회 endpoint와 상태 값을 확정한다.
- 검증 실패 시 공통 `ApiResponse` 오류와 필드별 오류를 제공한다.
- 구현 후 Swagger에 multipart 필드, 성공 응답과 오류 응답을 문서화한다.

## BE 확인 필요

1. 사업자등록번호의 하이픈 허용, 숫자 길이와 체크섬 검증 주체
2. 사업자등록증 허용 확장자·MIME, 최대 용량과 최소 해상도
3. multipart endpoint와 실제 필드명
4. 심사 상태 enum과 승인·반려·재제출 흐름
5. 이미 제출했거나 인증된 회원의 중복 요청 정책
6. 제출 완료와 온보딩 완료 상태의 관계
7. 이메일 회원가입 직후 Bearer 인증이 필요한 온보딩·사업자 API를 호출할 수 있도록
   access token을 발급하는 방식

## FE 임시 처리

- 사업자등록번호는 하이픈 없이 숫자 10자리만 허용한다.
- 사업자등록증은 한 개와 `image/*` MIME만 확인하고 용량 제한은 적용하지 않는다.
- 실제 API를 호출하지 않고 약 0.7초의 제출 중 상태 후 Pinia 메모리에 제출 정보를
  보관한다.
- BIZ-001-2는 메모리 상태가 없으면 BIZ-001로 돌아간다.

## FE 관련 파일

- `FE/src/domains/biz/pages/BusinessVerificationPage.vue`
- `FE/src/domains/biz/pages/BusinessVerificationPendingPage.vue`
- `FE/docs/frontend/api/api-index.md`
- `FE/docs/frontend/screens/BIZ-001/requirements.md`
