"""VLM 하자 설명 생성 백엔드 — 서브패키지로 감싸는 이유.

`worker/models/sam3/__init__.py`와 같은 이유다 — 여러 워커 패키지가 같은 이름의 모듈
(`registry.py`/`loader.py`/`prompts.py`/`describer.py`)을 가진 상태로 한 프로세스에
flat하게 로드되면 `sys.modules` 캐시가 충돌한다.

그래서 이 패키지도 **부모 디렉터리(`worker/models/`)를 sys.path에 넣고**
`from quality_vlm.xxx import ...` 형태로만 접근한다. 내부 모듈끼리는 상대 import
(`from . import registry` 등)를 쓴다. 런타임 진입점은 `worker/quality_check_worker_example.py`다.

설계: `.claude/plans/ai/CH011-quality-vlm-production-wiring.md`
"""
