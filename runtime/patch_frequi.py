"""Install repository-owned Testbot hooks into the installed FreqUI.

FreqUI lives inside the local Python environment and is not tracked in Git.
This patch keeps the Backtest hook and installs a local-only external JavaScript
bootstrap for FreqUI authentication.  Using an external script avoids browser
security policies which may ignore inline JavaScript.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import freqtrade

BACKTEST_TAG = '<script src="/testbot-backtest.js" defer></script>'
AUTOLOGIN_FILENAME = "testbot-autologin.js"
OLD_AUTOLOGIN_START = '<!-- TESTBOT_AUTOLOGIN_START -->'
OLD_AUTOLOGIN_END = '<!-- TESTBOT_AUTOLOGIN_END -->'
AUTOLOGIN_TAG_RE = re.compile(
    r'<script\s+src="/testbot-autologin\.js(?:\?[^\"]*)?"\s+defer></script>'
)


def _remove_old_inline_block(text: str) -> str:
    start = text.find(OLD_AUTOLOGIN_START)
    if start < 0:
        return text
    end = text.find(OLD_AUTOLOGIN_END, start)
    if end < 0:
        raise RuntimeError("FreqUI index contains an incomplete old Testbot autologin block")
    return text[:start] + text[end + len(OLD_AUTOLOGIN_END) :]


def _autologin_script(username: str, password: str) -> str:
    user_js = json.dumps(username)
    password_js = json.dumps(password)
    return f"""(() => {{
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
      localStorage.setItem(SELECTED_KEY, botId);
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
"""


def main() -> int:
    ui_dir = (
        Path(freqtrade.__file__).resolve().parent
        / "rpc"
        / "api_server"
        / "ui"
        / "installed"
    )
    index = ui_dir / "index.html"
    autologin_path = ui_dir / AUTOLOGIN_FILENAME
    if not index.is_file():
        raise RuntimeError(f"FreqUI index not found: {index}")

    text = index.read_text(encoding="utf-8")
    text = _remove_old_inline_block(text)
    text = AUTOLOGIN_TAG_RE.sub("", text)

    marker = "</body>"
    if marker not in text:
        raise RuntimeError("FreqUI index has no </body> marker; refusing unsafe patch")
    if BACKTEST_TAG not in text:
        text = text.replace(marker, f"{BACKTEST_TAG}{marker}", 1)

    username = os.environ.get("FREQTRADE__API_SERVER__USERNAME", "").strip()
    password = os.environ.get("FREQTRADE__API_SERVER__PASSWORD", "")
    if username and password:
        script = _autologin_script(username, password)
        autologin_path.write_text(script, encoding="utf-8", newline="")
        version = hashlib.sha256(f"{username}\0{password}".encode()).hexdigest()[:12]
        tag = f'<script src="/{AUTOLOGIN_FILENAME}?v={version}" defer></script>'
        text = text.replace(marker, f"{tag}{marker}", 1)
    else:
        autologin_path.unlink(missing_ok=True)

    index.write_text(text, encoding="utf-8", newline="")
    verify = index.read_text(encoding="utf-8")
    if verify.count(BACKTEST_TAG) != 1:
        raise RuntimeError("Testbot Backtest UI hook verification failed")
    if username and password:
        if not autologin_path.is_file() or verify.count(AUTOLOGIN_FILENAME) != 1:
            raise RuntimeError("External Testbot FreqUI auto-login hook verification failed")
        print(f"External Testbot FreqUI auto-login installed for {username}: {autologin_path}")
    else:
        if AUTOLOGIN_FILENAME in verify or autologin_path.exists():
            raise RuntimeError("Stale Testbot FreqUI auto-login remains without credentials")
        print(f"Testbot Backtest UI hook installed without auto-login credentials: {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
