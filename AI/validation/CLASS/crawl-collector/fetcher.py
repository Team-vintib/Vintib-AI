"""HTML 가져오기 — 정적(httpx) / SPA(Playwright) 두 백엔드 + robots·rate limit.

국내 쇼핑몰은 상품 목록을 JS로 그리는 곳이 많아(무신사·지그재그·번개장터 등) 정적 파싱만으로는
빈 페이지를 받는다. 그래서 사이트 스펙의 `render` 키로 백엔드를 갈아끼운다.

**요청 예절은 기본값으로 지킨다** — robots.txt 확인, 요청 간 지연(지터 포함), 단일 커넥션.
수집기는 데이터셋 한 번 만들려고 도는 물건이지 트래픽을 낼 이유가 없다.

httpx는 `requirements-dev.txt`에 이미 있지만 Playwright는 없다 — 둘 다 함수 내부에서 지연
import한다(이 모듈은 import만으로는 아무 의존성도 요구하지 않는다).
"""

from __future__ import annotations

import random
import time
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

DEFAULT_TIMEOUT = 20.0


class FetchError(RuntimeError):
    pass


@dataclass
class RateLimiter:
    """호스트 하나를 대상으로 한 요청 간 최소 간격. 지터를 섞어 규칙적 패턴을 피한다."""

    delay_seconds: float = 1.5
    jitter: float = 0.4
    _last: float = 0.0

    def wait(self) -> None:
        if self.delay_seconds <= 0:
            return
        elapsed = time.monotonic() - self._last
        target = self.delay_seconds + random.uniform(0, self.jitter)
        if elapsed < target:
            time.sleep(target - elapsed)
        self._last = time.monotonic()


class RobotsGate:
    """robots.txt 캐시 + 허용 여부 판정. 실패(404 등)하면 허용으로 본다(표준 동작)."""

    def __init__(self, user_agent: str, *, enabled: bool = True) -> None:
        self.user_agent = user_agent
        self.enabled = enabled
        self._cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def allowed(self, url: str) -> bool:
        if not self.enabled:
            return True
        parsed = urlparse(url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        if root not in self._cache:
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(urljoin(root, "/robots.txt"))
            try:
                parser.read()
            except Exception:
                self._cache[root] = None  # 읽을 수 없으면 판단 보류 = 허용
            else:
                self._cache[root] = parser
        parser = self._cache[root]
        if parser is None:
            return True
        return parser.can_fetch(self.user_agent, url)


class Fetcher:
    """스펙의 `render`에 따라 정적/브라우저 렌더 HTML을 돌려준다.

    `with Fetcher(...) as f:` 로 쓰면 httpx 클라이언트와 Playwright 브라우저가 정리된다.
    """

    def __init__(
        self,
        *,
        user_agent: str,
        render: str = "static",
        delay_seconds: float = 1.5,
        respect_robots: bool = True,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.user_agent = user_agent
        self.render = render
        self.timeout = timeout
        self.limiter = RateLimiter(delay_seconds=delay_seconds)
        self.robots = RobotsGate(user_agent, enabled=respect_robots)
        self._client = None  # httpx.Client
        self._pw = None  # playwright 컨텍스트 매니저
        self._browser = None
        self._page = None

    # ------------------------------------------------------------------
    def __enter__(self) -> "Fetcher":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._pw is not None:
            self._pw.stop()
            self._pw = None

    # ------------------------------------------------------------------
    def _httpx_client(self):
        if self._client is None:
            import httpx

            self._client = httpx.Client(
                headers={
                    "User-Agent": self.user_agent,
                    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
                },
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    def _playwright_page(self):
        if self._page is None:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError as exc:
                raise FetchError(
                    "render: playwright를 쓰려면 playwright 설치가 필요하다 — "
                    "pip install playwright && playwright install chromium"
                ) from exc
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True)
            context = self._browser.new_context(
                user_agent=self.user_agent, locale="ko-KR", viewport={"width": 1440, "height": 900}
            )
            self._page = context.new_page()
        return self._page

    # ------------------------------------------------------------------
    def get_html(self, url: str, *, wait_selector: str | None = None, scroll_times: int = 0) -> str:
        """페이지 HTML. robots 금지면 FetchError."""
        if not self.robots.allowed(url):
            raise FetchError(f"robots.txt가 이 경로 수집을 금지한다: {url}")
        self.limiter.wait()
        if self.render == "playwright":
            return self._get_html_playwright(url, wait_selector, scroll_times)
        return self._get_html_static(url)

    def _get_html_static(self, url: str) -> str:
        import httpx

        try:
            response = self._httpx_client().get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise FetchError(f"요청 실패: {url} ({exc})") from exc
        return response.text

    def _get_html_playwright(self, url: str, wait_selector: str | None, scroll_times: int) -> str:
        page = self._playwright_page()
        page.goto(url, wait_until="domcontentloaded", timeout=int(self.timeout * 1000))
        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=int(self.timeout * 1000))
            except Exception as exc:
                raise FetchError(
                    f"wait_selector({wait_selector!r})가 나타나지 않았다: {url} ({exc})"
                ) from exc
        for _ in range(max(0, scroll_times)):
            page.mouse.wheel(0, 20000)
            page.wait_for_timeout(800)  # 무한스크롤 로딩 대기
        return page.content()

    def get_bytes(self, url: str) -> bytes:
        """이미지 등 바이너리. 이미지는 항상 httpx로 받는다(브라우저 렌더 불필요)."""
        import httpx

        if not self.robots.allowed(url):
            raise FetchError(f"robots.txt가 이 이미지 수집을 금지한다: {url}")
        self.limiter.wait()
        try:
            response = self._httpx_client().get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise FetchError(f"이미지 요청 실패: {url} ({exc})") from exc
        return response.content
