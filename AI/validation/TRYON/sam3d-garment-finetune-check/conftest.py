"""이 스파이크의 pytest 설정.

**왜 필요한가**: 이 디렉터리는 이름에 하이픈이 있어(`sam3d-garment-finetune-check`) 패키지
경로로 import 되지 않는다. 그리고 AI 루트에서 `pytest -q` 를 돌리면 rootdir 이 `AI/` 라
`garment3d` 가 `sys.path` 에 들어오지 않는다. conftest 가 자기 디렉터리를 넣어 두면
**루트에서 돌려도, 이 디렉터리에서 돌려도** 같은 import 가 성립한다.

`AI/test/conftest.py` 가 `worker/` 를 넣는 것과 같은 방식이다.
"""

import sys
from pathlib import Path

_PROJECT_DIR = Path(__file__).resolve().parent

if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_DIR))
