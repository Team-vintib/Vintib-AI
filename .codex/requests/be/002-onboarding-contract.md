# 온보딩 도메인 API 통합 구현 요청

## 요청자 파트 / 대상 파트

- 요청자: FE
- 대상: BE

## 배경/이유

FE에는 ONBOARD-001 기본 정보, ONBOARD-002 관심 정보, ONBOARD-003 AI 시착 프로필, ONBOARD-004 회원 유형 선택 및 온보딩 완료 화면이 구현되어 있다. 현재 BE에는 이 흐름을 처리하는 `/api/me/**` 온보딩 API가 없으므로 FE 구현 기준으로 한 번에 설계/구현 요청한다.

기존 개별 요청 `001-onboarding-basic-info-api.md`, `002-onboarding-interests-api.md`, `003-onboarding-tryon-profile-api.md`, `004-onboarding-member-type-completion-api.md`를 이 문서로 병합한다.

## 현재 BE 구현 확인

- `Member`에는 `email`, `password`, `name`, `nickname`, `phoneNumber`, `address`, `gender`, `onboardingCompleted`가 있다.
- `Gender` enum은 `MALE`, `FEMALE`, `OTHER`가 있으나 FE 온보딩은 `MALE | FEMALE`만 사용한다.
- `Member.completeOnboarding(nickname, phoneNumber, address, gender)`는 기본 정보 저장과 동시에 `onboardingCompleted=true`로 바꾸는 형태다.
- `memberType`, `postalCode`, `detailAddress` 필드는 없다.
- 회원 관심 브랜드/카테고리 저장 도메인과 `/api/me/interests`는 없다.
- 시착 프로필 엔티티와 `/api/me/tryon`은 없다. 현재 `tryon` 패키지는 시착 결과(`/api/users/{userId}/tryons`)만 구현되어 있다.
- 브랜드/카테고리 마스터 조회는 이미 `GET /api/brands`, `GET /api/categories`로 구현되어 있고 응답 ID는 number다.

## 공통 응답 규격

모든 API는 현재 BE 공통 envelope를 사용한다.

성공:

```json
{
  "success": true,
  "data": null,
  "error": null
}
```

