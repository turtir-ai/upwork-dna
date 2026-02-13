/**
 * Upwork DNA - Electron Renderer Process
 */

const { ipcRenderer } = require('electron');

// State
let currentView = 'dashboard';
let stats = {
  totalScraped: 0,
  talentCount: 0,
  jobsCount: 0,
  projectsCount: 0
};

// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
  console.log('[Renderer] App initialized');

  // Setup navigation
  setupNavigation();

  // Setup buttons
  setupButtons();

  // Load initial data
  await loadStats();

  // Setup IPC listeners
  setupIpcListeners();

  // Start periodic refresh
  setInterval(loadStats, 5000);
});

function setupNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  const views = document.querySelectorAll('.view');
  const viewTitle = document.getElementById('view-title');

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const view = item.dataset.view;

      // Update nav
      navItems.forEach(i => i.classList.remove('active'));
      item.classList.add('active');

      // Update views
      views.forEach(v => v.classList.remove('active'));
      document.getElementById(`${view}-view`).classList.add('active');

      // Update title
      const titles = {
        dashboard: 'Dashboard',
        queue: 'Queue Manager',
        insights: 'Market Insights',
        keywords: 'Recommended Keywords',
        settings: 'Settings'
      };
      viewTitle.textContent = titles[view];

      currentView = view;

      // Load view-specific data
      loadViewData(view);
    });
  });
}

function setupButtons() {
  // Refresh button
  document.getElementById('refresh-btn').addEventListener('click', async () => {
    await loadStats();
    loadViewData(currentView);
  });

  // Open dashboard button
  document.getElementById('open-dashboard-btn').addEventListener('click', async () => {
    await ipcRenderer.invoke('open-dashboard');
  });

  // Add keywords button
  document.getElementById('add-keywords-btn').addEventListener('click', () => {
    addActivity('Yeni keyword ekleme extension popup üzerinden yapılır.');
  });

  // Clear queue button
  document.getElementById('clear-queue-btn').addEventListener('click', async () => {
    addActivity('Queue temizleme extension popup üzerinden yönetiliyor.');
  });

  // Apply keywords button
  document.getElementById('apply-keywords-btn').addEventListener('click', async () => {
    const result = await ipcRenderer.invoke('apply-keywords');
    if (result && result.ok) {
      addActivity(`Top ${result.queued} keyword orchestrator tarafından önerildi.`);
      loadViewData('keywords');
    }
  });

  // Log close button
  document.getElementById('log-close').addEventListener('click', () => {
    document.getElementById('log-panel').classList.remove('visible');
  });
}

function setupIpcListeners() {
  // Python logs
  ipcRenderer.on('python-log', (event, log) => {
    addPythonLog(log);
  });

  // New data
  ipcRenderer.on('new-data', (event, data) => {
    addActivity(`New data file: ${data.file}`);
    loadStats();
  });

  // New recommendations
  ipcRenderer.on('new-recommendations', (event, data) => {
    addActivity(`${data.keywords.length} new keywords recommended`);
    if (currentView === 'keywords') {
      loadViewData('keywords');
    }
  });
}

// ============================================================
// DATA LOADING
// ============================================================

async function loadStats() {
  const newStats = await ipcRenderer.invoke('get-stats');
  stats = { ...stats, ...newStats };

  // Update UI
  document.getElementById('total-scraped').textContent = stats.totalScraped || 0;
  document.getElementById('talent-count').textContent = stats.talentCount || 0;
  document.getElementById('jobs-count').textContent = stats.jobsCount || 0;
  document.getElementById('projects-count').textContent = stats.projectsCount || 0;
}

async function loadViewData(view) {
  switch (view) {
    case 'queue':
      await loadQueueData();
      break;
    case 'keywords':
      await loadKeywordsData();
      break;
    case 'insights':
      await loadInsightsData();
      break;
  }
}

