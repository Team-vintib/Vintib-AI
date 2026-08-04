# SY025 — AI 가상 시착 프로필(전신사진 + 신체치수) 등록/조회/수정/삭제

## 배경/목표

온보딩(ONBOARD-003)과 라이브 시착 패널에서 재사용할 "AI 가상 시착 프로필"(전신 사진 + 키/몸무게/가슴·허리·엉덩이둘레)을 등록·조회·수정·삭제하는 API가 아직 없다. `APIs.md`에는 `GET/PUT/DELETE /users/{id}/tryon`(TRYON-001/002)이 미구현으로 등록돼 있고, DB에는 `member_body_profile` 테이블 초안(`BE/docs/db/schema.sql` 57~64행)만 있을 뿐 JPA 엔티티는 아직 없다. 이미 구현된 `/api/users/{userId}/tryons`(복수형, TRYON-005 — 시착 "결과" 저장/조회/삭제)와는 다른 리소스다.

FE 요청 문서(`docs/requests/BE/002-onboarding-contract.md` §3.3, `007-live-tryon-contract.md` §3.4)는 `PUT /api/me/tryon`을 multipart로 요청했다. 이번 설계는 다음 두 가지를 사용자와 논의해 확정한 뒤 진행한다.

1. **경로**: 이 프로젝트에서 반복된 전례(같은 002 문서의 §3.1/3.2/3.4가 전부 `/api/me/X` → `/api/users/{id}/X`로 정정됨)를 따라 `/api/users/{userId}/tryon`으로 간다.
2. **업로드 방식**: 상품 이미지와 동일한 **presigned 2단계**로 간다. 개인 신체 사진이라 비공개 버킷에 저장해야 하고(업로드 방식과는 무관하게 어차피 그렇게 할 계획이었음), 기존 컨벤션과의 일관성도 고려해 이 방식으로 확정했다. FE가 이미 구현해둔 multipart 업로드 화면은 재작업이 필요하므로 계약 변경 요청 문서를 새로 남긴다.

## 작업 내용

### 1) DB 스키마 (`BE/docs/db/schema.sql` 57~64행)

