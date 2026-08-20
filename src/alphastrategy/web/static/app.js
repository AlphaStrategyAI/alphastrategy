(function () {
  "use strict";

  const NUMERIC_CAPS = [
    "max_gross",
    "max_name_weight",
    "max_names",
    "max_order_notional_frac",
    "max_orders_per_rebalance",
    "max_orders_per_day",
    "min_delta_dollar",
    "min_delta_frac",
  ];

  const state = {
    status: null,
    portfolio: null,
    bundles: null,
    activity: [],
    risk: null,
    deviationActive: false,
  };

  function fmtNum(value, digits) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "—";
    }
    return Number(value).toLocaleString(undefined, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  function fmtPct(value) {
    if (value === null || value === undefined) return "—";
    return fmtNum(Number(value) * 100, 1) + "%";
  }

  function fmtCountdown(seconds) {
    const s = Math.max(0, Math.floor(Number(seconds) || 0));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    const mm = String(m).padStart(2, "0");
    const ss = String(sec).padStart(2, "0");
    if (h > 0) return `${h}:${mm}:${ss}`;
    return `${mm}:${ss}`;
  }

  function fmtContribution(map) {
    if (!map || typeof map !== "object") return "—";
    const keys = Object.keys(map);
    if (!keys.length) return "—";
    return keys
      .sort()
      .map((asset) => `${asset} ${fmtPct(map[asset])}`)
      .join(" · ");
  }

  async function api(method, path, body) {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    const response = await fetch(path, opts);
    let payload = null;
    const text = await response.text();
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch (_err) {
        payload = { error: text };
      }
    }
    if (!response.ok) {
      const message =
        payload && payload.error ? String(payload.error) : `HTTP ${response.status}`;
      throw new Error(message);
    }
    return payload;
  }

  function showScreen(name) {
    document.querySelectorAll(".screen").forEach((el) => {
      el.classList.toggle("active", el.id === `screen-${name}`);
    });
    document.querySelectorAll("#nav button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.screen === name);
    });
  }

  function setError(el, message) {
    if (!message) {
      el.classList.add("hidden");
      el.textContent = "";
      return;
    }
    el.classList.remove("hidden");
    el.textContent = message;
  }

  function showImportRejection(body) {
    const box = document.getElementById("import-error");
    const ok = document.getElementById("import-ok");
    if (ok) {
      ok.classList.add("hidden");
      ok.textContent = "";
    }
    if (!box) return;
    box.classList.remove("hidden");
    const kind = document.getElementById("import-error-kind");
    const title = document.getElementById("import-error-title");
    const detail = document.getElementById("import-error-detail");
    const next = document.getElementById("import-error-next");
    if (kind) kind.textContent = (body && body.kind) || "unknown";
    if (title) title.textContent = (body && body.title) || "Import rejected";
    if (detail) detail.textContent = (body && body.error) || "";
    if (next) next.textContent = (body && body.next) || "";
  }

  function showImportOk(bundleId) {
    const box = document.getElementById("import-error");
    if (box) box.classList.add("hidden");
    const ok = document.getElementById("import-ok");
    if (!ok) return;
    ok.classList.remove("hidden");
    ok.textContent = `Imported ${bundleId}. Import is not permission to trade.`;
  }

  function grossExposure(portfolio) {
    const equity = Number(portfolio.equity) || 0;
    if (!equity) return 0;
    const positions = portfolio.positions || [];
    let gross = 0;
    for (const pos of positions) {
      const qty = Number(pos.qty) || 0;
      const mv = Number(pos.market_value) || Number(pos.current_price) * qty || 0;
      gross += Math.abs(mv || qty);
    }
    return gross / equity;
  }

  function sleeveState(bundleId, bundles, status) {
    const stoppedList = (bundles && bundles.stopped) || [];
    const alloc = bundles.paper[bundleId];
    const sleeves = (state.portfolio && state.portfolio.sleeves) || {};
    if (stoppedList.indexOf(bundleId) >= 0) return "stopped";
    if (
      status &&
      status.state === "stopped" &&
      (alloc > 0 || Object.prototype.hasOwnProperty.call(sleeves, bundleId))
    ) {
      return "stopped";
    }
    if (alloc && alloc > 0) {
      if (status && status.halted) return "halted";
      return "paper";
    }
    return "imported";
  }

  function policyLabel(key) {
    const labels = (state.risk && state.risk.labels) || {};
    const spoken = labels[key];
    return spoken || key;
  }

  function riskSummary(policy) {
    if (!policy) return "—";
    return (
      policyLabel("max_gross") +
      " " +
      fmtPct(policy.max_gross) +
      " · " +
      policyLabel("max_name_weight") +
      " " +
      fmtPct(policy.max_name_weight)
    );
  }

  function importedIds() {
    const bundles = state.bundles || { imported: [], paper: {} };
    const paper = bundles.paper || {};
    return [...new Set([...(bundles.imported || []), ...Object.keys(paper)])];
  }

  function hasPaperSleeve() {
    const paper = (state.bundles && state.bundles.paper) || {};
    return Object.keys(paper).some((id) => Number(paper[id]) > 0);
  }

  function renderFirstRun() {
    const el = document.getElementById("first-run");
    if (!el) return;
    const empty = importedIds().length === 0;
    el.classList.toggle("hidden", !empty);
  }

  function wantedGotBar(wanted, got, cap) {
    const w = Math.max(0, Number(wanted) || 0);
    const g = Math.max(0, Number(got) || 0);
    const scale = Math.max(Number(cap) || 0.2, w, g, 0.01);
    const wPct = Math.min(100, (w / scale) * 100);
    const gPct = Math.min(100, (g / scale) * 100);
    const drift = Math.abs(w - g) > 0.001 ? " drift" : "";
    return (
      `<div class="wg-cell"><div class="wg-track${drift}" aria-label="wanted ${fmtPct(w)} got ${fmtPct(g)}">` +
      `<span class="wg-got" style="width:${gPct}%"></span>` +
      `<span class="wg-wanted" style="left:${wPct}%"></span>` +
      `</div></div>`
    );
  }

  function paintUtilTrack(bar, used, cap, label) {
    if (!bar) return;
    const limit = Number(cap);
    const safeLimit = limit > 0 ? limit : 0;
    const ratio = safeLimit ? Number(used || 0) / safeLimit : 0;
    const pct = Math.min(100, Math.max(0, ratio * 100));
    bar.classList.remove("hidden", "warn", "fail");
    if (safeLimit && ratio >= 1) bar.classList.add("fail");
    else if (safeLimit && ratio >= 0.9) bar.classList.add("warn");
    bar.innerHTML = `<span class="util-fill" style="width:${pct}%"></span>`;
    bar.setAttribute("aria-label", label);
    bar.removeAttribute("aria-hidden");
  }

  function utilization() {
    return (
      (state.status && state.status.utilization) ||
      (state.risk && state.risk.utilization) ||
      {}
    );
  }

  function renderGrossUtilization(gross) {
    const bar = document.getElementById("metric-gross-bar");
    const cap = Number(state.risk && state.risk.account && state.risk.account.max_gross);
    const limit = cap > 0 ? cap : 1;
    paintUtilTrack(bar, gross, limit, `gross ${fmtPct(gross)} of cap ${fmtPct(limit)}`);
  }

  function renderRemainingBudgets() {
    const util = utilization();
    const names = util.names;
    const maxNames = util.max_names;
    const orders = util.orders_today;
    const maxOrders = util.max_orders_per_day;
    document.getElementById("metric-names").textContent =
      names == null || names === undefined ? "—" : String(names);
    document.getElementById("metric-names-cap").textContent =
      maxNames == null || maxNames === undefined ? "—" : `of ${maxNames}`;
    paintUtilTrack(
      document.getElementById("metric-names-bar"),
      names || 0,
      maxNames || 0,
      `names ${names} of ${maxNames}`
    );
    document.getElementById("metric-orders").textContent =
      orders == null || orders === undefined ? "—" : String(orders);
    document.getElementById("metric-orders-cap").textContent =
      maxOrders == null || maxOrders === undefined ? "—" : `of ${maxOrders}`;
    paintUtilTrack(
      document.getElementById("metric-orders-bar"),
      orders || 0,
      maxOrders || 0,
      `orders today ${orders} of ${maxOrders}`
    );
  }

  function renderCashComposition() {
    const util = utilization();
    const sub = document.getElementById("metric-cash-sub");
    const bar = document.getElementById("metric-cash-bar");
    if (!sub || !bar) return;
    const invested = util.invested_weight;
    const cashW = util.cash_weight;
    const target = util.target_cash_weight;
    if (invested == null || cashW == null) {
      sub.textContent = "—";
      bar.classList.add("hidden");
      bar.setAttribute("aria-hidden", "true");
      bar.innerHTML = "";
      return;
    }
    let line = `invested ${fmtPct(invested)} · cash ${fmtPct(cashW)}`;
    if (target != null) {
      line += ` · target cash ${fmtPct(target)}`;
    }
    sub.textContent = line;
    const pct = Math.min(100, Math.max(0, Number(invested) * 100));
    let marker = "";
    if (target != null) {
      const investedTarget = Math.min(100, Math.max(0, (1 - Number(target)) * 100));
      marker = `<span class="wg-wanted" style="left:${investedTarget}%"></span>`;
    }
    bar.classList.remove("hidden");
    bar.removeAttribute("aria-hidden");
    bar.innerHTML = `<span class="cash-invested" style="width:${pct}%"></span>${marker}`;
    bar.setAttribute(
      "aria-label",
      `invested ${fmtPct(invested)} cash ${fmtPct(cashW)}` +
        (target != null ? ` target cash ${fmtPct(target)}` : "")
    );
  }

  function renderRiskUtilization() {
    const container = document.getElementById("risk-utilization");
    if (!container) return;
    container.innerHTML = "";
    const util = utilization();
    function addCapRow(label, used, cap) {
      const row = document.createElement("div");
      const usedText = used == null || used === undefined ? "—" : used;
      const capText = cap == null || cap === undefined ? "—" : cap;
      const text = document.createElement("div");
      text.innerHTML = `<span class="muted">${label}</span> <span class="nums">${usedText} / ${capText}</span>`;
      const track = document.createElement("div");
      track.className = "util-track";
      paintUtilTrack(track, Number(used) || 0, Number(cap) || 0, `${label} ${usedText} of ${capText}`);
      row.appendChild(text);
      row.appendChild(track);
      container.appendChild(row);
    }
    addCapRow("Names", util.names, util.max_names);
    addCapRow("Orders today", util.orders_today, util.max_orders_per_day);
    const cashRow = document.createElement("div");
    const invested = util.invested_weight;
    const cashW = util.cash_weight;
    const cashText =
      invested == null || cashW == null
        ? "—"
        : `invested ${fmtPct(invested)} · cash ${fmtPct(cashW)}`;
    cashRow.innerHTML = `<span class="muted">Cash</span> <span class="nums">${cashText}</span>`;
    container.appendChild(cashRow);
  }

  function renderSessionMetrics() {
    const sessionEl = document.getElementById("metric-session");
    const countEl = document.getElementById("metric-countdown");
    const kindEl = document.getElementById("metric-countdown-kind");
    const clockLine = document.getElementById("clock-line");
    const clock = state.status && state.status.clock;
    const countdown = state.status && state.status.countdown;
    sessionEl.classList.remove("open");
    if (!clock || clock.error) {
      sessionEl.textContent = "UNAVAILABLE";
      countEl.textContent = "—";
      kindEl.textContent = "—";
      clockLine.textContent = "Clock unavailable";
      return;
    }
    if (clock.is_open) {
      sessionEl.textContent = "OPEN";
      sessionEl.classList.add("open");
    } else {
      sessionEl.textContent = "CLOSED";
    }
    if (countdown) {
      countEl.textContent = fmtCountdown(countdown.seconds);
      kindEl.textContent = countdown.next_rebalance || "—";
    } else {
      countEl.textContent = "—";
      kindEl.textContent = "—";
    }
    clockLine.textContent = `now ${clock.timestamp || "—"}`;
  }

  function nameCapBar(got, cap) {
    const g = Math.max(0, Number(got) || 0);
    const limit = Number(cap) > 0 ? Number(cap) : 0.2;
    const ratio = g / limit;
    const pct = Math.min(100, Math.max(0, ratio * 100));
    let cls = "util-track";
    if (ratio >= 1) cls += " fail";
    else if (ratio >= 0.9) cls += " warn";
    return (
      `<div class="wg-cell"><div class="${cls}" aria-label="name ${fmtPct(g)} of cap ${fmtPct(limit)}">` +
      `<span class="util-fill" style="width:${pct}%"></span></div></div>`
    );
  }

  function renderSleeveAllocBook(sleeves) {
    const track = document.getElementById("sleeve-alloc-track");
    const label = document.getElementById("sleeve-alloc-label");
    const ids = Object.keys(sleeves || {});
    if (!track || !label) return;
    if (!ids.length) {
      track.classList.add("hidden");
      label.classList.add("hidden");
      track.innerHTML = "";
      return;
    }
    const spoken = ids.reduce((sum, id) => sum + (Number(sleeves[id]) || 0), 0);
    const pct = Math.min(100, Math.max(0, spoken * 100));
    track.classList.remove("hidden", "warn", "fail");
    label.classList.remove("hidden");
    if (spoken >= 1) track.classList.add("fail");
    else if (spoken >= 0.9) track.classList.add("warn");
    track.innerHTML = `<span class="util-fill" style="width:${pct}%"></span>`;
    track.removeAttribute("aria-hidden");
    track.setAttribute("aria-label", `spoken ${fmtPct(spoken)} of paper book`);
    label.textContent = `Spoken ${fmtPct(spoken)} of paper book`;
  }

  function renderBanners() {
    const haltEl = document.getElementById("halt-banner");
    const flattenEl = document.getElementById("flatten-banner");
    const devEl = document.getElementById("deviation-banner");
    const halted = state.status && state.status.halted;
    const flattened =
      (state.status && state.status.flattened) ||
      (state.status &&
        (state.status.state === "stopped" || state.status.state === "flattening"));
    const reason =
      (state.portfolio && state.portfolio.halt_reason) ||
      (state.status && state.status.halt_reason) ||
      "";

    if (halted || reason) {
      haltEl.classList.remove("hidden");
      haltEl.textContent = `HALT: ${reason || state.status.state || "halted"}`;
    } else {
      haltEl.classList.add("hidden");
    }

    if (flattened) {
      flattenEl.classList.remove("hidden");
      flattenEl.textContent = "FLAT: paper account flattened";
    } else {
      flattenEl.classList.add("hidden");
    }

    if (state.deviationActive) {
      devEl.classList.remove("hidden");
      devEl.textContent = "DEVIATION: execution drift exceeds tolerance";
    } else {
      devEl.classList.add("hidden");
    }

    const killEl = document.getElementById("kill-outcome-banner");
    const lastKill = state.status && state.status.last_kill;
    const killReason = lastKill && lastKill.reason;
    if (killReason === "isolated") {
      killEl.className = "banner halt";
      killEl.textContent =
        "SLEEVE KILL: isolated residual for " +
        (lastKill.bundle_id || "sleeve") +
        " — other sleeves still live";
    } else if (killReason === "fallback_not_ready" || killReason === "fallback_error") {
      killEl.className = "banner fail";
      killEl.textContent =
        "SLEEVE KILL: could not isolate — whole paper account flattened";
    } else if (killReason === "unknown_sleeve") {
      killEl.className = "banner halt";
      killEl.textContent =
        "SLEEVE KILL: unknown sleeve " + (lastKill.bundle_id || "");
    } else {
      killEl.className = "banner halt hidden";
      killEl.textContent = "";
    }
  }

  function renderPortfolio() {
    const portfolio = state.portfolio || {};
    const equity = Number(portfolio.equity);
    const cash = Number(portfolio.cash);
    const pnl = Number(portfolio.pnl);

    document.getElementById("metric-equity").textContent = fmtNum(equity, 2);
    document.getElementById("metric-cash").textContent = fmtNum(cash, 2);

    const pnlEl = document.getElementById("metric-pnl");
    pnlEl.textContent = fmtNum(pnl, 2);
    pnlEl.classList.remove("positive", "negative");
    if (pnl > 0) pnlEl.classList.add("positive");
    if (pnl < 0) pnlEl.classList.add("negative");

    const gross = grossExposure(portfolio);
    document.getElementById("metric-gross").textContent = fmtPct(gross);
    renderGrossUtilization(gross);
    renderRemainingBudgets();
    renderCashComposition();
    renderFirstRun();
    renderSessionMetrics();

    const posBody = document.querySelector("#positions-table tbody");
    posBody.innerHTML = "";
    const positions = portfolio.positions || [];
    if (!positions.length) {
      let empty = "No positions yet. Import a .asb to begin.";
      if (importedIds().length) {
        empty = hasPaperSleeve()
          ? "No positions yet. The next legal open or close rebalance will trade."
          : "Imported bundles are not trading. Start paper on Run.";
      }
      posBody.innerHTML = `<tr><td colspan='7' class='muted'>${empty}</td></tr>`;
    } else {
      const cap =
        (state.risk && state.risk.account && state.risk.account.max_name_weight) || 0.2;
      for (const pos of positions) {
        const tr = document.createElement("tr");
        const notional = pos.notional == null ? "—" : fmtNum(pos.notional, 2);
        const wanted = pos.wanted == null ? "—" : fmtPct(pos.wanted);
        const got = pos.weight == null ? "—" : fmtPct(pos.weight);
        tr.innerHTML =
          `<td>${pos.symbol || "—"}</td><td class="nums">${fmtNum(pos.qty, 4)}</td>` +
          `<td class="nums">${notional}</td><td class="nums">${wanted}</td>` +
          `<td class="nums">${got}</td><td>${wantedGotBar(pos.wanted, pos.weight, cap)}</td>` +
          `<td>${nameCapBar(pos.weight, cap)}</td>`;
        posBody.appendChild(tr);
      }
    }

    const sleeveBody = document.querySelector("#sleeves-table tbody");
    sleeveBody.innerHTML = "";
    const sleeves = portfolio.sleeves || {};
    const contrib = portfolio.sleeve_contribution || {};
    const ids = Object.keys(sleeves).sort();
    if (!ids.length) {
      sleeveBody.innerHTML = "<tr><td colspan='3' class='muted'>No sleeves</td></tr>";
    } else {
      for (const id of ids) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${id}</td><td class="nums">${fmtPct(sleeves[id])}</td><td class="nums">${fmtContribution(contrib[id])}</td>`;
        sleeveBody.appendChild(tr);
      }
    }
    renderSleeveAllocBook(sleeves);

    renderBanners();
  }

  function pulseLabel(pulse) {
    if (pulse === "live") return "LIVE";
    if (pulse === "stale") return "STALE";
    if (pulse === "dead") return "DEAD";
    return "NO BEAT";
  }

  function renderDeskPulse() {
    const wrap = document.getElementById("desk-pulse");
    const label = document.getElementById("desk-pulse-label");
    if (!wrap || !label) return;
    const hb = (state.status && state.status.heartbeat) || {};
    const pulse = hb.pulse || "missing";
    wrap.className = "desk-pulse " + pulse;
    label.textContent = pulseLabel(pulse);
    const age = hb.age_seconds;
    const ageText = age == null || age === undefined ? "no stamp" : age + "s ago";
    wrap.title = "Supervisor beat " + pulseLabel(pulse) + " · " + ageText;
  }

  function renderStrategies() {
    const bundles = state.bundles || { imported: [], paper: {} };
    const risk = state.risk || { sleeves: {} };
    const tbody = document.querySelector("#strategies-table tbody");
    tbody.innerHTML = "";

    const ids = [...new Set([...bundles.imported, ...Object.keys(bundles.paper)])].sort();
    if (!ids.length) {
      tbody.innerHTML = "<tr><td colspan='4' class='muted'>No bundles imported</td></tr>";
      return;
    }

    for (const id of ids) {
      const st = sleeveState(id, bundles, state.status);
      const alloc = bundles.paper[id] || 0;
      const policy = risk.sleeves[id];
      const statusClass =
        st === "paper" ? "running" : st === "halted" ? "halt" : st === "stopped" ? "stopped" : "muted";
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${id}</td>
        <td class="status-${statusClass}">${st}</td>
        <td class="nums">${fmtPct(alloc)}</td>
        <td class="muted">${riskSummary(policy)}</td>
      `;
      tbody.appendChild(tr);
    }

    const select = document.getElementById("start-bundle");
    const prev = select.value;
    select.innerHTML = "";
    for (const id of bundles.imported) {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = id;
      select.appendChild(opt);
    }
    if (prev && bundles.imported.includes(prev)) {
      select.value = prev;
    }
  }

  function runFormIsDirty() {
    const container = document.getElementById("run-sleeves");
    if (!container) return false;
    if (container.contains(document.activeElement)) return true;
    const inputs = container.querySelectorAll("input");
    for (const input of inputs) {
      if (input.type === "checkbox") {
        if (input.checked) return true;
        continue;
      }
      if (input.name === "allocation" && input.value !== input.dataset.current) {
        return true;
      }
    }
    return false;
  }

  function renderRunSleeves() {
    const bundles = state.bundles || { imported: [], paper: {} };
    const container = document.getElementById("run-sleeves");
    container.innerHTML = "";

    const ids = [...new Set([...bundles.imported, ...Object.keys(bundles.paper)])].sort();
    for (const id of ids) {
      const card = document.createElement("div");
      card.className = "sleeve-card panel";
      const alloc = bundles.paper[id] || 0;
      card.innerHTML = `
        <h3>${id}</h3>
        <form class="inline sleeve-alloc-form" data-bundle="${id}">
          <label>
            Allocation
            <input type="number" min="0" max="1" step="0.01" name="allocation" value="${alloc}" data-current="${alloc}" required>
          </label>
          <label class="confirm-row">
            <input type="checkbox" name="confirm">
            Confirm paper allocation
          </label>
          <button type="submit" class="action primary">Set allocation</button>
        </form>
        <div class="inline">
          <button type="button" class="action warn" data-stop="${id}">Stop</button>
          <label class="confirm-row">
            <input type="checkbox" data-kill-confirm="${id}">
            Confirm sleeve kill
          </label>
          <button type="button" class="action danger" data-kill="${id}">Kill sleeve</button>
        </div>
      `;
      container.appendChild(card);
    }

    container.querySelectorAll(".sleeve-alloc-form").forEach((form) => {
      form.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const errEl = document.getElementById("run-error");
        const bundleId = form.dataset.bundle;
        const allocation = Number(form.querySelector('[name="allocation"]').value);
        const confirmed = form.querySelector('[name="confirm"]').checked;
        if (!confirmed) {
          setError(errEl, "Confirm paper allocation required");
          return;
        }
        try {
          await api("POST", "/api/paper/start", { bundle_id: bundleId, allocation });
          setError(errEl, "");
          const allocInput = form.querySelector('[name="allocation"]');
          form.querySelector('[name="confirm"]').checked = false;
          allocInput.dataset.current = allocInput.value;
          await refresh();
        } catch (err) {
          setError(errEl, err.message);
        }
      });
    });

    container.querySelectorAll("[data-stop]").forEach((btn) => {
      btn.addEventListener("click", () => stopSleeve(btn.dataset.stop));
    });
    container.querySelectorAll("[data-kill]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const bundleId = btn.dataset.kill;
        const box = container.querySelector(`[data-kill-confirm="${bundleId}"]`);
        if (!box || !box.checked) {
          setError(document.getElementById("run-error"), "Confirm sleeve kill");
          return;
        }
        box.checked = false;
        killSleeve(bundleId);
      });
    });
  }

  function eventSummary(ev) {
    switch (ev.event) {
      case "order":
        return `${ev.side || ""} ${ev.qty || ""} ${ev.symbol || ""}`.trim();
      case "halt":
        return ev.reason || "halt";
      case "rebalance": {
        const wantedN = ev.wanted && typeof ev.wanted === "object" ? Object.keys(ev.wanted).length : 0;
        const gotN = ev.got && typeof ev.got === "object" ? Object.keys(ev.got).length : 0;
        const orders = ev.orders == null ? "" : `${ev.orders} orders`;
        return `${ev.session_event || ""} · ${orders} · wanted ${wantedN} got ${gotN}`.trim();
      }
      case "execution_deviation":
        return `${ev.asset || ""} wanted ${ev.wanted} got ${ev.got}`;
      case "paper_start":
      case "paper_stop":
      case "import":
        return ev.bundle_id || ev.scope || "";
      case "kill": {
        const id = ev.bundle_id || "";
        if (ev.isolated === true) {
          return `isolated residual ${id}`.trim();
        }
        if (ev.isolated === false || ev.scope === "account") {
          return `flattened account ${id}`.trim();
        }
        return id || ev.scope || "";
      }
      case "flatten":
        return ev.scope || "account";
      default:
        return ev.event || "event";
    }
  }

  function renderActivity() {
    const list = document.getElementById("activity-list");
    list.innerHTML = "";
    const events = state.activity || [];
    const hb = (state.status && state.status.heartbeat) || {};
    const pulse = hb.pulse || "missing";
    const beatLine = document.getElementById("activity-heartbeat");
    if (beatLine) {
      const age = hb.age_seconds;
      const st = (state.status && state.status.state) || "—";
      const ageText = age == null || age === undefined ? "—" : age + "s ago";
      beatLine.textContent = `Beat ${pulseLabel(pulse)} · ${ageText} · ${st}`;
    }
    if (!events.length) {
      const copy =
        pulse === "dead" || pulse === "missing"
          ? "No audit events yet. Supervisor beat is not live."
          : "Heartbeat is running. No audit events yet. Rebalances fire at open+3m and close−12m.";
      list.innerHTML = `<li class='muted'>${copy}</li>`;
      return;
    }
    for (const ev of events.slice().reverse()) {
      const li = document.createElement("li");
      li.tabIndex = 0;
      const ts = ev.ts || ev.timestamp || "";
      const summary = document.createElement("div");
      summary.className = "activity-summary";
      summary.textContent = `${ts} ${ev.event || "event"} ${eventSummary(ev)}`;
      const detail = document.createElement("pre");
      detail.className = "activity-detail";
      const payload = { ...ev };
      delete payload.ts;
      delete payload.timestamp;
      delete payload.event;
      detail.textContent = JSON.stringify(payload, null, 2);
      li.appendChild(summary);
      li.appendChild(detail);
      li.addEventListener("click", () => {
        const open = li.classList.contains("expanded");
        list.querySelectorAll("li.expanded").forEach((row) => row.classList.remove("expanded"));
        if (!open) li.classList.add("expanded");
      });
      li.addEventListener("keydown", (ke) => {
        if (ke.key === "Enter" || ke.key === " ") {
          ke.preventDefault();
          li.click();
        }
      });
      list.appendChild(li);
    }
  }

  function renderRiskCaps(container, policy) {
    container.innerHTML = "";
    if (!policy) {
      container.textContent = "—";
      return;
    }
    for (const key of NUMERIC_CAPS) {
      const row = document.createElement("div");
      const val = policy[key];
      row.innerHTML = `<span class="muted">${policyLabel(key)}</span> <span class="nums">${val}</span>`;
      container.appendChild(row);
    }
    const longRow = document.createElement("div");
    longRow.innerHTML = `<span class="muted">${policyLabel("long_only")}</span> <span class="nums">${policy.long_only}</span>`;
    container.appendChild(longRow);
  }

  function buildRiskInputs(prefix, policy, current) {
    const form = document.createElement("form");
    form.className = "inline";
    form.dataset.prefix = prefix;

    for (const key of NUMERIC_CAPS) {
      const label = document.createElement("label");
      label.textContent = policyLabel(key);
      const input = document.createElement("input");
      input.type = "number";
      input.name = key;
      input.step = key.includes("frac") || key === "max_gross" || key === "max_name_weight" ? "0.01" : "1";
      input.placeholder = String(current[key]);
      input.dataset.current = String(current[key]);
      label.appendChild(input);
      form.appendChild(label);
    }

    const submit = document.createElement("button");
    submit.type = "submit";
    submit.className = "action primary";
    submit.textContent = "Tighten";
    form.appendChild(submit);
    return form;
  }

  function validateTighten(patch, current) {
    for (const key of NUMERIC_CAPS) {
      if (patch[key] === undefined) continue;
      const proposed = Number(patch[key]);
      const base = Number(current[key]);
      if (key === "min_delta_dollar" || key === "min_delta_frac") {
        if (proposed < base) {
          return `${policyLabel(key)} cannot loosen below ${base}`;
        }
      } else if (key === "max_names" || key === "max_orders_per_rebalance" || key === "max_orders_per_day") {
        if (proposed > base) {
          return `${policyLabel(key)} cannot loosen above ${base}`;
        }
      } else {
        if (proposed > base) {
          return `${policyLabel(key)} cannot loosen above ${base}`;
        }
      }
    }
    return null;
  }

  function riskFormIsDirty() {
    const forms = document.querySelectorAll("#screen-risk form");
    for (const form of forms) {
      if (form.contains(document.activeElement)) return true;
      const inputs = form.querySelectorAll("input");
      for (const input of inputs) {
        if (input.type === "checkbox") continue;
        if (input.value) return true;
      }
    }
    return false;
  }

  function renderRisk() {
    const risk = state.risk || { account: {}, sleeves: {} };
    renderRiskCaps(document.getElementById("risk-account-caps"), risk.account);
    renderRiskUtilization();
    if (riskFormIsDirty()) {
      return;
    }

    const accountForm = document.getElementById("risk-account-form");
    accountForm.innerHTML = "";
    const built = buildRiskInputs("account", risk.account, risk.account);
    accountForm.replaceWith(built);
    built.id = "risk-account-form";
    built.addEventListener("submit", onRiskAccountSubmit);

    const sleevesEl = document.getElementById("risk-sleeves");
    sleevesEl.innerHTML = "";
    const ids = Object.keys(risk.sleeves || {}).sort();
    if (!ids.length) {
      sleevesEl.innerHTML = "<p class='muted'>No sleeve overlays</p>";
      return;
    }
    for (const id of ids) {
      const panel = document.createElement("div");
      panel.className = "panel";
      const alloc = ((state.bundles && state.bundles.paper) || {})[id] || 0;
      panel.innerHTML = `<h2>${id}</h2><p class="muted nums">Allocation ${fmtPct(alloc)}</p>`;
      const form = buildRiskInputs(id, risk.sleeves[id], risk.sleeves[id]);
      form.addEventListener("submit", (ev) => onRiskSleeveSubmit(ev, id));
      panel.appendChild(form);
      sleevesEl.appendChild(panel);
    }
  }

  function detectDeviation(events) {
    let active = false;
    for (const ev of events) {
      if (ev.event === "execution_deviation") {
        active = true;
      }
      if (ev.event === "resume" || ev.event === "flatten" || ev.event === "rebalance") {
        active = false;
      }
    }
    return active;
  }

  async function refresh() {
    try {
      const [status, portfolio, bundles, activity, risk] = await Promise.all([
        api("GET", "/api/status"),
        api("GET", "/api/portfolio"),
        api("GET", "/api/bundles"),
        api("GET", "/api/activity"),
        api("GET", "/api/risk"),
      ]);
      state.status = status;
      state.portfolio = portfolio;
      state.bundles = bundles;
      state.activity = activity;
      state.risk = risk;
      state.deviationActive = detectDeviation(activity);
      if (portfolio.deviation || portfolio.deviations) {
        state.deviationActive = true;
      }
      const banner = document.getElementById("control-plane-banner");
      banner.classList.add("hidden");
      banner.textContent = "";
      renderDeskPulse();
      renderPortfolio();
      renderStrategies();
      if (!runFormIsDirty()) {
        renderRunSleeves();
      }
      renderActivity();
      renderRisk();
    } catch (err) {
      const banner = document.getElementById("control-plane-banner");
      banner.classList.remove("hidden");
      banner.textContent = `CONTROL PLANE: refresh failed — ${err.message}`;
    }
  }

  async function stopSleeve(bundleId) {
    const errEl = document.getElementById("run-error");
    try {
      await api("POST", "/api/paper/stop", { bundle_id: bundleId });
      setError(errEl, "");
      await refresh();
    } catch (err) {
      setError(errEl, err.message);
    }
  }

  async function killSleeve(bundleId) {
    const errEl = document.getElementById("run-error");
    try {
      await api("POST", "/api/paper/kill", { bundle_id: bundleId });
      setError(errEl, "");
      await refresh();
    } catch (err) {
      setError(errEl, err.message);
    }
  }

  async function onImportSubmit(ev) {
    ev.preventDefault();
    const fileInput = document.getElementById("import-file");
    if (!fileInput.files.length) return;

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
      const response = await fetch("/api/import", { method: "POST", body: formData });
      const text = await response.text();
      let payload = null;
      try {
        payload = JSON.parse(text);
      } catch (_e) {
        payload = { error: text };
      }
      if (!response.ok) {
        showImportRejection(payload && typeof payload === "object" ? payload : { error: text });
        return;
      }
      showImportOk(payload.bundle_id);
      fileInput.value = "";
      await refresh();
    } catch (err) {
      showImportRejection({
        kind: "unknown",
        title: "Import rejected",
        error: err.message,
        next: "Fix the .asb or re-export from alphaloop.",
      });
    }
  }

  async function onStartSubmit(ev) {
    ev.preventDefault();
    const errEl = document.getElementById("run-error");
    const bundleId = document.getElementById("start-bundle").value;
    const allocation = Number(document.getElementById("start-allocation").value);
    const confirmed = document.getElementById("start-confirm").checked;
    if (!confirmed) {
      setError(errEl, "Confirm paper start required");
      return;
    }
    try {
      await api("POST", "/api/paper/start", { bundle_id: bundleId, allocation });
      setError(errEl, "");
      document.getElementById("start-confirm").checked = false;
      await refresh();
    } catch (err) {
      setError(errEl, err.message);
    }
  }

  async function onRiskAccountSubmit(ev) {
    ev.preventDefault();
    const errEl = document.getElementById("risk-error");
    const form = ev.target;
    const current = state.risk.account;
    const patch = {};
    for (const key of NUMERIC_CAPS) {
      const input = form.querySelector(`[name="${key}"]`);
      if (input && input.value !== "") {
        patch[key] = Number(input.value);
      }
    }
    const violation = validateTighten(patch, current);
    if (violation) {
      setError(errEl, violation);
      return;
    }
    if (!Object.keys(patch).length) {
      setError(errEl, "Enter at least one tighter cap");
      return;
    }
    try {
      await api("PUT", "/api/risk", { account: patch });
      setError(errEl, "");
      form.reset();
      await refresh();
    } catch (err) {
      setError(errEl, err.message);
    }
  }

  async function onRiskSleeveSubmit(ev, bundleId) {
    ev.preventDefault();
    const errEl = document.getElementById("risk-error");
    const form = ev.target;
    const current = state.risk.sleeves[bundleId];
    const patch = {};
    for (const key of NUMERIC_CAPS) {
      const input = form.querySelector(`[name="${key}"]`);
      if (input && input.value !== "") {
        patch[key] = Number(input.value);
      }
    }
    const violation = validateTighten(patch, current);
    if (violation) {
      setError(errEl, violation);
      return;
    }
    if (!Object.keys(patch).length) {
      setError(errEl, "Enter at least one tighter cap");
      return;
    }
    try {
      await api("PUT", "/api/risk", { sleeves: { [bundleId]: patch } });
      setError(errEl, "");
      form.reset();
      await refresh();
    } catch (err) {
      setError(errEl, err.message);
    }
  }

  document.getElementById("nav").addEventListener("click", (ev) => {
    const btn = ev.target.closest("button[data-screen]");
    if (!btn) return;
    showScreen(btn.dataset.screen);
  });

  document.addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-go-screen]");
    if (!btn) return;
    showScreen(btn.getAttribute("data-go-screen"));
  });

  document.getElementById("import-form").addEventListener("submit", onImportSubmit);
  document.getElementById("start-form").addEventListener("submit", onStartSubmit);

  document.getElementById("account-kill").addEventListener("click", async () => {
    const errEl = document.getElementById("run-error");
    const confirmed = document.getElementById("account-kill-confirm").checked;
    const phrase = document.getElementById("account-kill-phrase").value;
    if (!confirmed || phrase !== "FLATTEN") {
      setError(errEl, "Type FLATTEN and confirm to flatten the whole paper account");
      return;
    }
    try {
      await api("POST", "/api/paper/kill", {});
      setError(errEl, "");
      document.getElementById("account-kill-confirm").checked = false;
      document.getElementById("account-kill-phrase").value = "";
      await refresh();
    } catch (err) {
      setError(errEl, err.message);
    }
  });

  document.getElementById("account-resume").addEventListener("click", async () => {
    const errEl = document.getElementById("run-error");
    try {
      await api("POST", "/api/paper/resume", {});
      setError(errEl, "");
      await refresh();
    } catch (err) {
      setError(errEl, err.message);
    }
  });

  const helpState = { loaded: false };

  function renderHelp(payload) {
    const body = document.getElementById("help-body");
    body.innerHTML = "";
    const title = document.createElement("p");
    title.className = "muted";
    title.textContent = payload.title || "Operator help";
    body.appendChild(title);
    const sections = payload.sections || [];
    for (const section of sections) {
      const h = document.createElement("h3");
      h.textContent = section.title || "";
      const p = document.createElement("p");
      p.textContent = section.body || "";
      body.appendChild(h);
      body.appendChild(p);
    }
  }

  async function loadHelp() {
    const body = document.getElementById("help-body");
    try {
      const payload = await api("GET", "/api/help");
      renderHelp(payload);
      helpState.loaded = true;
    } catch (err) {
      body.textContent = `Help unavailable — ${err.message}`;
    }
  }

  function setHelpOpen(open) {
    const panel = document.getElementById("help-panel");
    const toggle = document.getElementById("help-toggle");
    panel.classList.toggle("hidden", !open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    if (open && !helpState.loaded) {
      loadHelp();
    }
  }

  document.getElementById("help-toggle").addEventListener("click", () => {
    const open =
      document.getElementById("help-toggle").getAttribute("aria-expanded") === "true";
    setHelpOpen(!open);
  });

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") {
      setHelpOpen(false);
      return;
    }
    if (ev.ctrlKey || ev.metaKey) return;
    if (ev.key === "F1") {
      ev.preventDefault();
      const open =
        document.getElementById("help-toggle").getAttribute("aria-expanded") === "true";
      setHelpOpen(!open);
      return;
    }
    if (!ev.altKey) return;
    const SCREEN_KEYS = {
      Digit1: "portfolio",
      Digit2: "strategies",
      Digit3: "run",
      Digit4: "activity",
      Digit5: "risk",
    };
    const screen = SCREEN_KEYS[ev.code];
    if (!screen) return;
    ev.preventDefault();
    showScreen(screen);
  });

  refresh();
  setInterval(refresh, 5000);
})();
