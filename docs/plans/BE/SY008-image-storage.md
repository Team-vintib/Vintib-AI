# SY008 — 상품 이미지 · 시착 결과 이미지 S3 저장

## Context

`product_image` 테이블은 스키마에만 정의되어 있고 엔티티/API가 없다 (`SY004`~`SY006` 계획에서 "별도 계획으로 진행"이라 명시하며 반복적으로 범위 제외됨). `comments.sql`은 현재 `product_image.image_url`을 "S3 미제공이라 EC2 로컬 볼륨 기준(저장 방식 미확정)"이라 적어두고 있어, 저장 방식 결정이 이 계획의 목적이다. 시착 결과(`tryon_result`)는 테이블조차 없는 완전 신규 영역이다.

사용자와 논의 후 결정된 방향:
- **상품 이미지**(공개, 판매자가 최대 10장 업로드): presigned URL로 **브라우저가 S3에 직접 업로드**. FE가 아직 이 부분을 구현하지 않아 계약을 자유롭게 정의할 수 있고, 여러 장을 병렬 업로드할 수 있어 백엔드 대역폭 부담이 없다는 이점이 실익으로 작동한다.
- **시착 결과 이미지**(비공개, 본인만 조회): AI가 생성한 이미지이므로 브라우저 업로드 경로가 없다. private 버킷에 저장하고 **조회 시 presigned GET URL**을 매번 발급해 소유자만 볼 수 있게 한다.
- **시착 프로필 사진**(`member_body_profile.body_photo_url`, 시착 입력값)은 이번 계획 범위 밖이다 — 이미 `.codex/requests/be/003`에 별도 요청이 있고 사용자 원 요청("상품 이미지, 시착 결과 이미지")에도 포함되지 않는다.
- **시착 생성(`POST .../tryons`)**은 AI 쪽에 이미지 합성 엔드포인트 자체가 없어(현재 `/health`만 존재) 이번 계획 범위에서 제외한다. AI에 계약을 제안하는 요청 문서만 작성하고, 생성 API는 후속 계획으로 미룬다. 이번 계획은 시착 결과의 **저장/조회/삭제**만 구현한다(BE가 이미지를 이미 갖고 있다고 가정).

> [!IMPORTANT]
> **운영 스토리지는 실제 AWS S3가 아니다.** 이 계획은 prod = AWS S3를 전제했으나, 팀에 AWS 계정이 없어(SSAFY 제공 EC2 한 대, 웹 콘솔 없음) 버킷·IAM을 만들 방법 자체가 없었다. `JY006`에서 운영도 EC2 안의 자체 호스팅 MinIO로 확정했다. 아래 "공용 S3 인프라" 절의 서술 중 prod 관련 부분(AWS 콘솔 수동 설정, AWS 자격증명)은 `JY006`으로 대체됐다 — 애플리케이션 코드는 S3 호환 API만 쓰므로 그대로 유효하다.

## 공용 S3 인프라

- 버킷 2개: public(상품 이미지) / private(시착 결과). 버킷명·리전은 프로필별 env(`AWS_S3_PUBLIC_BUCKET`, `AWS_S3_PRIVATE_BUCKET`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, local 전용 `AWS_S3_ENDPOINT`)로 주입, `application.yml`에 `${..}` 기본값 패턴(기존 `ai.base-url`, `cors.allowed-origins`와 동일 스타일).
- 의존성 추가: `software.amazon.awssdk:s3` (SDK v2). 현재 `build.gradle`에 AWS 관련 의존성 전혀 없음(확인 완료).
- `global/config`에 `S3Config`(`S3Client`, `S3Presigner` 빈, local 프로필은 `endpointOverride`로 MinIO를 바라봄) + `S3StorageService`(재사용 컴포넌트, product/tryon 양쪽에서 씀):
  - presigned PUT URL 발급(업로드용, 5분 만료)
  - 업로드 완료 확인용 `HeadObject`(존재/실제 크기·Content-Type 검증 — presigned PUT 자체는 최대 용량을 강제할 수 없으므로 confirm 시점에 사후 검증하고, 기준 초과 시 객체 삭제 후 에러 처리)
  - `DeleteObject`
  - public 버킷 고정 URL 조립
  - private 버킷 presigned GET URL 발급(짧은 만료, 예: 5~10분)
