# 운영 오브젝트 스토리지 자체 호스팅 (MinIO)

## 배경/목표

`SY008`은 운영 이미지 저장소로 실제 AWS S3를 전제하고 구현됐다. 그러나 SSAFY가 제공하는 건 EC2 한 대(SSH만, 웹 콘솔 없음)뿐이고 팀에 AWS 계정이 없다 — 버킷·IAM을 만들 방법 자체가 없다. `SY008` 체크리스트의 미완 항목 2개(prod 버킷 생성, CI/CD Variables 등록)가 여기서 막힌다.

애플리케이션 코드는 S3 호환 API(SDK v2)만 쓰고 로컬 개발에서 이미 MinIO로 동작 중이므로, **운영도 EC2 안의 MinIO로 돌린다.** 도메인 로직 변경은 없고 인프라 배선만 바꾼다.

## 작업 내용

### MinIO를 운영 서비스로 승격

- 현재 `minio`는 로컬 전용인 `docker-compose.override.yml`에만 있다. 서비스 정의를 base(`docker-compose.yml`)로 옮기고, **호스트 포트 발행(9000/9001)은 override에 남긴다.**
- 운영에서는 어떤 호스트 포트도 열지 않는다. `vintib-net` 내부에서 `minio:9000`으로만 접근하고 외부 노출은 Caddy가 전담한다 — UFW를 건드리지 않는다는 기존 원칙(`docker-compose.prod.yml` 주석) 그대로.
- `docker-compose.prod.yml`에 logging·`mem_limit`을 다른 서비스와 같은 형식으로 추가. `backend`는 `minio` healthy 이후 기동(`depends_on`, 기존 override와 동일).
- 데이터는 named volume `minio-data`에 남는다. compose 교체 배포로는 지워지지 않는다.

### Caddy 라우팅

- `S3Config`는 endpoint가 설정되면 **path-style**을 강제하므로 공개/presigned URL은 `{publicEndpoint}/{bucket}/{key}` 형태가 된다. `AWS_S3_PUBLIC_ENDPOINT=https://i15a108.p.ssafy.io`로 두면 `https://i15a108.p.ssafy.io/vintib-public/product-images/...`.
- Caddyfile에 `/vintib-public/*`, `/vintib-private/*`를 `minio:9000`으로 넘기는 핸들을 추가하고, 나머지는 지금처럼 `backend:8080`으로 보낸다. **경로를 잘라내면 안 된다** — SigV4 서명에 경로가 포함되므로 `handle_path`가 아니라 `handle`을 쓴다.
- Caddy는 `reverse_proxy` 시 원본 Host 헤더를 보존하므로, presigner가 `i15a108.p.ssafy.io`로 서명한 값이 MinIO에서 그대로 검증된다.
- 백엔드 자신의 호출(`HeadObject` 등)은 Caddy를 거치지 않고 `AWS_S3_ENDPOINT=http://minio:9000`으로 직접 간다. 이 endpoint/publicEndpoint 분리는 `S3Config`에 이미 구현돼 있어 그대로 쓴다.

### 운영 버킷 초기화

- `LocalS3BucketInitializer`가 버킷 생성 + public 버킷 익명 읽기 정책까지 이미 처리한다. 다만 `@Profile("local")`이라 운영에서 돌지 않는다.
- 프로필 조건을 **"S3 endpoint가 설정돼 있으면 실행"**으로 바꾸고 이름에서 `Local`을 뺀다. MinIO를 쓰는 local/prod 양쪽에서 동작하고, 훗날 실제 AWS로 옮기면 endpoint가 비어 자동으로 꺼진다 — AWS에서는 버킷을 코드가 만들면 안 되므로 이 동작이 맞다.
- 콘솔에서 수동으로 할 일이 사라진다(`SY008` 체크리스트 81번 항목 해소).

### 자격증명·환경변수

- 백엔드가 받는 `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`는 MinIO root 자격증명이다. GitLab CI/CD Variables에는 **`PROD_MINIO_ROOT_USER` / `PROD_MINIO_ROOT_PASSWORD`** 이름으로 등록한다.
  - `PROD_` 접두사를 붙이는 이유는 `PROD_DB_PASSWORD`와 같다. 프로젝트 변수가 job 변수를 이기므로, `MINIO_ROOT_USER`라는 범용 이름으로 등록하면 `be-test`의 MinIO 서비스 컨테이너까지 운영 자격증명으로 뜬다.
