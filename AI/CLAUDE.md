# AI — 가상 시착 / 상품 설명 초안 / 라이브 발언 정보 추출 / 추천

담당 범위와 기술 스택(Python 3.12+, FastAPI 0.139.0)은 루트 `CLAUDE.md` 참고. 이 문서는
`AI/` 폴더 안에서만 적용되는 실행/CI/코딩 규칙을 다룬다.

## 🚫 하드 룰 — GMS API 호출은 Claude가 절대 실행하지 않는다

**`GMS_API_KEY`를 쓰는 코드를 Claude가 직접 실행하는 것을 금지한다.** 스크립트 작성·수정은
하되, **실행은 항상 사용자가 직접 한다.**, **Cost가 비쌀 것으로 예상되는 모델들은 코드에 추가하지 않는다. 사용자가 직접 변경하도록 안내만 해준다.**

- 금지 대상: GMS 게이트웨이(`gms.ssafy.io`)를 경유하는 **모든** 스크립트·스모크 테스트·노트북 셀·
  프로덕션 코드 경로. 모델 종류(haiku/sonnet/gemini)나 호출 횟수와 무관하게 **한 번도
  실행하지 않는다.** 구체적으로:
  - `validation/pricing-model-check/*.py`
  - **`app/pricing/`의 `llm_web_search` comps 백엔드** — 프로덕션 경로에도 GMS 호출이 있다.
    `registry.ACTIVE_COMPS_SOURCE`의 기본값은 항상 `"mock"`이어야 하고, Claude가 이 값을
    `"llm_web_search"`로 바꾸거나 그 상태로 서버·pytest를 실행하는 것을 금지한다.
    실백엔드 전환은 사용자만 한다.
  - **`app/pricing/`의 `naver` retail 백엔드** — GMS는 아니지만 같은 이유로 금지 대상이다.
    `registry.ACTIVE_RETAIL_SOURCE`의 기본값은 항상 `"mock"`이어야 하고, Claude가 이 값을
    `"naver"`로 바꾸거나 그 상태로 서버·pytest를 실행하는 것을 금지한다. 실백엔드 전환은
    사용자만 한다.
- 연결 확인·지연시간 측정·커버리지 비교처럼 "가볍다"고 판단되는 경우에도 예외 없다.
  판단 근거가 필요하면 실행을 사용자에게 요청하고 결과를 받아서 해석한다.
- **이유**: GMS는 팀 공용 유료 쿼터다. 서버사이드 웹검색은 별도 과금이고, 후보 목록을 순회하는
  스크립트는 사용자가 의도하지 않은 고가 모델까지 자동으로 호출한다. 실제로 `smoke_gms.py`가
  후보를 순회하며 `claude-opus-4-6`을 호출한 사고가 있었다(2026-07-29).
- 네이버 오픈API처럼 GMS와 무관한 무료 API도 **호출 비용·쿼터가 있는 외부 API면 먼저 물어본다.**
- 스크립트를 새로 만들 때는 **고가 모델이 기본 후보로 들어가지 않게** 하고, 비용이 드는 경로는
  기본 off(mock 폴백) + 명시적 플래그로만 켜지게 설계한다.

## 디렉터리 구조

- `app/` — **프로덕션 코드**(도메인 우선 구조, 아래 "프로덕션 모듈 구조" 참고). 진입점은
  `app/main.py`(`uvicorn app.main:app`), 앱 공통 설정은 `app/core/`, 도메인 공용 유틸은
  `app/shared/`, 기능은 `app/<도메인>/` 단위.
- `requirements.txt` — 프로덕션 런타임 의존성.
- `requirements-dev.txt` — CI/개발 도구(`ruff`, `black`, `pytest`, `httpx`) + `requirements.txt`.
- `test/` — **실제 테스트 코드.** `app/<도메인>/` 구조를 그대로 미러한다
  (`app/chat/` → `test/chat/`, `app/recommend/personalize/` → `test/recommend/personalize/`).
  프로덕션과 같은 lint 기준을 적용받는다.
  - **예외: `test/worker/`** — 리포 루트 `worker/`(추론 워커) 코드를 대상으로 한다. `worker/`는
    전용 CI 잡이 없어(`ai-test`는 `AI/**/*`만 감시) 그냥 두면 lint·test가 전혀 안 돈다. 그래서
    **torch 없이 돌 수 있는 순수 로직만이라도** 여기서 커버한다. import 경로는
    `test/conftest.py`가 `sys.path`에 넣어 준다(워커 실행 환경과 같은 방식).