- 로컬 개발: `docker-compose.override.yml`에 `minio` 서비스 추가(9000/9001 포트, `MINIO_ROOT_USER/PASSWORD`). `local` 프로필 전용 `ApplicationRunner`(`LocalS3BucketInitializer`, 기존 `CategoryBrandSeeder` 패턴과 동일)가 기동 시 버킷 존재 확인 후 없으면 생성 + public 버킷에 익명 읽기 정책 적용. prod 버킷/정책은 AWS 콘솔에서 1회성 수동 설정(코드 범위 아님, 체크리스트에 별도 표기).
- prod 자격증명: 기존 `PROD_DB_PASSWORD`와 동일하게 GitLab CI/CD Variables → `infra/ci/deploy.sh`의 `.env` heredoc에 `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_REGION`/버킷명 추가.
- 파일 검증 정책: 허용 Content-Type `image/jpeg`, `image/png`, `image/webp`만. 최대 10MB(고정값, `@ConfigurationProperties` 불필요할 만큼 단순). 상품 이미지 최대 10장(FE 문서 기준 기존 합의값).

## 상품 이미지 (`product` 도메인, 기존 `product_image` 테이블 재사용)

- 스키마: `product_image.image_url` → `image_key`로 컬럼명 변경(전체 URL이 아니라 S3 key만 저장하는 것으로 의미 확정). `comments.sql` 코멘트를 S3 기준으로 갱신. (`application-prod.yml`이 MVP 단계라 `ddl-auto: create`로 매 기동 시 스키마 재생성되므로 마이그레이션 없이 안전하게 컬럼명 변경 가능.)
- `ProductImage` 엔티티(`product_id` FK, `imageKey`, `sortOrder`, `isPrimary`) / `ProductImageRepository`.
- `ProductController`에 서브 리소스 엔드포인트 추가(모두 인증 필요, `product.isOwnedBy(sellerId)`로 소유자 검증 후 `NOT_PRODUCT_OWNER` 재사용):
  - `POST /api/products/{id}/images/upload-url` — `{fileName, contentType}` → presigned PUT URL + key 발급 (파일 1개당 1회 호출, FE가 최대 10회 반복)
  - `POST /api/products/{id}/images` — `{key, sortOrder, isPrimary}` → S3 `HeadObject` 검증 후 `ProductImage` row 생성, 총 개수 10장 제한
  - `PATCH /api/products/{id}/images/{imageId}` — `{sortOrder?, isPrimary?}` 부분 수정(추가 구현, 사용자 요청). `isPrimary: true` 시 `ProductImageRepository.clearPrimaryExcept(productId, imageId)`로 같은 상품의 다른 이미지를 먼저 대표 해제 — 대표 이미지는 상품당 항상 최대 1장. 같은 규칙을 `registerImage`(`clearPrimary`)에도 적용해 등록 시점부터 일관되게 함.
  - `DELETE /api/products/{id}/images/{imageId}` — DB row + S3 객체 삭제
- `ProductDetailResponse`에 `images: List<ProductImageResponse>`(`id`, `url`, `sortOrder`, `isPrimary`) 필드 추가 — 별도 목록 조회 엔드포인트 없이 상세 조회에 포함(기존 `GET /api/products/{id}`는 이미 공개 엔드포인트라 별도 permitAll 설정 불필요).
- 신규 `ErrorCode`(P 구역 이어서 추가): `P004 PRODUCT_IMAGE_NOT_FOUND`, `P005 PRODUCT_IMAGE_LIMIT_EXCEEDED`, `P006 INVALID_IMAGE_TYPE`, `P007 PRODUCT_IMAGE_UPLOAD_NOT_CONFIRMED`(HeadObject 실패).
- 업로드/확인/삭제 엔드포인트는 `SecurityConfig` 기본값(`anyRequest().authenticated()`)에 이미 포함되므로 `PUBLIC_ENDPOINTS` 변경 불필요.

## 시착 결과 이미지 (신규 `tryon` 도메인)

