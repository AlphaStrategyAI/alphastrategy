  const RISK_TIGHTEN_GROUPS = [
    { legend: "Gross", keys: ["max_gross", "max_name_weight", "max_order_notional_frac"] },
    { legend: "Names", keys: ["max_names"] },
    { legend: "Orders", keys: ["max_orders_per_rebalance", "max_orders_per_day"] },
    { legend: "Deltas", keys: ["min_delta_dollar", "min_delta_frac"] },
  ];

  function renderRiskCaps(container, policy, account) {
    const gross = document.getElementById("risk-cap-gross");
    const name = document.getElementById("risk-cap-name");
    const names = document.getElementById("risk-cap-names");
    const orders = document.getElementById("risk-cap-orders");
    const longEl = document.getElementById("risk-cap-long");
    const orderEl = document.getElementById("risk-cap-order");
    const rebalanceEl = document.getElementById("risk-cap-rebalance");
    if (!policy) {
      if (gross) gross.textContent = "—";
      if (name) name.textContent = "—";
      if (names) names.textContent = "—";
      if (orders) orders.textContent = "—";
      if (longEl) longEl.textContent = "—";
      if (orderEl) orderEl.textContent = "—";
      if (rebalanceEl) rebalanceEl.textContent = "—";
      return;
    }
    if (gross) gross.textContent = fmtPct(policy.max_gross);
    if (name) name.textContent = fmtPct(policy.max_name_weight);
    if (names) {
      names.textContent =
        policy.max_names == null || policy.max_names === undefined
          ? "—"
          : String(policy.max_names);
    }
    if (orders) {
      orders.textContent =
        policy.max_orders_per_day == null || policy.max_orders_per_day === undefined
          ? "—"
          : String(policy.max_orders_per_day);
    }
    if (longEl) {
      const flag = policy.long_only;
      longEl.textContent =
        flag == null || flag === undefined
          ? "—"
          : policyLabel("long_only") + " " + flag;
    }
    if (orderEl) {
      orderEl.textContent =
        policyLabel("max_order_notional_frac") + " " + fmtPct(policy.max_order_notional_frac);
    }
    if (rebalanceEl) {
      rebalanceEl.textContent =
        policy.max_orders_per_rebalance == null ||
        policy.max_orders_per_rebalance === undefined
          ? "—"
          : policyLabel("max_orders_per_rebalance") +
            " " +
            String(policy.max_orders_per_rebalance);
    }
    function markTighter(el, spokenVal, accountVal) {
      if (!el) return;
      el.classList.remove("warn");
      if (accountVal == null || accountVal === undefined) return;
      if (spokenVal == null || spokenVal === undefined) return;
      const spokenNum = Number(spokenVal);
      const accountNum = Number(accountVal);
      if (!Number.isFinite(spokenNum) || !Number.isFinite(accountNum)) return;
      if (spokenNum < accountNum) el.classList.add("warn");
    }
    markTighter(gross, policy.max_gross, account && account.max_gross);
    markTighter(name, policy.max_name_weight, account && account.max_name_weight);
    markTighter(names, policy.max_names, account && account.max_names);
    markTighter(orders, policy.max_orders_per_day, account && account.max_orders_per_day);
    markTighter(
      orderEl,
      policy.max_order_notional_frac,
      account && account.max_order_notional_frac
    );
    markTighter(
      rebalanceEl,
      policy.max_orders_per_rebalance,
      account && account.max_orders_per_rebalance
    );
    const flattened =
      Boolean(state.status && state.status.flattened) ||
      (state.status &&
        (state.status.state === "stopped" || state.status.state === "flattening"));
    function markLimit(el, key) {
      if (!el) return;
      el.classList.remove("fail");
      if (flattened) return;
      const limit = utilization().live_limit;
      if (limit && limit.reason === key) el.classList.add("fail");
    }
    markLimit(gross, "max_gross");
    markLimit(name, "max_name_weight");
    markLimit(names, "max_names");
    markLimit(orders, "max_orders_per_day");
    markLimit(longEl, "long_only");
    markLimit(orderEl, "max_order_notional_frac");
    markLimit(rebalanceEl, "max_orders_per_rebalance");
  }

  function buildRiskInputs(prefix, policy, current) {
    const form = document.createElement("form");
    form.dataset.prefix = prefix;
    const groups = document.createElement("div");
    groups.className = "risk-tighten-groups";
    for (const group of RISK_TIGHTEN_GROUPS) {
      const set = document.createElement("fieldset");
      set.className = "risk-group";
      const legend = document.createElement("legend");
      legend.textContent = group.legend;
      set.appendChild(legend);
      for (const key of group.keys) {
        const label = document.createElement("label");
        label.textContent = policyLabel(key);
        const input = document.createElement("input");
        input.type = "number";
        input.name = key;
        input.step =
          key.includes("frac") || key === "max_gross" || key === "max_name_weight"
            ? "0.01"
            : "1";
        input.placeholder = String(current[key]);
        input.dataset.current = String(current[key]);
        label.appendChild(input);
        set.appendChild(label);
      }
      groups.appendChild(set);
    }
    form.appendChild(groups);
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
          return `${policyLabel(key)} cannot loosen below ${base}`;
        }
      } else if (key === "max_names" || key === "max_orders_per_rebalance" || key === "max_orders_per_day") {
        if (proposed > base) {
          return `${policyLabel(key)} cannot loosen above ${base}`;
        }
      } else {
        if (proposed > base) {
          return `${policyLabel(key)} cannot loosen above ${base}`;
        }
      }
    }
    return null;
  }

  function overlayTighterCount(overlay, account) {
    if (!overlay || !account) return 0;
    let n = 0;
    for (const key of NUMERIC_CAPS) {
      if (overlay[key] === undefined || overlay[key] === null) continue;
      if (account[key] === undefined || account[key] === null) continue;
      const proposed = Number(overlay[key]);
      const base = Number(account[key]);
      if (key === "min_delta_dollar" || key === "min_delta_frac") {
        if (proposed > base) n += 1;
      } else if (proposed < base) {
        n += 1;
      }
    }
    return n;
  }

  function renderTightenGlance(risk) {
    const account = (risk && risk.account) || {};
    const defaults = (risk && risk.defaults) || {};
    const tightEl = document.getElementById("risk-tighten-tight");
    if (tightEl) {
      const n = overlayTighterCount(account, defaults);
      tightEl.textContent = String(n);
      tightEl.classList.toggle("warn", n > 0);
    }
    const dollarEl = document.getElementById("risk-tighten-delta-dollar");
    if (dollarEl) dollarEl.textContent = fmtNum(account.min_delta_dollar, 2);
    const fracEl = document.getElementById("risk-tighten-delta-frac");
    if (fracEl) fracEl.textContent = fmtPct(account.min_delta_frac);
    const fieldsEl = document.getElementById("risk-tighten-fields");
    if (fieldsEl) fieldsEl.textContent = String(NUMERIC_CAPS.length);
  }

  function renderOverlayGlance(risk) {
    const sleeves = (risk && risk.sleeves) || {};
    const account = (risk && risk.account) || {};
    const paper = (state.bundles && state.bundles.paper) || {};
    const ids = Object.keys(sleeves);
    let spoken = 0;
    let tighter = 0;
    let idle = 0;
    for (const id of ids) {
      const alloc = Number(paper[id]) || 0;
      spoken += alloc;
      if (alloc <= 0) idle += 1;
      if (overlayTighterCount(sleeves[id], account) > 0) tighter += 1;
    }
    const spokenEl = document.getElementById("risk-overlay-spoken");
    if (spokenEl) {
      spokenEl.textContent = fmtPct(spoken);
      spokenEl.classList.toggle("warn", spoken >= 0.9 && spoken < 1);
      spokenEl.classList.toggle("fail", spoken >= 1);
    }
    const spokenBar = document.getElementById("risk-overlay-spoken-bar");
    if (spokenBar) {
      paintUtilTrack(spokenBar, spoken, 1, "spoken " + fmtPct(spoken));
    }
    const countEl = document.getElementById("risk-overlay-count");
    if (countEl) countEl.textContent = String(ids.length);
    const tightEl = document.getElementById("risk-overlay-tighter");
    if (tightEl) {
      tightEl.textContent = String(tighter);
      tightEl.classList.toggle("warn", tighter > 0);
    }
    const idleEl = document.getElementById("risk-overlay-idle");
    if (idleEl) idleEl.textContent = String(idle);
  }

  function riskFormIsDirty() {
    if (document.querySelector("#screen-risk details[open]")) return true;
    const forms = document.querySelectorAll("#screen-risk form");
    for (const form of forms) {
      if (form.contains(document.activeElement)) return true;
      const inputs = form.querySelectorAll("input");
      for (const input of inputs) {
        if (input.type === "checkbox") continue;
        if (input.value) return true;
      }
    }
    return false;
  }

  function renderRisk() {
    const risk = state.risk || { account: {}, sleeves: {} };
    const spoken = (risk && risk.spoken) || (risk && risk.account) || {};
    renderRiskCaps(document.getElementById("risk-account-caps"), spoken, risk.account);
    renderRiskUtilization();
    renderTightenGlance(risk);
    renderOverlayGlance(risk);
    if (riskFormIsDirty()) {
      return;
    }

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
      sleevesEl.innerHTML =
        "<p class='muted'>No sleeve overlays. Import a qualified .asb, then tighten a sleeve here.</p>";
      return;
    }
    const account = risk.account || {};
    const contrib = (state.portfolio && state.portfolio.sleeve_contribution) || {};
    const lastContrib = (state.portfolio && state.portfolio.last_sleeve_contribution) || {};
    const bundles = state.bundles || { imported: [], paper: {} };
    for (const id of ids) {
      const panel = document.createElement("div");
      panel.className = "panel";
      const alloc = ((state.bundles && state.bundles.paper) || {})[id] || 0;
      const st = sleeveState(id, bundles, state.status);
      const statusClass =
        st === "paper"
          ? "status-running"
          : st === "halted"
            ? "status-halt"
            : st === "stopped"
              ? "status-stopped"
              : "status-muted";
      const head = document.createElement("div");
      head.className = "sleeve-head";
      const heading = document.createElement("h3");
      heading.textContent = id;
      const badge = document.createElement("span");
      badge.className = "sleeve-state " + statusClass;
      badge.textContent = st;
      head.appendChild(heading);
      head.appendChild(badge);
      panel.appendChild(head);
      const allocRow = document.createElement("div");
      allocRow.innerHTML =
        `<span class="muted nums">Allocation ${fmtPct(alloc)}</span>`;
      panel.appendChild(allocRow);
      const track = document.createElement("div");
      paintUtilTrack(track, alloc, 1, `allocation ${fmtPct(alloc)}`);
      panel.appendChild(track);
      const contribEl = document.createElement("div");
      contribEl.className = "nums";
      contribEl.innerHTML = formatContributionInner(contrib[id], lastContrib[id], id, alloc);
      panel.appendChild(contribEl);
      const tight = overlayTighterCount(risk.sleeves[id], account);
      const tightLine = document.createElement("p");
      tightLine.className = "nums tighter-line";
      if (tight) {
        tightLine.textContent = `${tight} tighter than account`;
        tightLine.classList.add("warn");
      } else {
        tightLine.textContent = "Same as account";
      }
      panel.appendChild(tightLine);
      const form = buildRiskInputs(id, risk.sleeves[id], risk.sleeves[id]);
      form.addEventListener("submit", (ev) => onRiskSleeveSubmit(ev, id));
      const details = document.createElement("details");
      details.className = "risk-sleeve-tighten";
      const summary = document.createElement("summary");
      summary.textContent = "Tighten this sleeve";
      details.appendChild(summary);
      details.appendChild(form);
      panel.appendChild(details);
      sleevesEl.appendChild(panel);
    }
  }

