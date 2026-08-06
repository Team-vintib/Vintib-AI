# AI

빈티지·세컨핸드 의류 라이브 경매 플랫폼 AI 모듈.

## 담당 범위

기능정의서 기준 아래 AI 기능을 담당한다.

- AI 가상 시착 (TRYON) — 등록 상품 이미지를 사용자 전신 사진에 합성
- 상품 설명 초안 생성 (PROD-07) — 상품 이미지 분석 기반, 확인 불가한 정보는 추정하지 않음
- 라이브 발언 기반 상품 정보 추출/정정 (LPROD-02~04)
- 라이브 댓글 관리 (CHAT-001) — 욕설·도배 판정. AI는 판정만 하고 차단 집행은 BE가 한다
- 반복 질문 자동 답변 (CHAT-02, CHAT-03) — 근거 있는 경우에만 응답
- 라이브 자막용 STT 연동 (LIVE-06)
- 개인화 상품 추천 / 브랜드 유사도 그래프 (REC)

## 기술 스택

- Python 3.12+, FastAPI 0.139.0, Uvicorn(standard), Pydantic v2 / pydantic-settings
- Lint/Format: Ruff, Black (requirements-dev.txt)
- 비동기 작업 큐: **Celery는 안 쓴다.** Redis(큐 저장소) + AI 게이트웨이의 HTTP poll/result
  엔드포인트로 직접 구현(`app/gateway/`, `worker/base_worker.py`). 이유는 아래 "왜 Celery가
  아닌가" 참고
- 가상 시착 모델: 미확정 (diffusion 기반 try-on 계열 검토)
- 이미지 처리: Pillow, OpenCV (아직 미설치)
- STT: 미확정 (Whisper 계열 또는 클라우드 API)
- 반복 질문 답변용 RAG: pgvector(PostgreSQL) 검토

### 왜 Celery가 아닌가

한때(`-191`) `AI/tryon_service/`에 FastAPI+Celery 조합을 실제로 만들었다가 `-189`에서
제거했다. 이유는 네트워크 제약과 정면충돌해서다.

- Celery 워커는 브로커(Redis)에 **직접** TCP로 접속해서 그 프로토콜로 대화한다 — HTTP가
  아니다.
- 이 Redis는 EC2 Docker 내부망에만 떠 있고 호스트 포트를 절대 열지 않는다(`docker-compose.yml`
  베이스 파일 규칙). 인증 없는 Redis를 인터넷에 그대로 노출하는 셈이라 의도적으로 막아둔
  것이다.
- 그래서 팀원 노트북(워커)이 Redis에 접속하려 해도 애초에 연결할 공인 주소 자체가 없다.
  워커가 NAT 뒤에 있어 "인바운드가 안 되는" 것과는 별개 문제다 — 워커가 먼저 거는 연결(아웃
  바운드)조차 받아줄 상대가 없는 것.
- 대신 워커는 유일하게 열려 있는 문(Caddy 443, HTTPS)으로 AI 게이트웨이에 HTTP 요청만
  보낸다. 게이트웨이가 Redis와 같은 내부망에 있으니 워커를 대신해 `RPUSH`/`BLPOP`을 해준다
  (`AI/app/gateway/router.py`의 `/ai/workers/poll`, `/ai/workers/result`). Celery가 하던
  역할(큐 적재/소비, 재시도)을 게이트웨이 + 워커의 HTTP 폴링 조합으로 필요한 만큼만 직접
  구현한 것 — Celery의 스케줄링·모니터링 같은 부가기능은 지금 규모에 필요 없어 가져오지
  않았다.

자세한 구조는 [`docs/infra-architecture.md`](./docs/infra-architecture.md) §2·§3.4,
API 계약은 [`docs/api-reference.md`](./docs/api-reference.md) 참고.

> 로컬에 Python이 없어 실제 설치·실행은 못 해봤고, `requirements.txt`는 PyPI 최신 안정 버전으로 고정만 해둠. 최초 실행 시 버전 충돌 있으면 조정 필요.

## 실행 방법

1. `python -m venv .venv` 후 가상환경 활성화
2. `pip install -r requirements-dev.txt`
3. `.env.example`을 `.env`로 복사 후 값 조정
4. `AI/`에서 `uvicorn app.main:app --reload --port 8000` (`.env`는 실행 CWD 기준 로드)

## 디렉터리 구조

