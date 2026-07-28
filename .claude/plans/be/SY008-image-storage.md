# SY008 — 상품 이미지 · 시착 결과 이미지 S3 저장

## Context

`product_image` 테이블은 스키마에만 정의되어 있고 엔티티/API가 없다 (`SY004`~`SY006` 계획에서 "별도 계획으로 진행"이라 명시하며 반복적으로 범위 제외됨). `comments.sql`은 현재 `product_image.image_url`을 "S3 미제공이라 EC2 로컬 볼륨 기준(저장 방식 미확정)"이라 적어두고 있어, 저장 방식 결정이 이 계획의 목적이다. 시착 결과(`tryon_result`)는 테이블조차 없는 완전 신규 영역이다.

사용자와 논의 후 결정된 방향:
- **상품 이미지**(공개, 판매자가 최대 10장 업로드): presigned URL로 **브라우저가 S3에 직접 업로드**. FE가 아직 이 부분을 구현하지 않아 계약을 자유롭게 정의할 수 있고, 여러 장을 병렬 업로드할 수 있어 백엔드 대역폭 부담이 없다는 이점이 실익으로 작동한다.
- **시착 결과 이미지**(비공개, 본인만 조회): AI가 생성한 이미지이므로 브라우저 업로드 경로가 없다. private 버킷에 저장하고 **조회 시 presigned GET URL**을 매번 발급해 소유자만 볼 수 있게 한다.
- **시착 프로필 사진**(`member_body_profile.body_photo_url`, 시착 입력값)은 이번 계획 범위 밖이다 — 이미 `.codex/requests/be/003`에 별도 요청이 있고 사용자 원 요청("상품 이미지, 시착 결과 이미지")에도 포함되지 않는다.
- **시착 생성(`POST .../tryons`)**은 AI 쪽에 이미지 합성 엔드포인트 자체가 없어(현재 `/health`만 존재) 이번 계획 범위에서 제외한다. AI에 계약을 제안하는 요청 문서만 작성하고, 생성 API는 후속 계획으로 미룬다. 이번 계획은 시착 결과의 **저장/조회/삭제**만 구현한다(BE가 이미지를 이미 갖고 있다고 가정).

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
  - `DELETE /api/products/{id}/images/{imageId}` — DB row + S3 객체 삭제
- `ProductDetailResponse`에 `images: List<ProductImageResponse>`(`id`, `url`, `sortOrder`, `isPrimary`) 필드 추가 — 별도 목록 조회 엔드포인트 없이 상세 조회에 포함(기존 `GET /api/products/{id}`는 이미 공개 엔드포인트라 별도 permitAll 설정 불필요).
- 신규 `ErrorCode`(P 구역 이어서 추가): `P004 PRODUCT_IMAGE_NOT_FOUND`, `P005 PRODUCT_IMAGE_LIMIT_EXCEEDED`, `P006 INVALID_IMAGE_TYPE`, `P007 PRODUCT_IMAGE_UPLOAD_NOT_CONFIRMED`(HeadObject 실패).
- 업로드/확인/삭제 엔드포인트는 `SecurityConfig` 기본값(`anyRequest().authenticated()`)에 이미 포함되므로 `PUBLIC_ENDPOINTS` 변경 불필요.

## 시착 결과 이미지 (신규 `tryon` 도메인)

- 신규 테이블 `tryon_result`(`schema.sql`/`comments.sql` 추가): `id`, `member_id`(FK), `product_id`(FK), `image_key`, `created_at`, `deleted_at`. 다중 아이템 합성("빈티지 코디") 등은 이번 범위 제외, 상품 1개 기준 단일 합성 결과만 다룬다.
- `TryOnResult` 엔티티 / `TryOnResultRepository`.
- 신규 `TryOnController`(`/api/me/tryons` — 경로에 `{id}` 없이 인증된 본인 기준. `APIs.md` 초안은 `/users/{id}/tryons`였지만, 시착 결과는 본인만 볼 수 있는 리소스라 path id와 principal 비교하는 IDOR 여지를 원천적으로 없애기 위해 `/api/me/tryons`로 결정 — 승인되면 `APIs.md`에도 반영):
  - `GET /api/me/tryons` — 목록, 각 항목에 presigned GET URL 포함
  - `GET /api/me/tryons/{id}` — 상세, presigned GET URL
  - `DELETE /api/me/tryons/{id}` — DB row + S3 객체 삭제
  - (생성 `POST /api/me/tryons`는 제외 — 아래 "AI 요청 문서" 참고)
- 신규 `ErrorCode`(T 구역 이어서 추가): `T003 TRYON_RESULT_NOT_FOUND`, `T004 TRYON_RESULT_NOT_OWNER`.
- 서비스: `TryOnResultService.saveResult(memberId, productId, imageBytes)`처럼 "이미 생성된 이미지를 저장하는" 메서드까지만 구현. 실제 AI 호출/합성 트리거는 후속 계획.

## 팀 간 요청 문서 (이번 계획에 포함되는 산출물)

- `.claude/requests/fe/001-product-image-presigned-upload.md`: 상품 이미지 2단계 업로드 흐름(업로드 URL 요청 → S3 직접 PUT → 등록 확인 호출) 계약 안내. FE가 아직 미구현이라 이번에 새로 합의.
- `.claude/requests/ai/001-tryon-result-contract.md`: 시착 합성 결과를 AI→BE로 어떻게 전달할지 제안 (AI가 이미지 바이트를 동기 응답으로 반환하고 BE가 S3 업로드까지 담당 — AI에 별도 AWS 자격증명을 주지 않기 위함, "Spring은 FastAPI만 바라본다" 원칙과도 일치). 확정은 AI 팀 몫.

