(() => {
  "use strict";

  const VIEW_ID = "testbot-backtest-view";
  const NAV_ID = "testbot-backtest-nav";
  const BATCH_CASES = [
    { pair: "PORTFOLIO", years: 3 },
    { pair: "PORTFOLIO", years: 1 },
    { pair: "BTC/USDT", years: 3 },
    { pair: "BTC/USDT", years: 1 },
    { pair: "ETH/USDT", years: 3 },
    { pair: "ETH/USDT", years: 1 },
    { pair: "SOL/USDT", years: 3 },
    { pair: "SOL/USDT", years: 1 },
    { pair: "XRP/USDT", years: 3 },
    { pair: "XRP/USDT", years: 1 },
    { pair: "BNB/USDT", years: 3 },
    { pair: "BNB/USDT", years: 1 },
    { pair: "DOGE/USDT", years: 3 },
    { pair: "DOGE/USDT", years: 1 }
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

  function targetLabel(pair) {
    return pair === "PORTFOLIO" ? "Gesamtportfolio" : pair;
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
        .tb-actions { display: flex; gap: 10px; align-items: end; }
        .tb-field label { display: block; color: #aebdc3; font-size: 13px; margin-bottom: 7px; }
        .tb-field select { width: 100%; height: 42px; border-radius: 4px; border: 1px solid #35454c; background: #101619; color: #edf5f7; padding: 0 12px; font: inherit; outline: none; }
        .tb-button { height: 42px; border: 1px solid #00b8d4; border-radius: 4px; background: #062e36; color: #00d2ee; font-weight: 600; padding: 0 22px; cursor: pointer; font: inherit; white-space: nowrap; }
        .tb-button-secondary { border-color: #8ba0a9; background: #1a2429; color: #dce8ec; }
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
        .tb-note { margin-top: 18px; padding-top: 15px; border-top: 1px solid #26343a; color: #81959e; font-size: 12px; line-height: 1.6; white-space: pre-line; }
        .tb-batch-table-wrap { overflow-x: auto; }
        .tb-batch-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        .tb-batch-table th, .tb-batch-table td { padding: 10px 12px; border-bottom: 1px solid #29383e; text-align: right; white-space: nowrap; }
        .tb-batch-table th:first-child, .tb-batch-table td:first-child { text-align: left; }
        .tb-batch-table th { color: #91a5ad; font-weight: 600; }
        .tb-batch-table td { color: #dce7ea; }
        .tb-batch-ok { color: #6fd39a !important; }
        .tb-batch-fail { color: #ff7f7f !important; }
        @media (max-width: 850px) { .tb-row { grid-template-columns: 1fr; } .tb-grid { grid-template-columns: repeat(2, 1fr); } .tb-actions { flex-direction: column; } .tb-button { width: 100%; } }
        @media (max-width: 520px) { .tb-wrap { padding: 20px 14px 45px; } .tb-grid { grid-template-columns: 1fr; } }
      </style>
      <div class="tb-wrap">
        <h1 class="tb-title">Backtest</h1>
        <p class="tb-sub">Simuliert exakt den aktuell gestarteten pair-lokalen Testbot mit historischen Binance-Daten. Der Gesamtportfolio-Modus teilt ein einziges 250-USDT-Konto realistisch auf alle sechs freigegebenen Märkte auf.</p>
        <div class="tb-panel">
          <div class="tb-row">
            <div class="tb-field">
              <label for="tb-pair">Prüfmodus</label>
              <select id="tb-pair">
                <option value="PORTFOLIO" selected>Gesamtportfolio · 6 liquide Spot-Pairs</option>
                <option value="BTC/USDT">Bitcoin · BTC/USDT</option>
                <option value="ETH/USDT">Ethereum · ETH/USDT</option>
                <option value="SOL/USDT">Solana · SOL/USDT</option>
                <option value="XRP/USDT">XRP · XRP/USDT</option>
                <option value="BNB/USDT">BNB · BNB/USDT</option>
                <option value="DOGE/USDT">Dogecoin · DOGE/USDT</option>
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
            <div class="tb-actions">
              <button id="tb-start" class="tb-button">Backtest starten</button>
              <button id="tb-start-all" class="tb-button tb-button-secondary">Alle 14 Backtests</button>
            </div>
          </div>
          <div class="tb-info">V12.12 ändert keine Signal- oder Exit-Schwelle von V12.9. XRP, BNB und DOGE erweitern ausschließlich das Universum und nutzen wie SOL nur den bestehenden breiten, langsamen Donchian-Kern. Der BTC/ETH-Trend-Reclaim bleibt auf BTC und ETH beschränkt. Eine pair-lokale Low-Profit-Sperre pausiert nach zwei schwachen Trades innerhalb von 14 Tagen für drei Tage. Der feste -5,5-%-Hard-Stop bleibt bestehen.<br><br><strong>Kapitalnutzung:</strong> Der Gesamtportfolio-Test ist die maßgebliche 250-USDT-Sicht. Alle sechs Märkte konkurrieren gemeinsam um höchstens drei Positionen zu je 80 USDT. Die Einzeltests dienen nur der Pair-Attribution und dürfen nicht als sechs getrennte 250-USDT-Konten addiert werden.<br><br><strong>Dateikontrolle:</strong> Der gesperrte Backtest protokolliert geöffnete Repo-, Konfigurations- und Strategy-Dateien. Native Arrow-Candle-Ladevorgänge werden an Freqtrades Dateinamen-Grenze mit SHA-256 vor und nach dem Lauf gebunden. Der Lauf scheitert, wenn eine andere Strategy, eine andere Konfiguration, Kerzen eines nicht angeforderten Pairs oder ein unerwarteter Kindprozess verwendet wird.<br><br><strong>Keine Testschleifen:</strong> Strategie-Logik, Parameter, Prüfmodus, Zeitraum und das feste Protokoll bilden einen Fingerabdruck. Ein bereits vorhandener Fingerabdruck wird vor Download und Simulation blockiert. Auch ein technisch fehlgeschlagener Versuch mit Ergebnis-ZIP bleibt blockiert. Nur Version, Kommentar oder Beschreibung zu ändern erzeugt keinen neuen Test.<br><br><strong>Alle 14 Backtests</strong> prüft Gesamtportfolio und alle sechs Einzelpaare jeweils über 3 Jahre und 1 Jahr. Bereits vorhandene Zellen werden sauber als Doppeltest übersprungen.</div>
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
        <div id="tb-batch-results" class="tb-panel tb-results">
          <div class="tb-result-head"><h2>Alle 14 Backtests</h2><div id="tb-batch-meta" class="tb-result-meta"></div></div>
          <div class="tb-batch-table-wrap">
            <table class="tb-batch-table">
              <thead><tr><th>Test</th><th>Gewinn / Verlust</th><th>USDT / Tag</th><th>Trades</th><th>Profit Factor</th><th>Drawdown</th><th>Kapitalzeit</th><th>Ohne Position</th><th>Status</th></tr></thead>
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
      const profit = Number(r.profit_usdt || 0);
      const trades = Number(r.trades || 0);
      const days = Math.max(1, Number(r.backtest_days || 0));
      const profitPerDay = profit / days;
      const tradesPerYear = (trades / days) * 365.25;
      const profitClass = profit > 0 ? "tb-positive" : profit < 0 ? "tb-negative" : "tb-neutral";
      results.style.display = "block";
      document.getElementById("tb-result-meta").textContent = `${targetLabel(r.pair)} · ${r.years} Jahr${Number(r.years) === 1 ? "" : "e"} · ${r.timeframe} / Detail ${r.timeframe_detail}`;
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
        resultCard("Kapitalzeit genutzt", `${Number(r.capital_time_utilization_pct || 0).toFixed(2)} %`, "tb-neutral"),
        resultCard("Zeit ohne Position", `${Number(r.no_position_time_pct || 0).toFixed(2)} %`, "tb-neutral"),
        resultCard("Ø offene Positionen", Number(r.average_open_positions || 0).toFixed(3), "tb-neutral"),
        resultCard("Max. gleichzeitig", String(Number(r.max_simultaneous_positions || 0)), "tb-neutral")
      ].join("");
      const independence = r.cross_pair_context === false ? "Signale bleiben pair-lokal: ja" : "Pair-Lokalität nicht bestätigt";
      const target = profitPerDay > 1 ? "Stretch-Ziel >1 USDT/Tag erreicht" : "Stretch-Ziel >1 USDT/Tag noch nicht erreicht";
      const entries = breakdownText(r.entry_tag_breakdown, "Keine Entry-Attribution verfügbar");
      const exits = breakdownText(r.exit_reason_breakdown, "Keine Exit-Attribution verfügbar");
      const experiment = r.experiment || {};
      const identity = r.test_identity || {};
      const fileAudit = r.execution_file_audit || {};
      const auditText = fileAudit.passed
        ? `${Number(fileAudit.observed_candle_files?.length || 0)} erwartete Candle-Dateien, exakte Strategy/Configs, keine fremde Repo-Datei und kein Kindprozess`
        : "keine Dateiaudit-Bestätigung";
      document.getElementById("tb-note").textContent = `Experiment ${experiment.experiment_id || "nicht angegeben"}; Vorgänger ${experiment.parent_experiment_id || "keiner"}. Geändert: ${experiment.change_summary || "nicht angegeben"}. Getestet wurde exakt ${r.strategy} mit Strategie-Hash ${String(r.strategy_sha256 || "").slice(0, 16)}… und Test-Fingerabdruck ${String(identity.test_fingerprint || "").slice(0, 16)}… . ${independence}. ${target}. Tatsächlicher Zeitraum: ${r.backtest_start || "?"} bis ${r.backtest_end || "?"} (${Number(r.backtest_days || 0)} Tage). Kerzendaten: ${r.data_integrity_validated ? "Lücken/Duplikate/Abdeckung geprüft" : "keine Integritätsbestätigung"}. Dateiaudit: ${auditText}.\nEntry-Familien: ${entries}\nExit-Gründe: ${exits}`;
    } else if (state.status === "running") {
      results.style.display = "none";
    }
  }

  function renderBatchResults(completed, total, currentLabel = "") {
    const panel = document.getElementById("tb-batch-results");
    const meta = document.getElementById("tb-batch-meta");
    const body = document.getElementById("tb-batch-body");
    if (!panel || !meta || !body) return;

    panel.style.display = "block";
    meta.textContent = batchRunning
      ? `${completed}/${total} abgeschlossen${currentLabel ? ` · läuft: ${currentLabel}` : ""}`
      : `${completed}/${total} abgeschlossen`;

    body.innerHTML = batchResults.map((item) => {
      const label = `${targetLabel(item.pair)} · ${item.years} Jahr${item.years === 1 ? "" : "e"}`;
      if (item.error) {
        if (item.skipped) {
          return `<tr><td>${label}</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td class="tb-neutral">Doppeltest übersprungen</td></tr>`;
        }
        return `<tr><td>${label}</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td class="tb-batch-fail">Fehler</td></tr>`;
      }
      const r = item.result;
      const profit = Number(r.profit_usdt || 0);
      const days = Math.max(1, Number(r.backtest_days || 0));
      const profitPerDay = profit / days;
      const profitClass = profit > 0 ? "tb-batch-ok" : profit < 0 ? "tb-batch-fail" : "";
      return `<tr><td>${label}</td><td class="${profitClass}">${money(profit)}</td><td class="${profitClass}">${money(profitPerDay)}</td><td>${Number(r.trades || 0)}</td><td>${Number(r.profit_factor || 0).toFixed(2)}</td><td>${Number(r.max_drawdown_pct || 0).toFixed(2)} %</td><td>${Number(r.capital_time_utilization_pct || 0).toFixed(2)} %</td><td>${Number(r.no_position_time_pct || 0).toFixed(2)} %</td><td class="tb-batch-ok">Fertig</td></tr>`;
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
    renderBatchResults(0, BATCH_CASES.length, "wird vorbereitet");

    for (let index = 0; index < BATCH_CASES.length; index += 1) {
      const test = BATCH_CASES[index];
      const label = `${targetLabel(test.pair)} · ${test.years} Jahr${test.years === 1 ? "" : "e"}`;
      pairSelect.value = test.pair;
      yearsSelect.value = String(test.years);
      renderBatchResults(batchResults.length, BATCH_CASES.length, label);

      try {
        const result = await startOneBacktest(test.pair, test.years);
        batchResults.push({ ...test, result });
      } catch (error) {
        batchResults.push({ ...test, error: String(error.message || error), skipped: Boolean(error.isDuplicate) });
      }
      renderBatchResults(batchResults.length, BATCH_CASES.length, "");
    }

    batchRunning = false;
    singleButton.disabled = false;
    allButton.disabled = false;
    renderBatchResults(batchResults.length, BATCH_CASES.length, "");
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
