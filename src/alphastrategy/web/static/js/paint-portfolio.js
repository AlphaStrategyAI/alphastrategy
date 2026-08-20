  function renderFirstRun() {
    const el = document.getElementById("first-run");
    if (!el) return;
    const empty = importedIds().length === 0;
    el.classList.toggle("hidden", !empty);
  }

  function applySessionChip(el) {
    if (!el) return;
    const clock = state.status && state.status.clock;
    const halted = (state.status && state.status.state) === "halted";
    el.classList.remove("open", "warn");
    if (!clock || clock.error) {
      el.textContent = "UNAVAILABLE";
      return;
    }
    if (clock.is_open) {
      el.textContent = "OPEN";
      el.classList.add(halted ? "warn" : "open");
      return;
    }
    el.textContent = "CLOSED";
  }

  function renderSessionMetrics() {
    const sessionEl = document.getElementById("metric-session");
    const countEl = document.getElementById("metric-countdown");
    const kindEl = document.getElementById("metric-countdown-kind");
    const nowEl = document.getElementById("metric-clock-now");
    const nowSub = document.getElementById("metric-clock-now-sub");
    const lastEl = document.getElementById("metric-last-rebalance");
    const lastSub = document.getElementById("metric-last-rebalance-sub");
    const clock = state.status && state.status.clock;
    const countdown = state.status && state.status.countdown;
    applySessionChip(sessionEl);
    if (countEl) countEl.classList.remove("warn", "fail");
    function dashNowLast() {
      if (nowEl) nowEl.textContent = "—";
      if (nowSub) nowSub.textContent = "—";
      if (lastEl) {
        lastEl.textContent = "—";
        lastEl.classList.remove("warn");
      }
      if (lastSub) lastSub.textContent = "—";
    }
    if (!clock || clock.error) {
      countEl.textContent = "—";
      kindEl.textContent = "—";
      dashNowLast();
      return;
    }
    if (countdown) {
      countEl.textContent = fmtCountdown(countdown.seconds);
      const kind = countdown.next_rebalance || "—";
      const halted =
        (state.status && state.status.state) === "halted" ||
        Boolean(state.status && state.status.halted);
      const flattened =
        Boolean(state.status && state.status.flattened) ||
        (state.status &&
          (state.status.state === "stopped" || state.status.state === "flattening"));
      if (halted) {
        countEl.classList.add("warn");
        kindEl.textContent = "held · " + kind;
      } else if (flattened) {
        countEl.classList.add("fail");
        kindEl.textContent = "flat · " + kind;
      } else if (
        utilization().live_limit &&
        utilization().live_limit.reason
      ) {
        countEl.classList.add("warn");
        kindEl.textContent = "flatten · " + kind;
      } else {
        kindEl.textContent = kind;
      }
    } else {
      countEl.textContent = "—";
      kindEl.textContent = "—";
    }
    const raw = clock.timestamp || clock.now || "";
    if (!raw) {
      if (nowEl) nowEl.textContent = "—";
      if (nowSub) nowSub.textContent = "—";
    } else {
      const s = String(raw);
      const m = s.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}(?::\d{2})?)/);
      if (m) {
        if (nowEl) nowEl.textContent = m[2];
        if (nowSub) nowSub.textContent = m[1];
      } else {
        if (nowEl) nowEl.textContent = s;
        if (nowSub) nowSub.textContent = "—";
      }
    }
    const last = state.status && state.status.last_rebalance_event;
    const complete = state.status && state.status.last_rebalance_complete;
    if (lastEl) lastEl.classList.remove("warn");
    if (!last) {
      if (lastEl) lastEl.textContent = "—";
      if (lastSub) lastSub.textContent = "—";
    } else {
      const parts = String(last).split(":");
      const kind = parts.length > 1 ? parts.slice(1).join(":") : String(last);
      const date = parts.length > 1 ? parts[0] : "—";
      if (complete === false) {
        if (lastEl) {
          lastEl.textContent = "spent";
          lastEl.classList.add("warn");
        }
        if (lastSub) lastSub.textContent = kind;
      } else {
        if (lastEl) lastEl.textContent = kind;
        if (lastSub) lastSub.textContent = date;
      }
    }
  }

  function bookDrift(positions, equity) {
    const rows = positions || [];
    const cap = Number(equity);
    let off = 0;
    let maxGap = 0;
    if (!rows.length || !(cap > 0)) {
      return { off: 0, maxGap: 0 };
    }
    const minDelta = Math.max(1, 0.001 * cap);
    for (const pos of rows) {
      if (pos.wanted == null || pos.wanted === undefined) continue;
      const got = Number(pos.weight) || 0;
      const wanted = Number(pos.wanted) || 0;
      const fill =
        pos.fill == null || pos.fill === undefined ? got : Number(pos.fill) || 0;
      const gap = Math.abs(wanted - fill);
      if (gap * cap >= minDelta) {
        off += 1;
        if (gap > maxGap) maxGap = gap;
      }
    }
    return { off, maxGap };
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
    const drift = bookDrift(positions, equity);
    const off = drift.off;
    const maxGap = drift.maxGap;
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
    const lastKill = state.status && state.status.last_kill;
    const killReason = lastKill && lastKill.reason;

    if (halted || reason) {
      haltEl.classList.remove("hidden");
      haltEl.textContent = `HALT: ${reason || state.status.state || "halted"}`;
    } else {
      haltEl.classList.add("hidden");
    }

    if (flattened) {
      flattenEl.classList.remove("hidden");
      const capFlat =
        killReason === "long_only" ||
        (killReason && NUMERIC_CAPS.indexOf(killReason) !== -1);
      flattenEl.textContent =
        killReason === "flatten_interrupted"
          ? "FLAT: interrupted flattening — paper account flattened"
          : capFlat
            ? "FLAT: " + policyLabel(killReason) + " — paper account flattened"
          : killReason === "limit"
            ? "FLAT: limit breach — paper account flattened"
            : "FLAT: paper account flattened";
    } else {
      flattenEl.classList.add("hidden");
    }

    renderLiveLimitBanner(flattened);

    if (state.deviationActive) {
      devEl.classList.remove("hidden");
      devEl.textContent = "DEVIATION: execution drift exceeds tolerance";
    } else {
      devEl.classList.add("hidden");
    }

    const killEl = document.getElementById("kill-outcome-banner");
    if (killReason === "isolated") {
      killEl.className = "banner halt";
      killEl.textContent =
        "SLEEVE KILL: isolated residual for " +
        (lastKill.bundle_id || "sleeve") +
        " — other sleeves still live";
    } else if (killReason === "fallback_interrupted") {
      killEl.className = "banner fail";
      killEl.textContent =
        "SLEEVE KILL: interrupted sleeve isolate — whole paper account flattened";
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
    renderPositionsGlance(positions);
    if (!positions.length) {
      let empty = "No positions yet. Import a .asb to begin.";
      if (importedIds().length) {
        empty = hasPaperSleeve()
          ? state.status && state.status.last_rebalance_complete === false
            ? "No positions yet. Clock Last is spent. Resume does not catch up."
            : "No positions yet. The next legal open or close rebalance will trade."
          : "Imported bundles are not trading. Start paper on Run.";
      }
      posBody.innerHTML = `<tr><td colspan='7' class='muted'>${empty}</td></tr>`;
    } else {
      const cap = spokenNameCap();
      for (const pos of positions) {
        const tr = document.createElement("tr");
        const notional = pos.notional == null ? "—" : fmtNum(pos.notional, 2);
        const wanted = pos.wanted == null ? "—" : fmtPct(pos.wanted);
        const got = pos.weight == null ? "—" : fmtPct(pos.weight);
        tr.innerHTML =
          `<td>${pos.symbol || "—"}</td><td class="nums">${fmtNum(pos.qty, 4)}</td>` +
          `<td class="nums">${notional}</td><td class="nums">${wanted}</td>` +
          `<td class="nums">${got}</td><td>${wantedGotBar(pos.wanted, pos.weight, cap, pos.fill)}</td>` +
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

  function supervisorLabel(raw) {
    const map = {
      idle_in_session: "IN SESSION",
      idle_out_of_session: "OUT OF SESSION",
      rebalancing: "REBALANCING",
      halted: "HALTED",
      flattening: "FLATTENING",
      stopped: "STOPPED",
      starting: "STARTING",
    };
    if (raw == null || raw === "" || raw === "—") return "—";
    if (map[raw]) return map[raw];
    return String(raw).replace(/_/g, " ").toUpperCase();
  }

  function renderPositionsGlance(positions) {
    const rowsEl = document.getElementById("pos-count-rows");
    const wantedEl = document.getElementById("pos-count-wanted");
    const gotEl = document.getElementById("pos-count-got");
    const capEl = document.getElementById("pos-count-cap");
    const rows = positions || [];
    const cap = spokenNameCap();
    let wantedN = 0;
    let gotN = 0;
    let atCap = 0;
    for (const pos of rows) {
      if (pos.wanted != null && pos.wanted !== undefined && Number(pos.wanted) > 0) {
        wantedN += 1;
      }
      if (Number(pos.qty) !== 0) gotN += 1;
      if (Number.isFinite(cap) && Math.abs(Number(pos.weight) || 0) > cap) atCap += 1;
    }
    if (rowsEl) rowsEl.textContent = String(rows.length);
    if (wantedEl) wantedEl.textContent = String(wantedN);
    if (gotEl) gotEl.textContent = String(gotN);
    if (capEl) {
      capEl.textContent = String(atCap);
      capEl.classList.toggle("fail", atCap > 0);
    }
  }

  function renderDeskPulse() {
    const wrap = document.getElementById("desk-pulse");
    const label = document.getElementById("desk-pulse-label");
    if (wrap && label) {
      const hb = (state.status && state.status.heartbeat) || {};
      const pulse = hb.pulse || "missing";
      wrap.className = "desk-pulse " + pulse;
      label.textContent = pulseLabel(pulse);
      const age = hb.age_seconds;
      const ageText = age == null || age === undefined ? "no stamp" : age + "s ago";
      wrap.title = "Supervisor beat " + pulseLabel(pulse) + " · " + ageText;
    }
    const sessionEl = document.getElementById("desk-session");
    if (sessionEl) {
      sessionEl.title = "RTH session";
      applySessionChip(sessionEl);
    }
    const stateEl = document.getElementById("desk-supervisor");
    if (stateEl) {
      const raw = (state.status && state.status.state) || "";
      stateEl.textContent = raw ? supervisorLabel(raw) : "—";
      stateEl.title = raw || "";
      stateEl.classList.toggle("halt", raw === "halted");
      stateEl.classList.toggle("fail", raw === "flattening" || raw === "stopped");
    }
  }
