# AI

빈티지·세컨핸드 의류 라이브 경매 플랫폼 AI 모듈.

## 담당 범위

기능정의서 기준 아래 AI 기능을 담당한다.

- AI 가상 시착 (TRYON) — 등록 상품 이미지를 사용자 전신 사진에 합성
- 상품 설명 초안 생성 (PROD-07) — 상품 이미지 분석 기반, 확인 불가한 정보는 추정하지 않음
- 라이브 발언 기반 상품 정보 추출/정정 (LPROD-02~04)
- 반복 질문 자동 답변 (CHAT-02, CHAT-03) — 근거 있는 경우에만 응답
- 라이브 자막용 STT 연동 (LIVE-06)

## 기술 스택

- Python 3.12+, FastAPI 0.139.0, Uvicorn(standard), Pydantic v2 / pydantic-settings
- Lint/Format: Ruff, Black (requirements-dev.txt)
- 비동기 작업 큐: Celery + Redis 도입 예정 (무거운 시착 합성 요청 처리, 아직 미설치)
- 가상 시착 모델: 미확정 (diffusion 기반 try-on 계열 검토)
- 이미지 처리: Pillow, OpenCV (아직 미설치)
- STT: 미확정 (Whisper 계열 또는 클라우드 API)
- 반복 질문 답변용 RAG: pgvector(PostgreSQL) 검토

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
│   └── recommend/        #   추천 도메인(자체완결): router.py / service.py / schemas.py / pipeline/
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml        # ruff/black 설정
└── test/                 # 모델 선정(비교·평가) 단계의 스파이크 코드, 프로덕션 코드 아님
```

프로덕션 기능은 `app/<도메인>/` 단위로 추가한다(도메인 우선 구조). 자세한 규약은 `CLAUDE.md`
"프로덕션 모듈 구조" 참고.

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

모델 선정(비교·평가) 단계의 실험 코드는 `test/`에 별도로 둔다.
프로덕션 기능 모듈 구조에는 포함되지 않으며, 노트북 특성상 `ruff check .`에서 제외된다.
후보 모델 로드/비교는 `test/model_selection/*.ipynb` 참고.
