# AI 게이트웨이 테스트 가이드

S15P11A108 · develop-AI 브랜치 기준 테스트 절차

## 1. 목적

AI 게이트웨이(FastAPI) + Redis 큐 + 워커 폴링 구조가 실제로 EC2 위에서 동작하는지, 배관(요청 접수 → 큐 적재 → 상태 조회) 단위로 검증한다. 모델(CatVTON 등) 연결 여부와 무관하게 이 절차만으로 인프라 정상 동작을 확인할 수 있다.

## 2. 사전 준비물

- EC2 접속용 개인키(.pem) — 로컬 컴퓨터에만 보관, git에는 절대 커밋하지 않는다
- EC2 도메인: `i15a108.p.ssafy.io`
- `.env` 값: `WORKER_API_KEY`(임의 강한 문자열), `DB_NAME`/`DB_USERNAME`/`DB_PASSWORD`, `PUBLIC_BASE_URL`

## 3. develop-AI 브랜치에서 테스트하는 방법

가장 정확한 방식은 EC2를 git 저장소로 관리하고, develop-AI 브랜치를 그대로 clone/pull해서 테스트하는 것이다.

### 3.1 최초 1회 — EC2를 git 저장소로 전환

EC2에 이미 파일이 올라가 있으나 git 저장소가 아닌 경우(파일만 복사된 상태), 아래 절차로 전환한다.

1. 로컬에서 feature 브랜치 작업을 develop-AI에 MR로 merge한다 (리뷰 후 병합).
2. EC2 접속 후 기존 폴더를 백업한다: `mv vintib vintib_backup_$(date +%Y%m%d)`
3. `git clone -b develop-AI <GitLab 저장소 주소> vintib`
4. `cd vintib && cp .env.example .env` 후 값 채우기 (백업 폴더의 기존 `.env` 값 참고 가능)

### 3.2 이후 — 최신 develop-AI 내용으로 갱신

```bash
cd ~/vintib
git checkout develop-AI
git pull origin develop-AI
```

파일이 실제로 갱신됐는지 반드시 눈으로 확인한다 (아래 4장 참고). pull만 믿고 바로 재빌드하면, 브랜치나 경로 착오로 옛 코드가 그대로 남아있는 것을 놓치기 쉽다.

### 3.3 컨테이너 기동 (운영 방식 그대로)

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

override 파일이 자동 병합되는 `-f` 없는 `up` 명령어는 로컬 개발 전용이며, Redis/Postgres/AI 포트가 호스트에 열려버린다. develop-AI 기준 테스트는 반드시 `-f` 두 개를 명시한 이 형태로 실행한다.

## 4. 임시 테스트 방법 (push 전, scp 기반)

아직 push하지 않은 로컬 변경사항을 빠르게 확인하고 싶을 때 쓰는 방식이다. git을 거치지 않으므로 정식 검증으로 취급하지 않는다.

```bash
# 로컬(Windows)에서
scp -i 키파일.pem AI/config.py AI/main.py AI/requirements.txt AI/schemas.py \
    ubuntu@i15a108.p.ssafy.io:~/vintib/AI/
scp -i 키파일.pem infra/caddy/Caddyfile ubuntu@i15a108.p.ssafy.io:~/vintib/infra/caddy/
scp -i 키파일.pem docker-compose.yml ubuntu@i15a108.p.ssafy.io:~/vintib/
scp -i 키파일.pem -r worker ubuntu@i15a108.p.ssafy.io:~/vintib/
```

scp 이후에는 반드시 EC2에서 파일 내용을 직접 열어 확인한다. scp 완료 메시지(100%)만으로는 "올바른 최신 버전을 보냈는지"까지 보장되지 않는다 — 실제로 로컬 파일 자체가 아직 수정 전이었던 경우가 여러 차례 있었다.

```bash
grep -B 2 -A 3 "def health_check" ~/vintib/AI/main.py
```

