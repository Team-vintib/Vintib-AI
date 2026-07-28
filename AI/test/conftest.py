"""AI 테스트 전역 설정.

**`worker/models/clipseg/`를 import 경로에 넣는다.** 리포 루트의 `worker/`는 별도 CI 잡이 없어
(`.gitlab-ci.yml`의 `ai-test`는 `AI/**/*`만 감시한다) 그냥 두면 lint·test가 전혀 돌지 않는다.
품질 검수 판정 로직이 그쪽으로 옮겨갔으므로, **순수 로직만이라도 AI의 pytest로 커버**한다
(torch가 필요한 CLIPSeg 백엔드는 목업으로 우회되므로 CI에서 그대로 돈다).

해당 테스트는 `test/worker/clipseg/`에 있다 — `test/`가 `app/<도메인>/`을 미러한다는 규칙의
예외이며, 리포 루트 `worker/`를 대상으로 한다는 뜻이다.

워커 패키지는 `sys.path` 삽입 방식으로 import되도록 만들어져 있다(`quality_check_worker_example.py`의
`CLIPSEG_CODE_PATH`, `tryon_worker_example.py`의 `CATVTON_CODE_PATH`와 같은 방식). 여기서도
같은 경로를 넣어 실행 환경과 동일하게 맞춘다.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CLIPSEG_PATH = _REPO_ROOT / "worker" / "models" / "clipseg"

if _CLIPSEG_PATH.is_dir():
    sys.path.insert(0, str(_CLIPSEG_PATH))
