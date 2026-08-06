# CI/CD 파이프라인 (S15P11A108-262)

GitLab CI + EC2 self-hosted 러너로 검증과 배포를 자동화한 구성. 인프라 자체는 [`ec2.md`](./ec2.md) 참고.

## 전체 흐름

```
MR 생성/갱신  →  test stage   (be-test / fe-test / ai-test)      ← 기존 docker 러너
develop-BE 병합 →  deploy stage (EC2 자동 배포)                    ← deploy 전용 러너
```

| 파이프라인 | 트리거 | 실행 잡 |
| --- | --- | --- |
| MR 검증 | `merge_request_event` | 변경된 파트만 (`BE/**` → be-test 등) |
| 배포 | `develop-BE` 브랜치 push(=병합) | `deploy` |

> MR 단계에서 이미 테스트가 돌기 때문에 배포 파이프라인은 테스트를 다시 돌리지 않는다.

## 러너 구성

러너 2개가 EC2 한 대에 함께 있다. 역할이 다르다.

| 러너 | executor | 태그 | 용도 | 호스트 도커 접근 |
| --- | --- | --- | --- | --- |
| `ip-172-26-2-120` | docker | (없음) | 빌드·테스트 | ❌ |
| **deploy 러너** | docker | `deploy` | 배포 | ✅ `docker.sock` 마운트 |

**배포 러너에만** 아래를 마운트한다. 일반 테스트 잡은 호스트 도커를 건드릴 수 없다.

```toml
volumes = [
  "/cache",
  "/var/run/docker.sock:/var/run/docker.sock",
  "/home/ubuntu/vintib:/home/ubuntu/vintib",
]
```

> 배포 디렉터리를 **호스트와 같은 경로로** 마운트하는 이유: compose 의 bind mount(Caddyfile 등)는 도커 데몬이 있는 호스트 파일시스템 기준으로 해석된다. 잡 안 경로와 호스트 경로가 다르면 마운트가 깨진다.

## 필요한 CI/CD Variables

`Settings → CI/CD → Variables`

| 변수 | 값 | 비고 |
| --- | --- | --- |
| `PROD_DB_PASSWORD` | 운영 DB 비밀번호 | **Masked** 권장 |
| `CORS_ALLOWED_ORIGINS` | API 호출을 허용할 FE 출처. 콤마로 여러 개 | |
| `PROD_MINIO_ROOT_USER` | 운영 MinIO root 계정명 | |
| `PROD_MINIO_ROOT_PASSWORD` | 운영 MinIO root 비밀번호 | **Masked** (8자 이상) |
| `PROD_MAIL_USERNAME` | 인증코드 발송용 Gmail 계정 | |
| `PROD_MAIL_PASSWORD` | 위 계정의 앱 비밀번호 | **Masked** 권장 |
| `PROD_JWT_SECRET` | JWT 서명 키 | **Masked** 권장. `openssl rand -base64 48` |
| `WORKER_API_KEY` | 백엔드 ↔ AI 워커 내부 인증 키 | **Masked** 권장. `openssl rand -base64 32`. AI 쪽과 같은 값이어야 함 |

`DB_NAME`·`DB_USERNAME`·`SPRING_PROFILES_ACTIVE`·`IMAGE_TAG` 는 `.gitlab-ci.yml` 에서 넣으므로 등록하지 않아도 된다.
리전·버킷명·S3 엔드포인트도 등록하지 않는다 — `deploy.sh` 와 compose 기본값이 정한다(아래 "오브젝트 스토리지" 참고).

> [!WARNING]
> **2026-07-31 발견**: `PROD_MAIL_USERNAME`/`PROD_MAIL_PASSWORD`가 지금까지 CI/CD Variables에도, `deploy.sh`의 `.env` 생성 로직에도 없었다. `application.yml`의 `MAIL_USERNAME`/`MAIL_PASSWORD` 기본값은 빈 문자열이고, mail actuator 헬스체크는 "자격증명 미설정 시 배포가 막히는 걸 방지"하려고 의도적으로 꺼둔 상태(아래 참고)라 배포는 계속 성공해 왔지만, 실제로는 **운영에서 이메일 인증코드가 발송되지 않고 있었다**(SMTP 인증 실패). 위 두 변수를 GitLab에 등록하고 재배포해야 정상화된다 — 등록 전까지는 `deploy.sh`가 필수 변수 누락으로 배포 자체를 막는다(2026-07-31 `deploy.sh` 변경).

> [!WARNING]
> **2026-08-05 발견**: `JWT_SECRET`도 CI/CD Variables·`deploy.sh` 어디에도 없었다. `application.yml`의 기본값(`local-dev-only-secret-key-please-change-in-prod-0123456789`, 소스에 그대로 노출)으로 운영 토큰이 서명되고 있었다는 뜻이다. `PROD_JWT_SECRET`을 GitLab에 등록하고 재배포해야 한다 — 등록 전까지는 `deploy.sh`가 필수 변수 누락으로 배포를 막는다(2026-08-05 `deploy.sh` 변경). 재배포 시점에 서명 키가 바뀌므로 그 이전에 발급된 운영 토큰은 전부 무효화된다(재로그인 필요).