- `validation/` — **PoC·스파이크 코드 전용. 프로덕션 코드가 아니다.**
  `validation/requirements-test.txt`에 무거운 ML 의존성(torch, transformers,
  sentence-transformers, FlagEmbedding, datasets 등)이 모여 있는데, **CI에는 설치되지 않는다**
  (아래 CI 섹션 참고) — 로컬에서 별도로 `pip install -r validation/requirements-test.txt`가 필요하다.
- `pyproject.toml` — `ruff`/`black`(`line-length=100`, `target-version=py312`) 설정과
  `pytest` 설정. `validation/AI_tryon/{tryondiffusion,catvton}`, `validation/**/*.ipynb`는
  외부/서드파티 코드·노트북이라 lint/format 대상에서 제외되어 있다.
  `per-file-ignores`(`E402`/`BLE001`/`F401` 완화)는 **`validation/**` 에만** 걸려 있다 —
  `test/`에 같이 걸면 테스트 코드의 미사용 import가 그냥 통과한다.

### 추론 코드는 `AI/`에 두지 않는다

`AI/docs/infra-architecture.md` §3.2가 규정한다 — **AI 게이트웨이는 추론을 직접 수행하지 않는
얇은 계층**이다. 모델·추론 코드는 리포지토리 루트 `worker/`에 두고 팀원 노트북에서 실행한다
(배포 대상 아님). `AI/app/`은 API 호출·라우팅·계약만 맡는다.

배포 이미지에 torch가 없다는 게 이 규칙의 실질적 근거다 — `AI/requirements.txt`에 없고
Dockerfile은 그것만 설치하므로, `app/` 안에 실모델 경로를 만들어도 **컨테이너에서는 동작하지
않는다**(ai 컨테이너 `mem_limit: 1g`이기도 하다).

## 프로덕션 모듈 구조 (도메인 우선)

프로덕션 코드는 `app/` 아래 **도메인 우선(domain-first)** 으로 둔다. 기능(추천·가상시착·상품설명
등)마다 자체완결 패키지 `app/<도메인>/`을 만들고, 도메인 내부에서 파일로 레이어를 나눈다. 최상위를
`api/`/`domain/`처럼 레이어로 쪼개지 않는다. BE(`domain/<name>/…` + `global/`)와 대응된다.

- `app/main.py` — FastAPI 앱 생성 + 각 도메인 router 등록(`app.include_router(...)`)과 `/health`.
- `app/core/` — 앱 전역 공통(cross-cutting). 설정(`config.py`), 이후 DB/Redis 클라이언트 등. (BE `global/` 대응)
- `app/shared/` — 여러 도메인이 공유하는 유틸(모델 레지스트리·임베딩 로더 등). `validation/`에서 승격 시 여기로.
- `app/<도메인>/` — 자체완결 기능 패키지. 내부 파일 규약:
  - `router.py` — API 레이어. `APIRouter`·엔드포인트, 요청 검증·응답 변환만. 로직은 service에 위임. (BE controller)
  - `service.py` — 도메인 비즈니스 로직. (BE service)
  - `schemas.py` — 요청/응답 pydantic 모델. (BE dto)
  - `pipeline/` (선택) — 오프라인 배치(임베딩·전처리 등, AI 특유). 무거운 ML import는 함수 내부 지연 import.
  - `dependencies.py`/`models.py`/`artifacts/`(gitignore) 등은 필요 시 추가.
- **서빙 경로(router/service)는 표준 라이브러리·경량 의존성만** 두고, 무거운 오프라인 의존성(torch·CLIP·umap 등)은 서비스 런타임(`requirements.txt`)에서 분리한다. 예: 추천 파이프라인 의존성은 `requirements-pipeline.txt`(CI 미설치)에 두고, 서빙은 사전계산 아티팩트만 읽는다.
- 도메인 테스트는 **`test/<도메인>/`** 에 둔다(`app/` 아래에 `tests/`를 만들지 않는다). 무거운
  의존성이 필요한 테스트는 `pytest.importorskip`로 가드한다(순수 로직/서빙 테스트는 CI에서 그대로
  실행). `pyproject.toml`의 `[tool.pytest.ini_options] pythonpath=["."]`로 `import app...`이 해석된다.
