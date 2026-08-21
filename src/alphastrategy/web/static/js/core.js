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

  const helpState = { loaded: false, payload: null };

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

  function fmtCountdown(seconds) {
    const s = Math.max(0, Math.floor(Number(seconds) || 0));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    const mm = String(m).padStart(2, "0");
    const ss = String(sec).padStart(2, "0");
    if (h > 0) return `${h}:${mm}:${ss}`;
    return `${mm}:${ss}`;
  }

  function fmtContribution(map) {
    if (!map || typeof map !== "object") return "—";
    const keys = Object.keys(map);
    if (!keys.length) return "—";
    return keys
      .sort()
      .map((asset) => `${asset} ${fmtPct(map[asset])}`)
      .join(" · ");
  }

  function formatContributionCell(nextMap, lastMap) {
    const nextText = fmtContribution(nextMap);
    const lastText = fmtContribution(lastMap);
    const hasLast = lastMap && typeof lastMap === "object" && Object.keys(lastMap).length;
    const differs = Boolean(hasLast && lastText !== nextText);
    const sub = differs
      ? `<div class="metric-sub nums">` + "last " + lastText + `</div>`
      : "";
    return `<td class="nums">${nextText}${sub}</td>`;
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
    if (helpState.payload) {
      renderHelp(helpState.payload);
    }
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

  function setRunError(band, message) {
    const ids = {
      promote: "run-error",
      sleeves: "run-sleeve-error",
      recover: "run-recover-error",
      flatten: "run-flatten-error",
    };
    for (const [key, id] of Object.entries(ids)) {
      const el = document.getElementById(id);
      if (!el) continue;
      setError(el, key === band ? message : "");
    }
  }

  function showImportRejection(body) {
    const box = document.getElementById("import-error");
    const ok = document.getElementById("import-ok");
    if (ok) {
      ok.classList.add("hidden");
      ok.textContent = "";
    }
    if (!box) return;
    box.classList.remove("hidden");
    const kind = document.getElementById("import-error-kind");
    const title = document.getElementById("import-error-title");
    const detail = document.getElementById("import-error-detail");
    const next = document.getElementById("import-error-next");
    if (kind) kind.textContent = (body && body.kind) || "unknown";
    if (title) title.textContent = (body && body.title) || "Import rejected";
    if (detail) detail.textContent = (body && body.error) || "";
    if (next) next.textContent = (body && body.next) || "";
  }

  function showImportOk(bundleId) {
    const box = document.getElementById("import-error");
    if (box) box.classList.add("hidden");
    const ok = document.getElementById("import-ok");
    if (!ok) return;
    ok.classList.remove("hidden");
    ok.textContent = `Imported ${bundleId}. Import is not permission to trade.`;
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
    const stoppedList = (bundles && bundles.stopped) || [];
    const alloc = bundles.paper[bundleId];
    const sleeves = (state.portfolio && state.portfolio.sleeves) || {};
    if (stoppedList.indexOf(bundleId) >= 0) return "stopped";
    if (
      status &&
      status.state === "stopped" &&
      (alloc > 0 || Object.prototype.hasOwnProperty.call(sleeves, bundleId))
    ) {
      return "stopped";
    }
    if (alloc && alloc > 0) {
      if (status && status.halted) return "halted";
      return "paper";
    }
    return "imported";
  }

  function policyLabel(key) {
    const labels = (state.risk && state.risk.labels) || {};
    const spoken = labels[key];
    return spoken || key;
  }

  function riskSummary(policy) {
    if (!policy) return "—";
    return (
      policyLabel("max_gross") +
      " " +
      fmtPct(policy.max_gross) +
      " · " +
      policyLabel("max_name_weight") +
      " " +
      fmtPct(policy.max_name_weight)
    );
  }

  function importedIds() {
    const bundles = state.bundles || { imported: [], paper: {} };
    const paper = bundles.paper || {};
    return [...new Set([...(bundles.imported || []), ...Object.keys(paper)])];
  }

  function hasPaperSleeve() {
    const paper = (state.bundles && state.bundles.paper) || {};
    return Object.keys(paper).some((id) => Number(paper[id]) > 0);
  }