async function loadQueueData() {
  const queueStatus = await ipcRenderer.invoke('get-queue-status');

  document.getElementById('queue-total').textContent = queueStatus.total || 0;
  document.getElementById('queue-pending').textContent = queueStatus.pending || 0;
  document.getElementById('queue-running').textContent = queueStatus.running || 0;
  document.getElementById('queue-completed').textContent = queueStatus.completed || 0;

  // Update queue list
  const queueList = document.getElementById('queue-list');
  if (queueStatus.keywords && queueStatus.keywords.length > 0) {
    queueList.innerHTML = queueStatus.keywords.map(kw => `
      <div class="queue-item status-${kw.status || 'pending'}">
        <span class="queue-item-keyword">${kw.keyword}</span>
        <span class="queue-item-status">${kw.status || 'pending'}</span>
        ${kw.results ? `<small>(J:${kw.results.jobs}, T:${kw.results.talent}, P:${kw.results.projects})</small>` : ''}
      </div>
    `).join('');
  } else {
    queueList.innerHTML = `
      <div class="empty-state">
        <p>Queue telemetry bekleniyor</p>
        <small>Extension çalışırken sayılar burada canlı görünür</small>
      </div>
    `;
  }
}

async function loadKeywordsData() {
  const recommendations = await ipcRenderer.invoke('get-keyword-recommendations');
  const keywordsList = document.getElementById('keywords-list');
  if (!recommendations || recommendations.length === 0) {
    keywordsList.innerHTML = `
      <div class="empty-state">
        <p>Henüz öneri yok</p>
        <small>/v1/recommendations/keywords endpointi veri ürettiğinde listelenecek</small>
      </div>
    `;
    return;
  }

  keywordsList.innerHTML = recommendations.slice(0, 30).map(rec => `
    <div class="keyword-card">
      <div class="keyword-info">
        <div class="keyword-name">${rec.keyword}</div>
        <div class="keyword-score">Opportunity: ${Number(rec.opportunity_score || 0).toFixed(1)} | Demand: ${rec.demand} | Supply: ${rec.supply}</div>
      </div>
      <span class="keyword-priority ${rec.recommended_priority}">${rec.recommended_priority}</span>
    </div>
  `).join('');
}

async function loadInsightsData() {
  const insights = await ipcRenderer.invoke('get-insights');
  const insightsList = document.getElementById('insights-list');
  if (!insights || insights.length === 0) {
    insightsList.innerHTML = `
      <div class="empty-state">
        <p>Insight bekleniyor</p>
        <small>Orchestrator verisi geldikçe içgörüler listelenir</small>
      </div>
    `;
    return;
  }

  insightsList.innerHTML = insights.map(item => `
    <div class="insight-card">
      <div class="insight-title">${item.title}</div>
      <div class="insight-description">${item.description}</div>
    </div>
  `).join('');
}

// ============================================================
// UI HELPERS
// ============================================================

function addActivity(text) {
  const activityList = document.getElementById('activity-list');
  const time = new Date().toLocaleTimeString();

  const item = document.createElement('div');
  item.className = 'activity-item';
  item.innerHTML = `
    <span class="activity-time">${time}</span>
    <span class="activity-text">${text}</span>
  `;

  activityList.insertBefore(item, activityList.firstChild);

  // Keep only last 50 items
  while (activityList.children.length > 50) {
    activityList.removeChild(activityList.lastChild);
  }
}

function addPythonLog(log) {
  const logPanel = document.getElementById('log-panel');
  const logContent = document.getElementById('log-content');

  // Show panel if hidden
  if (!logPanel.classList.contains('visible')) {
    logPanel.classList.add('visible');
  }

  const line = document.createElement('div');
  line.className = 'log-line';
  line.textContent = `[${new Date().toLocaleTimeString()}] ${log}`;

  logContent.appendChild(line);
  logContent.scrollTop = logContent.scrollHeight;

  // Keep only last 100 lines
  while (logContent.children.length > 100) {
    logContent.removeChild(logContent.firstChild);
  }
}

// ============================================================
// EXPORTS
// ============================================================

module.exports = { loadStats, loadViewData };
