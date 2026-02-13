// ===== DOM ELEMENTS =====
const keywordInput = document.getElementById("keyword");
const maxPagesInput = document.getElementById("max-pages");
const statusEl = document.getElementById("status");

const targetJobs = document.getElementById("target-jobs");
const targetTalent = document.getElementById("target-talent");
const targetProjects = document.getElementById("target-projects");

const startButton = document.getElementById("start");
const stopButton = document.getElementById("stop");
const exportJsonButton = document.getElementById("export-json");
const exportCsvButton = document.getElementById("export-csv");
const clearButton = document.getElementById("clear-data");

// Queue elements
const tabs = document.querySelectorAll('.tab');
const tabContents = document.querySelectorAll('.tab-content');
const queueKeywordsInput = document.getElementById("queue-keywords");
const queueMaxPages = document.getElementById("queue-max-pages");
const queueTargetJobs = document.getElementById("queue-target-jobs");
const queueTargetTalent = document.getElementById("queue-target-talent");
const queueTargetProjects = document.getElementById("queue-target-projects");
const queueAddBtn = document.getElementById("queue-add");
const queueStartBtn = document.getElementById("queue-start");
const queueClearBtn = document.getElementById("queue-clear");
const queueTotalEl = document.getElementById("queue-total");
const queuePendingEl = document.getElementById("queue-pending");
const queueCompletedEl = document.getElementById("queue-completed");
const queueListEl = document.getElementById("queue-list");

// ===== TAB SWITCHING =====
tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    const tabName = tab.dataset.tab;
    tabs.forEach(t => t.classList.remove('active'));
    tabContents.forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(`${tabName}-tab`).classList.add('active');

    if (tabName === 'queue') {
      updateQueueDisplay();
    }
  });
});

// ===== QUEUE FUNCTIONS =====
async function addKeywordsToQueue() {
  const text = queueKeywordsInput.value.trim();
  if (!text) {
    setStatus('Please enter at least one keyword.');
    return;
  }

  const keywords = text.split('\n').map(k => k.trim()).filter(k => k);
  const targets = [];
  if (queueTargetJobs.checked) targets.push('jobs');
  if (queueTargetTalent.checked) targets.push('talent');
  if (queueTargetProjects.checked) targets.push('projects');

  const maxPages = Number(queueMaxPages.value) || 0;

  if (targets.length === 0) {
    setStatus('Please select at least one target.');
    return;
  }

  const response = await sendMessage({
    type: 'QUEUE_ADD',
    keywords,
    options: { targets, maxPages }
  });

  if (response.ok) {
    queueKeywordsInput.value = '';
    setStatus(`Added ${keywords.length} keyword(s) to queue.`);
    updateQueueDisplay();
  } else {
    setStatus(`Error: ${response.error || 'Failed to add keywords'}`);
  }
}

async function clearQueue() {
  if (!confirm('Clear all keywords from queue?')) return;

  const response = await sendMessage({ type: 'QUEUE_CLEAR' });
  if (response.ok) {
    setStatus('Queue cleared.');
    updateQueueDisplay();
  }
}

async function startQueue() {
  const response = await sendMessage({ type: 'QUEUE_GET_STATUS' });
  if (!response.ok) return;

  const summary = response.summary;

  if (summary.pending === 0) {
    const sync = await sendMessage({ type: 'QUEUE_SYNC_RECOMMENDED_API' });
    if (sync.ok && sync.addedCount > 0) {
      setStatus(`API önerilerinden ${sync.addedCount} keyword eklendi. Queue başlatılıyor...`);
    } else {
      setStatus('No pending keywords to process.');
      return;
    }
  }

  // Start queue processor
  await sendMessage({ type: 'QUEUE_START' });
  setStatus('Queue started! Processing keywords automatically...');
  updateQueueDisplay();
}

