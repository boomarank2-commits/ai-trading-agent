from __future__ import annotations

import base64
import json
import shutil
import subprocess

import pytest

from runtime.patch_frequi import _autologin_script

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js is required for FreqUI hook tests")


def _execute_hook(store: dict, selected: str | None, *, token_valid: bool) -> dict:
    script = _autologin_script("testbot", "local-test-password")
    encoded = base64.b64encode(script.encode("utf-8")).decode("ascii")
    initial_values = {"ftAuthLoginInfo": json.dumps(store, separators=(",", ":"))}
    if selected is not None:
        initial_values["ftSelectedBot"] = selected

    runner = f"""
const values = new Map(Object.entries({json.dumps(initial_values)}));
global.localStorage = {{
  getItem: (key) => values.has(key) ? values.get(key) : null,
  setItem: (key, value) => values.set(key, String(value)),
}};
let reloadCount = 0;
global.window = {{
  location: {{
    origin: 'http://127.0.0.1:8080',
    reload: () => {{ reloadCount += 1; }},
  }},
}};
if (typeof global.btoa !== 'function') {{
  global.btoa = (value) => Buffer.from(value, 'binary').toString('base64');
}}
const calls = [];
global.fetch = async (url) => {{
  calls.push(url);
  if (url === '/api/v1/status') return {{ ok: {str(token_valid).lower()}, status: 200 }};
  if (url === '/api/v1/token/login') {{
    return {{
      ok: true,
      status: 200,
      json: async () => ({{
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
      }}),
    }};
  }}
  throw new Error(`Unexpected fetch: ${{url}}`);
}};
eval(Buffer.from('{encoded}', 'base64').toString('utf8'));
setTimeout(() => {{
  console.log(JSON.stringify({{
    store: JSON.parse(values.get('ftAuthLoginInfo')),
    selected: values.get('ftSelectedBot'),
    reloadCount,
    calls,
  }}));
}}, 100);
"""
    completed = subprocess.run(
        [NODE, "-e", runner],
        capture_output=True,
        check=True,
        text=True,
        timeout=10,
    )
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_valid_stale_bot_record_is_normalized_selected_and_reloaded_once() -> None:
    stale = {
        "ftbot.0": {
            "botName": "freqtrade",
            "apiUrl": "http://127.0.0.1:8080",
            "username": "testbot",
            "accessToken": "valid-access-token",
            "refreshToken": "valid-refresh-token",
            "autoRefresh": False,
            "sortId": 7,
        }
    }

    repaired = _execute_hook(stale, "ftbot.9", token_valid=True)
    bot = repaired["store"]["ftbot.0"]
    assert bot == {
        "botName": "Testbot",
        "apiUrl": "http://127.0.0.1:8080",
        "username": "testbot",
        "accessToken": "valid-access-token",
        "refreshToken": "valid-refresh-token",
        "autoRefresh": True,
        "sortId": 7,
    }
    assert repaired["selected"] == "ftbot.0"
    assert repaired["reloadCount"] == 1
    assert repaired["calls"] == ["/api/v1/status"]

    stable = _execute_hook(repaired["store"], repaired["selected"], token_valid=True)
    assert stable["reloadCount"] == 0
    assert stable["calls"] == ["/api/v1/status"]


def test_expired_token_is_replaced_and_reloads_ui() -> None:
    expired = {
        "ftbot.0": {
            "botName": "Testbot",
            "apiUrl": "http://127.0.0.1:8080",
            "username": "testbot",
            "accessToken": "expired-access-token",
            "refreshToken": "expired-refresh-token",
            "autoRefresh": True,
            "sortId": 0,
        }
    }

    result = _execute_hook(expired, "ftbot.0", token_valid=False)
    bot = result["store"]["ftbot.0"]
    assert bot["accessToken"] == "new-access-token"
    assert bot["refreshToken"] == "new-refresh-token"
    assert result["reloadCount"] == 1
    assert result["calls"] == ["/api/v1/status", "/api/v1/token/login"]