> [!WARNING]
> **2026-08-06 발견**: `develop-AI`가 `docker-compose.yml`의 `ai` 서비스에 `WORKER_API_KEY`를 추가하면서 `deploy.sh`의 `.env` 생성 로직에도 `WORKER_API_KEY=${WORKER_API_KEY}` 줄을 함께 넣었는데, `REQUIRED_VARS` 사전 검사에는 넣지 않았다. `main` 병합 시점에 GitLab에도 등록돼 있지 않아 `set -u`에 걸려 `.env` 생성 단계에서 곧바로 배포가 실패했다(`WORKER_API_KEY: parameter not set`). `PROD_JWT_SECRET` 때와 달리 이번엔 **조용히 배포되지도 못했다** — 실패 자체는 안전하게 막힌 것. `WORKER_API_KEY`를 GitLab에 등록하고 재배포해야 한다(`REQUIRED_VARS`는 이번에 `deploy.sh`에 함께 추가함). AI 쪽 `_check_worker_key()`가 값이 비어 있으면 무조건 401을 던지므로, 값은 AI 서비스가 기대하는 것과 동일해야 한다(BE↔AI 간 공유 비밀키 — AI 팀과 값 합의 필요).

`deploy.sh` 는 `.env` 를 만들기 **전에** 위 변수가 전부 채워졌는지 검사하고, 하나라도 비면 빠진 이름을 한 번에 출력하고 멈춘다. `.env` 도 임시 파일에 쓴 뒤 교체하므로, 실패해도 운영 `.env` 가 손상되지 않는다(= 롤백용 직전 태그가 보존된다).

> [!CAUTION]
> **변수 이름에 `DB_PASSWORD`·`DB_NAME` 같은 범용 이름을 쓰지 않는다.** GitLab 은 **프로젝트(및 그룹·인스턴스) CI/CD Variables 가 `.gitlab-ci.yml` 의 job 변수보다 우선**한다. 이름이 겹치면 테스트용 값이 운영값으로 덮어써져, 서비스 컨테이너는 `POSTGRES_*`(이름이 안 겹침)로 초기화되는데 접속만 운영값으로 시도하는 어긋남이 생긴다.
>
> `be-test` 는 `before_script` 에서 `DB_*`/`REDIS_*`/`SPRING_PROFILES_ACTIVE` 를 `export` 로 덮어써 자체 방어한다(export 는 변수 주입 뒤에 실행되므로 항상 이긴다). 값은 `POSTGRES_*` 에서 파생시켜 서비스가 실제로 만든 DB·계정과 어긋날 수 없게 했다. 하지만 `deploy` 잡은 여전히 영향을 받으므로 이름 규칙은 지켜야 한다.

> [!NOTE]
> **DB 연결 실패는 예외 메시지만으로 원인을 알 수 없다.** Hibernate 가 원인 `SQLException` 을 삼키고 `Unable to determine Dialect without JDBC metadata` 로 덮어쓴다. 그래서 `be-test` 는 (1) Gradle 실행 전에 `psql` 로 실제 로그인을 미리 해 보고, (2) `build.gradle` 의 `showStandardStreams = true` 로 테스트 JVM 로그를 빌드 로그에 흘려서 `FATAL: password authentication failed` 같은 원문 오류가 보이게 해 두었다.

> [!WARNING]
> **`PROD_DB_PASSWORD` 는 EC2 PostgreSQL 볼륨을 처음 만들 때 쓴 값과 반드시 같아야 한다.** PostgreSQL 은 볼륨 최초 생성 시점의 비밀번호만 유지한다. 다른 값을 넣으면 백엔드가 DB 에 붙지 못한다. 비밀번호를 정말 바꾸려면 컨테이너 안에서 `ALTER USER` 를 실행하거나 볼륨을 삭제해야 한다(데이터 손실).
>
> 변수를 **Protected** 로 설정하려면 `develop-BE` 도 protected 브랜치여야 한다. 아니면 배포 잡에서 값이 비어 배포가 실패한다.

## 배포 동작 ([`infra/ci/deploy.sh`](../../../infra/ci/deploy.sh))

1. **직전 태그 기록** — 현재 `.env` 의 `IMAGE_TAG` 를 롤백용으로 보관
2. **코드 동기화** — 체크아웃 → `/home/ubuntu/vintib` (`.env`·`_disabled/` 제외)
3. **override 격리** — `docker-compose.override.yml` 이 있으면 `_disabled/` 로 이동 (없으면 `-f` 누락 시 DB·Redis 가 외부 노출됨)
4. **`.env` 생성** — CI/CD Variables 기반
5. **빌드·기동** — `docker compose -f docker-compose.yml -f docker-compose.prod.yml -p vintib up -d`
6. **헬스체크** — `vintib-backend` 가 healthy 가 될 때까지 최대 180초 대기
7. **실패 시 롤백** — 직전 이미지 태그로 되돌려 재기동 후, 배포는 실패 처리
8. **정리** — dangling 이미지 prune (태그가 붙은 직전 이미지는 남으므로 롤백 가능)

