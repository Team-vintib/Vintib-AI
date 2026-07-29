# AI 서비스 아키텍처 설계서

S15P11A108 · AI 게이트웨이 / 워커 파이프라인

## 1. 배경 및 제약 조건

본 프로젝트는 배포용 GPU 서버 없이, 팀원 노트북(로컬 GPU)을 추론 워커로 활용해 AI 시착·품질검수·추천·채팅 기능을 서비스하는 것을 목표로 한다. 설계 시 다음 제약을 반드시 준수해야 한다.

- EC2 서버는 별도 웹 콘솔이 제공되지 않으며, SSH 원격 터미널로만 접근 가능하다.
- 기본 방화벽(UFW)은 22번 포트만 열려 있으며, 설정 실수 시 복구가 불가능하고 초기화만 가능하다.
- 이 EC2 인스턴스에 연결된 IAM 역할(`AmazonLightsailInstanceRole`)에는 S3 접근 권한이 없다 — 클라우드 오브젝트 스토리지를 쓸 수 없다.
- 워커가 실행되는 노트북은 가정용 공유기 뒤에 있어 인바운드 접속이 불가능하다(아웃바운드만 가능).

이 세 가지 제약이 아래 모든 설계 결정의 근거가 된다.

## 2. 전체 구조

시스템은 클라우드(EC2)와 로컬(팀원 노트북) 두 영역으로 명확히 나뉜다.

```
[React 프론트] → [Spring Boot 백엔드] → [Caddy] → [FastAPI AI 게이트웨이] → [Redis 큐]
                                                              ↑
                                              (HTTP polling) [로컬 노트북 워커]
```

핵심 설계 원칙은 두 가지다.

- 워커는 Redis에 직접 접속하지 않는다. Redis(6379), PostgreSQL(5432)은 EC2 내부 네트워크에서만 접근 가능하며 호스트에 포트를 열지 않는다. 워커는 FastAPI가 제공하는 HTTP 엔드포인트(poll/result)를 통해서만 큐와 상호작용한다.
- 외부에 노출되는 것은 Caddy(80/443)뿐이다. Caddy가 경로 기준으로 backend 또는 ai 컨테이너로 리버스 프록시한다.

## 3. 컴포넌트별 상세 설명

### 3.1 Caddy (리버스 프록시)

도메인(`i15a108.p.ssafy.io`)에 대한 TLS 인증서를 Let's Encrypt로 자동 발급·갱신하고, 경로 기준으로 요청을 분기한다.

| 경로 | 전달 대상 | 용도 |
|---|---|---|
| `/ai/*` | `ai:8000` | AI 게이트웨이 — job 접수/조회, 워커 poll/result, 이미지·리포트 업로드 |
| `/results/*` | `ai:8000` | 결과 이미지·JSON 리포트 정적 서빙(S3 대체) |
| 그 외 전부 | `backend:8080` | 기존 REST API, 인증, 주문/경매 등 |

backend, ai, postgres, redis 어느 것도 호스트 포트를 직접 열지 않는다. Docker는 포트 publish 시 iptables를 직접 조작해 UFW 규칙을 우회하므로, 이 원칙을 지키지 않으면 UFW 설정과 무관하게 서비스가 외부에 노출될 수 있다.

### 3.2 AI 게이트웨이 (FastAPI)

추론을 직접 수행하지 않는 얇은 계층이다. 역할은 (1) job을 큐에 접수하고 (2) 상태를 조회해주고 (3) 워커의 poll/result/업로드 요청을 받아 Redis·디스크에 반영하는 것뿐이다.

