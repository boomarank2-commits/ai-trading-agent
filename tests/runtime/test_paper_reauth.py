from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from runtime import paper_testbot_freqtrade


@contextmanager
def installed_test_route() -> Iterator[FastAPI]:
    from freqtrade.rpc.api_server.webserver import ApiServer

    original = ApiServer.configure_app

    def fake_freqtrade_configure(self, app: FastAPI, config: dict[str, object]) -> None:
        del self, config

        @app.get("/{rest_of_path:path}")
        async def ui_fallback(rest_of_path: str) -> dict[str, str]:
            return {"fallback": rest_of_path}

    try:
        ApiServer.configure_app = fake_freqtrade_configure
        paper_testbot_freqtrade.install_testbot_login_route()
        # Installation is intentionally idempotent.
        paper_testbot_freqtrade.install_testbot_login_route()
        app = FastAPI()
        ApiServer.configure_app(object(), app, {})
        yield app
    finally:
        ApiServer.configure_app = original


def test_fresh_login_route_precedes_ui_fallback_and_is_not_cached() -> None:
    with installed_test_route() as app, TestClient(app) as client:
        paths: list[str] = []
        for route in app.routes:
            if hasattr(route, "path"):
                paths.append(route.path)
                continue
            included_router = getattr(route, "original_router", None)
            if included_router is not None:
                paths.extend(
                    child.path
                    for child in included_router.routes
                    if hasattr(child, "path")
                )
        assert paths.index("/testbot-login") < paths.index("/{rest_of_path:path}")
        assert paths.count("/testbot-login") == 1

        response = client.get("/testbot-login")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert response.headers["cache-control"] == "no-store, max-age=0"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        assert response.headers["x-content-type-options"] == "nosniff"


def test_bootstrap_clears_only_this_origin_login_and_contains_no_credentials() -> None:
    with installed_test_route() as app, TestClient(app) as client:
        html = client.get("/testbot-login").text

    assert 'var authKey = "ftAuthLoginInfo"' in html
    assert 'var selectedKey = "ftSelectedBot"' in html
    assert "candidate.origin === window.location.origin" in html
    assert "delete records[botId]" in html
    assert "removed[selected]" in html
    assert 'location.replace("/login?redirect=%2Fdashboard")' in html
    assert "localStorage.clear" not in html
    assert "PaperOnly-250-USDT" not in html
    assert "FREQTRADE__API_SERVER__PASSWORD" not in html
    assert "accessToken =" not in html


def test_main_installs_login_before_delegating(monkeypatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(
        paper_testbot_freqtrade,
        "install_testbot_login_route",
        lambda: calls.append("login"),
    )
    monkeypatch.setattr(
        paper_testbot_freqtrade,
        "paper_main",
        lambda argv: calls.append(list(argv or [])) or 7,
    )

    assert paper_testbot_freqtrade.main(["--", "trade"]) == 7
    assert calls == ["login", ["--", "trade"]]
