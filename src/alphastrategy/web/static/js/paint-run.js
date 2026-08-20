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
      card.innerHTML = `
        <h3>${id}</h3>
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
          await api("POST", "/api/paper/start", { bundle_id: bundleId, allocation });
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

