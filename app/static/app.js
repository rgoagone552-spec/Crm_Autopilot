let jwtToken = null;
let currentPreviewId = null;
let currentSessionId = "session_" + Math.random().toString(36).substring(2, 9);

// Initialize app
document.addEventListener("DOMContentLoaded", async () => {
  await fetchDemoToken();
  await checkHealth();
  await refreshMonitor();
  setupEventListeners();
});

// Toast notification helper
function showToast(message, type = "info") {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = "toast";
  if (type === "success") toast.style.borderColor = "var(--success)";
  else if (type === "error") toast.style.borderColor = "var(--danger)";
  else toast.style.borderColor = "var(--primary)";

  toast.classList.remove("hidden");
  setTimeout(() => {
    toast.classList.add("hidden");
  }, 3500);
}

// Fetch Demo JWT Token
async function fetchDemoToken() {
  try {
    const res = await fetch("/auth/demo-token");
    if (res.ok) {
      const data = await res.json();
      jwtToken = data.access_token;
      document.getElementById("userName").textContent = "Sales Ops Director (Demo)";
    }
  } catch (err) {
    console.error("Failed to fetch demo token:", err);
  }
}

// Check Backend Health
async function checkHealth() {
  const statusEl = document.getElementById("statusText");
  const dotEl = document.querySelector(".status-dot");
  try {
    const res = await fetch("/health");
    if (res.ok) {
      statusEl.textContent = "AI Agent Online";
      dotEl.style.backgroundColor = "var(--success)";
    } else {
      statusEl.textContent = "Backend Error";
      dotEl.style.backgroundColor = "var(--danger)";
    }
  } catch (err) {
    statusEl.textContent = "Offline";
    dotEl.style.backgroundColor = "var(--danger)";
  }
}

