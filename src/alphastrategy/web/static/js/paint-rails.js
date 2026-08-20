  function finiteNumber(value, fallback) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function bookSourceLabel() {
    const src = state.status && state.status.book && state.status.book.source;
    const age =
      state.status && state.status.heartbeat && state.status.heartbeat.age_seconds;
    if (src === "heartbeat") {
      return Number.isFinite(age) ? "Beat " + age + "s" : "Beat";
    }
    if (src === "glance") return "Glance";
    return "—";
  }

  function paintBookSourceHeadings() {
    const label = bookSourceLabel();
    const text = label === "—" ? "" : label;
    ["book-source", "act-book-source", "risk-book-source"].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
    });
  }

  function paintDayPnl(portfolio) {
    const pnlEl = document.getElementById("metric-pnl");
    if (!pnlEl) return;
    const pnlSub = document.getElementById("metric-pnl-sub");
    const raw = portfolio && portfolio.pnl;
    const pnl = Number(raw);
    const hasPnl = raw != null && raw !== "" && Number.isFinite(pnl);
    pnlEl.textContent = hasPnl ? fmtNum(pnl, 2) : "—";
    pnlEl.classList.toggle("positive", hasPnl && pnl > 0);
    pnlEl.classList.toggle("negative", hasPnl && pnl < 0);
    if (pnlSub) {
      pnlSub.textContent =
        hasPnl && portfolio.pnl_source === "last_close" ? "vs last close" : "—";
    }
  }

  function formatDayPnlCell(raw) {
    const n = Number(raw);
    const has = raw != null && raw !== "" && Number.isFinite(n);
    const cls = has && n > 0 ? " positive" : has && n < 0 ? " negative" : "";
    return `<td class="nums${cls}">${has ? fmtNum(n, 2) : "—"}</td>`;
  }

  function wantedGotBar(wanted, got, cap, fill) {
    const w = Math.max(0, Number(wanted) || 0);
    const g = Math.max(0, Number(got) || 0);
    const capN = finiteNumber(cap, 0.2);
    const scale = Math.max(capN, w, g, 0.01);
    const wPct = Math.min(100, (w / scale) * 100);
    const gPct = Math.min(100, (g / scale) * 100);
    const fillW =
      fill == null || fill === undefined ? g : Math.max(0, Number(fill) || 0);
    const drift = Math.abs(w - fillW) > 0.001 ? " drift" : "";
    return (
      `<div class="wg-cell"><div class="wg-track${drift}" aria-label="wanted ${fmtPct(w)} got ${fmtPct(g)}">` +
      `<span class="wg-got" style="width:${gPct}%"></span>` +
      `<span class="wg-wanted" style="left:${wPct}%"></span>` +
      `</div></div>`
    );
  }

  function paintUtilTrack(bar, used, cap, label) {
    if (!bar) return;
    const usedN = Number(used) || 0;
    const limit = Number(cap);
    bar.classList.remove("hidden", "warn", "fail");
    bar.removeAttribute("aria-hidden");
    if (!Number.isFinite(limit)) {
      bar.classList.add("hidden");
      bar.setAttribute("aria-hidden", "true");
      bar.innerHTML = "";
      return;
    }
    let pct;
    if (limit === 0) {
      if (usedN > 0) bar.classList.add("fail");
      pct = usedN > 0 ? 100 : 0;
    } else {
      const ratio = usedN / limit;
      pct = Math.min(100, Math.max(0, ratio * 100));
      if (ratio >= 1) bar.classList.add("fail");
      else if (ratio >= 0.9) bar.classList.add("warn");
    }
    bar.innerHTML = `<span class="util-fill" style="width:${pct}%"></span>`;
    bar.setAttribute("aria-label", label);
  }

  function utilization() {
    return (
      (state.status && state.status.utilization) ||
      (state.risk && state.risk.utilization) ||
      {}
    );
  }

  function spokenPolicy() {
    return (
      (state.risk && state.risk.spoken) ||
      (state.risk && state.risk.account) ||
      {}
    );
  }

  function spokenNameCap() {
    const spoken = spokenPolicy();
    const util = utilization();
    if (Number.isFinite(Number(spoken.max_name_weight))) {
      return Number(spoken.max_name_weight);
    }
    if (Number.isFinite(Number(util.max_name_weight))) {
      return Number(util.max_name_weight);
    }
    return 0.2;
  }

  function renderLiveLimitBanner(flattened) {
    const el = document.getElementById("live-limit-banner");
    if (!el) return;
    const limit = utilization().live_limit;
    if (flattened || !limit || !limit.reason) {
      el.classList.add("hidden");
      el.textContent = "";
      return;
    }
    el.classList.remove("hidden");
    const through =
      limit.kind === "send" ? "next send through " : "live book through ";
    el.textContent =
      "LIMIT: " + through + policyLabel(limit.reason) + " — next rebalance will flatten";
  }

  function renderGrossUtilization(gross) {
    const bar = document.getElementById("metric-gross-bar");
    const util = utilization();
    const spoken = spokenPolicy();
    const limit = finiteNumber(util.max_gross, finiteNumber(spoken.max_gross, 1));
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
    const util = utilization();
    function fillUsedCap(valueId, capId, barId, used, cap, label) {
      const valueEl = document.getElementById(valueId);
      const capEl = document.getElementById(capId);
      const bar = document.getElementById(barId);
      const missing = used == null || used === undefined || cap == null || cap === undefined;
      if (valueEl) {
        valueEl.textContent = used == null || used === undefined ? "—" : String(used);
        const atCap =
          !missing && Number.isFinite(Number(cap)) && Number(used) > Number(cap);
        valueEl.classList.toggle("fail", atCap);
      }
      if (capEl) {
        capEl.textContent =
          cap == null || cap === undefined ? "—" : `of ${cap}`;
      }
      if (!bar) return;
      if (missing) {
        bar.classList.add("hidden");
        bar.setAttribute("aria-hidden", "true");
        return;
      }
      paintUtilTrack(bar, Number(used) || 0, Number(cap), `${label} ${used} of ${cap}`);
    }
    fillUsedCap(
      "risk-head-names",
      "risk-head-names-cap",
      "risk-head-names-bar",
      util.names,
      util.max_names,
      "names"
    );
    fillUsedCap(
      "risk-head-orders",
      "risk-head-orders-cap",
      "risk-head-orders-bar",
      util.orders_today,
      util.max_orders_per_day,
      "orders today"
    );
    const cashEl = document.getElementById("risk-head-cash");
    const cashSub = document.getElementById("risk-head-cash-sub");
    const cashBar = document.getElementById("risk-head-cash-bar");
    const cashW = util.cash_weight;
    const invested = util.invested_weight;
    const target = util.target_cash_weight;
    if (cashEl) {
      cashEl.textContent = cashW == null || cashW === undefined ? "—" : fmtPct(cashW);
    }
    if (cashSub) {
      cashSub.textContent =
        invested == null || invested === undefined ? "—" : `invested ${fmtPct(invested)}`;
    }
    if (cashBar) {
      if (invested == null || invested === undefined) {
        cashBar.classList.add("hidden");
        cashBar.setAttribute("aria-hidden", "true");
      } else {
        const pct = Math.min(100, Math.max(0, Number(invested) * 100));
        let marker = "";
        if (target != null && target !== undefined) {
          const investedTarget = Math.min(100, Math.max(0, (1 - Number(target)) * 100));
          marker = `<span class="wg-wanted" style="left:${investedTarget}%"></span>`;
        }
        cashBar.classList.remove("hidden");
        cashBar.removeAttribute("aria-hidden");
        cashBar.innerHTML = `<span class="cash-invested" style="width:${pct}%"></span>${marker}`;
        cashBar.setAttribute(
          "aria-label",
          `invested ${fmtPct(invested)}` +
            (cashW != null ? ` cash ${fmtPct(cashW)}` : "") +
            (target != null ? ` target cash ${fmtPct(target)}` : "")
        );
      }
    }
    const targetEl = document.getElementById("risk-head-target");
    if (targetEl) {
      targetEl.textContent =
        target == null || target === undefined ? "—" : fmtPct(target);
    }
  }

  function nameCapBar(got, cap) {
    const g = Math.max(0, Number(got) || 0);
    const limit = finiteNumber(cap, 0.2);
    let cls = "util-track";
    let pct;
    if (limit === 0) {
      if (g > 0) cls += " fail";
      pct = g > 0 ? 100 : 0;
    } else {
      const ratio = g / limit;
      pct = Math.min(100, Math.max(0, ratio * 100));
      if (ratio >= 1) cls += " fail";
      else if (ratio >= 0.9) cls += " warn";
    }
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