- 리전·버킷명은 변수로 받지 않고 `deploy.sh`가 고정값으로 기록한다. MinIO는 리전을 무시하고(SDK 요구 때문에 `us-east-1`만 채우면 된다) 버킷명도 전역 유일성 제약이 없어 환경마다 다를 이유가 없다. 결과적으로 **새로 등록할 CI/CD Variable은 2개**로 줄어든다.
- `deploy.sh`의 `.env`에 추가/변경: `AWS_S3_ENDPOINT`, `AWS_S3_PUBLIC_ENDPOINT`, `AWS_REGION`, 버킷명 2개(고정값) + `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`(minio 컨테이너용) + `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`(백엔드용, 같은 값 파생).
- ⚠️ **MinIO 볼륨도 Postgres와 같은 함정이 있다.** root 자격증명은 볼륨 최초 생성 시점 값으로 굳으므로, 나중에 값을 바꾸면 볼륨을 지우거나 별도 조치가 필요하다. `deploy.sh` 주석에 명시한다.

### 이미 반영된 선행 수정 (`hotfix/262-deploy-aws-env-vars`)

- `deploy.sh`가 `.env` 생성 전에 필수 변수를 전부 검사하고, 임시 파일에 쓴 뒤 교체하도록 이미 고쳤다. 스토리지 방식과 무관하게 유효하므로 유지하고, 필수 변수 목록만 위 내용에 맞춰 갱신한다.

## 구현 목록

- [x] `docker-compose.yml`: `minio` 서비스 이동(포트 미발행), `backend`에 `depends_on: minio`
- [x] `docker-compose.override.yml`: `minio` 호스트 포트(9000/9001)만 남기고 중복 정의 정리
- [x] `docker-compose.prod.yml`: `minio` logging·`mem_limit` 추가
- [x] `infra/caddy/Caddyfile`: `/vintib-public/*`, `/vintib-private/*` → `minio:9000` (경로 보존)
- [x] `LocalS3BucketInitializer` → `S3BucketInitializer`, 실행 조건을 `aws.s3.endpoint` 설정 여부로 변경
- [x] `infra/ci/deploy.sh`: `.env` 항목·필수 변수 목록 갱신, MinIO 볼륨 주의 주석 추가
- [x] `.gitlab-ci.yml`: deploy job 주석의 필요 변수 목록을 `PROD_MINIO_ROOT_USER`/`PROD_MINIO_ROOT_PASSWORD`로 교체
- [x] `SY008` 계획 문서에 스토리지 방식 변경 반영(미완 체크리스트 2건 정리)
- [x] `.claude/requests/fe/001-product-image-presigned-upload.md` 확인 — 하드코딩된 URL 예시가 없고 "응답의 `uploadUrl`을 그대로 PUT" 계약이라 **변경 불필요**
- [x] `BE/docs/infra/cicd.md`에 MinIO 운영 메모(볼륨·자격증명·디스크) 추가
- [x] `.claude/skills/BE:verify` 전체 실행 — `BUILD SUCCESSFUL`, 93개 테스트 전부 통과
- [x] `S3BucketInitializer` 동작 확인 — MinIO 에 `vintib-public`(익명 읽기 정책 적용)·`vintib-private`(private) 생성됨
- [x] Caddyfile `caddy validate` — `Valid configuration`
- [x] MinIO 이미지 버전 고정 (`RELEASE.2025-09-07T16-13-09Z`, base compose·`be-test` 양쪽) — 다른 서비스와 동일한 pin 정책
- [ ] (사용자) GitLab CI/CD Variables에 `PROD_MINIO_ROOT_USER`/`PROD_MINIO_ROOT_PASSWORD` 등록
- [ ] 배포 1회로 업로드 → 공개 URL 조회 → 시착 presigned GET 동작 확인

## 확인이 필요한 미결정 사항

- **디스크 용량.** 이미지가 EC2 볼륨에 쌓인다. 기존 주간 `docker system prune`은 named volume을 건드리지 않아 데이터는 안전하지만, 반대로 오래된 이미지가 자동으로 줄지도 않는다. 시착 결과 보관 기간은 `SY008`에서도 미정으로 남아 있어 여기서도 정하지 않는다 — 용량이 문제가 되면 그때 정책을 잡는다.
- **EC2 초기화 시 이미지 전부 소멸.** 제공 기간 종료·해킹 등으로 서버가 초기화되면 복구 수단이 없다. MVP·시연 범위에서는 수용 가능하다고 보고 별도 백업을 두지 않는다.
- **버킷 경로가 API와 같은 도메인을 공유한다.** `/vintib-public`, `/vintib-private`가 예약 경로가 되므로 향후 API 경로와 겹치지 않게 주의한다(현재 API는 전부 `/api/*`라 충돌 없음).
- **(이번 범위 밖, 별건) 운영 메일 자격증명이 비어 있다.** `deploy.sh`가 `.env`에 `MAIL_USERNAME`/`MAIL_PASSWORD`를 쓰지 않아 운영에서 두 값이 빈 문자열로 해석된다(`docker compose config`로 확인). 회원가입 이메일 인증이 운영에서 동작하지 않을 것으로 보인다. 이번 계획(스토리지)과 무관하고 GitLab 변수 추가 결정이 필요해 손대지 않았다 — 별도 티켓으로 처리한다.
