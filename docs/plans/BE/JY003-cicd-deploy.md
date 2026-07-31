# CI/CD 파이프라인 자동화 (S15P11A108-262)

## 배경/목표

MR 검증 CI(`.gitlab-ci.yml`, 완료)에 이어, **develop-BE 병합 시 EC2 자동 배포(CD)**를 완성한다. 완료조건: develop-BE 머지 → 자동 배포 → 서비스 정상 기동 1회 데모.

의존: -297(러너 등록·EC2 세팅, 완료), -47(compose, 완료).

## 현재 상태 (실측)

- 러너: EC2에 **docker executor**로 등록·online, **태그 없음**, `volumes=["/cache"]`, 비privileged.
- 배포 대상 compose·`.env`·override 격리는 -297에서 `/home/ubuntu/vintib`에 구성됨.
- 문제: docker executor 잡은 컨테이너 안에서 돈다 → 호스트에서 `docker compose up`을 하고 bind mount(Caddyfile)를 호스트 경로로 해석하려면 접근 방식이 필요하다.

## 작업 내용

- **배포 실행 경로**: **배포 전용 러너를 추가 등록(docker executor, tag: `deploy`)**. 기존 docker 러너는 build/test 담당, 신규 러너는 deploy 담당으로 역할 분리. 배포 러너에만 `/var/run/docker.sock`과 `/home/ubuntu/vintib`를 **호스트와 동일 경로로** 마운트한다 (compose의 bind mount는 도커 데몬이 있는 호스트 파일시스템 기준으로 해석되므로 경로가 어긋나면 마운트가 깨진다). 초안은 shell executor였으나 권한 장벽으로 뒤집혔다 — 아래 부록 참고.
- **deploy stage**: `develop-BE` push(머지) 시에만 트리거, `tags: [deploy]`.
  1. 잡이 체크아웃한 코드를 `/home/ubuntu/vintib`로 동기화(rsync, **`.env`·`_disabled/`는 보존**)
  2. `docker compose -f docker-compose.yml -f docker-compose.prod.yml -p vintib up -d --build`
  3. backend healthcheck 대기 → 실패 시 직전 이미지 태그로 롤백
- **이미지 태그**: `IMAGE_TAG`를 커밋 SHA로 지정해 빌드. 롤백은 직전 SHA 태그 재기동.
- **시크릿**: GitLab CI/CD Variables로 관리(레포 커밋 금지). 단 운영 DB 비밀번호는 호스트 `.env`에 이미 있으므로 **재생성하지 않고 그대로 재사용** — CD는 코드·이미지만 교체.
- **디스크 관리**: 배포 후 dangling 이미지 정리(`docker image prune -f`) + 주간 `docker system prune` (scheduled pipeline 또는 cron).
- **롤백 문서화**: `BE/docs/infra/`에 절차 기록.

## 구현 목록

- [x] EC2에 배포 전용 러너 추가 등록 (docker executor, tag: `deploy`) — 서버 작업
- [x] `.gitlab-ci.yml`: `deploy` stage 추가 (rules: develop-BE, tags: [deploy], environment: production)
- [x] 배포 스크립트 `infra/ci/deploy.sh` — 동기화 → compose up → healthcheck → 롤백
- [x] `IMAGE_TAG`를 `$CI_COMMIT_SHORT_SHA`로 전달
- [x] 배포 후 이미지 prune 처리 (`docker image prune -f`, 태그 붙은 직전 이미지는 롤백용으로 보존)
- [x] 롤백 절차 문서 (`BE/docs/infra/cicd.md`)
- [x] develop-BE 머지 1회로 자동 배포 데모

## 결정 사항 (2026-07-24 사용자 승인)

1. **배포 전용 러너를 추가 등록**(docker executor, tag: `deploy`). 그 러너에만 `docker.sock`과 배포 디렉터리를 마운트해 배포 잡만 호스트 도커에 접근한다.
2. **시크릿은 GitLab CI/CD Variables로 관리** — 배포 잡이 `.env`를 생성한다.
3. **순서**: -294를 먼저 끝내고 -262 진행.
4. **데모 머지 시점은 별도 조율** — 커밋·머지는 사용자 몫.

### shell executor를 쓰지 않는 이유 (실측)

계획 초안은 shell executor였으나 EC2 실측 결과 권한 장벽이 컸다.

- shell 잡은 `gitlab-runner` 사용자로 도는데 이 계정은 **docker 그룹에 없다** → 도커 명령 불가
- `/home/ubuntu`가 **0750**이라 배포 디렉터리 진입 자체가 불가, `.env`(600 ubuntu)도 읽기 불가 (실제로 확인)
- 쓰려면 docker 그룹 추가 + 디렉터리 이동/권한 완화가 필요한데, Gerrit이 동거하는 서버라 부담이 크다

반면 러너가 **배포 대상과 같은 호스트**에 있으므로, 잡 컨테이너에 배포 디렉터리를 **동일 경로로** 마운트하면 compose의 bind mount 경로가 그대로 맞고 권한 문제도 없다(컨테이너 root).

## 구현 중 조율 결과

- **배포 트리거 범위: develop-BE 전체로 확정.** `rules: $CI_COMMIT_BRANCH == "develop-BE"` — `changes:` 필터를 두지 않았다.
- 러너 등록 토큰 — GitLab 프로젝트 Settings → CI/CD → Runners 에서 발급(완료).
- **시크릿은 `PROD_DB_PASSWORD` 하나만 GitLab CI/CD Variables에 등록**하고, 배포 잡이 `umask 077`로 `.env`를 생성한다. 레포에 커밋되는 시크릿은 없다.
- **`PROD_DB_PASSWORD`는 현재 EC2 `.env`의 값과 반드시 같아야 한다.** PostgreSQL은 볼륨 최초 생성 시점의 비밀번호를 유지하므로, 다른 값을 넣으면 백엔드가 DB에 붙지 못한다.
