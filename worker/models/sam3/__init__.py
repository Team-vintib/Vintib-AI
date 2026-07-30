"""SAM3 품질 검수 백엔드 — 서브패키지로 감싸는 이유.

`worker/models/clipseg/`와 파일명이 완전히 같다(`contracts.py`/`registry.py`/`prompts.py`/
`segmenter.py`/`findings.py`/`scoring.py`/`overlay.py`). 둘 다 flat하게 sys.path에 넣으면
같은 이름의 모듈이 `sys.modules` 캐시에서 충돌한다 — 먼저 import된 쪽이 캐시에 남아 나중
import가 조용히 잘못된 모듈을 가져온다(`AI/test/conftest.py`가 `garment_measurement`에
같은 이유로 서브패키지 방식을 쓰는 것과 동일한 문제·동일한 해법).

그래서 이 패키지는 **부모 디렉터리(`worker/models/`)를 sys.path에 넣고**
`from sam3.xxx import ...`(또는 `from sam3 import xxx`) 형태로만 접근한다. 내부 모듈끼리는
상대 import(`from . import registry` 등)를 쓴다. 런타임에서 실제로 쓰는 진입점은
`worker/quality_check_worker_example.py`의 `sam3` 분기다.
"""