검증 실패:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "C001",
    "message": "잘못된 입력값입니다.",
    "errors": [
      {
        "field": "nickname",
        "value": "!",
        "reason": "닉네임은 한글, 영문, 숫자 2~10자로 입력해주세요."
      }
    ]
  }
}
```

`error.errors[].field`는 FE 요청 필드명과 동일해야 한다.

## 1. 기본 정보 저장

```http
PATCH /api/me/onboarding
Authorization: Bearer {accessToken}
Content-Type: application/json
```

요청:

```json
{
  "nickname": "빈티지러버",
  "gender": "FEMALE",
  "phoneNumber": "010-1234-5678",
  "postalCode": "06236",
  "address": "서울 강남구 테헤란로 212",
  "detailAddress": "3층"
}
```

필드 규칙:

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `nickname` | string | 필수 | 한글, 영문, 숫자 2~10자 |
| `gender` | enum | 필수 | FE는 `MALE`, `FEMALE`만 전송 |
| `phoneNumber` | string | 필수 | 국내 전화번호 형식 |
| `postalCode` | string/null | 선택 | Kakao 주소 검색 결과. 직접 입력 주소는 `null` 가능 |
| `address` | string | 필수 | 기본 주소 |
| `detailAddress` | string | 필수 | 상세 주소 |

요청 사항:

- 인증 토큰에서 현재 회원을 식별하고 클라이언트가 회원 ID를 보내지 않는다.
- 기본 정보 저장 시 `onboardingCompleted`를 true로 바꾸지 않는다.
- `postalCode`, `address`, `detailAddress`를 분리 저장할지, 기존 `address`에 결합 저장할지 확정한다.
- 닉네임 중복 검증과 오류 코드/HTTP status를 확정한다.
- `gender=OTHER`는 온보딩 API에서 받을지, 기존 enum에는 유지하되 FE 온보딩 계약에서는 제외할지 확정한다.

## 2. 관심 정보 저장

```http
PUT /api/me/interests
Authorization: Bearer {accessToken}
Content-Type: application/json
```

요청:

```json
{
  "brandIds": [1, 3],
  "categoryIds": [2, 5]
}
```

건너뛰기:

```json
{
  "brandIds": [],
  "categoryIds": []
}
```

필드 규칙:

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `brandIds` | number[] | 필수 | `GET /api/brands`의 `id`, 중복 없음, 빈 배열 허용 |
| `categoryIds` | number[] | 필수 | `GET /api/categories`의 `id`, 중복 없음, 빈 배열 허용 |

기존 FE 초기 요청은 `string[]`였지만 BE 브랜드/카테고리 마스터가 number ID로 구현되어 있으므로 최종 계약은 number ID 기준으로 확정 요청한다. FE는 실제 연동 시 타입을 number 배열로 맞춘다.

요청 사항:

- PUT은 회원의 기존 관심 브랜드/카테고리를 요청 배열 전체로 교체한다.
- 두 배열이 모두 비어 있으면 관심 정보 없이 건너뛴 상태로 저장한다.
- 존재하지 않는 ID, 비활성화 ID, 중복 ID에 대한 오류 규격을 확정한다.
- 저장 테이블/엔티티를 설계한다.

## 3. AI 시착 프로필 저장

```http
PUT /api/me/tryon
Authorization: Bearer {accessToken}
Content-Type: multipart/form-data
```

multipart 필드 규칙:

| 필드 | 타입 | 필수 | FE 규칙 |
| --- | --- | --- | --- |
| `bodyPhoto` | image file | 선택 | MIME type `image/*` |
| `heightCm` | integer string | 선택 | 0보다 큰 정수, cm |
| `weightKg` | integer string | 선택 | 0보다 큰 정수, kg |
| `chest` | integer string | 선택 | 0보다 큰 정수, 단위 확정 필요 |
| `waist` | integer string | 선택 | 0보다 큰 정수, 단위 확정 필요 |
| `hip` | integer string | 선택 | 0보다 큰 정수, 단위 확정 필요 |

요청 사항:

- 값이 없는 필드는 multipart 요청에서 생략한다.
- 사진만, 신체 정보 일부만, 사진과 신체 정보를 함께 저장할 수 있어야 한다.
- PUT은 전달된 값을 현재 회원의 AI 시착 프로필에 반영하는 멱등 요청으로 사용한다.
- 미전달 값은 기존 값을 유지하는지, null로 지우는지 명시한다. FE 현재 의도는 미전달 값 유지다.
- 건너뛰기와 모든 값이 빈 다음 단계는 FE가 API를 호출하지 않는다.
- `member_body_profile` 또는 동등한 테이블에 `body_photo_url`, `height_cm`, `weight_kg`, `chest`, `waist`, `hip` 저장 여부를 확정한다.
- 숫자 필드 최소/최대, 소수 허용 여부, 가슴/허리/엉덩이 단위를 확정한다.
- 사진 허용 형식, 최대 용량, 최소 해상도와 S3 저장 정책을 확정한다.
- 전신 사진 개인정보 동의, 보관 기간, 변경·삭제 정책을 확정한다.
- 기존 사진 삭제는 별도 endpoint로 둘지 확정한다.

필드 오류명은 `bodyPhoto`, `heightCm`, `weightKg`, `chest`, `waist`, `hip`을 사용한다.

## 4. 회원 유형 저장 및 온보딩 완료

```http
POST /api/me/onboarding/complete
Authorization: Bearer {accessToken}
Content-Type: application/json
```

요청:

```json
{
  "memberType": "GENERAL"
}
```

필드 규칙:

| 필드 | 타입 | 필수 | 규칙 |
| --- | --- | --- | --- |
| `memberType` | enum | 필수 | `GENERAL`, `BUSINESS` |

요청 사항:

- 회원 유형 저장과 `onboardingCompleted=true` 변경을 하나의 트랜잭션으로 처리한다.
- `Member.completeOnboarding()` 책임을 기본 정보 저장과 최종 완료 처리로 분리한다.
- `member.member_type` 컬럼과 Java enum 매핑을 추가한다.
- 이미 완료한 회원의 재요청을 멱등 성공으로 볼지, 회원 유형 변경 오류로 볼지 정책을 확정한다.
- 완료 이후 인증 응답 또는 내 정보 조회에서 `memberType`, `onboardingCompleted`를 제공한다.

성공 후 FE 라우팅:

- `GENERAL`: 홈
- `BUSINESS`: 사업자 인증 화면

## FE 관련 파일

- `FE/src/domains/onboard/api/onboarding.ts`
- `FE/src/domains/onboard/pages/OnboardingBasicInfoView.vue`
- `FE/src/domains/onboard/pages/OnboardingInterestsView.vue`
- `FE/src/domains/onboard/pages/OnboardingTryOnView.vue`
- `FE/src/domains/onboard/pages/OnboardingMemberTypeView.vue`
- `FE/docs/frontend/api/api-index.md`
