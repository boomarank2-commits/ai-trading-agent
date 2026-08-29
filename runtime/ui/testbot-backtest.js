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
  let singleRunning = false;
  let batchRunning = false;
  let batchResults = [];
  let preferredStatusView = null;

  function syncControls() {
    const disabled = singleRunning || batchRunning;
    ["tb-start", "tb-start-matrix", "tb-pair", "tb-years"].forEach((id) => {
      const control = document.getElementById(id);
      if (control) control.disabled = disabled;
    });
  }

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
    const found = PAIRS.find(([value]) => value === pair);
    return found ? `${found[1]} · ${found[0]}` : pair;
  }

  function resultNumber(value, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
  }

  function entryCapitalEfficiency(result) {
    const saved = Number(result.profit_per_100_entry_capital_usdt);
    if (Number.isFinite(saved)) return saved;
    const entryCapital = resultNumber(
      result.total_entry_capital_usdt,
      resultNumber(result.total_entry_chunks) * 80
    );
    return entryCapital > 0 ? 100 * resultNumber(result.profit_usdt) / entryCapital : 0;
  }

  function capitalDayEfficiency(result) {
    const saved = Number(result.profit_per_100_deployed_capital_day_usdt);
    if (Number.isFinite(saved)) return saved;
    const capitalDays = resultNumber(
      result.deployed_capital_usdt_days,
      resultNumber(result.capital_time_utilization_pct) / 100
        * resultNumber(result.starting_balance_usdt, 250)
        * resultNumber(result.backtest_days)
    );
    return capitalDays > 0 ? 100 * resultNumber(result.profit_usdt) / capitalDays : 0;
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

  function durationText(secondsValue) {
    const seconds = Number(secondsValue);
    if (!Number.isFinite(seconds) || seconds < 0) return "?";
    if (seconds < 60) return `${seconds.toFixed(1)} s`;
    return `${(seconds / 60).toFixed(2)} min`;
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
        .tb-history { margin-top: 22px; padding-top: 18px; border-top: 1px solid #26343a; }
        .tb-history h3 { margin: 0 0 6px; color: #eaf2f4; font-size: 17px; }
        .tb-history-intro { margin: 0 0 14px; color: #879ba4; font-size: 12px; line-height: 1.55; }
        .tb-history-table-wrap { overflow-x: auto; }
        .tb-history-table { width: 100%; border-collapse: collapse; font-size: 12px; }
        .tb-history-table th, .tb-history-table td { padding: 9px 10px; border-bottom: 1px solid #29383e; text-align: left; vertical-align: top; }
        .tb-history-table th { color: #91a5ad; font-weight: 600; white-space: nowrap; }
        .tb-history-table td { color: #cbd8dc; line-height: 1.45; min-width: 105px; }
        .tb-history-table td.tb-history-detail { min-width: 260px; white-space: normal; }
        .tb-history-table code { color: #8fd8e5; }
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
        <p class="tb-sub">Teste einen ausgewählten Coin oder starte alle zehn Coins dauerhaft und wiederaufnehmbar nacheinander. Jeder Einzeltest verwendet ein eigenes 250-USDT-Testwallet und dieselben aktuellen Bot-Regeln.</p>
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
              <button id="tb-start-matrix" class="tb-button tb-button-secondary">Alle 10 einzeln testen</button>
            </div>
          </div>
          <div class="tb-info">
            <strong>Einzeltest:</strong> Der gewählte Coin startet mit einem eigenen 250-USDT-Testwallet und simuliert exakt die aktuelle V12.33-Strategie.<br><br>
            <strong>Marktdaten:</strong> Vor einem neuen Lauf werden die benötigten 1m-, 15m-, 1h- und 4h-Binance-Kerzen automatisch bis heute aktualisiert. Fehlende ältere Bereiche werden nachgeladen; beschädigte oder lückenhafte Dateien werden für den betroffenen Coin frisch aufgebaut. Die geprüften Daten bleiben unter <code>runtime/user_data/data/binance</code> im Botordner gespeichert und können in späteren Läufen wiederverwendet werden.<br><br>
            <strong>Alle 10 einzeln testen:</strong> Startet serverseitig zehn getrennte Tests nacheinander. Jeder Coin beginnt mit eigenen 250 USDT. Plan, Fortschritt, Vorher/Nachher-Vergleich und Ergebnis werden dauerhaft gespeichert; ein Neuladen der UI unterbricht die Warteschlange nicht.<br><br>
            <strong>Aktive V12.33-Änderung:</strong> LTC bleibt sichtbar und seine Marktdaten werden weiter gepflegt, eröffnet aber mangels positiver Shared-Wallet-Evidenz vorerst keinen Trade. DOGE behält den 4h-Supertrend(20, 3), BCH die EMA30/EMA80-Route und SOL den ADX21-Filter; alle übrigen Routen bleiben gegenüber V12.31 unverändert.<br><br>
            <strong>Kapitalregel je Einzeltest:</strong> Nur BTC, ETH, LINK und TRX dürfen einen zweiten oder dritten 80-USDT-Block erhalten, und nur bei einem späteren vollständigen Einstiegssignal, einem bereits profitablen Trade und einem Kurs über allen vorherigen Einstiegskursen. SOL, XRP, BNB, DOGE und BCH handeln mit höchstens ihrem ersten Block; LTC eröffnet aktuell keinen Block. Verlust-Nachkäufe sind gesperrt.<br><br>
            <strong>Kapital-Effizienz:</strong> „USDT je 100 Entry-Kapital“ misst den historischen Nettogewinn je 100 tatsächlich gefüllten USDT. „USDT je 100 Kapitaltag“ berücksichtigt zusätzlich die Haltedauer: 80 USDT, die zehn Tage gebunden sind, zählen als 800 USDT-Tage. Beide Werte sind Rückblick-Messungen und keine Gewinnzusage.<br><br>
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
          <div id="tb-history" class="tb-history"></div>
        </div>
        <div id="tb-batch-results" class="tb-panel tb-results">
          <div class="tb-result-head"><h2 id="tb-batch-title">Alle 10 einzeln</h2><div id="tb-batch-meta" class="tb-result-meta"></div></div>
          <div class="tb-batch-table-wrap">
            <table class="tb-batch-table">
              <thead><tr><th>Coin</th><th>Gewinn / Verlust</th><th>Δ Vorgänger</th><th>USDT / Tag</th><th>USDT / 100 Entry</th><th>USDT / 100 Kapitaltag</th><th>Kapitalzeit</th><th>Trades</th><th>Profit Factor</th><th>Drawdown</th><th>Trefferquote</th><th>Status</th></tr></thead>
              <tbody id="tb-batch-body"></tbody>
            </table>
          </div>
        </div>
      </div>`;

    document.body.appendChild(view);
    syncBacktestTop(view);
    document.getElementById("tb-start").addEventListener("click", startBacktest);
    document.getElementById("tb-start-matrix").addEventListener("click", startAllBacktests);
    return view;
  }

  function renderState(state) {
    const status = document.getElementById("tb-status");
    const results = document.getElementById("tb-results");
    const button = document.getElementById("tb-start");
    const matrixButton = document.getElementById("tb-start-matrix");
    if (!status || !results || !button || !matrixButton) return;

    singleRunning = state.status === "running";
    syncControls();
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
      const profitPerDay = resultNumber(r.profit_per_calendar_day_usdt, profit / days);
      const tradesPerYear = resultNumber(r.trades_per_year, (trades / days) * 365.25);
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
        resultCard("Gewinn / Trade", money(resultNumber(r.profit_per_trade_usdt, trades > 0 ? profit / trades : 0)), profitClass),
        resultCard("USDT / 100 Entry-Kapital", money(entryCapitalEfficiency(r)), profitClass),
        resultCard("USDT / 100 Kapitaltag", money(capitalDayEfficiency(r)), profitClass),
        resultCard("Profit Factor", Number(r.profit_factor || 0).toFixed(2), Number(r.profit_factor) >= 1 ? "tb-positive" : "tb-negative"),
        resultCard("Trefferquote", `${Number(r.winrate_pct || 0).toFixed(2)} %`, "tb-neutral"),
        resultCard("Max. Drawdown", `${Number(r.max_drawdown_pct || 0).toFixed(2)} %`, Number(r.max_drawdown_pct) > 15 ? "tb-negative" : "tb-neutral"),
        resultCard("Startkapital", `${Number(r.starting_balance_usdt || 250).toFixed(2)} USDT`, "tb-neutral"),
        resultCard("Entry-Blöcke gesamt", String(Number(r.total_entry_chunks || 0)), "tb-neutral"),
        resultCard("Zusätzliche Blöcke", String(Number(r.additional_entry_chunks || 0)), "tb-neutral"),
        resultCard("Entry-Kapital gesamt", `${Number(r.total_entry_capital_usdt || 0).toFixed(2)} USDT`, "tb-neutral"),
        resultCard("Gebundene Kapitaltage", `${Number(r.deployed_capital_usdt_days || 0).toFixed(2)} USDT-Tage`, "tb-neutral"),
        resultCard("Kapitalzeit", `${Number(r.capital_time_utilization_pct || 0).toFixed(2)} %`, "tb-neutral"),
        resultCard("Zeit ohne Position", `${Number(r.no_position_time_pct || 0).toFixed(2)} %`, "tb-neutral"),
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
      const historical = r.historical_context || {};
      const timing = r.timing || {};
      const previous = historical.previous || null;
      const delta = historical.delta_vs_previous || null;
      const comparison = previous && delta
        ? `Vorgänger ${previous.strategy_version || "?"} / ${previous.run_id || "?"}: ${money(previous.profit_usdt)}. Änderung: ${money(delta.profit_usdt)} · Trades ${Number(delta.trades || 0) >= 0 ? "+" : ""}${Number(delta.trades || 0)} · Drawdown ${Number(delta.max_drawdown_pct || 0) >= 0 ? "+" : ""}${Number(delta.max_drawdown_pct || 0).toFixed(2)} Punkte. ${historical.assessment_de || ""}`
        : (historical.assessment_de || "Kein älterer gleicher Pair-/Zeitraumvergleich vorhanden.");
      const timingText = `Daten ${durationText(timing.market_data_seconds)} · Simulation ${durationText(timing.simulation_seconds)} · Auswertung ${durationText(timing.analysis_seconds)} · Gesamt ${durationText(timing.total_seconds)}`;
      document.getElementById("tb-note").textContent = `Aktuelle Strategie: V12.33 / ${r.strategy}. Experiment ${experiment.experiment_id || "?"}. Strategie-Hash ${String(r.strategy_sha256 || "").slice(0, 16)}… · Test-Fingerprint ${String(identity.test_fingerprint || "").slice(0, 16)}… . Tatsächlicher Zeitraum: ${r.backtest_start || "?"} bis ${r.backtest_end || "?"} (${Number(r.backtest_days || 0)} Tage). ${auditText}.\nLaufzeit: ${timingText}.\nHistorie: ${comparison}\nPaare: ${pairs}\nEntry-Familien: ${entries}\nExit-Gründe: ${exits}`;
      renderPairHistory(historical, r.pair);
    } else if (state.status === "running") {
      results.style.display = "none";
    }
  }

  function renderPairHistory(history, pair) {
    const target = document.getElementById("tb-history");
    if (!target) return;
    const preserved = Array.isArray(history.all_preserved_runs)
      ? history.all_preserved_runs
      : [];
    const documented = Array.isArray(history.documented_pair_experiments)
      ? history.documented_pair_experiments
      : [];
    if (!preserved.length && !documented.length) {
      target.innerHTML = `<h3>Testakte ${escapeHtml(pairLabel(pair))}</h3><p class="tb-history-intro">Für dieses Pair und diesen Zeitraum ist noch kein älterer materieller Versuch gespeichert.</p>`;
      return;
    }

    const runRows = preserved.map((run) => {
      const profit = Number(run.profit_usdt || 0);
      const profitClass = profit > 0 ? "tb-batch-ok" : profit < 0 ? "tb-batch-fail" : "";
      const period = `${String(run.backtest_start || "?").slice(0, 10)} bis ${String(run.backtest_end || "?").slice(0, 10)}`;
      const detail = [
        `<strong>Änderung:</strong> ${escapeHtml(run.change_summary || "nicht dokumentiert")}`,
        `<strong>Ergebnis:</strong> ${escapeHtml(run.result_summary || "nur Messwerte gespeichert")}`,
        `<strong>Erkenntnis:</strong> ${escapeHtml(run.lessons || "noch nicht bewertet")}`,
        `<strong>Nächster Schritt:</strong> ${escapeHtml(run.next_experiment || "noch offen")}`
      ].join("<br>");
      return `<tr><td><code>${escapeHtml(run.strategy_version || "?")}</code><br>${escapeHtml(run.experiment_id || "historisch")}</td><td>${escapeHtml(period)}</td><td class="${profitClass}">${money(profit)}</td><td>${Number(run.trades || 0)}</td><td>${Number(run.profit_factor || 0).toFixed(2)}</td><td>${Number(run.max_drawdown_pct || 0).toFixed(2)} %</td><td>${escapeHtml(run.decision || "nicht bewertet")}</td><td class="tb-history-detail">${detail}</td></tr>`;
    }).join("");
    const documentedRows = documented.map((experiment) => {
      const detail = [
        `<strong>Hypothese:</strong> ${escapeHtml(experiment.hypothesis || "nicht dokumentiert")}`,
        `<strong>Änderung:</strong> ${escapeHtml(experiment.change_summary || "nicht dokumentiert")}`,
        `<strong>Ergebnis:</strong> ${escapeHtml(experiment.result_summary || experiment.notes || "keine Finanzmessung")}`,
        `<strong>Erkenntnis:</strong> ${escapeHtml(experiment.lessons || "noch nicht bewertet")}`,
        `<strong>Nächster Schritt:</strong> ${escapeHtml(experiment.next_experiment || "noch offen")}`
      ].join("<br>");
      return `<tr><td><code>${escapeHtml(experiment.strategy_version || "?")}</code><br>${escapeHtml(experiment.experiment_id || "?")}</td><td>${escapeHtml(experiment.validation_window || experiment.date_decided || "dokumentiert")}</td><td>—</td><td>${escapeHtml(experiment.trade_count || "—")}</td><td>${escapeHtml(experiment.profit_factor || "—")}</td><td>${escapeHtml(experiment.max_drawdown || "—")}</td><td>${escapeHtml(experiment.decision || experiment.status || "nicht bewertet")}</td><td class="tb-history-detail">${detail}</td></tr>`;
    }).join("");
    target.innerHTML = `
      <h3>Testakte ${escapeHtml(pairLabel(pair))}</h3>
      <p class="tb-history-intro">Nur Versuche dieses Coins mit derselben Laufzeit. Identische Fingerabdrücke werden nicht erneut gerechnet. Ledger-Versuche ohne regulären UI-Lauf stehen zusätzlich in dieser Akte.</p>
      <div class="tb-history-table-wrap"><table class="tb-history-table">
        <thead><tr><th>Version / Versuch</th><th>Zeitraum</th><th>P/L</th><th>Trades</th><th>PF</th><th>DD</th><th>Entscheidung</th><th>Was wurde gelernt?</th></tr></thead>
        <tbody>${runRows}${documentedRows}</tbody>
      </table></div>`;
  }

  function renderBatchResults(completed, total, years, currentLabel = "") {
    const panel = document.getElementById("tb-batch-results");
    const meta = document.getElementById("tb-batch-meta");
    const title = document.getElementById("tb-batch-title");
    const body = document.getElementById("tb-batch-body");
    if (!panel || !meta || !body || !title) return;

    panel.style.display = "block";
    title.textContent = `Alle 10 einzeln · ${years} Jahr${years === 1 ? "" : "e"}`;
    meta.textContent = batchRunning
      ? `${completed}/${total} abgeschlossen${currentLabel ? ` · läuft: ${currentLabel}` : ""}`
      : `${completed}/${total} abgeschlossen · je Test 250 USDT Startwert`;

    body.innerHTML = batchResults.map((item) => {
      const label = pairLabel(item.pair);
      if (item.error) {
        const errorText = escapeHtml(item.error);
        if (item.skipped) {
          return `<tr><td>${label}</td>${"<td>—</td>".repeat(10)}<td class="tb-neutral tb-batch-error"><strong>Doppeltest übersprungen</strong>${errorText}</td></tr>`;
        }
        return `<tr><td>${label}</td>${"<td>—</td>".repeat(10)}<td class="tb-batch-fail tb-batch-error"><strong>Fehler</strong>${errorText}</td></tr>`;
      }
      const r = item.result;
      const profit = Number(r.profit_usdt || 0);
      const days = Math.max(1, Number(r.backtest_days || 0));
      const profitPerDay = resultNumber(r.profit_per_calendar_day_usdt, profit / days);
      const delta = r.historical_context && r.historical_context.delta_vs_previous;
      const deltaProfit = delta ? Number(delta.profit_usdt || 0) : null;
      const profitClass = profit > 0 ? "tb-batch-ok" : profit < 0 ? "tb-batch-fail" : "";
      const deltaClass = deltaProfit === null ? "" : deltaProfit > 0 ? "tb-batch-ok" : deltaProfit < 0 ? "tb-batch-fail" : "";
      const totalTime = r.timing && r.timing.total_seconds;
      const statusText = `${item.status === "reused" ? "Vorhanden" : "Fertig"} · ${durationText(totalTime)}`;
      return `<tr><td>${label}</td><td class="${profitClass}">${money(profit)}</td><td class="${deltaClass}">${deltaProfit === null ? "erster Vergleich" : money(deltaProfit)}</td><td class="${profitClass}">${money(profitPerDay)}</td><td class="${profitClass}">${money(entryCapitalEfficiency(r))}</td><td class="${profitClass}">${money(capitalDayEfficiency(r))}</td><td>${Number(r.capital_time_utilization_pct || 0).toFixed(2)} %</td><td>${Number(r.trades || 0)}</td><td>${Number(r.profit_factor || 0).toFixed(2)}</td><td>${Number(r.max_drawdown_pct || 0).toFixed(2)} %</td><td>${Number(r.winrate_pct || 0).toFixed(2)} %</td><td class="tb-batch-ok">${statusText}</td></tr>`;
    }).join("");
  }

  async function fetchStatus() {
    const response = await fetch("/api/v1/testbot/backtest/status", { cache: "no-store" });
    if (!response.ok) throw new Error("Backtest-Status konnte nicht geladen werden.");
    return response.json();
  }

  async function fetchBatchStatus() {
    const response = await fetch("/api/v1/testbot/backtest/batch/status", { cache: "no-store" });
    if (!response.ok) throw new Error("Batch-Status konnte nicht geladen werden.");
    return response.json();
  }

  function renderServerBatch(state, singleState = null) {
    if (!state || state.status === "idle") return;
    batchRunning = state.status === "running";
    batchResults = (Array.isArray(state.cases) ? state.cases : [])
      .filter((item) => ["completed", "reused", "failed"].includes(item.status))
      .map((item) => ({
        pair: item.pair,
        years: item.years,
        status: item.status,
        result: item.result,
        error: item.error,
        skipped: false
      }));
    const years = Number(state.years || document.getElementById("tb-years").value || 3);
    renderBatchResults(
      Number(state.completed_cases || 0) + Number(state.failed_cases || 0),
      PAIRS.length,
      years,
      state.current_pair ? pairLabel(state.current_pair) : ""
    );
    const status = document.getElementById("tb-status");
    const completedCases = Number(state.completed_cases || 0);
    const batchProgress = Math.max(0, Math.min(100, Number(state.progress || 0)));
    const singlePair = singleState ? String(singleState.pair || "") : "";
    const currentPairMatches = !state.current_pair || !singlePair || singlePair === state.current_pair;
    const currentPairProgress = batchRunning && singleState && singleState.status === "running" && currentPairMatches
      ? Math.max(0, Math.min(100, Number(singleState.progress || 0)))
      : null;
    const progress = currentPairProgress === null
      ? batchProgress
      : Math.max(batchProgress, Math.min(100, ((completedCases + currentPairProgress / 100) / PAIRS.length) * 100));
    if (status) status.style.display = "block";
    document.getElementById("tb-stage").textContent = String(state.stage || "Zehner-Batch");
    document.getElementById("tb-progress-text").textContent = batchRunning && currentPairProgress !== null
      ? `${completedCases}/${PAIRS.length} Coins · aktueller Coin ${currentPairProgress} % · Gesamt ${progress.toFixed(1)} %`
      : `${completedCases}/${PAIRS.length} Coins · ${progress.toFixed(1)} %`;
    document.getElementById("tb-progress-bar").style.width = `${progress}%`;
    const activity = document.getElementById("tb-activity");
    if (activity) {
      const currentStage = batchRunning && currentPairProgress !== null && singleState.stage
        ? ` Aktuelle Stufe: ${String(singleState.stage)}.`
        : "";
      activity.textContent = batchRunning
        ? `Gesamtlauf aktiv${state.current_pair ? ` · ${pairLabel(state.current_pair)} wird gerade gerechnet` : ""}.${currentStage} Ein fertiges Einzelergebnis beendet den Zehnerlauf nicht.`
        : state.status === "completed"
          ? "Alle zehn unterschiedlichen Coins wurden vollständig abgeschlossen."
          : "Der Zehnerlauf ist beendet, enthält aber mindestens einen Fehler.";
    }
    if (state.status === "failed" && state.batch_error) {
      const error = document.getElementById("tb-error");
      error.textContent = state.batch_error;
      error.style.display = "block";
    }
    syncControls();
  }

  function statusTimestamp(state) {
    if (!state) return 0;
    const timestamp = Date.parse(String(
      state.updated_at_utc || state.finished_at || state.started_at || state.started_at_utc || ""
    ));
    return Number.isFinite(timestamp) ? timestamp : 0;
  }

  async function loadStatus() {
    const [singleRequest, batchRequest] = await Promise.allSettled([
      fetchStatus(),
      fetchBatchStatus()
    ]);
    const singleState = singleRequest.status === "fulfilled" ? singleRequest.value : null;
    const batchState = batchRequest.status === "fulfilled" ? batchRequest.value : null;

    if (batchState && batchState.status === "running") {
      preferredStatusView = "batch";
      renderServerBatch(batchState, singleState);
      return;
    }
    if (singleState && singleState.status === "running") {
      preferredStatusView = "single";
      renderState(singleState);
      return;
    }
    if (preferredStatusView === "single" && singleState) {
      renderState(singleState);
      return;
    }
    if (preferredStatusView === "batch" && batchState && batchState.status !== "idle") {
      renderServerBatch(batchState, singleState);
      return;
    }
    if (batchState && batchState.status !== "idle" && statusTimestamp(batchState) >= statusTimestamp(singleState)) {
      preferredStatusView = "batch";
      renderServerBatch(batchState, singleState);
      return;
    }
    if (singleState) {
      preferredStatusView = "single";
      renderState(singleState);
    }
  }

  async function startBacktest() {
    const pair = document.getElementById("tb-pair").value;
    const years = Number(document.getElementById("tb-years").value);
    const button = document.getElementById("tb-start");
    const matrixButton = document.getElementById("tb-start-matrix");
    button.disabled = true;
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
      preferredStatusView = "single";
      renderState(payload);
      if (!pollTimer) pollTimer = setInterval(loadStatus, 1000);
    } catch (error) {
      renderState({ status: "failed", stage: error.isDuplicate ? "Doppeltest blockiert" : "Fehler", progress: 100, error: String(error.message || error) });
      button.disabled = false;
      matrixButton.disabled = false;
    }
  }

  async function startAllBacktests() {
    if (batchRunning) return;

    const singleButton = document.getElementById("tb-start");
    const matrixButton = document.getElementById("tb-start-matrix");
    const pairSelect = document.getElementById("tb-pair");
    const yearsSelect = document.getElementById("tb-years");
    const years = Number(yearsSelect.value);
    try {
      const current = await fetchStatus();
      if (current.status === "running") {
        throw new Error("Es läuft bereits ein Backtest. Bitte diesen zuerst beenden lassen.");
      }
    } catch (error) {
      renderState({ status: "failed", stage: "Fehler", progress: 100, error: String(error.message || error) });
      return;
    }

    batchRunning = true;
    batchResults = [];
    preferredStatusView = "batch";
    singleButton.disabled = true;
    matrixButton.disabled = true;
    pairSelect.disabled = true;
    yearsSelect.disabled = true;
    renderBatchResults(0, PAIRS.length, years, "wird vorbereitet");

    try {
      const response = await fetch("/api/v1/testbot/backtest/batch/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ years })
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Zehner-Batch konnte nicht gestartet werden.");
      }
      renderServerBatch(payload);
      if (!pollTimer) pollTimer = setInterval(loadStatus, 1000);
    } catch (error) {
      batchRunning = false;
      renderState({ status: "failed", stage: "Batch-Fehler", progress: 100, error: String(error.message || error) });
      syncControls();
    }
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
