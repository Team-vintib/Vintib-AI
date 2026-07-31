"""SAM3 품질 검수 백엔드 — 서브패키지로 감싸는 이유.

`worker/models/garment_measurement/`처럼, 여러 워커 패키지가 같은 이름의 모듈
(`contracts.py`/`registry.py`/`prompts.py`/`segmenter.py`/`findings.py`/`scoring.py`/
`overlay.py`)을 가진 상태로 한 프로세스에 flat하게 로드되면 `sys.modules` 캐시가 충돌한다 —
먼저 import된 쪽이 캐시에 남아 나중 import가 조용히 잘못된 모듈을 가져온다
(`AI/test/conftest.py` 참고).

그래서 이 패키지는 **부모 디렉터리(`worker/models/`)를 sys.path에 넣고**
`from sam3.xxx import ...`(또는 `from sam3 import xxx`) 형태로만 접근한다. 내부 모듈끼리는
상대 import(`from . import registry` 등)를 쓴다. 런타임에서 실제로 쓰는 진입점은
`worker/quality_check_worker_example.py`다.
"""