| 엔드포인트 | 메서드 | 설명 |
|---|---|---|
| `/health`, `/ai/health` | GET | 헬스체크. 컨테이너 내부용(`/health`)과 Caddy 경유 외부용(`/ai/health`) 두 경로 모두 응답 |
| `/ai/{feature}` | POST | 백엔드가 호출. job 생성 후 Redis 큐에 적재, job_id 즉시 반환 |
| `/ai/jobs/{job_id}` | GET | 클라이언트가 결과를 폴링. Redis에서 상태(queued/processing/success/failed) 조회 |
| `/ai/workers/poll` | GET | 워커가 주기적으로 호출. 큐에서 job을 BLPOP으로 꺼내 반환 |
| `/ai/workers/result` | POST | 워커가 처리 결과를 제출. 성공 시 저장, 실패 시 재시도 큐 또는 dead-letter로 이동 |
| `/ai/workers/upload-image` | POST | 워커가 결과 이미지를 multipart로 업로드. EC2 디스크에 저장 후 공개 URL 반환 |
| `/ai/workers/upload-json` | POST | 워커가 품질검수 리포트 등 JSON 결과물을 업로드 |

워커 전용 엔드포인트(poll/result/upload-*)는 `X-API-Key` 헤더 인증을 요구한다. 재시도 로직(최대 3회, 초과 시 dead-letter 큐 이동)도 워커가 아닌 게이트웨이 쪽에서 처리한다 — 워커는 Redis 상태를 직접 다룰 수 없기 때문이다.

### 3.3 Redis

job 큐와 결과 임시 캐시 용도로만 사용한다. 이미지 등 큰 바이너리는 절대 담지 않는다(URL만 저장). 결과는 TTL 1시간으로 자동 만료된다.

| 키 패턴 | 용도 |
|---|---|
| `queue:{feature}` | 기능별 job 대기열 (tryon, quality_check, chat_rag, recommend_offline) |
| `result:{job_id}` | job 상태/결과 (TTL 3600초) |
| `dead_letter` | 최대 재시도 횟수를 초과한 job이 격리되는 큐 |

### 3.4 워커 (로컬 노트북)

팀원 노트북이 GPU 추론을 전담한다. `base_worker.py`가 공통 골격(poll → 추론 → 결과 제출, 재시도, 에러 핸들링)을 제공하며, 각 기능은 `run_inference()` 한 함수만 구현하면 된다.

```python
class TryonWorker(BaseWorker):
    feature = "tryon"
    def run_inference(self, payload):
        # 이 함수 내부만 모델별로 교체하면 됨
        ...
```

이 구조 덕분에 베이스 모델을 먼저 연결해 MVP를 검증하고, 이후 고도화 모델로 교체할 때도 게이트웨이·큐·API 계약은 전혀 건드리지 않는다. 나중에 GPU 서버가 확보되면 워커 실행 위치만 노트북에서 클라우드로 옮기면 되고, 코드 변경은 필요 없다.

### 3.5 결과물 저장 (S3 대체)

이 EC2의 IAM 역할에는 S3 권한이 없어(`s3:ListAllMyBuckets` 등 AccessDenied 확인됨), 결과 이미지·리포트는 EC2 로컬 디스크에 저장하는 방식으로 대체했다.

- 워커는 결과 이미지를 로컬 디스크가 아니라, 게이트웨이의 `/ai/workers/upload-image`로 HTTP(multipart) 전송한다 — 워커 자신의 디스크는 외부에서 접근 불가능하기 때문이다.
- 게이트웨이가 EC2 디스크(`/app/results`, `results-data` 볼륨)에 저장하고, FastAPI StaticFiles로 `/results` 경로에 마운트한다.
- Caddy가 `/results/*`를 `ai:8000`으로 라우팅해 최종적으로 `https://i15a108.p.ssafy.io/results/...` 형태의 공개 URL이 만들어진다.

현재 EC2 디스크 사용량은 여유가 있으나(약 4% 사용), 결과물이 자동으로 삭제되지 않는 구조이므로 실제 서비스 단계 진입 전 보관 기간 정책(retention) 스크립트 추가가 필요하다.

## 4. 보안 설계