## 구현 목록

- [ ] `build.gradle`: `software.amazon.awssdk:s3` 추가
- [ ] `docs/db/schema.sql`, `comments.sql`: `product_image.image_url` → `image_key` 컬럼명 변경 + 코멘트 갱신, `tryon_result` 테이블 신규 추가 + 코멘트
- [ ] `regen.sh`/`export-erd.sh` 재실행 (data-dictionary.md, ERD 갱신)
- [ ] `global/config/S3Config` (`S3Client`, `S3Presigner` 빈, local endpoint override)
- [ ] `global/config`(또는 유사 위치)에 `S3StorageService` (presigned PUT/GET, HeadObject 검증, delete, public URL 조립)
- [ ] `docker-compose.override.yml`: `minio` 서비스 추가
- [ ] `LocalS3BucketInitializer` (`@Profile("local")` `ApplicationRunner`): 버킷 생성 + public 버킷 익명 읽기 정책
- [ ] `application.yml`/`application-local.yml`/`application-prod.yml`: `aws.*` 설정 추가
- [ ] `infra/ci/deploy.sh`, GitLab CI/CD Variables: AWS 자격증명/버킷명 prod 반영
- [ ] `ProductImage` 엔티티 / `ProductImageRepository`
- [ ] `ProductService`(또는 신규 `ProductImageService`): upload-url 발급, 등록(HeadObject 검증 + 개수 제한), 삭제
- [ ] `ProductController`: `POST /{id}/images/upload-url`, `POST /{id}/images`, `DELETE /{id}/images/{imageId}` (Swagger 포함)
- [ ] `ProductDetailResponse`에 `images` 필드 추가
- [ ] `ErrorCode`: P004~P007 추가
- [ ] `TryOnResult` 엔티티 / `TryOnResultRepository`
- [ ] `TryOnResultService`: 목록/상세(presigned GET 발급)/삭제/`saveResult(...)`
- [ ] `TryOnController`(`/api/me/tryons`): GET 목록, GET 상세, DELETE (Swagger 포함)
- [ ] `ErrorCode`: T003~T004 추가
- [ ] `.claude/requests/fe/001-product-image-presigned-upload.md` 작성
- [ ] `.claude/requests/ai/001-tryon-result-contract.md` 작성
- [ ] `ProductImageServiceTest`, `TryOnResultServiceTest` (Mockito, `S3StorageService` 목 처리 — 기존 서비스 테스트 컨벤션과 동일)
- [ ] `.claude/skills/verify`(BE) 기준 빌드/테스트 통과 확인
- [ ] (인프라, 코드 범위 아님) prod S3 버킷 생성 + public 버킷 정책 콘솔에서 수동 설정

## 확인이 필요한 미결정 사항

- `/api/me/tryons` 경로가 `APIs.md`의 `/users/{id}/tryons` 초안과 다르다 — 승인되면 `APIs.md` 갱신 필요.
- 시착 결과 보관 기간/삭제 정책(예: N일 후 자동 삭제)은 정해진 바 없어 이번 범위에서는 사용자가 수동 삭제하는 것만 지원한다.
- AI 쪽 시착 생성 계약(요청 문서로 제안만) 및 실제 `POST /api/me/tryons` 생성 API는 AI 응답 후 별도 계획(SY009 예정)으로 진행.

## 검증

- `.claude/skills/BE:verify`로 CI와 동일한 빌드/테스트 실행.
- 로컬에서 `docker compose up -d postgres redis minio` 후 애플리케이션 기동 → Swagger UI로 상품 이미지 upload-url 발급 → 실제 presigned URL에 `curl -T`로 이미지 PUT → confirm 호출 → `GET /api/products/{id}`에 `images` 포함 확인. 시착 결과는 `TryOnResultService.saveResult`를 테스트 코드/임시 컨트롤러 없이 서비스 테스트로만 검증(생성 API가 없으므로 E2E 업로드 확인은 후속 계획에서)

## 참고: 배포 환경 CORS/HTTPS 버그 수정

- 원인 1: Caddy가 TLS를 종단하고 backend엔 평문 HTTP로 넘기는데 `server.forward-headers-strategy`가 없어, Spring이 요청을 http로 인식 → springdoc이 Swagger 서버 URL을 `http://`로 생성 → https로 열린 Swagger UI의 "Execute"가 스킴이 다른(교차 출처) 요청이 되어 CORS/mixed-content로 막힘.
- 원인 2: 직전 CORS 설정 커밋(`e12c1c5`)이 `CORS_ALLOWED_ORIGINS` 프로퍼티를 코드에는 추가했지만 `docker-compose.yml`의 backend `environment:`와 `infra/ci/deploy.sh`의 `.env` 생성부에는 배선하지 않아, 운영에서 항상 기본값(`http://localhost:5173`)만 쓰이고 있었음.
- 수정: `BE/src/main/resources/application.yml`에 `server.forward-headers-strategy: framework` 추가, `docker-compose.yml` backend 환경변수에 `CORS_ALLOWED_ORIGINS` 추가, `infra/ci/deploy.sh` `.env` heredoc에 `CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS}` 추가, `.gitlab-ci.yml`에 필요한 CI/CD Variable로 문서화.
- 커밋: `[S15P11A108-310] fix: 배포 환경 CORS/HTTPS 스킴 인식 문제 수정`
- **남은 수동 작업**: GitLab 프로젝트 Settings → CI/CD → Variables에 `CORS_ALLOWED_ORIGINS`(실제 FE 배포 origin) 추가 필요. 미설정 시 `deploy.sh`가 `set -u`로 다음 배포에서 즉시 실패함(의도된 동작).