- 신규 테이블 `tryon_result`(`schema.sql`/`comments.sql` 추가): `id`, `member_id`(FK), `product_id`(FK), `image_key`, `created_at`, `deleted_at`. 다중 아이템 합성("빈티지 코디") 등은 이번 범위 제외, 상품 1개 기준 단일 합성 결과만 다룬다.
- `TryOnResult` 엔티티 / `TryOnResultRepository`.
- 신규 `TryOnController`(`APIs.md`의 `/users/{id}/tryons` 스펙을 그대로 따름 — 처음엔 IDOR 우려로 `/api/me/tryons`(본인 기준, path id 없음)로 구현했다가, 사용자 지시로 공유 계약 문서인 `APIs.md`에 맞춰 되돌림. IDOR은 경로 대신 컨트롤러에서 `path userId == 인증된 principal` 체크로 막는다 — 불일치 시 `T004`):
  - `GET /api/users/{userId}/tryons` — 목록, 각 항목에 presigned GET URL 포함
  - `GET /api/users/{userId}/tryons/{id}` — 상세, presigned GET URL
  - `DELETE /api/users/{userId}/tryons/{id}` — DB row + S3 객체 삭제
  - (생성 `POST /api/users/{userId}/tryons`는 제외 — 아래 "AI 요청 문서" 참고)
- 신규 `ErrorCode`(T 구역 이어서 추가): `T003 TRYON_RESULT_NOT_FOUND`, `T004 TRYON_RESULT_NOT_OWNER`.
- 서비스: `TryOnResultService.saveResult(memberId, productId, imageBytes)`처럼 "이미 생성된 이미지를 저장하는" 메서드까지만 구현. 실제 AI 호출/합성 트리거는 후속 계획.

## 팀 간 요청 문서 (이번 계획에 포함되는 산출물)

- `.claude/requests/fe/001-product-image-presigned-upload.md`: 상품 이미지 2단계 업로드 흐름(업로드 URL 요청 → S3 직접 PUT → 등록 확인 호출) 계약 안내. FE가 아직 미구현이라 이번에 새로 합의.
- `.claude/requests/ai/001-tryon-result-contract.md`: 시착 합성 결과를 AI→BE로 어떻게 전달할지 제안 (AI가 이미지 바이트를 동기 응답으로 반환하고 BE가 S3 업로드까지 담당 — AI에 별도 AWS 자격증명을 주지 않기 위함, "Spring은 FastAPI만 바라본다" 원칙과도 일치). 확정은 AI 팀 몫.

## 구현 목록

- [x] `build.gradle`: `software.amazon.awssdk:s3` 추가
- [x] `docs/db/schema.sql`, `comments.sql`: `product_image.image_url` → `image_key` 컬럼명 변경 + 코멘트 갱신, `tryon_result` 테이블 신규 추가 + 코멘트
- [x] `regen.sh`/`export-erd.sh` 재실행 (data-dictionary.md, ERD 갱신)
- [x] `global/config/S3Config` (`S3Client`, `S3Presigner` 빈, local endpoint override) — `aws.s3.endpoint`(백엔드 내부용)와 `aws.s3.public-endpoint`(presigned URL용) 분리 (아래 "구현 중 발견/수정한 버그" 참고)
- [x] `global/storage/S3StorageService` (presigned PUT/GET, HeadObject 검증, delete, public URL 조립)
- [x] `docker-compose.override.yml`: `minio` 서비스 추가
- [x] `global/storage/LocalS3BucketInitializer` (`@Profile("local")` `ApplicationRunner`): 버킷 생성 + public 버킷 익명 읽기 정책
- [x] `application.yml`/`application-local.yml`: `aws.*` 설정 추가
- [x] `infra/ci/deploy.sh`, `.gitlab-ci.yml`: AWS 자격증명/버킷명 prod 반영 (GitLab CI/CD Variables 등록은 아직 사용자 몫 — 아래 "남은 수동 작업" 참고)
- [x] `ProductImage` 엔티티 / `ProductImageRepository`
- [x] 신규 `ProductImageService`: upload-url 발급, 등록(HeadObject 검증 + 개수 제한), 삭제
- [x] `ProductController`: `POST /{id}/images/upload-url`, `POST /{id}/images`, `PATCH /{id}/images/{imageId}`, `DELETE /{id}/images/{imageId}` (Swagger 포함)
- [x] `ProductDetailResponse`에 `images` 필드 추가
- [x] `ErrorCode`: P004~P007 추가
- [x] `TryOnResult` 엔티티 / `TryOnResultRepository`
- [x] `TryOnResultService`: 목록/상세(presigned GET 발급)/삭제/`saveResult(...)`
- [x] `TryOnController`(`/api/users/{userId}/tryons`, `APIs.md` 스펙 그대로): GET 목록, GET 상세, DELETE (Swagger 포함)
- [x] `ErrorCode`: T003~T004 추가
- [x] `.claude/requests/fe/001-product-image-presigned-upload.md` 작성
- [x] `.claude/requests/ai/001-tryon-result-contract.md` 작성
- [x] `ProductImageServiceTest`, `TryOnResultServiceTest` (Mockito, `S3StorageService` 목 처리)
- [x] `.claude/skills/verify`(BE) 기준 빌드/테스트 통과 확인 — 61개 테스트 전체 통과
- [x] ~~(인프라, 코드 범위 아님) prod S3 버킷 생성 + public 버킷 정책 콘솔에서 수동 설정~~ → **`JY006`으로 대체.** 운영 스토리지를 자체 호스팅 MinIO로 바꾸면서 `S3BucketInitializer`가 기동 시 자동 생성하므로 수동 설정 항목이 사라졌다.
- [x] ~~GitLab CI/CD Variables에 `AWS_REGION`/`AWS_S3_PUBLIC_BUCKET`/`AWS_S3_PRIVATE_BUCKET`/`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` 등록~~ → **`JY006`으로 대체.** `PROD_MINIO_ROOT_USER`/`PROD_MINIO_ROOT_PASSWORD` 2개로 줄었다.

