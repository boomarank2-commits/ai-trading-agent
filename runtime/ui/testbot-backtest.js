(() => {
  "use strict";

  const VIEW_ID = "testbot-backtest-view";
  const NAV_ID = "testbot-backtest-nav";
  const PAIRS = [
    ["BTC/USDT", "Bitcoin"],
    ["ETH/USDT", "Ethereum"],
    ["SOL/USDT", "Solana"],
    ["XRP/USDT", "XRP"],
    ["BNB/USDT", "BNB"],
    ["DOGE/USDT", "Dogecoin"],
    ["LINK/USDT", "Chainlink"],
    ["TRX/USDT", "TRON"],
    ["LTC/USDT", "Litecoin"],
    ["BCH/USDT", "Bitcoin Cash"]
  ];

  let pollTimer = null;
  let batchRunning = false;
  let batchResults = [];

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

  function pairLabel(pair) {
    const found = PAIRS.find(([value]) => value === pair);
    return found ? `${found[1]} · ${found[0]}` : pair;
  }

  function resultCard(label, value, className = "") {
    return `<div class="tb-metric"><div class="tb-label">${label}</div><div class="tb-value ${className}">${value}</div></div>`;
  }

  function breakdownText(items, emptyText) {
    if (!Array.isArray(items) || !items.length) return emptyText;
    return items.map((item) => {
      const label = String(item.label || "?");
      const trades = Number(item.trades || 0);
      const wins = Number(item.wins || 0);
      const pnl = money(item.profit_usdt || 0);
      return `${label}: ${trades} Trades · ${wins} Gewinner · ${pnl}`;
    }).join(" | ");
  }

  function pairOptions() {
    return PAIRS.map(([pair, name]) => `<option value="${pair}">${name} · ${pair}</option>`).join("");
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
        .tb-row { display: grid; grid-template-columns: minmax(240px, 1fr) minmax(180px, .55fr) auto; gap: 18px; align-items: end; }
        .tb-actions { display: flex; gap: 10px; align-items: end; }
        .tb-field label { display: block; color: #aebdc3; font-size: 13px; margin-bottom: 7px; }
        .tb-field select { width: 100%; height: 42px; border-radius: 4px; border: 1px solid #35454c; background: #101619; color: #edf5f7; padding: 0 12px; font: inherit; outline: none; }
        .tb-button { height: 42px; border: 1px solid #00b8d4; border-radius: 4px; background: #062e36; color: #00d2ee; font-weight: 600; padding: 0 22px; cursor: pointer; font: inherit; white-space: nowrap; }
        .tb-button-secondary { border-color: #8ba0a9; background: #1a2429; color: #dce8ec; }
        .tb-button:disabled { opacity: .55; cursor: not-allowed; }
        .tb-info { margin-top: 17px; color: #879ba4; font-size: 13px; line-height: 1.6; }
        .tb-info strong { color: #bdcbd0; }
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
        .tb-note { margin-top: 18px; padding-top: 15px; border-top: 1px solid #26343a; color: #81959e; font-size: 12px; line-height: 1.6; white-space: pre-line; }
        .tb-batch-table-wrap { overflow-x: auto; }
        .tb-batch-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .tb-batch-table th, .tb-batch-table td { padding: 10px 12px; border-bottom: 1px solid #29383e; text-align: right; white-space: nowrap; }
        .tb-batch-table th:first-child, .tb-batch-table td:first-child { text-align: left; }
        .tb-batch-table th { color: #91a5ad; font-weight: 600; }
        .tb-batch-table td { color: #dce7ea; }
        .tb-batch-ok { color: #6fd39a !important; }
        .tb-batch-fail { color: #ff7f7f !important; }
        @media (max-width: 900px) { .tb-row { grid-template-columns: 1fr; } .tb-grid { grid-template-columns: repeat(2, 1fr); } .tb-actions { flex-direction: column; } .tb-button { width: 100%; } }
        @media (max-width: 520px) { .tb-wrap { padding: 20px 14px 45px; } .tb-grid { grid-template-columns: 1fr; } }
      </style>
      <div class="tb-wrap">
        <h1 class="tb-title">Backtest · 10 Kryptowährungen</h1>
        <p class="tb-sub">Jeder Coin wird separat mit einem eigenen virtuellen Startwert von 250 USDT getestet. Zeitraum und Coin sind frei wählbar.</p>
        <div class="tb-panel">
          <div class="tb-row">
            <div class="tb-field">
              <label for="tb-pair">Kryptowährung</label>
              <select id="tb-pair">${pairOptions()}</select>
            </div>
            <div class="tb-field">
              <label for="tb-years">Zeitraum</label>
              <select id="tb-years">
                <option value="1">1 Jahr</option>
                <option value="2">2 Jahre</option>
                <option value="3" selected>3 Jahre</option>
              </select>
            </div>
            <div class="tb-actions">
              <button id="tb-start" class="tb-button">Backtest starten</button>
              <button id="tb-start-all" class="tb-button tb-button-secondary">Alle 10 nacheinander</button>
            </div>
          </div>
          <div class="tb-info">
            <strong>Einzeltest:</strong> Der gewählte Coin startet mit einem eigenen 250-USDT-Testwallet und simuliert exakt die aktuelle V12.17-Strategie. Ein Entry-Block beträgt höchstens 80 USDT. Falls derselbe Coin später erneut ein vollständiges Entry-Signal erzeugt, darf die Simulation – genau wie der Paperbot – einen zweiten oder dritten 80-USDT-Block ergänzen.<br><br>
            <strong>Alle 10 nacheinander:</strong> Der aktuell gewählte Zeitraum gilt für alle zehn Coins. Bei 2 Jahren entstehen also zehn voneinander unabhängige 2-Jahres-Backtests mit jeweils 250 USDT Startwert. Das entspricht nominell 2.500 USDT über zehn getrennte Simulationen, ist aber ausdrücklich <strong>kein gemeinsames 2.500-USDT-Portfolio</strong>.<br><br>
            <strong>Getrennt vom Paperbot:</strong> Der laufende Paperbot besitzt nur ein gemeinsames 250-USDT-Wallet und insgesamt maximal drei 80-USDT-Blöcke über alle zehn Coins. Der spätere Gesamt-Systembacktest dieses gemeinsamen 3×80-Wallets ist ein eigener Test und gehört nicht zum Knopf „Alle 10 nacheinander“.
          </div>
        </div>
        <div id="tb-status" class="tb-panel tb-status">
          <div class="tb-status-line"><span id="tb-stage" class="tb-stage">Bereit</span><span id="tb-progress-text" class="tb-progress-text">0 %</span></div>
          <div class="tb-progress"><div id="tb-progress-bar"></div></div>
          <div id="tb-error" class="tb-error"></div>
        </div>
        <div id="tb-results" class="tb-panel tb-results">
          <div class="tb-result-head"><h2>Einzelergebnis</h2><div id="tb-result-meta" class="tb-result-meta"></div></div>
          <div id="tb-grid" class="tb-grid"></div>
          <div id="tb-note" class="tb-note"></div>
        </div>
        <div id="tb-batch-results" class="tb-panel tb-results">
          <div class="tb-result-head"><h2 id="tb-batch-title">Alle 10 Einzeltests</h2><div id="tb-batch-meta" class="tb-result-meta"></div></div>
          <div class="tb-batch-table-wrap">
            <table class="tb-batch-table">
              <thead><tr><th>Coin</th><th>Gewinn / Verlust</th><th>USDT / Tag</th><th>Trades</th><th>Profit Factor</th><th>Drawdown</th><th>Trefferquote</th><th>Status</th></tr></thead>
              <tbody id="tb-batch-body"></tbody>
            </table>
          </div>
        </div>
      </div>`;

    document.body.appendChild(view);
    document.getElementById("tb-start").addEventListener("click", startBacktest);
    document.getElementById("tb-start-all").addEventListener("click", startAllBacktests);
    return view;
  }

  function renderState(state) {
    const status = document.getElementById("tb-status");
    const results = document.getElementById("tb-results");
    const button = document.getElementById("tb-start");
    const allButton = document.getElementById("tb-start-all");
    if (!status || !results || !button || !allButton) return;

    const active = state.status === "running" || batchRunning;
    button.disabled = active;
    allButton.disabled = active;
    status.style.display = state.status === "idle" ? "none" : "block";
    const stageText = String(state.stage || "Bereit").replaceAll("V12.15", "V12.17");
    document.getElementById("tb-stage").textContent = stageText;
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
      const profit = Number(r.profit_usdt || 0);
      const trades = Number(r.trades || 0);
      const days = Math.max(1, Number(r.backtest_days || 0));
      const profitPerDay = profit / days;
      const tradesPerYear = (trades / days) * 365.25;
      const profitClass = profit > 0 ? "tb-positive" : profit < 0 ? "tb-negative" : "tb-neutral";
      results.style.display = "block";
      document.getElementById("tb-result-meta").textContent = `${pairLabel(r.pair)} · ${r.years} Jahr${Number(r.years) === 1 ? "" : "e"} · Start 250 USDT`;
      document.getElementById("tb-grid").innerHTML = [
        resultCard("Gewinn / Verlust", money(profit), profitClass),
        resultCard("USDT / Tag", money(profitPerDay), profitClass),
        resultCard("Rendite", percent(r.profit_pct), profitClass),
        resultCard("Endkapital", `${Number(r.final_balance_usdt || 0).toFixed(2)} USDT`, profitClass),
        resultCard("Trades", String(trades), "tb-neutral"),
        resultCard("Trades / Jahr", tradesPerYear.toFixed(2), "tb-neutral"),
        resultCard("Profit Factor", Number(r.profit_factor || 0).toFixed(2), Number(r.profit_factor) >= 1 ? "tb-positive" : "tb-negative"),
        resultCard("Trefferquote", `${Number(r.winrate_pct || 0).toFixed(2)} %`, "tb-neutral"),
        resultCard("Max. Drawdown", `${Number(r.max_drawdown_pct || 0).toFixed(2)} %`, Number(r.max_drawdown_pct) > 15 ? "tb-negative" : "tb-neutral"),
        resultCard("Startkapital", `${Number(r.starting_balance_usdt || 250).toFixed(2)} USDT`, "tb-neutral")
      ].join("");

      const entries = breakdownText(r.entry_tag_breakdown, "Keine Entry-Attribution verfügbar");
      const exits = breakdownText(r.exit_reason_breakdown, "Keine Exit-Attribution verfügbar");
      const experiment = r.experiment || {};
      const identity = r.test_identity || {};
      const fileAudit = r.execution_file_audit || {};
      const auditText = fileAudit.passed ? "Datei-/Candle-Audit bestanden" : "keine Audit-Bestätigung";
      document.getElementById("tb-note").textContent = `Aktuelle Strategie: V12.17 / ${r.strategy}. Experiment ${experiment.experiment_id || "?"}. Strategie-Hash ${String(r.strategy_sha256 || "").slice(0, 16)}… · Test-Fingerprint ${String(identity.test_fingerprint || "").slice(0, 16)}… . Tatsächlicher Zeitraum: ${r.backtest_start || "?"} bis ${r.backtest_end || "?"} (${Number(r.backtest_days || 0)} Tage). ${auditText}.\nEntry-Familien: ${entries}\nExit-Gründe: ${exits}`;
    } else if (state.status === "running") {
      results.style.display = "none";
    }
  }

  function renderBatchResults(completed, total, years, currentLabel = "") {
    const panel = document.getElementById("tb-batch-results");
    const meta = document.getElementById("tb-batch-meta");
    const title = document.getElementById("tb-batch-title");
    const body = document.getElementById("tb-batch-body");
    if (!panel || !meta || !body || !title) return;

    panel.style.display = "block";
    title.textContent = `Alle 10 Einzeltests · ${years} Jahr${years === 1 ? "" : "e"}`;
    meta.textContent = batchRunning
      ? `${completed}/${total} abgeschlossen${currentLabel ? ` · läuft: ${currentLabel}` : ""}`
      : `${completed}/${total} abgeschlossen · je Test 250 USDT Startwert`;

    body.innerHTML = batchResults.map((item) => {
      const label = pairLabel(item.pair);
      if (item.error) {
        if (item.skipped) {
          return `<tr><td>${label}</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td class="tb-neutral">Doppeltest übersprungen</td></tr>`;
        }
        return `<tr><td>${label}</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td class="tb-batch-fail">Fehler</td></tr>`;
      }
      const r = item.result;
      const profit = Number(r.profit_usdt || 0);
      const days = Math.max(1, Number(r.backtest_days || 0));
      const profitPerDay = profit / days;
      const profitClass = profit > 0 ? "tb-batch-ok" : profit < 0 ? "tb-batch-fail" : "";
      return `<tr><td>${label}</td><td class="${profitClass}">${money(profit)}</td><td class="${profitClass}">${money(profitPerDay)}</td><td>${Number(r.trades || 0)}</td><td>${Number(r.profit_factor || 0).toFixed(2)}</td><td>${Number(r.max_drawdown_pct || 0).toFixed(2)} %</td><td>${Number(r.winrate_pct || 0).toFixed(2)} %</td><td class="tb-batch-ok">Fertig</td></tr>`;
    }).join("");
  }

  async function fetchStatus() {
    const response = await fetch("/api/v1/testbot/backtest/status", { cache: "no-store" });
    if (!response.ok) throw new Error("Backtest-Status konnte nicht geladen werden.");
    return response.json();
  }

  async function loadStatus() {
    try {
      renderState(await fetchStatus());
    } catch (_error) {}
  }

  async function startOneBacktest(pair, years) {
    const response = await fetch("/api/v1/testbot/backtest/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pair, years })
    });
    const payload = await response.json();
    if (!response.ok) {
      const error = new Error(payload.detail || "Backtest konnte nicht gestartet werden.");
      error.isDuplicate = response.status === 409 && String(payload.detail || "").startsWith("Doppeltest blockiert:");
      throw error;
    }
    renderState(payload);

    while (true) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      const state = await fetchStatus();
      renderState(state);
      if (state.status === "completed") return state.result;
      if (state.status === "failed") {
        throw new Error(state.error || "Backtest ist fehlgeschlagen.");
      }
    }
  }

  async function startBacktest() {
    const pair = document.getElementById("tb-pair").value;
    const years = Number(document.getElementById("tb-years").value);
    const button = document.getElementById("tb-start");
    const allButton = document.getElementById("tb-start-all");
    button.disabled = true;
    allButton.disabled = true;
    try {
      const response = await fetch("/api/v1/testbot/backtest/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pair, years })
      });
      const payload = await response.json();
      if (!response.ok) {
        const error = new Error(payload.detail || "Backtest konnte nicht gestartet werden.");
        error.isDuplicate = response.status === 409 && String(payload.detail || "").startsWith("Doppeltest blockiert:");
        throw error;
      }
      renderState(payload);
      if (!pollTimer) pollTimer = setInterval(loadStatus, 1000);
    } catch (error) {
      renderState({ status: "failed", stage: error.isDuplicate ? "Doppeltest blockiert" : "Fehler", progress: 100, error: String(error.message || error) });
      button.disabled = false;
      allButton.disabled = false;
    }
  }

  async function startAllBacktests() {
    if (batchRunning) return;

    const singleButton = document.getElementById("tb-start");
    const allButton = document.getElementById("tb-start-all");
    const pairSelect = document.getElementById("tb-pair");
    const yearsSelect = document.getElementById("tb-years");
    const years = Number(yearsSelect.value);
    const cases = PAIRS.map(([pair]) => ({ pair, years }));

    try {
      const current = await fetchStatus();
      if (current.status === "running") {
        throw new Error("Es läuft bereits ein Backtest. Bitte diesen zuerst beenden lassen.");
      }
    } catch (error) {
      renderState({ status: "failed", stage: "Fehler", progress: 100, error: String(error.message || error) });
      return;
    }

    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }

    batchRunning = true;
    batchResults = [];
    singleButton.disabled = true;
    allButton.disabled = true;
    pairSelect.disabled = true;
    yearsSelect.disabled = true;
    renderBatchResults(0, cases.length, years, "wird vorbereitet");

    for (let index = 0; index < cases.length; index += 1) {
      const test = cases[index];
      const label = pairLabel(test.pair);
      pairSelect.value = test.pair;
      renderBatchResults(batchResults.length, cases.length, years, label);

      try {
        const result = await startOneBacktest(test.pair, test.years);
        batchResults.push({ ...test, result });
      } catch (error) {
        batchResults.push({ ...test, error: String(error.message || error), skipped: Boolean(error.isDuplicate) });
      }
      renderBatchResults(batchResults.length, cases.length, years, "");
    }

    batchRunning = false;
    singleButton.disabled = false;
    allButton.disabled = false;
    pairSelect.disabled = false;
    yearsSelect.disabled = false;
    renderBatchResults(batchResults.length, cases.length, years, "");
    if (!pollTimer) pollTimer = setInterval(loadStatus, 1000);
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