| 포트 | 서비스 | 정책 |
|---|---|---|
| 22 | SSH | 기본 유지. 절대 닫지 않음 |
| 80 / 443 | Caddy | 유일하게 호스트에 노출되는 포트. TLS 종단 |
| 8000 | ai (FastAPI) | 컨테이너 내부 전용. 호스트/외부에 미노출, Caddy 경유로만 접근 |
| 8080 | backend | 컨테이너 내부 전용. 호스트/외부에 미노출, Caddy 경유로만 접근 |
| 6379 | Redis | 완전 비공개. 워커도 직접 접속하지 않음 |
| 5432 | PostgreSQL | 완전 비공개. backend만 내부에서 접근 |

워커 인증은 고정 API 키(`WORKER_API_KEY`) 방식을 사용한다. 게이트웨이의 워커 전용 엔드포인트는 `X-API-Key` 헤더를 검증하며, 값이 일치하지 않으면 401을 반환한다.

UFW 조작 시 락아웃(SSH 접속 불가) 방지를 위해, 규칙 추가 후 반드시 별도 SSH 세션에서 재접속을 확인한 뒤에만 기존 세션을 종료하는 절차를 따른다.

## 5. Job / Result 스키마

모든 기능이 아래 공통 계약을 공유한다. 이 스키마를 유지하는 한, 워커 내부의 모델 구현을 바꿔도 게이트웨이 코드는 변경할 필요가 없다.

| 필드 | 설명 |
|---|---|
| `job_id` | UUID. job 생성 시 게이트웨이가 발급 |
| `type` | tryon / quality_check / chat_rag / recommend_offline 중 하나 |
| `payload` | 기능별 입력 데이터(dict) |
| `retry_count` | 재시도 횟수. 3회 초과 시 dead-letter로 이동 |
| `status` | queued / processing / success / failed |
| `result` | 성공 시 결과 데이터(dict). 이미지는 URL로만 담김 |
| `worker_id` | 처리한 워커 식별자 (hostname-feature 형식) |

## 6. 기능별 처리 방식 분류

무거운 생성·추론은 비동기 큐로, 이미 준비된 데이터의 단순 조회는 동기 API로 나눈다.

**판단 기준은 ⑴ 자원 위치 ⑵ 가용성 ⑶ 외부 API 지연이다.**

- EC2 `ai` 컨테이너에는 GPU가 없고 torch도 없다(`mem_limit: 1g`). 노트북은 공유기 뒤라
  인바운드가 불가능하다 — **인바운드가 안 되는 자원은 동기 호출 대상이 될 수 없다.**
- 노트북 워커는 팀원이 켜야 돈다. 동기 API가 노트북에 의존하면 **노트북이 꺼진 순간 API가
  죽는다.** 비동기면 job이 `queued`로 남아 정직하게 표현된다.
- 흔한 오해: 큐 자체는 지연을 거의 만들지 않는다. `/ai/workers/poll`이 `BLPOP(timeout=5)`로
  블로킹하므로 워커가 대기 중이면 job 도착 즉시 반환된다. **느린 건 추론이지 큐가 아니다.**

**⑶은 앞의 둘과 결론이 다르다.** 자원이 **아웃바운드 외부 API**(GMS 등)면 인바운드 제약도
노트북 의존도 없다 — 컨테이너가 직접 호출할 수 있다. 그런데 느리다면(가격책정 실측 7.7초,
`CH002` V2) 동기 REST로는 화면을 세운다. 이 경우의 답은 **워커 큐가 아니라 컨테이너 내
백그라운드 실행**이다. 워커 큐로 보내면 HTTP 호출만 하는 기능이 "누군가 노트북을 켜 놔야
동작하는" 상태가 되어 가용성이 오히려 나빠진다.

> 폴링 계약은 세 방식이 모두 동일하다 — `GET /ai/jobs/{job_id}`는 `result:{job_id}`만 읽고
> `JobResult`에 job 종류 필드가 없어서 feature와 무관하기 때문이다. BE는 어느 쪽이든 폴링
> 코드를 하나만 유지한다.