## 5. API 동작 확인 체크리스트

| # | 명령어 | 기대 응답 | 확인 항목 |
|---|---|---|---|
| 1 | `curl https://i15a108.p.ssafy.io/ai/health` | `{"status":"ok"}` | Caddy → ai 라우팅 정상 |
| 2 | `curl -X POST .../ai/tryon -d '{"test":"data"}'` | `{"job_id":"..."}` | job 접수 및 큐 적재 |
| 3 | `curl .../ai/jobs/{job_id}` | `{"status":"queued",...}` | 상태 조회 (워커 없으면 queued 유지) |

컨테이너 내부에서 직접 확인이 필요할 때는 아래 명령어로 Caddy 계층을 우회해 원인을 좁힌다.

```bash
docker exec vintib-ai python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read())"
docker exec vintib-caddy wget -qO- http://ai:8000/health
```

## 6. 워커 연결 e2e 테스트 (모델 연결 이후)

1. 팀원 노트북에서 `GATEWAY_URL=https://i15a108.p.ssafy.io/ai`, `WORKER_API_KEY` 환경변수 설정
2. `worker/tryon_worker_example.py` 등 `_load_pipeline()` 내부에 실제 모델 연결 확인
3. `python tryon_worker_example.py`로 워커 실행 (poll 로그가 주기적으로 찍히는지 확인)
4. 5장의 2번 명령어로 job 생성
5. 수 초~수십 초 후 5장의 3번 명령어로 재조회 → status가 success로 바뀌고 `result.image_url`이 채워지는지 확인
6. 해당 URL을 브라우저로 직접 열어 이미지가 실제로 보이는지 확인 (`https://i15a108.p.ssafy.io/results/...`)

## 7. 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| `docker compose up` 시 `services.ai.volumes must be a array` | `volumes:` 아래 실제 리스트 항목(`- results-data:/app/results`)이 빠짐. YAML 문법 오류 |
| `/ai/health` 호출 시 backend의 인증 에러(U010 등) 응답 | Caddy가 아직 새 Caddyfile로 재기동되지 않음. `restart`로 반영 안 될 수 있어 `rm -sf` 후 `up --no-deps`로 재생성 필요 |
| `/ai/health` 호출 시 `Method Not Allowed` | 게이트웨이 라우트가 `/health`로만 등록되어 있고 `/ai/health` 접두어가 없음. 같은 함수에 두 데코레이터(`@app.get("/health")`, `@app.get("/ai/health")`) 등록 필요 |
| 파일을 고쳐 scp/재빌드해도 컨테이너 안 내용이 그대로 | 로컬 원본 파일 자체가 저장되지 않았거나, scp가 실제로 전송되지 않은 경우가 대부분. `docker build --no-cache` 이전에 EC2 호스트 파일(`cat ~/vintib/AI/main.py`)부터 직접 확인 |
| backend가 계속 unhealthy | `JwtAuthenticationFilter`가 헬스체크 경로에도 인증을 요구하는 별도 버그. AI 게이트웨이 테스트와는 무관 — caddy는 `up ... caddy --no-deps`로 backend 의존성을 우회해 개별 기동 가능 |
| Caddy 관리 API(2019) 접근 시 `Connection refused` | 정상. 이번 구성에서는 admin API를 별도로 열어두지 않음 — 원인 진단은 컨테이너 내부 파일 확인으로 대체 |

## 8. 참고 — 이번에 확인된 보안 로그

Caddy 접근 로그에서 `/brevo/.env`, `/transactional/.env` 등 존재하지 않는 경로로 `.env` 파일을 노리는 자동화 봇 스캔이 관측되었다. 우리 서버의 `.env`는 해당 경로에 없어 실질적 노출은 없었으나, 인터넷에 노출된 도메인이라면 흔히 발생하는 정찰성 스캔이다. 추후 여유가 있을 때 Caddy 접근 로그 모니터링 또는 rate limiting 도입을 검토한다.