```
AI/
├── app/                  # 프로덕션 코드 (도메인 우선 구조)
│   ├── main.py           #   FastAPI 앱 진입점 + 도메인 router 등록 (+ /health)
│   ├── core/             #   앱 공통(설정 등, cross-cutting) — config.py
│   ├── shared/           #   도메인 공용 유틸(모델 레지스트리·임베딩 로더 등)
│   ├── chat/             #   라이브 댓글 관리 도메인(자체완결): router/service/schemas + pipeline/
│   └── recommend/        #   추천 도메인(자체완결): router.py / service.py / schemas.py / pipeline/
├── docs/                 # 참조 문서(런북·아키텍처·고도화 전략) — docs/README.md가 색인
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml        # ruff/black 설정
└── test/                 # 모델 선정(비교·평가) 단계의 스파이크 코드, 프로덕션 코드 아님
```

프로덕션 기능은 `app/<도메인>/` 단위로 추가한다(도메인 우선 구조). 자세한 규약은 `CLAUDE.md`
"프로덕션 모듈 구조" 참고.

## 문서

참조 문서는 [`docs/`](./docs/README.md)에 모여 있다. 목적별 색인은 그 안의 `README.md`를 본다.

| 문서 | 언제 보나 |
| --- | --- |
| [`docs/testing-guide.md`](./docs/testing-guide.md) | EC2에 올려 직접 테스트할 때 — 배포 절차·API 체크리스트·트러블슈팅 |
| [`docs/infra-architecture.md`](./docs/infra-architecture.md) | 게이트웨이·워커·큐 구조를 파악할 때 |
| [`docs/tryon-advancement-strategy.md`](./docs/tryon-advancement-strategy.md) | 가상 시착 개선 방향 (`S15P11A108-195`) |
| [`docs/chat-advancement-strategy.md`](./docs/chat-advancement-strategy.md) | 라이브 댓글 관리 개선 방향 (`S15P11A108-197`) |

구현 전 설계 계획은 문서가 아니라 루트 `.claude/plans/ai/`에 둔다(공통 규율).

## 추천 브랜드 그래프 아티팩트 빌드 (오프라인)

추천 API(`/recommend/graph`, `/recommend/{entity}/{id}/similar`)는 오프라인에서 사전계산한
아티팩트를 읽어 서빙한다. 아티팩트가 없으면 503을 반환한다. 서빙 자체는 표준 라이브러리만
쓰지만, 아티팩트 생성에는 CLIP 등 무거운 의존성이 필요하다.

1. `pip install -r requirements-pipeline.txt` (CLIP/numpy/umap/pyyaml — CI엔 설치되지 않음)
2. `app/recommend/data/brands.example.yaml`을 `brands.yaml`로 복사하고, `data/images/<id>/`에
   브랜드별 상품 이미지를 넣는다. (`brands.yaml`·`images/`·`artifacts/`는 gitignore)
3. 빌드:
   ```bash
   python -m app.recommend.pipeline.build_artifact \
       --data app/recommend/data --entity brand --out app/recommend/artifacts
   ```
4. `uvicorn app.main:app` 실행 후 `/recommend/graph?entity=brand` 확인.

`--entity seller`로 같은 파이프라인을 상점 유사도에도 재사용할 수 있다(그룹 키만 상점 id로).

## 라이브 댓글 관리 정확도 평가 (오프라인)

댓글 판정 API(`/chat/moderate`)와 반복질문 근거 경로의 **정확도**를 측정한다(S15P11A108-196).
무거운 의존성이 없어 `requirements-dev.txt`만으로 돌아간다.

```bash
python -m app.chat.pipeline.evaluate              # 전체 + artifacts/eval_report.md 기록
python -m app.chat.pipeline.evaluate --sets A     # 호환셋(210건)만
python -m app.chat.pipeline.evaluate --no-report  # 콘솔만
```

- Set A는 `test/model_selection/classifier_benchmark.ipynb`와 **같은 210건**이라 그 노트북에
  기록된 모델 수치와 직접 대조할 수 있다. Set B는 오탐 발굴용 수제 세트, Set C는 반복질문셋.
- 리포트(`app/chat/artifacts/`)는 생성물이라 gitignore 대상이다. 측정 결과와 오탐/미탐 정리는
  `.claude/plans/ai/004-live-comment-moderation-evaluation.md`에 기록해 둔다.
- 회귀는 `app/chat/tests/test_chat_evaluation.py`가 CI에서 잡는다(실측 하한 + 알려진 오탐/미탐
  집합 고정).

모델 선정(비교·평가) 단계의 실험 코드는 `test/`에 별도로 둔다.
프로덕션 기능 모듈 구조에는 포함되지 않으며, 노트북 특성상 `ruff check .`에서 제외된다.
후보 모델 로드/비교는 `test/model_selection/*.ipynb` 참고.
