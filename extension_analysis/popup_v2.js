// Upwork DNA Scraper v2.0 - Enhanced Popup Controller

// ===== DOM ELEMENTS =====
const tabs = document.querySelectorAll('.tab');
const tabContents = document.querySelectorAll('.tab-content');

// Queue elements
const queueKeywordsInput = document.getElementById('queue-keywords');
const queueTargetJobs = document.getElementById('queue-target-jobs');
const queueTargetTalent = document.getElementById('queue-target-talent');
const queueTargetProjects = document.getElementById('queue-target-projects');
const queueMaxPages = document.getElementById('queue-max-pages');
const queueAddBtn = document.getElementById('queue-add');
const queueClearBtn = document.getElementById('queue-clear');
const queueStartBtn = document.getElementById('queue-start');
const queuePauseBtn = document.getElementById('queue-pause');
const queueResumeBtn = document.getElementById('queue-resume');
const queueStopBtn = document.getElementById('queue-stop');
const queueExportAllBtn = document.getElementById('queue-export-all');
const syncProfileBtn = document.getElementById('sync-profile');
const profileSyncStatusEl = document.getElementById('profile-sync-status');

// Queue display elements
const queueTotalEl = document.getElementById('queue-total');
const queuePendingEl = document.getElementById('queue-pending');
const queueRunningEl = document.getElementById('queue-running');
const queueCompletedEl = document.getElementById('queue-completed');
const queueErrorEl = document.getElementById('queue-error');
const queueProgressFill = document.getElementById('queue-progress-fill');
const queueProgressText = document.getElementById('queue-progress-text');
const queueListEl = document.getElementById('queue-list');

// Stats elements
const statTotalProcessed = document.getElementById('stat-total-processed');
const statTotalJobs = document.getElementById('stat-total-jobs');
const statDaily = document.getElementById('stat-daily');
const statDailyLimit = document.getElementById('stat-daily-limit');
const statTotalErrors = document.getElementById('stat-total-errors');
const statTotalTalent = document.getElementById('stat-total-talent');
const statTotalProjects = document.getElementById('stat-total-projects');
const queueStatsPanel = document.getElementById('queue-stats');

// Status elements
const statusEl = document.getElementById('status');
const hintText = document.getElementById('hint-text');

// Original single-run elements
const keywordInput = document.getElementById('keyword');
const maxPagesInput = document.getElementById('max-pages');
const targetJobs = document.getElementById('target-jobs');
const targetTalent = document.getElementById('target-talent');
const targetProjects = document.getElementById('target-projects');
const startButton = document.getElementById('start');
const stopButton = document.getElementById('stop');
const exportJsonButton = document.getElementById('export-json');
const exportCsvButton = document.getElementById('export-csv');
const clearButton = document.getElementById('clear-data');

// ===== STATE =====
let currentTab = 'queue';
let statusUpdateInterval = null;

// ===== TAB SWITCHING =====
tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    const tabName = tab.dataset.tab;
    switchTab(tabName);
  });
});

function switchTab(tabName) {
  tabs.forEach(t => t.classList.remove('active'));
  tabContents.forEach(c => c.classList.remove('active'));

  document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
  document.getElementById(`${tabName}-tab`).classList.add('active');

  currentTab = tabName;

  if (tabName === 'queue') {
    updateQueueDisplay();
  }
}

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
  const response = await sendMessage({ type: 'QUEUE_START', keywords: [], options: {} });
  if (response.ok) {
    setStatus('Queue processing started.');
    updateQueueDisplay();
  } else {
    setStatus(`Error: ${response.error || 'Failed to start queue'}`);
  }
}

async function pauseQueue() {
  const response = await sendMessage({ type: 'QUEUE_PAUSE' });
  if (response.ok) {
    setStatus('Queue paused.');
    updateQueueDisplay();
  }
}

async function resumeQueue() {
  const response = await sendMessage({ type: 'QUEUE_RESUME' });
  if (response.ok) {
    setStatus('Queue resumed.');
    updateQueueDisplay();
  }
}

async function stopQueue() {
  const response = await sendMessage({ type: 'QUEUE_STOP' });
  if (response.ok) {
    setStatus('Queue stopped.');
    updateQueueDisplay();
  }
}

async function exportAllQueue() {
  setStatus('Exporting all completed runs...');
  // TODO: Implement export all functionality
  setStatus('Export feature coming soon!');
}

