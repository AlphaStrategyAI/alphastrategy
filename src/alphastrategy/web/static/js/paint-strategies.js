  function renderStrategies() {
    const bundles = state.bundles || { imported: [], paper: {} };
    const risk = state.risk || { sleeves: {} };
    const tbody = document.querySelector("#strategies-table tbody");
    tbody.innerHTML = "";

    const ids = [...new Set([...bundles.imported, ...Object.keys(bundles.paper)])].sort();
    const counts = { imported: 0, paper: 0, halted: 0, stopped: 0 };
    for (const id of ids) {
      counts[sleeveState(id, bundles, state.status)] += 1;
    }
    const setCount = (elId, value, onClass) => {
      const el = document.getElementById(elId);
      if (!el) return;
      el.textContent = String(value);
      if (onClass) el.classList.toggle(onClass, value > 0);
    };
    setCount("strat-count-imported", counts.imported);
    setCount("strat-count-paper", counts.paper, "status-running");
    setCount("strat-count-halted", counts.halted, "status-halt");
    setCount("strat-count-stopped", counts.stopped, "status-stopped");

    if (!ids.length) {
      tbody.innerHTML = "<tr><td colspan='4' class='muted'>No bundles imported</td></tr>";
    } else {
      for (const id of ids) {
        const st = sleeveState(id, bundles, state.status);
        const alloc = bundles.paper[id] || 0;
        const policy = risk.sleeves[id];
        const statusClass =
          st === "paper" ? "running" : st === "halted" ? "halt" : st === "stopped" ? "stopped" : "muted";
        const importedAt = (bundles.imported_at || {})[id];
        const when = importedAt ? String(importedAt).slice(0, 10) : "—";
        const tr = document.createElement("tr");
        tr.innerHTML = `
        <td>${id}<div class="metric-sub nums">${when}</div></td>
        <td class="status-${statusClass}">${st}</td>
        <td class="nums">${fmtPct(alloc)}<div class="util-track" data-alloc-rail></div>${formatWeightsWaitSub(id, alloc)}</td>
        <td class="muted">${riskSummary(policy)}</td>
      `;
        tbody.appendChild(tr);
        const track = tr.querySelector("[data-alloc-rail]");
        paintUtilTrack(track, alloc, 1, "allocation " + fmtPct(alloc));
      }
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
