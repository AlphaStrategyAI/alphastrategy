  function renderFirstRun() {
    const el = document.getElementById("first-run");
    if (!el) return;
    const empty = importedIds().length === 0;
    el.classList.toggle("hidden", !empty);
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

  function renderBookDrift(positions, equity) {
    const el = document.getElementById("metric-drift");
    const sub = document.getElementById("metric-drift-sub");
    const bar = document.getElementById("metric-drift-bar");
    if (!el || !sub || !bar) return;
    const rows = positions || [];
    const cap = Number(equity);
    if (!rows.length || !(cap > 0)) {
      el.textContent = "—";
      el.classList.remove("fail");
      sub.textContent = "—";
      bar.classList.add("hidden");
      bar.setAttribute("aria-hidden", "true");
      bar.innerHTML = "";
      return;
    }
    const minDelta = Math.max(1, 0.001 * cap);
    let off = 0;
    let maxGap = 0;
    for (const pos of rows) {
      if (pos.wanted == null || pos.wanted === undefined) continue;
      const got = Number(pos.weight) || 0;
      const wanted = Number(pos.wanted) || 0;
      const gap = Math.abs(wanted - got);
      if (gap * cap >= minDelta) {
        off += 1;
        if (gap > maxGap) maxGap = gap;
      }
    }
    el.textContent = String(off);
    el.classList.toggle("fail", off > 0);
    sub.textContent = off ? `max ${fmtPct(maxGap)}` : "—";
    paintUtilTrack(
      bar,
      off,
      Math.max(rows.length, 1),
      `drift ${off} of ${rows.length}`
    );
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
    renderBookDrift(positions, equity);
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