async function updateQueueDisplay() {
  const response = await sendMessage({ type: 'QUEUE_GET_STATUS' });
  if (!response.ok) return;

  const summary = response.summary;

  // Update counts
  queueTotalEl.textContent = summary.total;
  queuePendingEl.textContent = summary.pending;
  queueCompletedEl.textContent = summary.completed;

  // Update list
  if (summary.keywords.length === 0) {
    queueListEl.innerHTML = '<div class="queue-empty">No keywords in queue</div>';
  } else {
    queueListEl.innerHTML = summary.keywords.map(kw => {
      const statusLabel = kw.status.charAt(0).toUpperCase() + kw.status.slice(1);
      const results = kw.results ? `(J:${kw.results.jobs}, T:${kw.results.talent}, P:${kw.results.projects})` : '';
      return `
        <div class="queue-item status-${kw.status}">
          <span class="queue-item-keyword">${escapeHtml(kw.keyword)}</span>
          <span class="queue-item-status">${statusLabel}</span>
          ${results ? `<small>${results}</small>` : ''}
        </div>
      `;
    }).join('');
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ===== ORIGINAL FUNCTIONS =====
function setStatus(text) {
  statusEl.textContent = text;
  statusEl.classList.remove('blocked', 'warning');
  if (text.includes('Blocked') || text.includes('SESSION EXPIRED') || text.includes('RATE LIMITED')) {
    statusEl.classList.add('blocked');
  }
}

function formatSummary(summary) {
  if (!summary) return "";
  const counts = summary.counts || {};
  return [
    `Run: ${summary.runId}`,
    `Keyword: ${summary.keyword}`,
    `Status: ${summary.status}`,
    `Jobs: ${counts.jobs || 0}`,
    `Talent: ${counts.talent || 0}`,
    `Projects: ${counts.projects || 0}`
  ].join(" | ");
}

function renderStatus(payload) {
  if (!payload) {
    setStatus("Status: Idle");
    return;
  }

  if (payload.active) {
    const active = payload.active;
    const summary = payload.activeSummary;
    const base = formatSummary(summary) || "Active run";
    const phase = active.phase || "list";
    let phaseInfo = `Phase: ${phase}`;
    if (phase === "details") {
      const detailTotal = active.detailTotal || 0;
      const detailCurrent = detailTotal > 0 ? Math.min(active.detailIndex + 1, detailTotal) : 0;
      phaseInfo += ` | Detail: ${detailCurrent}/${detailTotal}`;
    } else {
      phaseInfo += ` | Page: ${active.pageIndex}`;
    }
    const maxInfo = phase === "list" && active.maxPages > 0 ? ` | Max pages: ${active.maxPages}` : "";
    const targetInfo = `Target: ${active.target}`;
    let text = `${base}\n${targetInfo} | ${phaseInfo}${maxInfo}`;

    if (active.blocked) {
      if (active.sessionExpired) {
        text += `\n⚠️ SESSION EXPIRED – Upwork logged you out. Re-login and restart.`;
      } else if (active.rateLimited) {
        text += `\n⚠️ RATE LIMITED – Too many requests. Wait a few minutes.`;
      } else {
        text += `\nBlocked: solve challenge at ${active.blockedUrl}`;
      }
    }

    setStatus(text);
    return;
  }

  if (payload.latestSummary) {
    setStatus(formatSummary(payload.latestSummary));
    return;
  }

  setStatus("Status: Idle");
}

function updateStatus() {
  try {
    chrome.runtime.sendMessage({ type: "GET_STATUS" }, (response) => {
      if (chrome.runtime.lastError) {
        // Suppress async response errors
        return;
      }
      renderStatus(response);
    });
  } catch (err) {
    // Extension context may be invalidated
  }
}

function sendMessage(message) {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime.lastError) {
          // Suppress "message channel closed" errors when popup closes
          resolve({});
          return;
        }
        resolve(response || {});
      });
    } catch (err) {
      resolve({});
    }
  });
}

// ===== EVENT LISTENERS =====
queueAddBtn.addEventListener("click", addKeywordsToQueue);
queueStartBtn.addEventListener("click", startQueue);
queueClearBtn.addEventListener("click", clearQueue);

startButton.addEventListener("click", () => {
  const keyword = keywordInput.value.trim();
  const targets = [];
  if (targetJobs.checked) targets.push("jobs");
  if (targetTalent.checked) targets.push("talent");
  if (targetProjects.checked) targets.push("projects");

  const maxPages = Number(maxPagesInput.value) || 0;

  sendMessage({
    type: "START_RUN",
    config: { keyword, targets, maxPages }
  }).then((response) => {
    if (!response || !response.ok) {
      const error = response && response.error ? response.error : "Failed to start.";
      setStatus(`Error: ${error}`);
      return;
    }
    setStatus(`Started: ${response.runId}`);
    updateStatus();
  });
});

stopButton.addEventListener("click", () => {
  sendMessage({ type: "STOP_RUN" }).then((response) => {
    if (!response || !response.ok) {
      const error = response && response.error ? response.error : "No active run.";
      setStatus(`Error: ${error}`);
      return;
    }
    setStatus("Stopped.");
    updateStatus();
  });
});

exportJsonButton.addEventListener("click", () => {
  sendMessage({ type: "EXPORT_JSON" }).then((response) => {
    if (!response || !response.ok) {
      setStatus(`Error: ${response?.error || "Export failed."}`);
      return;
    }
    setStatus("JSON export started.");
  });
});

exportCsvButton.addEventListener("click", () => {
  sendMessage({ type: "EXPORT_CSV" }).then((response) => {
    if (!response || !response.ok) {
      setStatus(`Error: ${response?.error || "Export failed."}`);
      return;
    }
    setStatus("CSV export started.");
  });
});

clearButton.addEventListener("click", () => {
  sendMessage({ type: "CLEAR_DATA" }).then((response) => {
    if (!response || !response.ok) {
      setStatus("Error: failed to clear.");
      return;
    }
    setStatus("Data cleared.");
  });
});

// ===== INITIALIZATION =====
updateStatus();
updateQueueDisplay();
setInterval(() => {
  updateStatus();
  updateQueueDisplay();
}, 2000);