## 이미지 저장 플로우 (실제 구현된 요청/응답 형태)

**상품 이미지 업로드 (판매자, 최대 10장)**

1. `POST /api/products/{id}/images/upload-url` — body `{ fileName, contentType }` → 응답 `{ key, uploadUrl, expiresInSeconds }` (presigned PUT, 5분 만료). 이미지 1장당 1회 호출.
2. FE가 응답받은 `uploadUrl`에 파일 바이너리를 **직접 PUT**(S3/MinIO로, 백엔드 경유 없음). `Content-Type` 헤더를 1단계에서 보낸 값과 동일하게 맞춰야 한다.
3. `POST /api/products/{id}/images` — body `{ key, sortOrder, isPrimary }` → 서버가 `HeadObject`로 실제 업로드 여부·용량(10MB 이하)을 검증한 뒤 `ProductImage` row 생성. 검증 실패 시 `P006`(형식) / `P007`(업로드 미확인), 상품당 10장 초과 시 `P005`.
4. `PATCH /api/products/{id}/images/{imageId}` — body `{ sortOrder?, isPrimary? }`(부분 수정, 사진 재업로드 없음). `isPrimary: true`면 같은 상품의 다른 이미지를 서버가 자동으로 대표 해제.
5. `DELETE /api/products/{id}/images/{imageId}` — DB row + S3 객체를 함께 삭제.
6. `GET /api/products/{id}`(기존 상세 조회) 응답에 `images: [{ id, url, sortOrder, isPrimary }]`가 포함된다. `url`은 public 버킷 고정 URL(만료 없음, presigned 아님).

**시착 결과 조회 (본인 전용)**

- 생성 경로 없음(AI 계약 미정, 위 "시착 결과 이미지" 절 참고). `TryOnResultService.saveResult(memberId, productId, imageBytes)`가 이미지 바이트를 받아 private 버킷에 저장 + row 생성하는 지점까지만 구현되어 있고, 이걸 호출하는 컨트롤러/AI 연동은 후속 계획(SY009)에서 붙인다.
- `GET /api/users/{userId}/tryons` — 응답 `[{ id, productId, imageUrl, createdAt }]`, `imageUrl`은 조회 시점에 발급한 presigned GET URL(10분 만료). `userId`가 인증된 본인이 아니면 `T004`.
- `GET /api/users/{userId}/tryons/{id}` — 단건, 동일 형태. 본인 것이 아니면 `T004`, 없으면 `T003`.
- `DELETE /api/users/{userId}/tryons/{id}` — soft delete(`deleted_at`) + S3 객체 실제 삭제.