| 기능 | 처리 방식 | 비고 |
|---|---|---|
| AI 시착 (CatVTON) | 비동기 큐 + 워커 | 가장 무거운 작업. job_id 폴링 방식 |
| 품질검수 (CLIPSeg) | 비동기 큐 + 워커 | 오염·하자 점수화, 결과가 가격책정의 입력이 됨. 접수는 `POST /quality/inspections`(요청 검증용 어댑터), 결과는 `GET /ai/jobs/{id}` |
| 비속어 필터 | 동기 (게이트웨이 직접) | 경량 모델. 큐를 거치지 않음. ⚠️ 실모델(KcELECTRA) 갈래는 `requirements.txt`에 transformers가 없어 **현재 배포 불가** — 별도 판단 필요 |
| 채팅 RAG | 동기 (게이트웨이 직접) | 현재 임베더가 순수 파이썬(`mock_bigram`)이라 컨테이너 안에서 성립. 실임베딩 모델로 바꾸면 재검토 |
| 추천 offline | **오프라인 배치 스크립트** | 큐를 쓰지 않는다. 상품 등록 시마다가 아니라 사람이 돌리는 아티팩트 생성 배치(`app/recommend/pipeline/`)라 job 큐가 불필요하다 |
| 추천 online | 동기 (사전계산 아티팩트 조회) | 지연시간 민감 — 큐를 거치면 안 됨 |
| 가격책정 | **비동기(컨테이너 내 백그라운드) + job 폴링. 워커 없음** | GMS 웹검색으로 중고 시세를 모아 산정. GPU·인바운드 제약이 없어 큐를 쓰지 않고 `ai` 컨테이너가 직접 처리한다 — 비동기인 이유는 **느려서**다(haiku 최저 라운드에서도 7.7초, `CH002` V2 실측). 접수는 `POST /pricing/estimates`, 결과는 `GET /ai/jobs/{id}` |

### 워커 가용성

워커가 꺼져 있으면 job은 `queued`로 남아 TTL(1시간)에 만료된다 — 이건 장애가 아니라 **정상
상태**다. BE·FE가 "처리 중"과 "아무도 안 듣고 있음"을 구별할 수 있도록
`GET /ai/workers/status`가 기능별 최근 폴링 시각과 대기 job 수를 노출한다.

⚠️ **알려진 한계**: 워커가 job을 poll한 직후 죽으면 그 job은 큐에서 이미 빠진 뒤라 재시도
대상이 되지 않고 `processing`인 채로 TTL까지 남는다. 가시성 타임아웃 도입은 별도 과제다.

## 7. 저장소 디렉토리 구조

```
S15P11A108/
  AI/                 # EC2 배포 대상 — FastAPI 게이트웨이
    main.py
    config.py
    schemas.py
    requirements.txt
  BE/                 # EC2 배포 대상 — Spring Boot 백엔드
  FE/                 # 프론트엔드
  infra/
    caddy/Caddyfile   # EC2 배포 대상 — 리버스 프록시 설정
  worker/             # 배포 대상 아님 — 팀원 노트북에서 직접 실행
    base_worker.py
    tryon_worker_example.py
    quality_check_worker_example.py
    storage_utils.py
  docker-compose.yml          # 베이스 (호스트 포트 미publish)
  docker-compose.override.yml # 로컬 개발용 (자동 병합, 포트 오픈)
  docker-compose.prod.yml     # 운영용 (-f로 명시 지정, Caddy만 노출)
```

`worker/`는 git으로 버전 관리는 하되, docker-compose 배포 대상에는 포함하지 않는다 — 실행 위치(팀원 노트북)와 관리 방식(git)을 분리하기 위함이다.

## 8. 향후 과제

- Redis에 `requirepass` 설정 및 관련 환경변수(`REDIS_PASSWORD`) 전 서비스 반영
- EC2 결과물 디스크 보관 기간 정책(retention) 스크립트 추가
- 각 워커의 `run_inference()` / `_load_pipeline()`에 실제 모델(CatVTON, ViT 등) 연결
- 동기 처리가 필요한 기능이 확정되면, 노트북 게이트웨이 + 터널링(Cloudflare Tunnel 등) 구조 추가 검토
- 백엔드 `/actuator/health`가 JWT 인증을 요구하는 문제 해결 필요 (별도 이슈)
