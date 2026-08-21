  function runFormIsDirty() {
    const container = document.getElementById("run-sleeves");
    if (!container) return false;
    if (container.contains(document.activeElement)) return true;
    const inputs = container.querySelectorAll("input");
    for (const input of inputs) {
      if (input.type === "checkbox") {
        if (input.checked) return true;
        continue;
      }
      if (input.name === "allocation" && input.value !== input.dataset.current) {
        return true;
      }
    }
    return false;
  }

  function renderRunSleeves() {
    const bundles = state.bundles || { imported: [], paper: {} };
    const container = document.getElementById("run-sleeves");
    container.innerHTML = "";

    const ids = [...new Set([...bundles.imported, ...Object.keys(bundles.paper)])].sort();
    let spoken = 0;
    let live = 0;
    let idle = 0;
    for (const id of ids) {
      const alloc = Number(bundles.paper[id]) || 0;
      spoken += alloc;
      if (alloc > 0) live += 1;
      else idle += 1;
    }
    const remaining = Math.max(0, 1 - spoken);
    const remEl = document.getElementById("run-remaining");
    if (remEl) {
      remEl.textContent = fmtPct(remaining);
      remEl.classList.toggle("warn", spoken >= 0.9 && spoken < 1);
      remEl.classList.toggle("fail", spoken >= 1);
    }
    const spokenEl = document.getElementById("run-spoken");
    if (spokenEl) spokenEl.textContent = fmtPct(spoken);
    const liveEl = document.getElementById("run-count-active");
    if (liveEl) liveEl.textContent = String(live);
    const idleEl = document.getElementById("run-count-idle");
    if (idleEl) idleEl.textContent = String(idle);
    if (!ids.length) {
      container.innerHTML = "<p class='muted'>No sleeves yet. Import a qualified .asb, then start paper.</p>";
      return;
    }
    for (const id of ids) {
      const card = document.createElement("div");
      card.className = "sleeve-card panel";
      const alloc = bundles.paper[id] || 0;
      const st = sleeveState(id, bundles, state.status);
      const statusClass =
        st === "paper"
          ? "status-running"
          : st === "halted"
            ? "status-halt"
            : st === "stopped"
              ? "status-stopped"
              : "status-muted";
      card.innerHTML = `
        <div class="sleeve-head">
          <h3>${id}</h3>
          <span class="sleeve-state ${statusClass}">${st}</span>
        </div>
        <div class="util-track" data-alloc-rail></div>
        <form class="inline sleeve-alloc-form" data-bundle="${id}">
          <label>
            Allocation
            <input type="number" min="0" max="1" step="0.01" name="allocation" value="${alloc}" data-current="${alloc}" required>
          </label>
          <label class="confirm-row">
            <input type="checkbox" name="confirm">
            Confirm paper allocation
          </label>
          <button type="submit" class="action primary">Set allocation</button>
        </form>
        <div class="inline">
          <button type="button" class="action warn" data-stop="${id}">Stop</button>
          <label class="confirm-row">
            <input type="checkbox" data-kill-confirm="${id}">
            Confirm sleeve kill
          </label>
          <button type="button" class="action danger" data-kill="${id}">Kill sleeve</button>
        </div>
      `;
      const track = card.querySelector("[data-alloc-rail]");
      paintUtilTrack(track, alloc, 1, "allocation " + fmtPct(alloc));
      container.appendChild(card);
    }

    container.querySelectorAll(".sleeve-alloc-form").forEach((form) => {
      form.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const bundleId = form.dataset.bundle;
        const allocation = Number(form.querySelector('[name="allocation"]').value);
        const confirmed = form.querySelector('[name="confirm"]').checked;
        if (!confirmed) {
          setRunError("sleeves", "Confirm paper allocation required");
          return;
        }
        try {
          const started = await api("POST", "/api/paper/start", {
            bundle_id: bundleId,
            allocation,
          });
          void (started && started.flattened);
          void (started && started.held);
          setRunError("sleeves", "");
          const allocInput = form.querySelector('[name="allocation"]');
          form.querySelector('[name="confirm"]').checked = false;
          allocInput.dataset.current = allocInput.value;
          await refresh();
        } catch (err) {
          setRunError("sleeves", err.message);
        }
      });
    });

    container.querySelectorAll("[data-stop]").forEach((btn) => {
      btn.addEventListener("click", () => stopSleeve(btn.dataset.stop));
    });
    container.querySelectorAll("[data-kill]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const bundleId = btn.dataset.kill;
        const box = container.querySelector(`[data-kill-confirm="${bundleId}"]`);
        if (!box || !box.checked) {
          setRunError("sleeves", "Confirm sleeve kill");
          return;
        }
        box.checked = false;
        killSleeve(bundleId);
      });
    });
  }

  function renderRunStartHint() {
    const el = document.getElementById("run-start-hint");
    if (!el) return;
    const halted =
      (state.status && state.status.state === "halted") ||
      Boolean(state.status && state.status.halted);
    const flattened =
      Boolean(state.status && state.status.flattened) ||
      (state.status &&
        (state.status.state === "flattening" || state.status.state === "stopped"));
    if (halted) {
      el.className = "warn";
      const reason =
        (state.status && state.status.halt_reason) ||
        (state.portfolio && state.portfolio.halt_reason) ||
        "";
      el.textContent = /start paper seeds last sleeve weights/i.test(String(reason))
        ? "Start paper that cannot seed last weights holds. Resume does not catch up."
        : "Start paper while halted waits for resume. Resume does not catch up.";
      return;
    }
    if (flattened) {
      el.className = "fail";
      const kill = state.status && state.status.last_kill;
      const killReason = kill && kill.reason;
      const capFlat =
        killReason === "long_only" ||
        (killReason && NUMERIC_CAPS.indexOf(killReason) !== -1);
      const restart =
        "Start paper after flatten starts the session loop again and does not catch up.";
      el.textContent = capFlat
        ? policyLabel(killReason) + " flattened the paper account. " + restart
        : restart;
      return;
    }
    el.className = "muted";
    el.textContent =
      "Start paper is a second explicit action. Import is not permission to trade.";
  }

  function renderRunStopHint() {
    const el = document.getElementById("run-stop-hint");
    if (!el) return;
    el.className = "muted";
    el.textContent =
      "Stop zeros that sleeve on the next legal rebalance and does not flatten now.";
  }

  function renderRunRecover() {
    const el = document.getElementById("run-halt-reason");
    if (!el) return;
    const halted = state.status && state.status.halted;
    const reason =
      (state.portfolio && state.portfolio.halt_reason) ||
      (state.status && state.status.halt_reason) ||
      "";
    if (halted || reason) {
      el.className = "warn";
      el.textContent = /start paper seeds last sleeve weights/i.test(String(reason))
        ? "Start paper that cannot seed last weights holds. Resume does not catch up."
        : reason || (state.status && state.status.state) || "halted";
      return;
    }
    el.className = "muted";
    el.textContent = "Resume is only after halt.";
  }

