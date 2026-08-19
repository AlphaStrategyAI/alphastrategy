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
    const alloc = bundles.paper[bundleId];
    if (alloc && alloc > 0) {
      if (status && status.halted) return "halted";
      return "paper";
    }
    return "imported";
  }

  function riskSummary(policy) {
    if (!policy) return "—";
    return `gross ${fmtPct(policy.max_gross)} · name ${fmtPct(policy.max_name_weight)}`;
  }

  function renderBanners() {
    const haltEl = document.getElementById("halt-banner");
    const devEl = document.getElementById("deviation-banner");
    const halted = state.status && state.status.halted;
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

    if (state.deviationActive) {
      devEl.classList.remove("hidden");
      devEl.textContent = "DEVIATION: execution drift exceeds tolerance";
    } else {
      devEl.classList.add("hidden");
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

    document.getElementById("metric-gross").textContent = fmtPct(grossExposure(portfolio));

    const clock = state.status && state.status.clock;
    const clockLine = document.getElementById("clock-line");
    if (clock && !clock.error) {
      const open = clock.is_open ? "OPEN" : "CLOSED";
      const next = clock.is_open ? clock.next_close : clock.next_open;
      clockLine.textContent = `Market ${open} · next event ${next || "—"} · now ${clock.timestamp || "—"}`;
    } else {
      clockLine.textContent = "Clock unavailable";
    }

    const posBody = document.querySelector("#positions-table tbody");
    posBody.innerHTML = "";
    const positions = portfolio.positions || [];
    if (!positions.length) {
      posBody.innerHTML = "<tr><td colspan='2' class='muted'>No positions</td></tr>";
    } else {
      for (const pos of positions) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${pos.symbol || "—"}</td><td class="nums">${fmtNum(pos.qty, 4)}</td>`;
        posBody.appendChild(tr);
      }
    }

    const sleeveBody = document.querySelector("#sleeves-table tbody");
    sleeveBody.innerHTML = "";
    const sleeves = portfolio.sleeves || {};
    const ids = Object.keys(sleeves).sort();
    if (!ids.length) {
      sleeveBody.innerHTML = "<tr><td colspan='2' class='muted'>No sleeves</td></tr>";
    } else {
      for (const id of ids) {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${id}</td><td class="nums">${fmtPct(sleeves[id])}</td>`;
        sleeveBody.appendChild(tr);
      }
    }

    renderBanners();
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
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${id}</td>
        <td class="status-${st === "paper" ? "running" : st === "halted" ? "halt" : "muted"}">${st}</td>
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
        <p class="muted nums">Allocation ${fmtPct(alloc)}</p>
        <div class="inline">
          <button type="button" class="action warn" data-stop="${id}">Stop</button>
          <button type="button" class="action danger" data-kill="${id}">Kill sleeve</button>
        </div>
      `;
      container.appendChild(card);
    }

    container.querySelectorAll("[data-stop]").forEach((btn) => {
      btn.addEventListener("click", () => stopSleeve(btn.dataset.stop));
    });
    container.querySelectorAll("[data-kill]").forEach((btn) => {
      btn.addEventListener("click", () => killSleeve(btn.dataset.kill));
    });
  }

  function renderActivity() {
    const list = document.getElementById("activity-list");
    list.innerHTML = "";
    const events = state.activity || [];
    if (!events.length) {
      list.innerHTML = "<li class='muted'>No events</li>";
      return;
    }
    for (const ev of events.slice().reverse()) {
      const li = document.createElement("li");
      const ts = ev.ts || ev.timestamp || "";
      const payload = { ...ev };
      delete payload.ts;
      delete payload.timestamp;
      li.textContent = `${ts} ${ev.event || "event"} ${JSON.stringify(payload)}`;
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
      row.innerHTML = `<span class="muted">${key}</span> <span class="nums">${val}</span>`;
      container.appendChild(row);
    }
    const longRow = document.createElement("div");
    longRow.innerHTML = `<span class="muted">long_only</span> <span class="nums">${policy.long_only}</span>`;
    container.appendChild(longRow);
  }

  function buildRiskInputs(prefix, policy, current) {
    const form = document.createElement("form");
    form.className = "inline";
    form.dataset.prefix = prefix;

    for (const key of NUMERIC_CAPS) {
      const label = document.createElement("label");
      label.textContent = key;
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
          return `${key} cannot loosen below ${base}`;
        }
      } else if (key === "max_names" || key === "max_orders_per_rebalance" || key === "max_orders_per_day") {
        if (proposed > base) {
          return `${key} cannot loosen above ${base}`;
        }
      } else {
        if (proposed > base) {
          return `${key} cannot loosen above ${base}`;
        }
      }
    }
    return null;
  }

  function renderRisk() {
    const risk = state.risk || { account: {}, sleeves: {} };
    renderRiskCaps(document.getElementById("risk-account-caps"), risk.account);

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
      panel.innerHTML = `<h2>${id}</h2>`;
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
      renderPortfolio();
      renderStrategies();
      renderRunSleeves();
      renderActivity();
      renderRisk();
    } catch (err) {
      console.error(err);
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
    const errEl = document.getElementById("import-error");
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
        throw new Error(payload.error || `HTTP ${response.status}`);
      }
      setError(errEl, "");
      fileInput.value = "";
      await refresh();
    } catch (err) {
      setError(errEl, err.message);
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

  document.getElementById("import-form").addEventListener("submit", onImportSubmit);
  document.getElementById("start-form").addEventListener("submit", onStartSubmit);

  document.getElementById("account-kill").addEventListener("click", async () => {
    const errEl = document.getElementById("run-error");
    try {
      await api("POST", "/api/paper/kill", {});
      setError(errEl, "");
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

  refresh();
  setInterval(refresh, 5000);
})();
