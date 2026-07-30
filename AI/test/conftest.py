"""AI 테스트 전역 설정.

**`worker/models/clipseg/`·`worker/models/garment_measurement/`·`worker/models/sam3/`를 import
경로에 넣는다.** 리포 루트의 `worker/`는 별도 CI 잡이 없어(`.gitlab-ci.yml`의 `ai-test`는
`AI/**/*`만 감시한다) 그냥 두면 lint·test가 전혀 돌지 않는다. 품질검수·실측 판정 로직이 그쪽에
있으므로, **순수 로직만이라도 AI의 pytest로 커버**한다(torch가 필요한 백엔드는 목업으로
우회되므로 CI에서 그대로 돈다).

해당 테스트는 `test/worker/clipseg/`·`test/worker/garment_measurement/`·`test/worker/sam3/`에
있다 — `test/`가 `app/<도메인>/`을 미러한다는 규칙의 예외이며, 리포 루트 `worker/`를 대상으로
한다는 뜻이다.

**두 경로를 넣는 방식이 서로 다르다.** `clipseg/`는 `contracts.py`/`registry.py`/`scenarios.py`
등을 flat하게 두고 그 디렉터리 자체를 sys.path에 넣는다(`quality_check_worker_example.py`의
`CLIPSEG_CODE_PATH`와 같은 방식) — 바로 `import contracts`로 접근한다. `garment_measurement/`·
`sam3/`는 `clipseg/`와 파일명이 같아서(`contracts.py`/`registry.py`/...) flat하게 넣으면
`import contracts`가 어느 쪽을 가져올지 꼬인다(먼저 import된 모듈이 전역 캐시에 남는다). 그래서
이 둘은 진짜 서브패키지(`__init__.py` 보유)로 만들고 **부모 디렉터리**(`worker/models/`)를
sys.path에 넣어 `from garment_measurement.xxx import ...`/`from sam3.xxx import ...` 형태로만
접근한다 — CatVTON이 `model.` 네임스페이스로 같은 문제를 피한 것과 동일한 원리다.
"""

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CLIPSEG_PATH = _REPO_ROOT / "worker" / "models" / "clipseg"
_WORKER_MODELS_PATH = _REPO_ROOT / "worker" / "models"  # garment_measurement/sam3 패키지의 부모

if _CLIPSEG_PATH.is_dir():
    sys.path.insert(0, str(_CLIPSEG_PATH))
if _WORKER_MODELS_PATH.is_dir():
    sys.path.insert(0, str(_WORKER_MODELS_PATH))


class FakeRedis:
    """게이트웨이가 쓰는 redis 명령만 흉내내는 최소 스텁.

    실 Redis는 CI에 없다. `app.gateway.router.r`(모듈 전역 클라이언트)을 이걸로 갈아끼우면
    큐에 무엇이 실렸는지·결과 키에 무엇이 저장됐는지를 그대로 들여다볼 수 있다.

    `test/` 아래에는 `__init__.py`를 둘 수 없어(stdlib `test` 패키지를 가린다) 테스트끼리
    import가 안 된다. 그래서 공용 스텁은 여기 conftest에 둔다.
    """

    def __init__(self) -> None:
        self.pushed: list[tuple[str, str]] = []
        self.stored: dict[str, str] = {}

    def rpush(self, key: str, value: str) -> int:
        self.pushed.append((key, value))
        return len(self.pushed)

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.stored[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self.stored.get(key)

    def llen(self, key: str) -> int:
        return sum(1 for pushed_key, _ in self.pushed if pushed_key == key)


@pytest.fixture
def fake_redis(monkeypatch):
    """게이트웨이의 전역 Redis 클라이언트를 가짜로 교체한다."""
    from app.gateway import router as gateway_router

    fake = FakeRedis()
    monkeypatch.setattr(gateway_router, "r", fake)
    return fake
