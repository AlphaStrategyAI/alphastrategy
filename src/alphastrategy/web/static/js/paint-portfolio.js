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

