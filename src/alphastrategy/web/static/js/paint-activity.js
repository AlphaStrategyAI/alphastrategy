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