```sql
-- 전신 사진·신체 정보 (ONBOARD-003, TRYON-001~002)
-- body_photo_key: 비공개(private) 버킷에 저장되는 S3 key. presigned GET으로만 열 수 있어
-- 고정 URL이 아니라 key를 저장한다 — tryon_result.image_key와 동일한 이유.
CREATE TABLE member_body_profile (
    member_id      BIGINT PRIMARY KEY REFERENCES member (id),
    body_photo_key VARCHAR(500),
    height_cm      SMALLINT,
    weight_kg      SMALLINT,
    chest_cm       SMALLINT,
    waist_cm       SMALLINT,
    hip_cm         SMALLINT,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`local`은 `ddl-auto: update`라 Hibernate가 엔티티 매핑대로 테이블을 만든다(이 테이블은 어느 환경에도 아직 존재하지 않아 컬럼명 변경으로 인한 마이그레이션 이슈 없음). 구현 후 `bash docs/db/regen.sh`, `bash docs/db/export-erd.sh`로 `data-dictionary.md`/`erd.md`/`docs/db/img/`를 재생성한다.

### 2) 엔티티 — `tryon/entity/MemberBodyProfile.java`

`business_info`(66~76행, 아직 엔티티 없음)와 같은 "공유 PK 1:1" 구조. `@Id private Long memberId` + `@MapsId @OneToOne @JoinColumn(name="member_id") private Member member`.

필드: `bodyPhotoKey`(nullable String), `heightCm`/`weightKg`/`chest`/`waist`/`hip`(nullable Short), `updatedAt`. setter 없이 상태 변경 메서드만 공개:
- `updatePhoto(String bodyPhotoKey)` — 사진 key 교체 + `updatedAt` 갱신.
- `mergeMeasurements(Short heightCm, Short weightKg, Short chest, Short waist, Short hip)` — **인자가 null이면 기존 값 유지**, non-null만 반영 + `updatedAt` 갱신.

`tryon_result`와 달리 `deleted_at` 컬럼이 스키마에 없다 — 이 프로필은 히스토리 개념이 없는 "현재 상태" 단일 로우라 **하드 삭제**로 간다.

### 3) 레포지토리 — `tryon/repository/MemberBodyProfileRepository.java`

`JpaRepository<MemberBodyProfile, Long>`. PK가 곧 `memberId`라 `findById(memberId)`가 그대로 "본인 프로필 조회"다.

### 4) DTO

- `TryOnProfileUploadUrlRequest(@NotBlank String contentType)` — `ProductImageUploadUrlRequest`의 `fileName`은 실제로 안 쓰이는 필드였으므로 이번엔 처음부터 뺀다.
- `TryOnProfileUploadUrlResponse(String key, String uploadUrl, long expiresInSeconds)` — product 패턴 그대로.
- `TryOnProfileUpdateRequest(String bodyPhotoKey, Short heightCm, Short weightKg, Short chest, Short waist, Short hip)` — 전부 nullable, JSON body. 값이 있을 때만 `@Positive`로 0 이하만 막고, 상한은 두지 않는다(과도한 정책 판단은 범위 밖).
- `TryOnProfileResponse(String bodyPhotoUrl, Short heightCm, Short weightKg, Short chest, Short waist, Short hip, LocalDateTime updatedAt)` — `bodyPhotoUrl`은 조회 시점에 발급하는 presigned GET URL, 사진 없으면 `null`.

### 5) 서비스 — `tryon/service/TryOnProfileService.java`

`TryOnResultService`/`ProductImageService`와 동일 스타일(`@Transactional(readOnly=true)` 클래스 + 쓰기 메서드에 `@Transactional`).

- `createUploadUrl(memberId, request)`: content-type 검증(jpeg/png/webp, 실패 시 `INVALID_IMAGE_TYPE` P006 재사용) → key `"tryon-profiles/%d/%s.%s".formatted(memberId, UUID.randomUUID(), extension)` → `privateBucket`에 `s3StorageService.createUploadUrl()`. DB 접근 없음(로우가 없어도 URL 발급은 가능해야 "사진부터 먼저 올리기" 흐름이 자연스럽다).
- `getProfile(memberId)`: 없으면 `TRYON_PROFILE_NOT_FOUND`(T001, 기존 코드 재사용). 있으면 `bodyPhotoKey` non-null일 때만 presigned GET URL 발급.
- `upsertProfile(memberId, request)`: 없으면 `memberRepository.findById`로 `Member` 조회 후 새 프로필 생성. `bodyPhotoKey`가 요청에 있고 기존 값과 다르면 `verifyUploaded`(`ProductImageService`와 동일한 `headObject` + 10MB 상한 검증, 실패 시 신규 `T005`) → 통과하면 **기존 사진이 있었으면 먼저 S3에서 삭제**(orphan 방지) → `updatePhoto`. 이어서 `mergeMeasurements` 항상 호출(부분 병합). `save` 후 응답.
- `deleteProfile(memberId)`: 없으면 `T001`. 사진 있으면 S3 삭제 후 로우 하드 삭제.

### 6) 컨트롤러 — `tryon/controller/TryOnProfileController.java`

`@RequestMapping("/api/users/{userId}/tryon")`. `TryOnController`와 동일한 `requireSelf` 패턴(principal ≠ path userId면 즉시 403, 존재 자체를 안 드러냄) — 에러 코드는 프로필 전용 신규 코드(아래 참고).

- `POST /upload-url` → 200
- `GET` → 200 / 404
- `PUT` → 200(생성·수정 겸용 upsert)
- `DELETE` → 204 / 404

### 7) `ErrorCode` 추가 (T 구역)

```java
TRYON_PROFILE_UPLOAD_NOT_CONFIRMED(HttpStatus.BAD_REQUEST, "T005", "업로드가 확인되지 않았습니다. 먼저 사진을 업로드해주세요."),
TRYON_PROFILE_NOT_OWNER(HttpStatus.FORBIDDEN, "T006", "본인의 시착 프로필만 처리할 수 있습니다."),
```

`member`/`users` 패키지는 본인 확인에 공용 `MEMBER_FORBIDDEN`(U013)을 쓰지만, `tryon` 패키지는 이미 결과(복수형) 쪽에서 `TRYON_RESULT_NOT_OWNER`(T004)로 리소스별 전용 코드를 파는 선례가 있다. 같은 패키지 내부 일관성을 우선해 `T006`을 새로 판다. 업로드 미확인도 같은 논리로 product의 `P007`을 재사용하지 않고 `T005`를 새로 판다.

### 8) `OnboardingRequiredFilter` 화이트리스트 수정 (필수)

`AntPathMatcher`의 `*`는 한 세그먼트만 매칭해 기존 `/api/users/*`는 `/api/users/{id}/tryon`에 안 걸린다(`/api/users/*/interests`가 세그먼트를 명시한 것과 같은 이유). 온보딩 미완료 회원도 이 API를 호출해야 하므로(온보딩 절차 자체) 반드시 고쳐야 한다.

```java
// 제거: new WhitelistEntry(null, "/api/me/tryon"),  ← 죽은 항목(실제 경로 아님)
// 추가:
new WhitelistEntry(null, "/api/users/*/tryon"),
new WhitelistEntry(null, "/api/users/*/tryon/upload-url"),
```

### 9) FE 계약 변경 요청 문서 — `docs/requests/FE/009-tryon-profile-presigned-upload.md` (신규)

`docs/requests/FE/001-product-image-presigned-upload.md`와 동일 형식(배경/이유, 요청 내용에 API 스펙 4단계 + 에러코드 표, 관련 자료, 처리 결과는 비워둠).

- `POST /api/users/{userId}/tryon/upload-url` → `{ key, uploadUrl, expiresInSeconds }`
- S3 직접 PUT (상품 이미지와 동일)
- `PUT /api/users/{userId}/tryon` — `{ bodyPhotoKey?, heightCm?, weightKg?, chest?, waist?, hip? }`(전부 선택, 보낸 필드만 반영) → 저장된 프로필 전체 반환
- `GET`/`DELETE /api/users/{userId}/tryon` — `GET`은 미등록 시 404(`T001`)가 정상 흐름임을 명시(FE는 에러 토스트가 아니라 빈 폼으로 처리)
- 에러코드: `P006`(이미지 형식), `T001`(프로필 없음), `T005`(업로드 미확인), `T006`(본인 아님)

### 10) 기존 FE 요청 문서 갱신

- `docs/requests/BE/002-onboarding-contract.md` §3.3, `docs/requests/BE/007-live-tryon-contract.md` §3.4를 같은 문서의 §3.1/3.2/3.4가 이미 쓴 톤("구현 완료, 계약은 다르게 확정됨" + 새 문서 링크)으로 갱신.

### 11) 테스트 — `TryOnProfileServiceTest` (Mockito 단위, `TryOnResultServiceTest` 스타일)

업로드 URL 발급(private 버킷 presigned PUT) / 지원하지 않는 이미지 타입 예외 / 프로필 없음 조회 시 404 / 사진 없이 신체 치수만으로 최초 등록 / **기존 프로필에 일부 필드만 보내면 나머지 값 유지**(핵심 케이스) / 사진 교체 시 기존 S3 객체 삭제 후 신규 key로 교체 / 업로드 미확인 key 거부 / 삭제 시 S3 삭제 + 하드 삭제 / 없는 프로필 삭제 시 404.

컨트롤러는 `TryOnController`처럼 별도 컨트롤러 테스트 없이 서비스 테스트로 충분(기존 관행).

### 12) `BE/README.md` 디렉터리 구조 갱신

`tryon/` 항목 주석에 프로필을 포괄하도록 수정, `entity/` 줄에 `MemberBodyProfile` 추가.

## 구현 목록

- [x] `BE/docs/db/schema.sql`(+`comments.sql`) — `member_body_profile.body_photo_url` → `body_photo_key`, `chest_cm`/`waist_cm`/`hip_cm` 추가
- [x] `regen.sh` 재실행 — `data-dictionary.md` 갱신(`erd.md`는 컬럼 단위 상세가 없는 관계도라 변경 불필요, `export-erd.sh` 재실행 불필요)
- [x] `tryon/entity/MemberBodyProfile.java`
- [x] `tryon/repository/MemberBodyProfileRepository.java`
- [x] `tryon/dto/request/TryOnProfileUploadUrlRequest.java`, `TryOnProfileUpdateRequest.java`
- [x] `tryon/dto/response/TryOnProfileUploadUrlResponse.java`, `TryOnProfileResponse.java`
- [x] `tryon/service/TryOnProfileService.java`
- [x] `tryon/controller/TryOnProfileController.java` (Swagger 포함)
- [x] `ErrorCode`에 `T005`, `T006` 추가
- [x] `OnboardingRequiredFilter` 화이트리스트 수정
- [x] `docs/requests/FE/009-tryon-profile-presigned-upload.md` 신규 작성
- [x] `docs/requests/BE/002-onboarding-contract.md` §3.3, `007-live-tryon-contract.md` §3.4 갱신(+ `012-be-request-index.md` 인덱스 갱신)
- [x] `TryOnProfileServiceTest` (10건: 업로드URL발급, 지원안하는타입, 프로필없음404, 최초등록, 부분병합, 사진교체, 업로드미확인, 삭제, 사진없이삭제, 없는프로필삭제404)
- [x] `BE/README.md` 갱신
- [x] `.claude/skills/BE:verify` 기준 `./gradlew build` 통과 확인 (`BUILD SUCCESSFUL`, 전체 301건 테스트 green, 신규 10건 포함)

## 확인 필요한 미결정 사항

- 신체 치수 상한값(예: 300cm/500kg 등)을 둘지 — 이번엔 `@Positive`(0 이하 방지)만 걸고 상한은 안 둠.
- 시착 프로필 사진도 상품 이미지와 동일한 10MB 상한을 그대로 적용 — 전신 사진이라 더 큰 상한이 필요하면 조정.

## 검증 방법

1. `.claude/skills/BE:verify` 기준 `./gradlew build`(CI `be-test`와 동일) 통과 확인.
2. 로컬 Postgres/Redis/MinIO 기동 후 실제 API 호출로 흐름 검증: `POST .../tryon/upload-url` → S3(MinIO)로 PUT → `PUT .../tryon`(치수만) → `GET`으로 값 확인 → 재차 `PUT`(사진 key만) → 기존 치수 유지되는지 확인 → `DELETE` → `GET` 시 404 확인.
3. `OnboardingRequiredFilter` 화이트리스트 반영 확인: 온보딩 미완료(`onboardingCompleted=false`) 신규 회원 토큰으로 위 흐름이 `ONBOARDING_REQUIRED`(403) 없이 통과하는지 확인.
4. `TryOnProfileServiceTest` 전체 통과 확인.

### 실제 검증 완료 (2026-08-02)

로컬 `bootRun` + Postgres/MinIO로 1~4 전부 실제 API 호출로 검증했다(온보딩 미완료 회원 계정으로 진행).

- `GET`(미등록) → 404 `T001`, `ONBOARDING_REQUIRED`에 안 걸림(화이트리스트 정상)
- `POST /upload-url` → key/uploadUrl 발급 → MinIO에 실제 PUT 성공
- `PUT`(사진 key + heightCm/weightKg) → 200, presigned GET URL 포함해 정상 저장
- `GET` 재조회 → 저장값 일치
- `PUT`(chest만) → heightCm/weightKg 유지, chest만 추가됨(부분 병합 확인)
- `DELETE` → 204 → `GET` 재조회 → 404 `T001`
- 삭제 후 MinIO(`mc ls`)·DB(`SELECT`) 양쪽에서 실제로 지워졌음을 확인(하드 삭제)
- 본인 아닌 `userId`로 접근 시 403 `T006` 확인(IDOR 방지)
- 검증용 계정(`member.id=535`)은 정리 완료

검증 중 **이번 작업과 무관한 기존 이슈**를 하나 발견: 로컬 부팅 로그에 `member.member_type`/`member.status` 컬럼의 Hibernate DDL(`ALTER COLUMN ... SET DATA TYPE ... DEFAULT ...`)이 Postgres 문법 오류(`syntax error at or near "DEFAULT"`)로 실패하는 로그가 있다. 이미 컬럼이 존재하는 상태에서 재기동 시 매번 뜨는 것으로 보이고 부팅 자체는 막지 않지만, `member_body_profile`과는 무관한 기존 이슈라 별도로 확인이 필요하다.