async function syncProfileFromCurrentTab() {
  setStatus('Syncing profile from active Upwork tab...');
  const response = await sendMessage({ type: 'SYNC_PROFILE_FROM_ACTIVE_TAB' });

  if (!response?.ok) {
    setStatus(`Profile sync failed: ${response?.error || 'unknown error'}`);
    await refreshProfileSyncStatus();
    return;
  }

  setStatus(`Profile synced (${response.keywordCount || 0} keywords).`);
  await refreshProfileSyncStatus();
}

function renderProfileSyncStatus(state) {
  if (!profileSyncStatusEl) return;
  if (!state || !state.updatedAt) {
    profileSyncStatusEl.textContent = 'Profile sync: not started';
    return;
  }

  const badge = state.status === 'ok' ? '✅' : '⚠️';
  const source = state.sourceUrl || 'n/a';
  const when = state.syncedAt || state.updatedAt;
  profileSyncStatusEl.textContent = `${badge} Profile sync • ${when} • ${source}`;
}

async function refreshProfileSyncStatus() {
  const response = await sendMessage({ type: 'GET_PROFILE_SYNC_STATUS' });
  if (!response?.ok) return;
  renderProfileSyncStatus(response.state || {});
}

// ===== QUEUE DISPLAY =====
async function updateQueueDisplay() {
  const response = await sendMessage({ type: 'QUEUE_GET_STATUS' });
  if (!response.ok) return;

  const summary = response.summary;

  // Update counts
  queueTotalEl.textContent = summary.total;
  queuePendingEl.textContent = summary.pending;
  queueRunningEl.textContent = summary.running;
  queueCompletedEl.textContent = summary.completed;
  queueErrorEl.textContent = summary.error;

  // Update progress
  const progress = summary.total > 0 ? Math.round((summary.completed / summary.total) * 100) : 0;
  queueProgressFill.style.width = `${progress}%`;
  queueProgressText.textContent = `${progress}%`;

  // Update list
  renderQueueList(summary.keywords || []);

  // Update stats
  statTotalProcessed.textContent = summary.stats.totalProcessed || 0;
  statDaily.textContent = summary.stats.dailyProcessed || 0;
  statDailyLimit.textContent = summary.stats.dailyLimit || 100;
  statTotalErrors.textContent = summary.stats.totalErrors || 0;
  statTotalJobs.textContent = summary.stats.totalItems?.jobs || 0;
  statTotalTalent.textContent = summary.stats.totalItems?.talent || 0;
  statTotalProjects.textContent = summary.stats.totalItems?.projects || 0;

  // Show stats panel if queue has items
  queueStatsPanel.style.display = summary.total > 0 ? 'block' : 'none';

  // Update buttons state
  queueStartBtn.disabled = summary.isRunning || summary.pending === 0;
  queuePauseBtn.disabled = !summary.isRunning || summary.isPaused;
  queueResumeBtn.style.display = summary.isPaused ? 'inline-block' : 'none';
  queuePauseBtn.style.display = summary.isPaused ? 'none' : 'inline-block';
  queueStopBtn.disabled = !summary.isRunning;
}

function renderQueueList(keywords) {
  if (keywords.length === 0) {
    queueListEl.innerHTML = '<div class="queue-list-empty">No keywords in queue</div>';
    return;
  }

  queueListEl.innerHTML = keywords.map(kw => {
    const statusClass = `status-${kw.status}`;
    const statusLabel = kw.status.charAt(0).toUpperCase() + kw.status.slice(1);
    const results = kw.results ? `(J:${kw.results.jobs}, T:${kw.results.talent}, P:${kw.results.projects})` : '';

    return `
      <div class="queue-item ${statusClass}">
        <span class="queue-item-keyword">${escapeHtml(kw.keyword)}</span>
        <span class="queue-item-status">${statusLabel}</span>
        <span class="queue-item-results">${results}</span>
      </div>
    `;
  }).join('');
}

// ===== SINGLE RUN FUNCTIONS (Original) =====
function startSingleRun() {
  const keyword = keywordInput.value.trim();
  const targets = [];
  if (targetJobs.checked) targets.push('jobs');
  if (targetTalent.checked) targets.push('talent');
  if (targetProjects.checked) targets.push('projects');

  const maxPages = Number(maxPagesInput.value) || 0;

  sendMessage({
    type: 'START_RUN',
    config: { keyword, targets, maxPages }
  }, (response) => {
    if (!response || !response.ok) {
      const error = response && response.error ? response.error : 'Failed to start.';
      setStatus(`Error: ${error}`);
      return;
    }
    setStatus(`Started: ${response.runId}`);
  });
}