- 새 도메인은 위 파일 규약대로 만들고 `app/main.py`에 router를 prefix/tags와 함께 등록한다.
- `validation/`(PoC·스파이크)과 `app/`(프로덕션)은 명확히 분리한다 — `validation/` 코드를
  프로덕션에서 import하지 않는다. 반대 방향(`test/`·`validation/`이 `app/`을 import)은 정상이다.

### 테스트 배치 규칙 2가지 (지키지 않으면 수집이 깨진다)

- **`test/` 아래에 `__init__.py`를 만들지 않는다.** 파이썬 표준 라이브러리에 `test` 패키지가 있어서
  `test/__init__.py` + `pythonpath=["."]` 조합은 stdlib `test`를 가린다.
- 그래서 pytest가 파일 경로가 아닌 **basename으로 모듈을 식별**한다 → **테스트 파일 이름은 리포
  전체에서 유일해야 한다.** `test_<도메인>_<대상>.py` 규칙을 따른다
  (`test_chat_service.py`, `test_recommend_service.py`처럼). 도메인이 달라도 `test_service.py`가
  둘이면 수집 단계에서 에러가 난다.
- 테스트에서 목업 데이터를 읽을 때 `Path(__file__)` 상대경로를 쓰지 않는다 — 데이터는 프로덕션
  패키지(`app/<도메인>/data/`)에 있고 테스트는 `test/` 아래라 경로가 어긋난다. 프로덕션 모듈의
  경로 상수를 재사용한다(예: `test/chat/test_chat_service.py`가 `app.chat.faq._DATA_DIR`를 씀).

## CI 규칙 — 커밋 전 반드시 로컬에서 통과시킬 것

`.gitlab-ci.yml`의 `ai-test` 잡은 `AI/**` 변경이 있는 MR마다 다음을 실행한다:

1. `pip install -r AI/requirements-dev.txt`만 설치(무거운 ML 라이브러리 설치 안 함)
2. `ruff check .`
3. `black --check .`
4. `pytest -q` — 테스트가 하나도 없으면(exit 5) 통과 처리, 그 외 실패는 파이프라인을 그대로 실패시킴

커밋 전에 로컬에서 동일한 절차를 그대로 돌려서 확인한다:

```bash
cd AI
pip install -r requirements-dev.txt   # ruff==0.15.22, black==26.5.1, pytest==9.1.1 고정
ruff check .
black --check .   # 실패하면 black . 로 자동 정렬 후 diff를 리뷰
pytest -q
```

- **`AI/test/`·`AI/validation/`에 파일을 새로 추가/수정했다면 위 3개(ruff/black/pytest)를
  빠짐없이 돌릴 것.** 특히 `black --check`는 새로 만든 파일을 깜빡하고 안 돌리기 쉽다 — 실제로
  `test_recommendation_benchmark.py`/`test_dataset.py`를 black 없이 커밋했다가 CI의
  `black --check .` 단계에서 실패한 적이 있다. 새 파일을 추가하는 커밋에서는 항상 위
  4단계를 순서대로 실행한 뒤 커밋할 것.
- 로컬 Python이 3.12보다 낮으면(`target-version=py312`) black이 "Python 3.X cannot parse
  code formatted for Python 3.12" 경고를 띄울 수 있다 — 포맷팅 자체는 정상 동작하니 경고는
  무시해도 되지만, 가능하면 3.12 인터프리터로 맞추는 게 안전하다.

## 테스트 작성 규칙 — 무거운 ML 의존성 가드 필수

CI는 `AI/requirements-dev.txt`만 설치하고 `AI/validation/requirements-test.txt`(torch 등)는
설치하지 않는다. `AI/test/`·`AI/validation/` 어느 쪽이든 이런 무거운 라이브러리를 import하는
모듈을 대상으로 pytest 테스트를 작성할 때는, 테스트 파일 최상단에서
`pytest.importorskip(...)`으로 감싸 CI(라이브러리 없는 환경)에서 에러 없이 스킵되게 해야 한다:

