  const RISK_TIGHTEN_GROUPS = [
    { legend: "Gross", keys: ["max_gross", "max_name_weight", "max_order_notional_frac"] },
    { legend: "Names", keys: ["max_names"] },
    { legend: "Orders", keys: ["max_orders_per_rebalance", "max_orders_per_day"] },
    { legend: "Deltas", keys: ["min_delta_dollar", "min_delta_frac"] },
  ];

  function renderRiskCaps(container, policy) {
    container.innerHTML = "";
    if (!policy) {
      container.textContent = "—";
      return;
    }
    for (const key of NUMERIC_CAPS) {
      const row = document.createElement("div");
      const val = policy[key];
      row.innerHTML = `<span class="muted">${policyLabel(key)}</span> <span class="nums">${val}</span>`;
      container.appendChild(row);
    }
    const longRow = document.createElement("div");
    longRow.innerHTML = `<span class="muted">${policyLabel("long_only")}</span> <span class="nums">${policy.long_only}</span>`;
    container.appendChild(longRow);
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

  function riskFormIsDirty() {
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
    renderRiskCaps(document.getElementById("risk-account-caps"), risk.account);
    renderRiskUtilization();
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
      sleevesEl.innerHTML = "<p class='muted'>No sleeve overlays</p>";
      return;
    }
    for (const id of ids) {
      const panel = document.createElement("div");
      panel.className = "panel";
      const alloc = ((state.bundles && state.bundles.paper) || {})[id] || 0;
      panel.innerHTML = `<h2>${id}</h2><p class="muted nums">Allocation ${fmtPct(alloc)}</p>`;
      const form = buildRiskInputs(id, risk.sleeves[id], risk.sleeves[id]);
      form.addEventListener("submit", (ev) => onRiskSleeveSubmit(ev, id));
      panel.appendChild(form);
      sleevesEl.appendChild(panel);
    }
  }

