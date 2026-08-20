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