## 구현 중 발견/수정한 버그

- **(실제 버그) presigned/공개 URL이 도커 내부 호스트명으로 서명되던 문제**: 백엔드 컨테이너가 MinIO를 부르는 내부 주소(`minio:9000`)와, 브라우저·FE가 열어야 하는 주소(`localhost:9000`)가 다른데 endpoint를 하나로 같이 쓰고 있어 presigned URL이 브라우저에서 열리지 않았다. `aws.s3.endpoint`(백엔드 전용)와 `aws.s3.public-endpoint`(presigned/공개 URL 전용, 비어 있으면 `endpoint`로 폴백)로 분리해 해결. `S3Config`/`S3StorageService` 참고.
- (사소한 버그) `ProductImageService.createUploadUrl`이 key를 만들 때 파라미터로 받은 `productId` 대신 `product.getId()`를 써서 `registerImage`와 일관성이 어긋나 있던 것을 수정.
- 실제 컨테이너(Postgres/Redis/MinIO)로 상품 생성 → 업로드 URL 발급 → PUT → 등록 → 상세조회 노출 → 삭제(S3 객체 실제 삭제 확인) → 형식/미확인 오류 → 시착 목록/상세(presigned GET, 서명 없는 요청은 403, 타인 접근 403) → 삭제까지 수동 E2E로 확인.

## 확인이 필요한 미결정 사항

- 시착 결과 보관 기간/삭제 정책(예: N일 후 자동 삭제)은 정해진 바 없어 이번 범위에서는 사용자가 수동 삭제하는 것만 지원한다.
- AI 쪽 시착 생성 계약(요청 문서로 제안만) 및 실제 `POST /api/users/{userId}/tryons` 생성 API는 AI 응답 후 별도 계획(SY009 예정)으로 진행.

## 검증

- `.claude/skills/BE:verify`로 CI와 동일한 빌드/테스트 실행.
- 로컬에서 `docker compose up -d postgres redis minio` 후 애플리케이션 기동 → Swagger UI로 상품 이미지 upload-url 발급 → 실제 presigned URL에 `curl -T`로 이미지 PUT → confirm 호출 → `GET /api/products/{id}`에 `images` 포함 확인. 시착 결과는 `TryOnResultService.saveResult`를 테스트 코드/임시 컨트롤러 없이 서비스 테스트로만 검증(생성 API가 없으므로 E2E 업로드 확인은 후속 계획에서)

## 참고: 배포 환경 CORS/HTTPS 버그 수정

- 원인 1: Caddy가 TLS를 종단하고 backend엔 평문 HTTP로 넘기는데 `server.forward-headers-strategy`가 없어, Spring이 요청을 http로 인식 → springdoc이 Swagger 서버 URL을 `http://`로 생성 → https로 열린 Swagger UI의 "Execute"가 스킴이 다른(교차 출처) 요청이 되어 CORS/mixed-content로 막힘.
- 원인 2: 직전 CORS 설정 커밋(`e12c1c5`)이 `CORS_ALLOWED_ORIGINS` 프로퍼티를 코드에는 추가했지만 `docker-compose.yml`의 backend `environment:`와 `infra/ci/deploy.sh`의 `.env` 생성부에는 배선하지 않아, 운영에서 항상 기본값(`http://localhost:5173`)만 쓰이고 있었음.
- 수정: `BE/src/main/resources/application.yml`에 `server.forward-headers-strategy: framework` 추가, `docker-compose.yml` backend 환경변수에 `CORS_ALLOWED_ORIGINS` 추가, `infra/ci/deploy.sh` `.env` heredoc에 `CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS}` 추가, `.gitlab-ci.yml`에 필요한 CI/CD Variable로 문서화.
- 커밋: `[S15P11A108-310] fix: 배포 환경 CORS/HTTPS 스킴 인식 문제 수정`
- **남은 수동 작업**: GitLab 프로젝트 Settings → CI/CD → Variables에 `CORS_ALLOWED_ORIGINS`(실제 FE 배포 origin) 추가 필요. 미설정 시 `deploy.sh`가 `set -u`로 다음 배포에서 즉시 실패함(의도된 동작).