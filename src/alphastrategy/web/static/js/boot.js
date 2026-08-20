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
    try {
      await api("POST", "/api/paper/stop", { bundle_id: bundleId });
      setRunError("sleeves", "");
      await refresh();
    } catch (err) {
      setRunError("sleeves", err.message);
    }
  }

  async function killSleeve(bundleId) {
    try {
      await api("POST", "/api/paper/kill", { bundle_id: bundleId });
      setRunError("sleeves", "");
      await refresh();
    } catch (err) {
      setRunError("sleeves", err.message);
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
    const bundleId = document.getElementById("start-bundle").value;
    const allocation = Number(document.getElementById("start-allocation").value);
    const confirmed = document.getElementById("start-confirm").checked;
    if (!confirmed) {
      setRunError("promote", "Confirm paper start required");
      return;
    }
    try {
      await api("POST", "/api/paper/start", { bundle_id: bundleId, allocation });
      setRunError("promote", "");
      document.getElementById("start-confirm").checked = false;
      await refresh();
    } catch (err) {
      setRunError("promote", err.message);
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
    const confirmed = document.getElementById("account-kill-confirm").checked;
    const phrase = document.getElementById("account-kill-phrase").value;
    if (!confirmed || phrase !== "FLATTEN") {
      setRunError("flatten", "Type FLATTEN and confirm to flatten the whole paper account");
      return;
    }
    try {
      await api("POST", "/api/paper/kill", {});
      setRunError("flatten", "");
      document.getElementById("account-kill-confirm").checked = false;
      document.getElementById("account-kill-phrase").value = "";
      await refresh();
    } catch (err) {
      setRunError("flatten", err.message);
    }
  });

  document.getElementById("account-resume").addEventListener("click", async () => {
    try {
      await api("POST", "/api/paper/resume", {});
      setRunError("recover", "");
      await refresh();
    } catch (err) {
      setRunError("recover", err.message);
    }
  });

  function activeScreen() {
    const btn = document.querySelector("#nav button.active");
    return (btn && btn.dataset.screen) || "portfolio";
  }

  function renderHelp(payload) {
    helpState.payload = payload || helpState.payload;
    const howtoRoot = document.getElementById("help-howto");
    const body = document.getElementById("help-body");
    if (!howtoRoot || !body || !helpState.payload) return;
    const screen = activeScreen();
    const howtos = helpState.payload.howtos || [];
    const howto = howtos.find((item) => item.screen === screen) || howtos[0] || {};
    howtoRoot.innerHTML = "";
    const h = document.createElement("h3");
    h.textContent = howto.title || "";
    const p = document.createElement("p");
    p.textContent = howto.body || "";
    howtoRoot.appendChild(h);
    howtoRoot.appendChild(p);
    const taskRoot = document.getElementById("help-tasks");
    if (taskRoot) {
      taskRoot.innerHTML = "";
      const tasks = helpState.payload.tasks || [];
      for (const item of tasks) {
        const screens = item.screens || [];
        if (screens.indexOf(screen) < 0) continue;
        const th = document.createElement("h3");
        th.textContent = item.title || "";
        const tp = document.createElement("p");
        tp.textContent = item.body || "";
        taskRoot.appendChild(th);
        taskRoot.appendChild(tp);
      }
    }
    body.innerHTML = "";
    const title = document.createElement("p");
    title.className = "muted";
    title.textContent = helpState.payload.title || "Operator help";
    body.appendChild(title);
    for (const section of helpState.payload.sections || []) {
      const sh = document.createElement("h3");
      sh.textContent = section.title || "";
      const sp = document.createElement("p");
      sp.textContent = section.body || "";
      body.appendChild(sh);
      body.appendChild(sp);
    }
  }

  async function loadHelp() {
    const howtoRoot = document.getElementById("help-howto");
    try {
      const payload = await api("GET", "/api/help");
      renderHelp(payload);
      helpState.loaded = true;
    } catch (err) {
      if (howtoRoot) {
        howtoRoot.textContent = `Help unavailable — ${err.message}`;
      }
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