function stopSingleRun() {
  sendMessage({ type: 'STOP_RUN' }, (response) => {
    if (!response || !response.ok) {
      const error = response && response.error ? response.error : 'No active run.';
      setStatus(`Error: ${error}`);
      return;
    }
    setStatus('Stopped.');
  });
}

function exportJson() {
  sendMessage({ type: 'EXPORT_JSON' }, (response) => {
    if (!response || !response.ok) {
      setStatus(`Error: ${response?.error || 'Export failed.'}`);
      return;
    }
    setStatus('JSON export started.');
  });
}

function exportCsv() {
  sendMessage({ type: 'EXPORT_CSV' }, (response) => {
    if (!response || !response.ok) {
      setStatus(`Error: ${response?.error || 'Export failed.'}`);
      return;
    }
    setStatus('CSV export started.');
  });
}

function clearData() {
  if (!confirm('Clear all scraped data?')) return;
  sendMessage({ type: 'CLEAR_DATA' }, (response) => {
    if (!response || !response.ok) {
      setStatus('Error: failed to clear.');
      return;
    }
    setStatus('Data cleared.');
  });
}

// ===== STATUS UPDATES =====
async function updateStatus() {
  const response = await sendMessage({ type: 'GET_STATUS' });
  renderStatus(response);
}

function renderStatus(payload) {
  if (!payload) {
    setStatus('Status: Idle');
    statusEl.classList.remove('blocked');
    return;
  }

  if (payload.active) {
    const active = payload.active;
    const summary = payload.activeSummary;
    const base = formatSummary(summary) || 'Active run';
    const phase = active.phase || 'list';
    let phaseInfo = `Phase: ${phase}`;

    if (phase === 'details') {
      const detailTotal = active.detailTotal || 0;
      const detailCurrent = detailTotal > 0 ? Math.min(active.detailIndex + 1, detailTotal) : 0;
      phaseInfo += ` | Detail: ${detailCurrent}/${detailTotal}`;
    } else {
      phaseInfo += ` | Page: ${active.pageIndex}`;
    }

    const maxInfo = phase === 'list' && active.maxPages > 0 ? ` | Max pages: ${active.maxPages}` : '';
    const targetInfo = `Target: ${active.target}`;
    let text = `${base}\n${targetInfo} | ${phaseInfo}${maxInfo}`;

    if (active.blocked) {
      text += `\n⚠️ BLOCKED: Solve challenge at ${active.blockedUrl}`;
      statusEl.classList.add('blocked');
    } else {
      statusEl.classList.remove('blocked');
    }

    setStatus(text);
    return;
  }

  if (payload.latestSummary) {
    setStatus(formatSummary(payload.latestSummary));
    statusEl.classList.remove('blocked');
    return;
  }

  setStatus('Status: Idle');
  statusEl.classList.remove('blocked');
}

function formatSummary(summary) {
  if (!summary) return '';
  const counts = summary.counts || {};
  return [
    `Run: ${summary.runId}`,
    `Keyword: ${summary.keyword}`,
    `Status: ${summary.status}`,
    `Jobs: ${counts.jobs || 0}`,
    `Talent: ${counts.talent || 0}`,
    `Projects: ${counts.projects || 0}`
  ].join(' | ');
}

function setStatus(text) {
  statusEl.textContent = text;
}

// ===== UTILITIES =====
function sendMessage(message, callback) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (response) => {
      if (callback) callback(response);
      resolve(response || {});
    });
  });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ===== EVENT LISTENERS =====
queueAddBtn.addEventListener('click', addKeywordsToQueue);
queueClearBtn.addEventListener('click', clearQueue);
queueStartBtn.addEventListener('click', startQueue);
queuePauseBtn.addEventListener('click', pauseQueue);
queueResumeBtn.addEventListener('click', resumeQueue);
queueStopBtn.addEventListener('click', stopQueue);
queueExportAllBtn.addEventListener('click', exportAllQueue);
if (syncProfileBtn) {
  syncProfileBtn.addEventListener('click', syncProfileFromCurrentTab);
}

startButton.addEventListener('click', startSingleRun);
stopButton.addEventListener('click', stopSingleRun);
exportJsonButton.addEventListener('click', exportJson);
exportCsvButton.addEventListener('click', exportCsv);
clearButton.addEventListener('click', clearData);

// ===== INITIALIZATION =====
function init() {
  updateStatus();
  updateQueueDisplay();
  refreshProfileSyncStatus();

  // Update every 2 seconds
  statusUpdateInterval = setInterval(() => {
    updateStatus();
    if (currentTab === 'queue') {
      updateQueueDisplay();
    }
  }, 2000);
}

// Start when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
