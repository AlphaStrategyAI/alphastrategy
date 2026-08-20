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

  function formatField(value) {
    if (value == null || value === "") return "—";
    if (typeof value !== "object") return String(value);
    const keys = Object.keys(value);
    if (!keys.length) return "—";
    return keys
      .sort()
      .map((k) => `${k} ${value[k]}`)
      .join(" · ");
  }

  function detailList(rows) {
    const dl = document.createElement("dl");
    dl.className = "activity-fields";
    for (const [label, value] of rows) {
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.className = "nums";
      dd.textContent = formatField(value);
      dl.appendChild(dt);
      dl.appendChild(dd);
    }
    return dl;
  }

  function bookTable(wanted, got) {
    const table = document.createElement("table");
    table.className = "activity-book";
    table.innerHTML = "<thead><tr><th>Symbol</th><th>Wanted</th><th>Got</th></tr></thead>";
    const tbody = document.createElement("tbody");
    const keys = [...new Set([...Object.keys(wanted || {}), ...Object.keys(got || {})])].sort();
    if (!keys.length) {
      tbody.innerHTML = "<tr><td colspan='3' class='muted'>—</td></tr>";
    } else {
      for (const key of keys) {
        const tr = document.createElement("tr");
        tr.innerHTML =
          `<td>${key}</td>` +
          `<td class="nums">${fmtPct(wanted && wanted[key])}</td>` +
          `<td class="nums">${fmtPct(got && got[key])}</td>`;
        tbody.appendChild(tr);
      }
    }
    table.appendChild(tbody);
    return table;
  }

  function eventDetail(ev) {
    const wrap = document.createElement("div");
    wrap.className = "activity-detail";
    const kind = ev.event;
    if (kind === "rebalance") {
      wrap.appendChild(bookTable(ev.wanted, ev.got));
      wrap.appendChild(
        detailList([
          ["Session", ev.session_event],
          ["Orders", ev.orders],
        ])
      );
      return wrap;
    }
    if (kind === "execution_deviation") {
      const asset = ev.asset || "—";
      wrap.appendChild(bookTable({ [asset]: ev.wanted }, { [asset]: ev.got }));
      return wrap;
    }
    if (kind === "order") {
      wrap.appendChild(
        detailList([
          ["Symbol", ev.symbol],
          ["Side", ev.side],
          ["Qty", ev.qty],
        ])
      );
      return wrap;
    }
    if (kind === "halt") {
      wrap.appendChild(detailList([["Reason", ev.reason]]));
      return wrap;
    }
    if (kind === "kill") {
      const outcome = ev.isolated === true ? "isolated residual" : "flattened account";
      wrap.appendChild(
        detailList([
          ["Outcome", outcome],
          ["Bundle", ev.bundle_id],
          ["Scope", ev.scope],
        ])
      );
      return wrap;
    }
    if (kind === "flatten") {
      wrap.appendChild(detailList([["Scope", ev.scope || "account"]]));
      return wrap;
    }
    if (kind === "paper_start" || kind === "paper_stop" || kind === "import") {
      wrap.appendChild(detailList([["Bundle", ev.bundle_id || ev.scope]]));
      return wrap;
    }
    const rows = Object.keys(ev)
      .filter((key) => key !== "ts" && key !== "timestamp" && key !== "event")
      .sort()
      .map((key) => [key, ev[key]]);
    wrap.appendChild(detailList(rows.length ? rows : [["Detail", "—"]]));
    return wrap;
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

  function renderActivity() {
    const list = document.getElementById("activity-list");
    list.innerHTML = "";
    const events = state.activity || [];
    const hb = (state.status && state.status.heartbeat) || {};
    const pulse = hb.pulse || "missing";
    const beatLine = document.getElementById("activity-heartbeat");
    if (beatLine) {
      beatLine.textContent = pulseLabel(pulse);
      beatLine.classList.remove("live", "stale", "dead", "missing");
      beatLine.classList.add(pulse);
    }
    const ageEl = document.getElementById("act-beat-age");
    if (ageEl) {
      const age = hb.age_seconds;
      ageEl.textContent = age == null || age === undefined ? "—" : age + "s";
    }
    const intervalEl = document.getElementById("act-beat-interval");
    if (intervalEl) {
      const interval =
        hb.interval_seconds == null || hb.interval_seconds === undefined
          ? 20
          : hb.interval_seconds;
      intervalEl.textContent = interval + "s";
    }
    const stateEl = document.getElementById("act-beat-state");
    if (stateEl) {
      const raw = (state.status && state.status.state) || "";
      stateEl.textContent = raw ? supervisorLabel(raw) : "—";
      stateEl.title = raw || "";
      stateEl.classList.toggle("halt", raw === "halted");
      stateEl.classList.toggle("fail", raw === "flattening" || raw === "stopped");
    }
    const counts = { rebalance: 0, halt: 0, deviation: 0, kill: 0 };
    for (const ev of events) {
      if (ev.event === "rebalance") counts.rebalance += 1;
      else if (ev.event === "halt") counts.halt += 1;
      else if (ev.event === "execution_deviation") counts.deviation += 1;
      else if (ev.event === "kill" || ev.event === "flatten") counts.kill += 1;
    }
    const setTape = (elId, value, onClass) => {
      const el = document.getElementById(elId);
      if (!el) return;
      el.textContent = String(value);
      if (onClass) el.classList.toggle(onClass, value > 0);
    };
    setTape("act-count-rebalance", counts.rebalance, "status-running");
    setTape("act-count-halt", counts.halt, "status-halt");
    setTape("act-count-deviation", counts.deviation, "status-fail");
    setTape("act-count-kill", counts.kill, "status-fail");
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
      li.appendChild(summary);
      li.appendChild(eventDetail(ev));
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
