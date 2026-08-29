(() => {
  "use strict";

  const VIEW_ID = "testbot-backtest-view";
  const NAV_ID = "testbot-backtest-nav";
  const BODY_OPEN_CLASS = "testbot-backtest-open";
  const PAIRS = [
    ["BTC/USDT", "Bitcoin"], ["ETH/USDT", "Ethereum"], ["SOL/USDT", "Solana"],
    ["XRP/USDT", "XRP"], ["BNB/USDT", "BNB"], ["DOGE/USDT", "Dogecoin"],
    ["LINK/USDT", "Chainlink"], ["TRX/USDT", "TRON"], ["LTC/USDT", "Litecoin"],
    ["BCH/USDT", "Bitcoin Cash"]
  ];
  const TARGET_PER_DAY = 2.40;
  let pollTimer = null;
  let running = false;

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#39;");

  function money(value) {
    const n = Number(value || 0);
    return `${n > 0 ? "+" : ""}${n.toFixed(2)} USDT`;
  }
  function pct(value) {
    const n = Number(value || 0);
    return `${n > 0 ? "+" : ""}${n.toFixed(2)} %`;
  }
  function pairLabel(pair) {
    const hit = PAIRS.find(([value]) => value === pair);
    return hit ? `${hit[1]} · ${hit[0]}` : pair;
  }
  function num(value, fallback = 0) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }
  function pairOptions() {
    return PAIRS.map(([pair, name]) => `<option value="${pair}">${name} · ${pair}</option>`).join("");
  }
  function metric(label, value, cls = "") {
    return `<div class="hx-metric"><div class="hx-label">${label}</div><div class="hx-value ${cls}">${value}</div></div>`;
  }
  function resultClass(value) {
    return num(value) > 0 ? "hx-positive" : num(value) < 0 ? "hx-negative" : "";
  }

  function createView() {
    let view = document.getElementById(VIEW_ID);
    if (view) return view;
    view = document.createElement("div");
    view.id = VIEW_ID;
    view.innerHTML = `
      <style>
        body.${BODY_OPEN_CLASS} main { display:none !important; }
        #${VIEW_ID}{position:fixed;inset:0;z-index:60;overflow:auto;background:#101619;color:#d6e0e4;font-family:inherit}
        #${VIEW_ID} *{box-sizing:border-box}.hx-wrap{max-width:1220px;margin:0 auto;padding:28px 30px 60px}
        .hx-title{font-size:26px;font-weight:650;margin:0 0 7px;color:#f2f6f7}.hx-sub{margin:0 0 22px;color:#93a5ad;line-height:1.55}
        .hx-panel{background:#171e22;border:1px solid #26343a;border-radius:5px;padding:20px;margin-bottom:18px}
        .hx-row{display:grid;grid-template-columns:minmax(230px,1fr) minmax(160px,.45fr) auto;gap:16px;align-items:end}
        .hx-field label{display:block;color:#aebdc3;font-size:13px;margin-bottom:7px}.hx-field select{width:100%;height:42px;border:1px solid #35454c;background:#101619;color:#edf5f7;padding:0 11px}
        .hx-actions{display:flex;gap:10px}.hx-button{height:42px;border:1px solid #00b8d4;background:#062e36;color:#00d2ee;font-weight:650;padding:0 18px;cursor:pointer;white-space:nowrap}
        .hx-button.secondary{border-color:#8ba0a9;background:#1a2429;color:#dce8ec}.hx-button:disabled{opacity:.55;cursor:not-allowed}
        .hx-info{margin-top:16px;color:#8da0a8;font-size:13px;line-height:1.62}.hx-info strong{color:#c1d0d5}.hx-info code{color:#8fd8e5}
        .hx-status{display:none}.hx-statusline{display:flex;justify-content:space-between;gap:18px;margin-bottom:9px}.hx-stage{color:#e1ecef}.hx-progress-text{color:#8ca0a8}
        .hx-progress{height:8px;background:#0d1215;border:1px solid #253239;overflow:hidden}.hx-progress>div{height:100%;width:0;background:#00b8d4;transition:width .25s}
        .hx-error{display:none;margin-top:13px;padding:11px;border:1px solid #743d3d;background:#2c1818;color:#ffb6b6;white-space:pre-wrap}
        .hx-section-title{font-size:18px;margin:0 0 12px;color:#eaf2f4}.hx-grid{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:10px}
        .hx-metric{background:#101619;border:1px solid #29383e;padding:14px;min-height:78px}.hx-label{font-size:12px;color:#81959e;margin-bottom:8px}.hx-value{font-size:19px;font-weight:650;color:#e4eef1}
        .hx-positive{color:#6fd39a}.hx-negative{color:#ff7f7f}.hx-note{margin-top:14px;color:#81959e;font-size:12px;line-height:1.55}
        .hx-table-wrap{overflow-x:auto}.hx-table{width:100%;border-collapse:collapse;font-size:12px}.hx-table th,.hx-table td{padding:9px 10px;border-bottom:1px solid #29383e;text-align:right;white-space:nowrap}.hx-table th:first-child,.hx-table td:first-child{text-align:left}.hx-table th{color:#91a5ad}.hx-table td{color:#dce7ea}.hx-table .bad{color:#ff9d9d;text-align:left;white-space:normal;min-width:240px}
        .hx-portfolio{border-color:#00b8d4}.hx-target{font-size:12px;color:#93a5ad;margin-top:12px}.hx-breakdown{margin-top:14px;color:#a7b7bd;font-size:12px;line-height:1.6}
        @media(max-width:900px){.hx-row{grid-template-columns:1fr}.hx-grid{grid-template-columns:repeat(2,1fr)}.hx-actions{flex-direction:column}.hx-button{width:100%}}
        @media(max-width:520px){.hx-wrap{padding:20px 13px 45px}.hx-grid{grid-template-columns:1fr}}
      </style>
      <div class="hx-wrap">
        <h1 class="hx-title">Hixton V5B Deep Research Routes · 10 Coins + 3×80 Portfolio</h1>
        <p class="hx-sub">Separater HIXTON-V5B-Fingerprint nach Deep Research. Der gerade laufende V5-Backtest bleibt davon vollständig getrennt. Kein V4-Gewinnstop, kein Midline-Exit, kein Trailing und kein Pyramiding.</p>
        <div class="hx-panel">
          <div class="hx-row">
            <div class="hx-field"><label for="hx-pair">Einzeltest</label><select id="hx-pair">${pairOptions()}</select></div>
            <div class="hx-field"><label for="hx-years">Zeitraum</label><select id="hx-years"><option value="1">1 Jahr</option><option value="2">2 Jahre</option><option value="3" selected>3 Jahre</option></select></div>
            <div class="hx-actions">
              <button id="hx-start-one" class="hx-button secondary">Gewählten Coin testen</button>
              <button id="hx-start-all" class="hx-button">Alle 10 + 3×80 Portfolio testen</button>
            </div>
          </div>
          <div class="hx-info">
            <strong>Hixton-Motor:</strong> Auf jedem verwendeten Zeitrahmen unverändert VIDYA 10/20 → SMA 15 und ATR 200 × 2. Der originale gegenüberliegende Hixton-Flip bleibt der Exit.<br><br>
            <strong>Route A · ETH/XRP/DOGE/TRX:</strong> geschlossenes 15m-Flip-Up + letzter abgeschlossener 1h-Close über der 1h-VIDYA + echte native 1h-VIDYA nicht fallend. Kein 4h-Filter. Exit auf originalem 15m-Flip-Down.<br><br>
            <strong>Route B · BTC/SOL/LINK/BNB:</strong> gleiche strenge 15m+1h-Route, zusätzlich muss der tatsächliche bestätigte 4h-Hixton-Trendzustand <code>trendUp</code> bullisch sein. Kein Ersatzfilter aus 4h-Close&gt;VIDYA plus steigender VIDYA.<br><br>
            <strong>Route C · LTC/BCH:</strong> nativer abgeschlossener 1h-Hixton-Flip-Up als Einstieg, bestätigt durch den tatsächlichen bullischen 4h-Hixton-<code>trendUp</code>-State. Exit auf dem nativen abgeschlossenen 1h-Flip-Down. Forward-Fill darf ein 1h-Ereignis nur einmal auslösen.<br><br>
            <strong>Einzeltests:</strong> Jeder Coin wird unabhängig mit eigenem 250-USDT-Testwallet und 80-USDT-Position gemessen. Die zehn Einzelgewinne werden ausdrücklich nicht zu einem Portfolioergebnis addiert.<br><br>
            <strong>Datenprüfung:</strong> Vor einem echten neuen Lauf werden Binance-Daten für 1m, 15m, 1h und 4h bis zum aktuellen Stand geladen. Für den Backtest werden ${75} zusätzliche Warm-up-Tage vor dem Testfenster angefordert. Lücken, Duplikate, zu später Start und veraltetes Ende werden geprüft; ein fehlerhafter Coin-Datensatz wird vollständig neu aufgebaut.<br><br>
            <strong>Gesamttest:</strong> Der große Knopf rechnet zuerst alle zehn Einzeltests. Nur wenn alle gültig sind, folgt automatisch der echte chronologische Portfolio-Backtest: ein gemeinsames 250-USDT-Wallet, maximal drei gleichzeitige Positionen à 80 USDT, also maximal 240 USDT im Markt.<br><br>
            <strong>Forschungsregel:</strong> V5B ist ein eigener preregistrierter Fingerprint. ETH/XRP/DOGE/TRX sind die V3A-Kontrollen; BTC/SOL/LINK/BNB testen nur den zusätzlichen echten 4h-Trend-State; LTC/BCH testen ausschließlich den strukturellen Wechsel auf native 1h-Signale plus 4h-Regime.
          </div>
        </div>
        <div id="hx-status" class="hx-panel hx-status">
          <div class="hx-statusline"><span id="hx-stage" class="hx-stage">Bereit</span><span id="hx-progress-text" class="hx-progress-text">0 %</span></div>
          <div class="hx-progress"><div id="hx-progress-bar"></div></div>
          <div id="hx-error" class="hx-error"></div>
        </div>
        <div id="hx-single" class="hx-panel" style="display:none"></div>
        <div id="hx-individuals" class="hx-panel" style="display:none"></div>
        <div id="hx-portfolio" class="hx-panel hx-portfolio" style="display:none"></div>
      </div>`;
    document.body.appendChild(view);
    document.getElementById("hx-start-one").addEventListener("click", startOne);
    document.getElementById("hx-start-all").addEventListener("click", startAll);
    return view;
  }

  function syncTop(view) {
    const header = document.querySelector("header");
    view.style.top = `${header ? Math.ceil(header.getBoundingClientRect().bottom) : 0}px`;
  }
  function setControls(disabled) {
    ["hx-start-one", "hx-start-all", "hx-pair", "hx-years"].forEach((id) => {
      const node = document.getElementById(id); if (node) node.disabled = disabled;
    });
  }
  function showStatus(stage, progress, error = "") {
    const box = document.getElementById("hx-status"); if (!box) return;
    box.style.display = "block";
    document.getElementById("hx-stage").textContent = String(stage || "Bereit");
    document.getElementById("hx-progress-text").textContent = `${num(progress).toFixed(1)} %`;
    document.getElementById("hx-progress-bar").style.width = `${Math.max(0, Math.min(100, num(progress)))}%`;
    const err = document.getElementById("hx-error");
    err.textContent = error || ""; err.style.display = error ? "block" : "none";
  }

  function renderSingle(result) {
    const box = document.getElementById("hx-single"); if (!box || !result) return;
    const daily = num(result.profit_per_calendar_day_usdt);
    box.innerHTML = `<h2 class="hx-section-title">${esc(pairLabel(result.pair))} · unabhängiger 250-USDT-Test</h2>
      <div class="hx-grid">
        ${metric("Gewinn", money(result.profit_usdt), resultClass(result.profit_usdt))}
        ${metric("Endkapital", money(result.final_balance_usdt))}
        ${metric("Trades", esc(result.trades ?? 0))}
        ${metric("Profit Factor", num(result.profit_factor).toFixed(3))}
        ${metric("Max. Drawdown", pct(-Math.abs(num(result.max_drawdown_pct))), "hx-negative")}
        ${metric("Ø USDT / Tag", `${daily.toFixed(3)} USDT`, resultClass(daily))}
        ${metric("Kapitalzeit", `${num(result.capital_time_utilization_pct).toFixed(2)} %`)}
        ${metric("Testtage", esc(result.backtest_days ?? "?"))}
      </div>
      <div class="hx-note">Datenintegrität: ${result.data_integrity_validated ? "geprüft" : "nicht bestätigt"} · Zeitraum: ${esc(result.backtest_start)} bis ${esc(result.backtest_end)}${result.reused_existing_result ? " · identisches vorhandenes Ergebnis wiederverwendet" : ""}</div>`;
    box.style.display = "block";
  }

  function renderIndividuals(cases, years) {
    const box = document.getElementById("hx-individuals"); if (!box) return;
    if (!Array.isArray(cases) || !cases.length) { box.style.display = "none"; return; }
    const rows = cases.map((item) => {
      const r = item.result || {};
      if (item.status === "failed") return `<tr><td>${esc(pairLabel(item.pair))}</td><td colspan="8" class="bad">FEHLER: ${esc(item.error || "unbekannt")}</td></tr>`;
      return `<tr><td>${esc(pairLabel(item.pair))}</td><td class="${resultClass(r.profit_usdt)}">${money(r.profit_usdt)}</td><td>${num(r.trades)}</td><td>${num(r.profit_factor).toFixed(3)}</td><td>${num(r.max_drawdown_pct).toFixed(2)} %</td><td>${num(r.profit_per_calendar_day_usdt).toFixed(3)}</td><td>${num(r.capital_time_utilization_pct).toFixed(2)} %</td><td>${num(r.no_position_time_pct).toFixed(2)} %</td><td>${esc(item.status)}</td></tr>`;
    }).join("");
    box.innerHTML = `<h2 class="hx-section-title">10 unabhängige Hixton-Einzeltests · ${esc(years)} Jahr(e)</h2>
      <div class="hx-table-wrap"><table class="hx-table"><thead><tr><th>Coin</th><th>P/L</th><th>Trades</th><th>PF</th><th>DD</th><th>USDT/Tag</th><th>Kapitalzeit</th><th>Ohne Position</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="hx-note">Diese Ergebnisse sind zehn getrennte 250-USDT-Diagnosen. Ihre P/L-Werte dürfen nicht als gemeinsames 250-USDT-Ergebnis summiert werden.</div>`;
    box.style.display = "block";
  }

  function renderPortfolio(result, status, error) {
    const box = document.getElementById("hx-portfolio"); if (!box) return;
    if (status === "failed" || status === "blocked") {
      box.innerHTML = `<h2 class="hx-section-title">Gemeinsames 3×80-Portfolio</h2><div class="hx-error" style="display:block">${esc(error || "Portfolio wurde nicht ausgeführt.")}</div>`;
      box.style.display = "block"; return;
    }
    if (!result) { box.style.display = "none"; return; }
    const daily = num(result.profit_per_calendar_day_usdt);
    const targetPct = TARGET_PER_DAY > 0 ? 100 * daily / TARGET_PER_DAY : 0;
    const breakdown = Array.isArray(result.pair_breakdown) && result.pair_breakdown.length
      ? result.pair_breakdown.map((row) => `${esc(row.pair)}: ${num(row.trades)} Trades · ${money(row.profit_usdt)}`).join(" | ")
      : "Keine Pair-Aufschlüsselung verfügbar.";
    box.innerHTML = `<h2 class="hx-section-title">ECHTER GEMEINSAMER PORTFOLIO-LAUF · 250 USDT · max. 3×80</h2>
      <div class="hx-grid">
        ${metric("Portfolio-Gewinn", money(result.profit_usdt), resultClass(result.profit_usdt))}
        ${metric("Endkapital", money(result.final_balance_usdt))}
        ${metric("Trades", esc(result.trades ?? 0))}
        ${metric("Profit Factor", num(result.profit_factor).toFixed(3))}
        ${metric("Max. Drawdown", `${num(result.max_drawdown_pct).toFixed(2)} %`)}
        ${metric("Ø USDT / Kalendertag", `${daily.toFixed(3)} USDT`, resultClass(daily))}
        ${metric("Max. gleichzeitig", esc(result.max_simultaneous_positions ?? "?"))}
        ${metric("Max. eingesetztes Kapital", `${num(result.max_deployed_capital_usdt).toFixed(2)} USDT`)}
      </div>
      <div class="hx-target">Entwicklungsziel: ${TARGET_PER_DAY.toFixed(2)} USDT/Tag für das gesamte 3×80-System. Dieser Lauf erreicht historisch ${targetPct.toFixed(1)} % davon. Das ist eine Vergleichsmarke, keine Gewinnzusage.</div>
      <div class="hx-breakdown"><strong>Beitrag je Coin:</strong> ${breakdown}</div>
      <div class="hx-note">Chronologischer Freqtrade-Lauf: offene Positionen blockieren ihren Slot bis zum tatsächlichen Exit. Ergebnis ist das maßgebliche kombinierte Hixton-Resultat.${status === "reused" ? " Identischer bereits ausgeführter Portfolio-Fingerprint wurde wiederverwendet." : ""}</div>`;
    box.style.display = "block";
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || `${response.status} ${response.statusText}`);
    return payload;
  }
  const singleStatus = () => fetchJson("/api/v1/testbot/backtest/status");
  const batchStatus = () => fetchJson("/api/v1/testbot/backtest/batch/status");

  function renderBatch(state, single) {
    running = state.status === "running";
    setControls(running);
    let detail = state.stage || "Hixton-Gesamttest";
    if (running && state.current_pair && single && single.stage) detail += ` · ${single.stage}`;
    showStatus(detail, state.progress, state.batch_error || "");
    renderIndividuals(state.cases || [], state.years || 3);
    renderPortfolio(state.portfolio_result, state.portfolio_status, state.portfolio_error);
  }

  async function refresh() {
    try {
      const [one, batch] = await Promise.allSettled([singleStatus(), batchStatus()]);
      const single = one.status === "fulfilled" ? one.value : null;
      const matrix = batch.status === "fulfilled" ? batch.value : null;
      if (matrix && matrix.status !== "idle") {
        renderBatch(matrix, single);
      } else if (single) {
        running = single.status === "running"; setControls(running);
        showStatus(single.stage, single.progress, single.error || "");
        if (single.result) renderSingle(single.result);
      }
    } catch (error) {
      showStatus("Statusfehler", 100, String(error.message || error)); setControls(false);
    }
  }

  async function startOne() {
    setControls(true);
    document.getElementById("hx-individuals").style.display = "none";
    document.getElementById("hx-portfolio").style.display = "none";
    try {
      const payload = await fetchJson("/api/v1/testbot/backtest/start", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({pair:document.getElementById("hx-pair").value, years:Number(document.getElementById("hx-years").value)})
      });
      running = payload.status === "running"; showStatus(payload.stage, payload.progress); if (!pollTimer) pollTimer=setInterval(refresh,1000);
    } catch (error) { showStatus("Start fehlgeschlagen",100,String(error.message||error)); setControls(false); }
  }

  async function startAll() {
    setControls(true);
    document.getElementById("hx-single").style.display = "none";
    document.getElementById("hx-individuals").style.display = "none";
    document.getElementById("hx-portfolio").style.display = "none";
    try {
      const payload = await fetchJson("/api/v1/testbot/backtest/batch/start", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({years:Number(document.getElementById("hx-years").value)})
      });
      renderBatch(payload, null); if (!pollTimer) pollTimer=setInterval(refresh,1000);
    } catch (error) { showStatus("Gesamttest konnte nicht gestartet werden",100,String(error.message||error)); setControls(false); }
  }

  function hideView() {
    const view=document.getElementById(VIEW_ID); if(view)view.style.display="none";
    document.body.classList.remove(BODY_OPEN_CLASS);
  }
  function showView(event) {
    if(event)event.preventDefault(); const view=createView(); document.body.classList.add(BODY_OPEN_CLASS); syncTop(view); view.style.display="block"; refresh(); if(!pollTimer)pollTimer=setInterval(refresh,1000);
  }
  function replaceText(node, from, to) {
    if(node.nodeType===Node.TEXT_NODE){if(node.nodeValue?.includes(from))node.nodeValue=node.nodeValue.replace(from,to);return;} node.childNodes.forEach((child)=>replaceText(child,from,to));
  }
  function installNavigation() {
    if(document.getElementById(NAV_ID))return true;
    const logs=Array.from(document.querySelectorAll("a")).find((a)=>a.textContent?.trim()==="Logs");
    if(!logs||!logs.parentElement)return false;
    const nav=logs.cloneNode(true); nav.id=NAV_ID; nav.removeAttribute("href"); nav.setAttribute("role","button"); nav.setAttribute("title","Hixton Backtest"); replaceText(nav,"Logs","Backtest"); nav.addEventListener("click",showView); logs.parentElement.insertBefore(nav,logs.nextSibling);
    document.addEventListener("click",(event)=>{const a=event.target.closest&&event.target.closest("a");if(a&&a.id!==NAV_ID)hideView();},true);
    return true;
  }

  new MutationObserver(()=>installNavigation()).observe(document.documentElement,{childList:true,subtree:true});
  window.addEventListener("resize",()=>{const view=document.getElementById(VIEW_ID);if(view&&view.style.display!=="none")syncTop(view);});
  installNavigation();
})();