```python
import pytest

torch = pytest.importorskip("torch")

from my_module import Something  # noqa: E402 — importorskip 이후 import
```

순수 로직(표준 라이브러리만 사용하는 데이터 분리/전처리 함수 등)을 테스트할 때는 이 가드가
필요 없다 — CI에서 그대로 실행된다.

- 가드 적용 예: `validation/model_selection/test_recommendation_benchmark.py`(torch 필요)
- 가드 불필요 예: `validation/recommendation-embedding-finetune/test_dataset.py`(순수 로직만,
  무거운 의존성은 함수 내부에서 지연 import)

## `AI/validation/` 코드 관례 (PoC/스파이크)

- 모델 후보·설정은 `model_selection/model_registry.py`처럼 중앙 레지스트리에
  `{"이름": "HF 모델ID 또는 로컬 경로"}` 딕셔너리 + `ACTIVE_*` 상수로 관리한다 — 키 하나만
  바꾸면 스왑되는 패턴.
- 모델 로딩은 `loaders.py`류의 공용 헬퍼로 분리하고, 무거운 라이브러리는 함수 내부에서 지연
  import한다(모듈 최상단 import로 인한 불필요한 로딩 지연 방지, import 시점 네트워크 I/O 방지).
- 파인튜닝/데이터 검증형 스파이크는 `<feature>-finetune-check/`, `<feature>-condition-check/`
  같은 디렉터리명을 쓰고, `dataset.py`(전처리/분리) + 학습 스크립트 + 평가 스크립트로 3분할한다.
- 재현성: 랜덤 시드·split 비율은 파일 상단 상수(`SEED`, `VAL_RATIO` 등)로 노출하고, 학습·평가
  스크립트가 같은 상수를 공유해 val split을 재현한다.
- 검증셋을 구성할 때는 항목(row) 단위로 먼저 train/val을 나누고, (anchor, positive/negative)
  쌍은 그 이후 각 split 내부에서만 만든다 — 순서를 반대로 하면 같은 아이템이 양쪽 split에
  걸쳐 평가 지표가 부풀려진다.
- 학습 산출물(모델 체크포인트, 재생성 가능한 데이터셋 등)은 `.gitignore`에 반영되어 있는지
  확인할 것 — PoC 결과물을 통째로 커밋하면 저장소가 급격히 커진다.

## 참조 문서 (규율 아님 — 필요할 때 찾아 읽을 것)

아래는 지켜야 할 규칙이 아니라 **참조 지식**이다. 해당 상황이 오면 읽고, 아니면 읽지 않아도 된다.
색인은 `docs/README.md`.

| 문서 | 읽어야 하는 상황 |
| --- | --- |
| `docs/testing-guide.md` | EC2 배포·테스트를 돕게 될 때. SSH 접속, compose 실행, API 확인 절차가 있다 |
| `docs/infra-architecture.md` | 게이트웨이(`app/gateway/`)·워커·Redis 큐가 엮인 구조를 알아야 할 때. Job/Result 스키마 포함 |
| `docs/tryon-advancement-strategy.md` | 가상 시착 개선 작업을 할 때 |
| `docs/chat-advancement-strategy.md` | 라이브 댓글 관리(`app/chat/`) 개선 작업을 할 때. 실측 기반 한계점과 기법 우선순위가 있다 |
| `docs/recommendation-advancement-strategy.md` | 브랜드 유사도 그래프(`app/recommend/`) 개선 작업을 할 때. 크롤링 텍스트 임베딩·다면 유사도·FE 전달 설계가 있다 |

구현 전 설계 계획은 여기가 아니라 루트 `.claude/plans/ai/`에 있다. 소스 파일 docstring의
`설계: .claude/plans/ai/00N-*.md` 줄이 해당 모듈의 설계 근거를 가리킨다 — 모듈을 고치기 전에
그 문서를 먼저 읽는다.

## 커밋/브랜치 규칙

루트 `.claude/commit-convention.md` 참고. `[JIRA-KEY] type: subject` 형식, push는 항상
사용자가 직접 실행한다.
