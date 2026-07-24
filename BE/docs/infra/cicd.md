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

`DB_NAME`·`DB_USERNAME`·`SPRING_PROFILES_ACTIVE`·`IMAGE_TAG` 는 `.gitlab-ci.yml` 에서 넣으므로 등록하지 않아도 된다.

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
| 백엔드가 DB 인증 실패 | `DB_PASSWORD` 변수 값이 볼륨 생성 시점 비밀번호와 다름 (위 경고 참고) |
| Caddyfile not found | 배포 디렉터리를 호스트와 다른 경로로 마운트함. 같은 경로여야 함 |
| develop-BE 에 머지했는데 파이프라인이 안 생김 | `workflow.rules` 에 `develop-BE` 조건이 있는지 확인 |