이미지는 커밋 SHA(`$CI_COMMIT_SHORT_SHA`)로 태깅된다.

## 오브젝트 스토리지 (MinIO)

상품 이미지·시착 결과는 AWS S3 가 아니라 **EC2 안의 MinIO 컨테이너**에 저장한다. SSAFY 가 제공하는 건 EC2 한 대(SSH 전용, 웹 콘솔 없음)뿐이라 팀에 AWS 계정이 없기 때문이다. 설계 배경은 계획 `JY006` 참고.

- **외부 노출 경로**: `caddy` 가 `/vintib-public/*`, `/vintib-private/*` 만 `minio:9000` 으로 프록시한다. MinIO 는 호스트 포트를 열지 않는다(9000/9001 발행은 `docker-compose.override.yml` = 로컬 전용).
- **버킷 생성**: `S3BucketInitializer` 가 기동 시 없으면 만들고 public 버킷에 익명 읽기 정책을 적용한다. 콘솔에서 수동으로 할 일이 없다. `aws.s3.endpoint` 가 비어 있으면(= 실제 AWS S3) 아무것도 하지 않는다.
- **자격증명**: 백엔드의 `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` 는 compose 에서 `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` 로부터 파생된다. 둘이 어긋나면 서명 검증이 전부 실패하므로 별도 변수로 두지 않는다.
- **데이터**: named volume `minio-data`. 주간 `docker system prune` 은 볼륨을 건드리지 않아 안전하지만, 반대로 오래된 이미지가 자동으로 줄지도 않는다. 디스크 사용량을 주기적으로 확인할 것.

> [!WARNING]
> **`PROD_MINIO_ROOT_USER`/`PROD_MINIO_ROOT_PASSWORD` 는 `minio-data` 볼륨을 처음 만들 때의 값으로 굳는다.** PostgreSQL 과 같은 함정이다. 나중에 바꾸면 백엔드의 서명 검증이 전부 실패하고, 되돌리려면 볼륨을 지워야 한다 — **업로드된 이미지가 전부 사라진다.** 처음 등록할 때 신중하게 정할 것.

> [!CAUTION]
> **EC2 가 초기화되면 업로드된 이미지도 함께 사라진다.** 별도 백업을 두지 않는 선택이므로(MVP·시연 범위), 시연 직전 재업로드가 필요할 수 있다는 점을 감안할 것.

## 롤백

### 자동

헬스체크가 180초 안에 통과하지 못하면 스크립트가 **직전 이미지 태그로 자동 롤백**하고 파이프라인을 실패시킨다. 잡 로그에 `backend` 컨테이너 로그 마지막 50줄이 함께 출력된다.

### 수동

자동 롤백까지 실패했거나, 배포는 성공했는데 나중에 문제를 발견한 경우.

```bash
ssh -i I15A108T.pem ubuntu@i15a108.p.ssafy.io
cd /home/ubuntu/vintib

# 1) 되돌릴 수 있는 이미지 확인
docker images vintib-backend --format '{{.Tag}}\t{{.CreatedSince}}'

# 2) 원하는 태그로 교체
sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=<되돌릴_태그>/' .env
docker compose -f docker-compose.yml -f docker-compose.prod.yml -p vintib up -d

# 3) 확인
docker compose -f docker-compose.yml -f docker-compose.prod.yml -p vintib ps
curl -sS https://i15a108.p.ssafy.io/api/health
```

> GitLab 에서 이전 커밋의 배포 잡을 **Retry** 해도 같은 효과를 낸다(그 커밋 SHA 로 다시 빌드·배포).

## 디스크 관리

러너 빌드와 런타임이 한 인스턴스에 동거해 이미지가 빠르게 쌓인다.

- 배포할 때마다 `docker image prune -f` 로 dangling 이미지 자동 정리
- 태그가 붙은 과거 이미지는 롤백용으로 남으므로, 누적되면 주기적으로 정리한다

```bash
# 디스크 사용량 확인
docker system df

# 오래된 것 정리 (실행 중인 컨테이너가 쓰는 이미지는 보존됨)
docker system prune -a --filter "until=168h"
```

## 트러블슈팅

| 증상 | 원인·조치 |
| --- | --- |
| 배포 잡이 계속 pending | `deploy` 태그를 가진 러너가 없거나 offline. 러너 상태 확인 |
| `DB_PASSWORD` 가 비어 배포 실패 | 변수가 **Protected** 인데 `develop-BE` 가 protected 브랜치가 아님 |
| `WORKER_API_KEY: parameter not set` 로 `.env` 생성 단계에서 실패 | `WORKER_API_KEY`가 GitLab CI/CD Variables 에 등록되지 않음. 등록 후 재배포 |
| 백엔드가 DB 인증 실패 | `DB_PASSWORD` 변수 값이 볼륨 생성 시점 비밀번호와 다름 (위 경고 참고) |
| Caddyfile not found | 배포 디렉터리를 호스트와 다른 경로로 마운트함. 같은 경로여야 함 |
| develop-BE 에 머지했는데 파이프라인이 안 생김 | `workflow.rules` 에 `develop-BE` 조건이 있는지 확인 |
