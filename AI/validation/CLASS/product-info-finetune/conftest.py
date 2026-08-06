"""테스트를 `tests/`로 모으면서도 `aihub_*.py` 모듈이 계속 import되게 하는 conftest.

pytest는 `conftest.py`가 있는 폴더를 항상 sys.path에 올려주지만(파일이 있다는 사실
자체로), 여기서 명시적으로 한 번 더 넣어 확실히 한다. 이게 없으면 `tests/` 밑의
`test_class_finetune_*.py`가 `import aihub_finetune_vit` 같은 걸 할 때 그 모듈이
`tests/`가 아니라 이 폴더(부모)에 있어서 `ModuleNotFoundError`가 난다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
