"""Install the repository-owned Testbot UI hooks into the installed FreqUI index.

FreqUI itself is downloaded by Freqtrade into .venv and is therefore not kept
in Git. This patch is intentionally small and idempotent:

* keep the repository-served Backtest navigation hook;
* when STARTBOT provides the localhost FreqUI credentials through environment
  variables, add a local-only bootstrap which repairs stale/missing FreqUI
  tokens automatically.

The bootstrap never enables real trading. It only authenticates the browser to
Freqtrade's already-running localhost API so Dashboard/Chart/Logs can see the
paper bot again after a local password change.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import freqtrade

SCRIPT_TAG = '<script src="/testbot-backtest.js" defer></script>'
AUTOLOGIN_START = '<!-- TESTBOT_AUTOLOGIN_START -->'
AUTOLOGIN_END = '<!-- TESTBOT_AUTOLOGIN_END -->'


def _remove_autologin(text: str) -> str:
    start = text.find(AUTOLOGIN_START)
    if start < 0:
        return text
    end = text.find(AUTOLOGIN_END, start)
    if end < 0:
        raise RuntimeError("FreqUI index contains an incomplete Testbot autologin block")
    return text[:start] + text[end + len(AUTOLOGIN_END) :]


def _autologin_block(username: str, password: str) -> str:
    user_js = json.dumps(username)
    password_js = json.dumps(password)
    return f"""{AUTOLOGIN_START}
<script>
(() => {{
  const TESTBOT_USERNAME = {user_js};
  const TESTBOT_PASSWORD = {password_js};
  const STORAGE_KEY = 'ftAuthLoginInfo';
  const SELECTED_KEY = 'ftSelectedBot';
  const API_URL = window.location.origin;

  const parseStore = () => {{
    try {{
      const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{{}}');
      return value && typeof value === 'object' ? value : {{}};
    }} catch (_) {{
      return {{}};
    }}
  }};

  const chooseBotId = (store) => {{
    for (const [botId, info] of Object.entries(store)) {{
      if (info && info.apiUrl === API_URL) return botId;
    }}
    let index = 0;
    while (store[`ftbot.${{index}}`] && store[`ftbot.${{index}}`].apiUrl !== API_URL) index += 1;
    return `ftbot.${{index}}`;
  }};

  const basicHeader = (username, password) => {{
    const bytes = new TextEncoder().encode(`${{username}}:${{password}}`);
    let binary = '';
    for (const byte of bytes) binary += String.fromCharCode(byte);
    return `Basic ${{btoa(binary)}}`;
  }};

  const tokenWorks = async (token) => {{
    if (!token) return false;
    try {{
      const response = await fetch('/api/v1/status', {{
        headers: {{ Authorization: `Bearer ${{token}}` }},
        cache: 'no-store',
      }});
      return response.ok;
    }} catch (_) {{
      return false;
    }}
  }};

  const login = async () => {{
    const store = parseStore();
    const botId = chooseBotId(store);
    const existing = store[botId] || {{}};

    if (
      existing.apiUrl === API_URL &&
      existing.username === TESTBOT_USERNAME &&
      await tokenWorks(existing.accessToken)
    ) {{
      if (localStorage.getItem(SELECTED_KEY) !== botId) localStorage.setItem(SELECTED_KEY, botId);
      return;
    }}

    const response = await fetch('/api/v1/token/login', {{
      method: 'POST',
      headers: {{
        Authorization: basicHeader(TESTBOT_USERNAME, TESTBOT_PASSWORD),
        'Content-Type': 'application/json',
      }},
      body: '{{}}',
      cache: 'no-store',
    }});
    if (!response.ok) {{
      console.error('Testbot FreqUI auto-login failed:', response.status);
      return;
    }}

    const tokens = await response.json();
    if (!tokens.access_token || !tokens.refresh_token) {{
      console.error('Testbot FreqUI auto-login returned no tokens.');
      return;
    }}

    store[botId] = {{
      botName: 'Testbot',
      apiUrl: API_URL,
      username: TESTBOT_USERNAME,
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      autoRefresh: true,
      sortId: Number.isFinite(existing.sortId) ? existing.sortId : 0,
    }};
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
    localStorage.setItem(SELECTED_KEY, botId);
    window.location.reload();
  }};

  login().catch((error) => console.error('Testbot FreqUI auto-login error:', error));
}})();
</script>
{AUTOLOGIN_END}"""


def main() -> int:
    index = (
        Path(freqtrade.__file__).resolve().parent
        / "rpc"
        / "api_server"
        / "ui"
        / "installed"
        / "index.html"
    )
    if not index.is_file():
        raise RuntimeError(f"FreqUI index not found: {index}")

    text = index.read_text(encoding="utf-8")
    text = _remove_autologin(text)

    marker = "</body>"
    if marker not in text:
        raise RuntimeError("FreqUI index has no </body> marker; refusing unsafe patch")

    if SCRIPT_TAG not in text:
        text = text.replace(marker, f"{SCRIPT_TAG}{marker}", 1)

    username = os.environ.get("FREQTRADE__API_SERVER__USERNAME", "").strip()
    password = os.environ.get("FREQTRADE__API_SERVER__PASSWORD", "")
    if username and password:
        text = text.replace(marker, f"{_autologin_block(username, password)}{marker}", 1)

    index.write_text(text, encoding="utf-8", newline="")
    verify = index.read_text(encoding="utf-8")
    if verify.count(SCRIPT_TAG) != 1:
        raise RuntimeError("Testbot Backtest UI hook verification failed")
    if username and password:
        if verify.count(AUTOLOGIN_START) != 1 or verify.count(AUTOLOGIN_END) != 1:
            raise RuntimeError("Testbot FreqUI auto-login hook verification failed")
        print(f"Testbot FreqUI auto-login installed for {username}: {index}")
    else:
        if AUTOLOGIN_START in verify or AUTOLOGIN_END in verify:
            raise RuntimeError("Stale Testbot FreqUI auto-login hook remains without credentials")
        print(f"Testbot Backtest UI hook installed without auto-login credentials: {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
