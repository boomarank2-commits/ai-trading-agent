"""Official paper-test entrypoint with a deterministic fresh FreqUI login.

FreqUI persists access and refresh tokens in the browser.  The paper launcher
intentionally rotates the server-side JWT key on every start, which makes the
old tokens invalid.  FreqUI 3.1.1 keeps the corresponding bot entry, however,
and can consequently show an empty dashboard instead of its login form.

This wrapper adds one loopback-only, credential-free bootstrap page before
Freqtrade's catch-all UI route.  It removes only the saved browser connection
for this exact origin and then redirects to FreqUI's normal login form.  The
audited exact-strategy loader and all paper safety controls remain in
``paper_locked_freqtrade``.
"""

from __future__ import annotations

import secrets
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI
from starlette.responses import HTMLResponse

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runtime.paper_locked_freqtrade import main as paper_main

_LOGIN_PATH = "/testbot-login"
_LOGIN_ROUTE_NAME = "daviddtech_testbot_fresh_login"
_PATCH_MARKER = "__daviddtech_testbot_login_installed__"

_REAUTH_SCRIPT = r"""
(function () {
  "use strict";
  var authKey = "ftAuthLoginInfo";
  var selectedKey = "ftSelectedBot";
  var removed = Object.create(null);
  try {
    var raw = window.localStorage.getItem(authKey);
    if (raw) {
      var records = JSON.parse(raw);
      if (records && typeof records === "object" && !Array.isArray(records)) {
        Object.keys(records).forEach(function (botId) {
          var record = records[botId];
          if (!record || (typeof record.apiUrl !== "string" && record.apiUrl !== null)) {
            return;
          }
          try {
            var candidate = new URL(
              record.apiUrl || window.location.origin,
              window.location.origin
            );
            if ((candidate.protocol === "http:" || candidate.protocol === "https:") &&
                candidate.origin === window.location.origin) {
              delete records[botId];
              removed[botId] = true;
            }
          } catch (_invalidUrl) {
            // Preserve malformed or unrelated entries instead of deleting broadly.
          }
        });
        if (Object.keys(records).length > 0) {
          window.localStorage.setItem(authKey, JSON.stringify(records));
        } else {
          window.localStorage.removeItem(authKey);
        }
      }
    }
    var selected = window.localStorage.getItem(selectedKey);
    if (selected && removed[selected]) {
      window.localStorage.removeItem(selectedKey);
    }
  } catch (_invalidStorage) {
    // FreqUI handles corrupt storage itself. Never delete unrelated data blindly.
  }
  window.location.replace("/login?redirect=%2Fdashboard");
}());
""".strip()


def _login_html(nonce: str) -> str:
    return (
        "<!doctype html><html lang=\"de\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Testbot-Anmeldung</title></head><body>"
        "<p>Die lokale Testbot-Anmeldung wird vorbereitet.</p>"
        f"<script nonce=\"{nonce}\">{_REAUTH_SCRIPT}</script>"
        "</body></html>"
    )


def _build_login_router() -> APIRouter:
    router = APIRouter(include_in_schema=False)

    @router.get(_LOGIN_PATH, name=_LOGIN_ROUTE_NAME)
    async def fresh_testbot_login() -> HTMLResponse:
        nonce = secrets.token_urlsafe(24)
        return HTMLResponse(
            _login_html(nonce),
            headers={
                "Cache-Control": "no-store, max-age=0",
                "Pragma": "no-cache",
                "Content-Security-Policy": (
                    "default-src 'none'; "
                    f"script-src 'nonce-{nonce}'; "
                    "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
                ),
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
            },
        )

    return router


def install_testbot_login_route() -> None:
    """Install the login bootstrap before Freqtrade adds its UI catch-all."""

    from freqtrade.rpc.api_server.webserver import ApiServer

    current = ApiServer.configure_app
    if bool(getattr(current, _PATCH_MARKER, False)):
        return
    login_router = _build_login_router()

    def configure_with_login(
        self: Any,
        app: FastAPI,
        config: dict[str, Any],
    ) -> Any:
        app.include_router(login_router)
        return current(self, app, config)

    setattr(configure_with_login, _PATCH_MARKER, True)
    ApiServer.configure_app = configure_with_login


def main(argv: list[str] | None = None) -> int:
    install_testbot_login_route()
    return paper_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
