(() => {
  "use strict";

  const VIEW_ID = "testbot-backtest-view";
  const NAV_ID = "testbot-backtest-nav";
  const BODY_OPEN_CLASS = "testbot-backtest-open";
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
    document.body.classList.remove(BODY_OPEN_CLASS);
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

  function syncBacktestTop(view) {
    const header = document.querySelector("header");
    const headerBottom = header ? Math.ceil(header.getBoundingClientRect().bottom) : 0;
    view.style.top = `${headerBottom}px`;
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
    if (pair === "PORTFOLIO") return "Alle 10 zusammen · gemeinsames 250-USDT-Wallet";
    const found = PAIRS.find(([value]) => value === pair);
    return found ? `${found[1]} · ${found[0]}` : pair;
  }

  function elapsedText(value) {
    const timestamp = Date.parse(String(value || ""));
    if (!Number.isFinite(timestamp)) return "";
    const seconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
    if (seconds < 60) return `${seconds} s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} min ${seconds % 60} s`;
    return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
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
    view = document.createElement("div");
    view.id = VIEW_ID;
    view.innerHTML = `
      <style>
        body.${BODY_OPEN_CLASS} main { display: none !important; }
        #${VIEW_ID} { position: fixed; left: 0; right: 0; bottom: 0; top: 0; z-index: 60; overflow: auto; background: #101619; color: #d6e0e4; font-family: inherit; }
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
        .tb-batch-error { max-width: 420px; white-space: normal !important; text-align: left !important; line-height: 1.45; }
        .tb-batch-error strong { display: block; margin-bottom: 4px; }
        @media (max-width: 900px) { .tb-row { grid-template-columns: 1fr; } .tb-grid { grid-template-columns: repeat(2, 1fr); } .tb-actions { flex-direction: column; } .tb-button { width: 100%; } }
        @media (max-width: 520px) { .tb-wrap { padding: 20px 14px 45px; } .tb-grid { grid-template-columns: 1fr; } }
      </style>
      <div class="tb-wrap">
        <h1 class="tb-title">Backtest · 10 Kryptowährungen</h1>
        <p class="tb-sub">Ein Coin kann mit eigenen 250 USDT getestet werden. Der gemeinsame Systemtest lässt alle zehn Coins um dasselbe 250-USDT-Wallet und höchstens drei 80-USDT-Blöcke konkurrieren.</p>
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
              <button id="tb-start" class="tb-button">Gewählten Coin testen</button>
              <button id="tb-start-all" class="tb-button">Alle 10 zusammen</button>
              <button id="tb-start-matrix" class="tb-button tb-button-secondary">10 Einzeltests</button>
            </div>
          </div>
          <div class="tb-info">
            <strong>Einzeltest:</strong> Der gewählte Coin startet mit einem eigenen 250-USDT-Testwallet und simuliert exakt die aktuelle V12.18-Strategie.<br><br>
            <strong>Marktdaten:</strong> Vor einem neuen Lauf werden die benötigten 1m-, 15m-, 1h- und 4h-Binance-Kerzen automatisch bis heute aktualisiert. Fehlende ältere Bereiche werden nachgeladen; beschädigte oder lückenhafte Dateien werden für den betroffenen Coin frisch aufgebaut. Die geprüften Daten bleiben unter <code>runtime/user_data/data/binance</code> im Botordner gespeichert und können in späteren Läufen wiederverwendet werden.<br><br>
            <strong>Alle 10 zusammen:</strong> Das ist der echte Systemtest des Paperbots. Alle zehn Coins teilen sich ein einziges 250-USDT-Wallet; gleichzeitig sind höchstens drei Entry-Blöcke zu je maximal 80 USDT beziehungsweise 240 USDT Gesamteinsatz erlaubt.<br><br>
            <strong>Mehrere Blöcke im selben Coin:</strong> Ein zweiter oder dritter Block ist nur bei einem späteren vollständigen Einstiegssignal zulässig, wenn der offene Trade bereits im Gewinn liegt und der neue Kurs über allen vorherigen Einstiegskursen liegt. Verlust-Nachkäufe sind gesperrt.<br><br>
            <strong>10 Einzeltests:</strong> Führt für die Diagnose zehn getrennte Tests mit jeweils eigenen 250 USDT aus. Diese Matrix ist kein gemeinsames Portfolio und wird in der Auswertung getrennt gekennzeichnet.<br><br>
            <strong>Optimierung:</strong> Dieser Bildschirm misst immer den unveränderten aktuellen Bot und ändert keine Parameter automatisch. Ein Coin mit schwachem Ergebnis erhält anschließend eine eigene, dokumentierte Parameter-Hypothese als neue Strategy-Version. Nur wenn deren neue Tests und Robustheitsprüfungen besser sind, darf sie später in den Paperbot übernommen werden.
          </div>
        </div>
        <div id="tb-status" class="tb-panel tb-status">
          <div class="tb-status-line"><span id="tb-stage" class="tb-stage">Bereit</span><span id="tb-progress-text" class="tb-progress-text">0 %</span></div>
          <div class="tb-progress"><div id="tb-progress-bar"></div></div>
          <div id="tb-activity" class="tb-info"></div>
          <div id="tb-error" class="tb-error"></div>
        </div>
        <div id="tb-results" class="tb-panel tb-results">
          <div class="tb-result-head"><h2 id="tb-result-title">Einzelergebnis</h2><div id="tb-result-meta" class="tb-result-meta"></div></div>
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
    syncBacktestTop(view);
    document.getElementById("tb-start").addEventListener("click", startBacktest);
    document.getElementById("tb-start-all").addEventListener("click", startPortfolioBacktest);
    document.getElementById("tb-start-matrix").addEventListener("click", startAllBacktests);
    return view;
  }

  function renderState(state) {
    const status = document.getElementById("tb-status");
    const results = document.getElementById("tb-results");
    const button = document.getElementById("tb-start");
    const allButton = document.getElementById("tb-start-all");
    const matrixButton = document.getElementById("tb-start-matrix");
    if (!status || !results || !button || !allButton || !matrixButton) return;

    const active = state.status === "running" || batchRunning;
    button.disabled = active;
    allButton.disabled = active;
    matrixButton.disabled = active;
    status.style.display = state.status === "idle" ? "none" : "block";
    const stageText = String(state.stage || "Bereit");
    document.getElementById("tb-stage").textContent = stageText;
    document.getElementById("tb-progress-text").textContent = `${Number(state.progress || 0)} %`;
    document.getElementById("tb-progress-bar").style.width = `${Math.max(0, Math.min(100, Number(state.progress || 0)))}%`;
    const activity = document.getElementById("tb-activity");
    if (activity) {
      if (state.status === "running") {
        const stageAge = elapsedText(state.stage_started_at || state.started_at);
        const activityAge = elapsedText(state.last_activity_at);
        activity.textContent = `${state.subprocess_alive ? "Rechen-/Downloadprozess aktiv" : "Ablauf aktiv"}${stageAge ? ` · aktuelle Stufe seit ${stageAge}` : ""}${activityAge ? ` · letzte Protokollaktivität vor ${activityAge}` : ""}. Große 1-Minuten-Datensätze können mehrere Minuten ohne Prozentwechsel benötigen.`;
      } else {
        activity.textContent = "";
      }
    }

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
      document.getElementById("tb-result-title").textContent = r.portfolio_mode ? "Gemeinsames Zehn-Paare-Systemergebnis" : "Einzelergebnis";
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
        resultCard("Startkapital", `${Number(r.starting_balance_usdt || 250).toFixed(2)} USDT`, "tb-neutral"),
        resultCard("Entry-Blöcke gesamt", String(Number(r.total_entry_chunks || 0)), "tb-neutral"),
        resultCard("Zusätzliche Blöcke", String(Number(r.additional_entry_chunks || 0)), "tb-neutral"),
        resultCard("Max. aktive Blöcke", String(Number(r.max_active_entry_chunks || 0)), Number(r.max_active_entry_chunks || 0) > 3 ? "tb-negative" : "tb-neutral"),
        resultCard("Max. Einsatz", `${Number(r.max_deployed_capital_usdt || 0).toFixed(2)} USDT`, Number(r.max_deployed_capital_usdt || 0) > 240.05 ? "tb-negative" : "tb-neutral")
      ].join("");

      const entries = breakdownText(r.entry_tag_breakdown, "Keine Entry-Attribution verfügbar");
      const exits = breakdownText(r.exit_reason_breakdown, "Keine Exit-Attribution verfügbar");
      const experiment = r.experiment || {};
      const identity = r.test_identity || {};
      const fileAudit = r.execution_file_audit || {};
      const auditText = fileAudit.passed ? "Datei-/Candle-Audit bestanden" : "keine Audit-Bestätigung";
      const pairs = Array.isArray(r.pair_breakdown) && r.pair_breakdown.length
        ? r.pair_breakdown.map((item) => `${item.pair}: ${item.trades} Trades · ${item.entry_chunks} Blöcke · ${money(item.profit_usdt)}`).join(" | ")
        : "Keine Paar-Attribution verfügbar";
      document.getElementById("tb-note").textContent = `Aktuelle Strategie: V12.18 / ${r.strategy}. Experiment ${experiment.experiment_id || "?"}. Strategie-Hash ${String(r.strategy_sha256 || "").slice(0, 16)}… · Test-Fingerprint ${String(identity.test_fingerprint || "").slice(0, 16)}… . Tatsächlicher Zeitraum: ${r.backtest_start || "?"} bis ${r.backtest_end || "?"} (${Number(r.backtest_days || 0)} Tage). ${auditText}.\nPaare: ${pairs}\nEntry-Familien: ${entries}\nExit-Gründe: ${exits}`;
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
        const errorText = escapeHtml(item.error);
        if (item.skipped) {
          return `<tr><td>${label}</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td class="tb-neutral tb-batch-error"><strong>Doppeltest übersprungen</strong>${errorText}</td></tr>`;
        }
        return `<tr><td>${label}</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td class="tb-batch-fail tb-batch-error"><strong>Fehler</strong>${errorText}</td></tr>`;
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
    const matrixButton = document.getElementById("tb-start-matrix");
    button.disabled = true;
    allButton.disabled = true;
    matrixButton.disabled = true;
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
      matrixButton.disabled = false;
    }
  }

  async function startPortfolioBacktest() {
    if (batchRunning) return;
    const years = Number(document.getElementById("tb-years").value);
    try {
      await startOneBacktest("PORTFOLIO", years);
    } catch (error) {
      renderState({ status: "failed", stage: error.isDuplicate ? "Doppeltest blockiert" : "Fehler", progress: 100, error: String(error.message || error) });
    }
  }

  async function startAllBacktests() {
    if (batchRunning) return;

    const singleButton = document.getElementById("tb-start");
    const allButton = document.getElementById("tb-start-all");
    const matrixButton = document.getElementById("tb-start-matrix");
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
    matrixButton.disabled = true;
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
    matrixButton.disabled = false;
    pairSelect.disabled = false;
    yearsSelect.disabled = false;
    renderBatchResults(batchResults.length, cases.length, years, "");
    if (!pollTimer) pollTimer = setInterval(loadStatus, 1000);
  }

  function showBacktest(event) {
    if (event) event.preventDefault();
    const view = createView();
    document.body.classList.add(BODY_OPEN_CLASS);
    syncBacktestTop(view);
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
  window.addEventListener("resize", () => {
    const view = document.getElementById(VIEW_ID);
    if (view && view.style.display !== "none") syncBacktestTop(view);
  });
  installNavigation();
})();
