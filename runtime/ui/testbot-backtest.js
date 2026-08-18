(() => {
  "use strict";

  const VIEW_ID = "testbot-backtest-view";
  const NAV_ID = "testbot-backtest-nav";
  let pollTimer = null;

  function replaceText(node, from, to) {
    if (node.nodeType === Node.TEXT_NODE) {
      if (node.nodeValue && node.nodeValue.includes(from)) {
        node.nodeValue = node.nodeValue.replace(from, to);
      }
      return;
    }
    node.childNodes.forEach((child) => replaceText(child, from, to));
  }

  function hideBacktest() {
    const view = document.getElementById(VIEW_ID);
    if (view) view.style.display = "none";
    const nav = document.getElementById(NAV_ID);
    if (nav) {
      nav.style.color = "";
      nav.style.borderColor = "";
    }
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function money(value) {
    const number = Number(value || 0);
    return `${number > 0 ? "+" : ""}${number.toFixed(2)} USDT`;
  }

  function percent(value) {
    const number = Number(value || 0);
    return `${number > 0 ? "+" : ""}${number.toFixed(2)} %`;
  }

  function resultCard(label, value, className = "") {
    return `<div class="tb-metric"><div class="tb-label">${label}</div><div class="tb-value ${className}">${value}</div></div>`;
  }

  function createView() {
    let view = document.getElementById(VIEW_ID);
    if (view) return view;

    const logsLink = Array.from(document.querySelectorAll("a")).find(
      (anchor) => anchor.textContent && anchor.textContent.trim() === "Logs"
    );
    const navBottom = logsLink
      ? Math.max(90, Math.round(logsLink.closest("header")?.getBoundingClientRect().bottom || logsLink.parentElement?.getBoundingClientRect().bottom || 95))
      : 95;

    view = document.createElement("div");
    view.id = VIEW_ID;
    view.innerHTML = `
      <style>
        #${VIEW_ID} { position: fixed; left: 0; right: 0; bottom: 0; top: ${navBottom}px; z-index: 60; overflow: auto; background: #101619; color: #d6e0e4; font-family: inherit; }
        #${VIEW_ID} * { box-sizing: border-box; }
        .tb-wrap { max-width: 1180px; margin: 0 auto; padding: 28px 30px 60px; }
        .tb-title { font-size: 25px; font-weight: 600; margin: 0 0 7px; color: #f2f6f7; }
        .tb-sub { margin: 0 0 26px; color: #93a5ad; line-height: 1.55; }
        .tb-panel { background: #171e22; border: 1px solid #26343a; border-radius: 4px; padding: 22px; margin-bottom: 20px; }
        .tb-row { display: grid; grid-template-columns: minmax(220px, 1fr) minmax(220px, 1fr) auto; gap: 18px; align-items: end; }
        .tb-field label { display: block; color: #aebdc3; font-size: 13px; margin-bottom: 7px; }
        .tb-field select { width: 100%; height: 42px; border-radius: 4px; border: 1px solid #35454c; background: #101619; color: #edf5f7; padding: 0 12px; font: inherit; outline: none; }
        .tb-button { height: 42px; border: 1px solid #00b8d4; border-radius: 4px; background: #062e36; color: #00d2ee; font-weight: 600; padding: 0 22px; cursor: pointer; font: inherit; white-space: nowrap; }
        .tb-button:disabled { opacity: .55; cursor: not-allowed; }
        .tb-info { margin-top: 17px; color: #879ba4; font-size: 13px; line-height: 1.55; }
        .tb-status, .tb-results { display: none; }
        .tb-status-line { display: flex; justify-content: space-between; gap: 20px; margin-bottom: 10px; }
        .tb-stage { color: #d9e5e8; }
        .tb-progress-text { color: #88a0aa; }
        .tb-progress { height: 8px; background: #0d1215; border: 1px solid #253239; overflow: hidden; border-radius: 4px; }
        .tb-progress > div { height: 100%; width: 0; background: #00b8d4; transition: width .25s ease; }
        .tb-error { margin-top: 14px; padding: 12px 14px; border: 1px solid #743d3d; background: #2c1818; color: #ffb6b6; border-radius: 4px; display: none; white-space: pre-wrap; }
        .tb-result-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 18px; gap: 20px; }
        .tb-result-head h2 { font-size: 18px; margin: 0; color: #eaf2f4; }
        .tb-result-meta { color: #78909a; font-size: 12px; }
        .tb-grid { display: grid; grid-template-columns: repeat(4, minmax(150px, 1fr)); gap: 12px; }
        .tb-metric { background: #101619; border: 1px solid #29383e; padding: 16px; min-height: 82px; }
        .tb-label { font-size: 12px; color: #81959e; margin-bottom: 8px; }
        .tb-value { color: #e4eef1; font-size: 20px; font-weight: 600; }
        .tb-positive { color: #6fd39a; }
        .tb-negative { color: #ff7f7f; }
        .tb-neutral { color: #e4eef1; }
        .tb-note { margin-top: 18px; padding-top: 15px; border-top: 1px solid #26343a; color: #81959e; font-size: 12px; line-height: 1.6; }
        @media (max-width: 850px) { .tb-row { grid-template-columns: 1fr; } .tb-grid { grid-template-columns: repeat(2, 1fr); } .tb-button { width: 100%; } }
        @media (max-width: 520px) { .tb-wrap { padding: 20px 14px 45px; } .tb-grid { grid-template-columns: 1fr; } }
      </style>
      <div class="tb-wrap">
        <h1 class="tb-title">Backtest</h1>
        <p class="tb-sub">Simuliert exakt den aktuell gestarteten adaptiven Testbot mit historischen Binance-Daten. Der Backtest besitzt keine zweite Strategie und schaltet keine Strategien von außen um.</p>
        <div class="tb-panel">
          <div class="tb-row">
            <div class="tb-field">
              <label for="tb-pair">Handelspaar</label>
              <select id="tb-pair">
                <option value="BTC/USDT">Bitcoin · BTC/USDT</option>
                <option value="ETH/USDT">Ethereum · ETH/USDT</option>
                <option value="SOL/USDT">Solana · SOL/USDT</option>
              </select>
            </div>
            <div class="tb-field">
              <label for="tb-years">Zeitraum</label>
              <select id="tb-years">
                <option value="1">1 Jahr</option>
                <option value="2" selected>2 Jahre</option>
                <option value="3">3 Jahre</option>
              </select>
            </div>
            <button id="tb-start" class="tb-button">Backtest starten</button>
          </div>
          <div class="tb-info">Es werden ausschließlich 15m-, 1m-, 1h- und 4h-Kerzen des ausgewählten Coins geladen. BTC, ETH und SOL verwenden keine gegenseitigen Marktregime. V12.8 kombiniert pro Coin den bislang stärksten pair-lokalen Donchian-Kern: BTC mit dem bewährten Volumenfilter, ETH mit dem V12.7-Qualitätsfilter und SOL wieder mit dem breiteren V12.5-Kern. Nur SOL testet zusätzlich einen Gewinnschutz: ab +5 % wird ein Stop-Boden bei +1 % über Einstieg nachgezogen. Der feste -5,5-%-Hard-Stop bleibt bestehen. 1m dient der genaueren Fill-/Stop-Simulation.</div>
        </div>
        <div id="tb-status" class="tb-panel tb-status">
          <div class="tb-status-line"><span id="tb-stage" class="tb-stage">Bereit</span><span id="tb-progress-text" class="tb-progress-text">0 %</span></div>
          <div class="tb-progress"><div id="tb-progress-bar"></div></div>
          <div id="tb-error" class="tb-error"></div>
        </div>
        <div id="tb-results" class="tb-panel tb-results">
          <div class="tb-result-head"><h2>Ergebnis</h2><div id="tb-result-meta" class="tb-result-meta"></div></div>
          <div id="tb-grid" class="tb-grid"></div>
          <div id="tb-note" class="tb-note"></div>
        </div>
      </div>`;
    document.body.appendChild(view);
    document.getElementById("tb-start").addEventListener("click", startBacktest);
    return view;
  }

  function renderState(state) {
    const status = document.getElementById("tb-status");
    const results = document.getElementById("tb-results");
    const button = document.getElementById("tb-start");
    if (!status || !results || !button) return;

    const active = state.status === "running";
    button.disabled = active;
    status.style.display = state.status === "idle" ? "none" : "block";
    document.getElementById("tb-stage").textContent = state.stage || "Bereit";
    document.getElementById("tb-progress-text").textContent = `${Number(state.progress || 0)} %`;
    document.getElementById("tb-progress-bar").style.width = `${Math.max(0, Math.min(100, Number(state.progress || 0)))}%`;

    const error = document.getElementById("tb-error");
    if (state.status === "failed" && state.error) {
      error.textContent = state.error;
      error.style.display = "block";
    } else {
      error.style.display = "none";
      error.textContent = "";
    }

    if (state.status === "completed" && state.result) {
      const r = state.result;
      const profitClass = Number(r.profit_usdt) > 0 ? "tb-positive" : Number(r.profit_usdt) < 0 ? "tb-negative" : "tb-neutral";
      results.style.display = "block";
      document.getElementById("tb-result-meta").textContent = `${r.pair} · ${r.years} Jahr${Number(r.years) === 1 ? "" : "e"} · ${r.timeframe} / Detail ${r.timeframe_detail}`;
      document.getElementById("tb-grid").innerHTML = [
        resultCard("Gewinn / Verlust", money(r.profit_usdt), profitClass),
        resultCard("Rendite", percent(r.profit_pct), profitClass),
        resultCard("Endkapital", `${Number(r.final_balance_usdt || 0).toFixed(2)} USDT`, profitClass),
        resultCard("Trades", String(r.trades), "tb-neutral"),
        resultCard("Profit Factor", Number(r.profit_factor || 0).toFixed(2), Number(r.profit_factor) >= 1 ? "tb-positive" : "tb-negative"),
        resultCard("Trefferquote", `${Number(r.winrate_pct || 0).toFixed(2)} %`, "tb-neutral"),
        resultCard("Max. Drawdown", `${Number(r.max_drawdown_pct || 0).toFixed(2)} %`, Number(r.max_drawdown_pct) > 15 ? "tb-negative" : "tb-neutral"),
        resultCard("Startkapital", `${Number(r.starting_balance_usdt || 250).toFixed(2)} USDT`, "tb-neutral")
      ].join("");
      const independence = r.cross_pair_context === false ? "Pair-unabhängig: ja" : "Pair-unabhängig: nicht bestätigt";
      const adaptive = r.adaptive_router ? "Adaptiver Router: aktiv" : "Adaptiver Router: nicht bestätigt";
      document.getElementById("tb-note").textContent = `Getestet wurde exakt ${r.strategy} mit Strategie-Hash ${String(r.strategy_sha256 || "").slice(0, 16)}… . ${adaptive}. ${independence}. Tatsächlicher Zeitraum: ${r.backtest_start || "?"} bis ${r.backtest_end || "?"} (${Number(r.backtest_days || 0)} Tage). Kerzendaten: ${r.data_integrity_validated ? "Lücken/Duplikate/Abdeckung geprüft" : "keine Integritätsbestätigung"}.`;
    } else if (state.status === "running") {
      results.style.display = "none";
    }
  }

  async function loadStatus() {
    try {
      const response = await fetch("/api/v1/testbot/backtest/status", { cache: "no-store" });
      if (!response.ok) return;
      renderState(await response.json());
    } catch (_error) {}
  }

  async function startBacktest() {
    const pair = document.getElementById("tb-pair").value;
    const years = Number(document.getElementById("tb-years").value);
    const button = document.getElementById("tb-start");
    button.disabled = true;
    try {
      const response = await fetch("/api/v1/testbot/backtest/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pair, years })
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Backtest konnte nicht gestartet werden.");
      renderState(payload);
      if (!pollTimer) pollTimer = setInterval(loadStatus, 1000);
    } catch (error) {
      renderState({ status: "failed", stage: "Fehler", progress: 100, error: String(error.message || error) });
      button.disabled = false;
    }
  }

  function showBacktest(event) {
    if (event) event.preventDefault();
    const view = createView();
    view.style.display = "block";
    const nav = document.getElementById(NAV_ID);
    if (nav) {
      nav.style.color = "#00d2ee";
      nav.style.borderColor = "#00b8d4";
    }
    loadStatus();
    if (!pollTimer) pollTimer = setInterval(loadStatus, 1000);
  }

  function findThemeControl(header, logsLink) {
    if (!header) return null;
    const controls = Array.from(header.querySelectorAll("button, [role='button']"));
    const namedThemeControl = controls.find((control) => {
      const label = `${control.getAttribute("aria-label") || ""} ${control.getAttribute("title") || ""}`.toLowerCase();
      return label.includes("theme") || label.includes("dark") || label.includes("light") || label.includes("mode");
    });
    if (namedThemeControl) return namedThemeControl;

    const logsRect = logsLink.getBoundingClientRect();
    const controlsToRight = controls.filter(
      (control) => control !== logsLink && control.getBoundingClientRect().left > logsRect.left
    );
    if (!controlsToRight.length) return null;
    return controlsToRight.reduce((rightmost, control) =>
      control.getBoundingClientRect().left > rightmost.getBoundingClientRect().left ? control : rightmost
    );
  }

  function installNavigation() {
    if (document.getElementById(NAV_ID)) return true;
    const logsLink = Array.from(document.querySelectorAll("a")).find(
      (anchor) => anchor.textContent && anchor.textContent.trim() === "Logs"
    );
    if (!logsLink || !logsLink.parentElement) return false;

    const backtest = logsLink.cloneNode(true);
    backtest.id = NAV_ID;
    backtest.removeAttribute("href");
    backtest.setAttribute("role", "button");
    backtest.setAttribute("title", "Backtest");
    replaceText(backtest, "Logs", "Backtest");
    backtest.addEventListener("click", showBacktest);

    const header = logsLink.closest("header");
    const themeControl = findThemeControl(header, logsLink);
    if (themeControl && themeControl.parentElement) {
      themeControl.parentElement.insertBefore(backtest, themeControl);
    } else {
      logsLink.parentElement.insertBefore(backtest, logsLink.nextSibling);
    }

    document.addEventListener("click", (event) => {
      const anchor = event.target.closest && event.target.closest("a");
      if (anchor && anchor.id !== NAV_ID) hideBacktest();
    }, true);
    return true;
  }

  const observer = new MutationObserver(() => installNavigation());
  observer.observe(document.documentElement, { childList: true, subtree: true });
  installNavigation();
})();