// Event Listeners
function setupEventListeners() {
  // Preset chips
  document.querySelectorAll(".chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.getElementById("promptInput").value = btn.getAttribute("data-prompt");
    });
  });

  // Seed Button
  document.getElementById("seedBtn").addEventListener("click", async () => {
    try {
      showToast("🌱 Seeding CRM test records...", "info");
      const res = await fetch("/autopilot/seed", {
        method: "POST",
        headers: { Authorization: `Bearer ${jwtToken}` },
      });
      if (res.ok) {
        showToast("✅ Database successfully seeded!", "success");
        await refreshMonitor();
      } else {
        showToast("Failed to seed database.", "error");
      }
    } catch (err) {
      showToast("Network error while seeding.", "error");
    }
  });

  // Monitor Scan Now Button
  document.getElementById("scanNowBtn").addEventListener("click", async () => {
    const btn = document.getElementById("scanNowBtn");
    btn.disabled = true;
    btn.textContent = "Scanning...";
    try {
      const res = await fetch("/autopilot/monitor/scan-now", {
        method: "POST",
        headers: { Authorization: `Bearer ${jwtToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        updateMonitorUI(data.briefing);
        showToast("🛰️ Autonomous pipeline scan completed!", "success");
      }
    } catch (err) {
      showToast("Failed to scan pipeline.", "error");
    } finally {
      btn.disabled = false;
      btn.textContent = "⚡ Scan Pipeline Now";
    }
  });

  // Connector Ping: Salesforce
  document.getElementById("testSfBtn").addEventListener("click", async () => {
    try {
      const res = await fetch("/autopilot/connectors/salesforce/test", {
        method: "POST",
        headers: { Authorization: `Bearer ${jwtToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        showToast(`☁️ Salesforce Ping OK: ${data.environment}`, "success");
      }
    } catch (err) {
      showToast("Salesforce ping failed.", "error");
    }
  });

  // Connector Ping: HubSpot
  document.getElementById("testHsBtn").addEventListener("click", async () => {
    try {
      const res = await fetch("/autopilot/connectors/hubspot/test", {
        method: "POST",
        headers: { Authorization: `Bearer ${jwtToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        showToast(`🧡 HubSpot Ping OK: ${data.environment}`, "success");
      }
    } catch (err) {
      showToast("HubSpot ping failed.", "error");
    }
  });

  // Connector Sync: Salesforce & HubSpot
  document.getElementById("syncConnectorsBtn").addEventListener("click", async () => {
    const btn = document.getElementById("syncConnectorsBtn");
    btn.disabled = true;
    btn.textContent = "Syncing...";
    try {
      const res = await fetch("/autopilot/connectors/sync", {
        method: "POST",
        headers: { Authorization: `Bearer ${jwtToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        showToast(`🔄 Synced ${data.connectors_synced} CRM providers into local pipeline!`, "success");
        await refreshMonitor();
      }
    } catch (err) {
      showToast("Failed to sync CRM connectors.", "error");
    } finally {
      btn.disabled = false;
      btn.textContent = "🔄 Sync Deals";
    }
  });

  // Generate Preview Button
  document.getElementById("previewBtn").addEventListener("click", () => handleGeneratePreview());

  // Approve Button
  document.getElementById("approveBtn").addEventListener("click", () => handleExecuteDecision(true));

  // Reject Button
  document.getElementById("rejectBtn").addEventListener("click", () => handleExecuteDecision(false));
}

// Refresh Monitor status
async function refreshMonitor() {
  try {
    const res = await fetch("/autopilot/monitor/status", {
      headers: { Authorization: `Bearer ${jwtToken}` },
    });
    if (res.ok) {
      const data = await res.json();
      if (data.latest_briefing) {
        updateMonitorUI(data.latest_briefing);
      } else {
        // Trigger initial scan
        const scanRes = await fetch("/autopilot/monitor/scan-now", {
          method: "POST",
          headers: { Authorization: `Bearer ${jwtToken}` },
        });
        if (scanRes.ok) {
          const scanData = await scanRes.json();
          updateMonitorUI(scanData.briefing);
        }
      }
    }
  } catch (err) {
    console.error("Monitor refresh failed:", err);
  }
}

function updateMonitorUI(briefing) {
  if (!briefing || !briefing.metrics) return;
  const m = briefing.metrics;
  const totLakh = m.total_pipeline_value / 100000;
  const riskLakh = m.total_value_at_risk / 100000;

  document.getElementById("monTotalValue").textContent = `₹${(totLakh / 100).toFixed(2)} Cr`;
  document.getElementById("monValueRisk").textContent = `₹${riskLakh.toFixed(1)} Lakh`;
  document.getElementById("monCriticalCount").textContent = `${m.critical_deals_count} Critical`;
  document.getElementById("monBriefingText").textContent = briefing.autonomous_recommendation || "Pipeline healthy.";
}

// Format Currency
function formatLakh(amount) {
  if (!amount) return "₹0";
  const lakh = amount / 100000;
  return `₹${amount.toLocaleString()} (₹${lakh.toFixed(1)}L)`;
}

// Handle Generate Preview
async function handleGeneratePreview(customQuery = null) {
  const promptInput = document.getElementById("promptInput");
  const query = customQuery || promptInput.value.trim();
  if (!query) {
    showToast("Please enter an operational request first.", "error");
    return;
  }

  const btn = document.getElementById("previewBtn");
  btn.disabled = true;
  btn.innerHTML = `<span>State Machine Running...</span>`;

  try {
    const res = await fetch("/autopilot/preview", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwtToken}`,
      },
      body: JSON.stringify({
        query: query,
        session_id: currentSessionId,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to execute workflow.");
    }

    const preview = await res.json();

    // Check if Feature 4 Multi-Turn Disambiguation was triggered
    if (preview.needs_clarification) {
      renderDisambiguation(preview);
      showToast("❓ Ambiguous request: please pick an option to clarify.", "info");
      return;
    }

    // Hide disambiguation card if resolved
    document.getElementById("disambiguationSection").classList.add("hidden");

    currentPreviewId = preview.preview_id;
    renderPreview(preview);
    showToast("📋 LangGraph Dry-run plan compiled for review.", "info");
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span>Execute Agent Workflow</span><span class="arrow">→</span>`;
  }
}

// Render Disambiguation Options (Feature 4)
function renderDisambiguation(preview) {
  const section = document.getElementById("disambiguationSection");
  const qEl = document.getElementById("disambiguationQuestion");
  const optsContainer = document.getElementById("disambiguationOptions");

  document.getElementById("previewSection").classList.add("hidden");
  document.getElementById("reportSection").classList.add("hidden");

  qEl.textContent = preview.clarification_question || "Please select the target parameters:";
  optsContainer.innerHTML = "";

  (preview.suggested_options || []).forEach((opt, idx) => {
    const tile = document.createElement("button");
    tile.className = "disambiguation-tile";
    tile.innerHTML = `
      <span class="tile-title">${idx + 1}. ${opt.title}</span>
      <span class="tile-desc">${opt.description}</span>
    `;
    tile.addEventListener("click", () => {
      handleGeneratePreview(`Option ${idx + 1}`);
    });
    optsContainer.appendChild(tile);
  });

  section.classList.remove("hidden");
  section.scrollIntoView({ behavior: "smooth" });
}

// Render Preview Card
function renderPreview(preview) {
  const previewSection = document.getElementById("previewSection");
  const reportSection = document.getElementById("reportSection");
  reportSection.classList.add("hidden");

  // Intent
  const intent = preview.intent || {};
  document.getElementById("intentAmount").textContent = formatLakh(intent.min_amount);
  document.getElementById("intentDays").textContent = `${intent.days_inactive || 7} Days Inactive`;
  document.getElementById("intentStatus").textContent = (intent.status || "open").toUpperCase();
  document.getElementById("intentAction").textContent = "LangGraph Self-Healing Flow";

  // Matched Records Table with ML Risk Columns
  document.getElementById("matchedCount").textContent = `${preview.matched_count} records qualifying`;
  const tbody = document.getElementById("matchedTbody");
  tbody.innerHTML = "";

  if (preview.matched_records && preview.matched_records.length > 0) {
    preview.matched_records.forEach((rec) => {
      const tr = document.createElement("tr");

      // Risk Tier styling
      let tierClass = "risk-low";
      if (rec.risk_tier === "CRITICAL") tierClass = "risk-critical";
      else if (rec.risk_tier === "HIGH") tierClass = "risk-high";
      else if (rec.risk_tier === "MEDIUM") tierClass = "risk-medium";

      // Factors tags
      const factorsHtml = (rec.risk_factors || [])
        .map((f) => `<span class="factor-tag">• ${f}</span>`)
        .join(" ");

      tr.innerHTML = `
        <td><strong>#${rec.opportunity_id}</strong></td>
        <td><strong>${rec.account_name || "N/A"}</strong></td>
        <td>${formatLakh(rec.amount)}</td>
        <td>${rec.days_since_activity !== null ? `${rec.days_since_activity}d inactive` : "Never"}</td>
        <td><strong style="font-size: 1rem;">${rec.risk_score_pct || 0}%</strong></td>
        <td><span class="risk-pill ${tierClass}">${rec.risk_tier || "NORMAL"}</span></td>
        <td style="max-width: 320px;">${factorsHtml}</td>
      `;
      tbody.appendChild(tr);
    });
  } else {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem; color: var(--text-dim);">No opportunities currently meet these criteria.</td></tr>`;
  }

  // Proposed Actions
  const actionsList = document.getElementById("actionsList");
  actionsList.innerHTML = "";
  (preview.proposed_actions || []).forEach((action) => {
    const li = document.createElement("li");
    const dueFormatted = new Date(action.due_at).toLocaleDateString();
    li.textContent = `[${action.priority.toUpperCase()}] Assign task to Owner ${action.owner_id} for ${action.account_name} due ${dueFormatted}: "${action.description}"`;
    actionsList.appendChild(li);
  });

  previewSection.classList.remove("hidden");
  previewSection.scrollIntoView({ behavior: "smooth" });
}

// Handle Approve / Reject Decision
async function handleExecuteDecision(approved) {
  if (!currentPreviewId) return;

  const approveBtn = document.getElementById("approveBtn");
  const rejectBtn = document.getElementById("rejectBtn");
  const glitchCheck = document.getElementById("glitchCheck");

  approveBtn.disabled = true;
  rejectBtn.disabled = true;

  try {
    const res = await fetch("/autopilot/execute", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwtToken}`,
      },
      body: JSON.stringify({
        preview_id: currentPreviewId,
        approved: approved,
        simulate_glitch: glitchCheck.checked,
      }),
    });

    const result = await res.json();

    if (!approved) {
      showToast("❌ Plan rejected. No actions were performed.", "info");
      document.getElementById("previewSection").classList.add("hidden");
      return;
    }

    renderReport(result);
    showToast("🎉 Actions approved and persisted in database!", "success");
    await refreshMonitor();
  } catch (err) {
    showToast("Error executing decision.", "error");
  } finally {
    approveBtn.disabled = false;
    rejectBtn.disabled = false;
  }
}

// Render Execution Report
function renderReport(result) {
  const reportSection = document.getElementById("reportSection");
  const summary = result.summary || {};

  document.getElementById("statCreated").textContent = summary.tasks_created || 0;
  document.getElementById("statSkipped").textContent = summary.tasks_skipped || 0;
  document.getElementById("statHealed").textContent = summary.self_healed_events || 0;
  document.getElementById("statVerified").textContent = summary.verified_in_db ? "Verified ✓" : "Pending";

  // Self-Healing log box
  const recoveryBox = document.getElementById("recoveryLogBox");
  const recoveryList = document.getElementById("recoveryList");
  recoveryList.innerHTML = "";

  if (result.recovery_log && result.recovery_log.length > 0) {
    result.recovery_log.forEach((log) => {
      const li = document.createElement("li");
      li.textContent = log;
      recoveryList.appendChild(li);
    });
    recoveryBox.classList.remove("hidden");
  } else {
    recoveryBox.classList.add("hidden");
  }

  const tbody = document.getElementById("tasksTbody");
  tbody.innerHTML = "";

  const createdTasks = result.created_tasks || [];
  if (createdTasks.length > 0) {
    createdTasks.forEach((task) => {
      const tr = document.createElement("tr");
      const dueFormatted = new Date(task.due_at).toLocaleDateString();
      tr.innerHTML = `
        <td><strong style="color: var(--success);">Task #${task.task_id}</strong></td>
        <td>Opp #${task.opportunity_id}</td>
        <td>Owner ${task.owner_id}</td>
        <td>${dueFormatted}</td>
        <td>${task.description}</td>
      `;
      tbody.appendChild(tr);
    });
  } else {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 1.5rem; color: var(--text-dim);">No new tasks created (all duplicates were safely skipped).</td></tr>`;
  }

  reportSection.classList.remove("hidden");
  reportSection.scrollIntoView({ behavior: "smooth" });
}
