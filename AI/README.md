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
4. `uvicorn main:app --reload --port 8000`

## 디렉터리 구조

```
AI/
├── main.py          # FastAPI 앱 진입점 (/health 엔드포인트만 존재)
├── config.py         # pydantic-settings 기반 환경설정
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml    # ruff/black 설정
```

기능별(가상 시착, 설명 생성 등) 모듈 분리는 실제 구현 시작 시 진행.
