/**
 * Upwork DNA - Electron Main Process
 * ================================
 * Automated market intelligence application with:
 * - Embedded Chrome extension for scraping
 * - Streamlit dashboard for visualization
 * - Background Python pipeline for analysis
 * - Continuous data flywheel automation
 */

const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const fs = require('fs').promises;
const { spawn, exec } = require('child_process');
const axios = require('axios');

const ORCHESTRATOR_API_BASE = process.env.UPWORK_ORCHESTRATOR_API || 'http://127.0.0.1:8000';

// Global references
let mainWindow = null;
let dashboardWindow = null;
let pythonProcess = null;
let extensionDir = null;
let analistDir = null;
let pythonExecutable = null;

// ============================================================
// PATH RESOLUTION
// ============================================================

// Find Python executable - try venv first, then system Python
async function findPython() {
  return new Promise((resolve) => {
    // Try multiple venv locations and then system Python
    const candidates = process.platform === 'win32'
      ? ['python', 'python3', 'py']
      : [
          // Try venv first (preferred) - check common locations
          '/Users/dev/Documents/upworkextension/analist/venv/bin/python',
          '/Users/dev/Documents/upworkextension/analist/venv/bin/python3',
          '/Users/dev/Documents/upworkextension/venv/bin/python',
          '/Users/dev/Documents/upworkextension/venv/bin/python3',
          // Then system Python
          'python3', 'python',
          '/usr/bin/python3',
          '/usr/local/bin/python3',
          '/opt/homebrew/bin/python3'
        ];

    let tried = [];

    (function tryNext(index) {
      if (index >= candidates.length) {
        console.error('[Python] Not found, tried:', tried.join(', '));
        resolve(null);
        return;
      }

      const cmd = candidates[index];
      tried.push(cmd);

      // Test if this python works
      exec(`${cmd} --version`, { timeout: 5000 }, (error) => {
        if (!error) {
          console.log('[Python] Found:', cmd);
          resolve(cmd);
        } else {
          tryNext(index + 1);
        }
      });
    })(0);
  });
}

// Determine paths - handles dev, app bundle, and packaged scenarios
function getPaths() {
  const isDev = process.argv.includes('--dev');

  let baseDir;
  let extDir;
  let anaDir;

  if (isDev) {
    // Development mode
    baseDir = path.join(__dirname, '..');
    extDir = path.join(baseDir, '..', 'original_repo_v2');
    anaDir = path.join(baseDir, '..', 'analist');
  } else {
    // Production mode - check if we're in an app bundle
    const appPath = process.appPath || app.getAppPath();

    if (appPath.includes('.app')) {
      // Running from macOS app bundle
      // The extension and analist are symlinks in Resources
      const resourcesDir = path.join(path.dirname(appPath), 'Resources');
      extDir = path.join(resourcesDir, 'extension');
      anaDir = path.join(resourcesDir, 'analist');
      baseDir = resourcesDir;
    } else {
      // Regular packaged app
      baseDir = path.join(process.resourcesPath, 'app.asar.unpacked');
      extDir = path.join(baseDir, 'original_repo_v2');
      anaDir = path.join(baseDir, 'analist');
    }
  }

  // Single source of truth for extension + orchestrator ingest
  const dataDir = path.join(app.getPath('home'), 'Downloads', 'upwork_dna');

  return {
    base: baseDir,
    extension: extDir,
    analist: anaDir,
    upworkData: dataDir,
    dashboardUrl: 'http://localhost:8501'
  };
}

async function apiGet(endpoint, fallback = null) {
  try {
    const response = await axios.get(`${ORCHESTRATOR_API_BASE}${endpoint}`, {
      timeout: 3500
    });
    return response.data;
  } catch (error) {
    return fallback;
  }
}

async function apiPost(endpoint, payload = {}, fallback = null) {
  try {
    const response = await axios.post(`${ORCHESTRATOR_API_BASE}${endpoint}`, payload, {
      timeout: 3500
    });
    return response.data;
  } catch (error) {
    return fallback;
  }
}

// Verify paths exist
async function verifyPaths(paths) {
  const results = { extension: false, analist: false };

  try {
    await fs.access(paths.extension);
    results.extension = true;
    console.log('[Paths] Extension directory exists:', paths.extension);
  } catch (e) {
    console.error('[Paths] Extension directory NOT found:', paths.extension);
    // Try to resolve symlink
    try {
      const realPath = await fs.realpath(paths.extension);
      console.log('[Paths] Real path:', realPath);
      results.extension = true;
    } catch (e2) {
      console.error('[Paths] Cannot resolve extension path');
    }
  }

  try {
    await fs.access(paths.analist);
    results.analist = true;
    console.log('[Paths] Analyst directory exists:', paths.analist);
  } catch (e) {
    console.error('[Paths] Analyst directory NOT found:', paths.analist);
    try {
      const realPath = await fs.realpath(paths.analist);
      console.log('[Paths] Real path:', realPath);
      results.analist = true;
    } catch (e2) {
      console.error('[Paths] Cannot resolve analyst path');
    }
  }

  return results;
}

// ============================================================
// APP INITIALIZATION
// ============================================================

app.on('ready', async () => {
  const paths = getPaths();
  extensionDir = paths.extension;
  analistDir = paths.analist;

  console.log('[App] Upwork DNA starting...');
  console.log('[App] App path:', process.appPath || app.getAppPath());
  console.log('[App] Extension dir:', extensionDir);
  console.log('[App] Analyst dir:', analistDir);

  // Find Python executable
  pythonExecutable = await findPython();
  if (!pythonExecutable) {
    console.error('[App] WARNING: Python not found - dashboard will not work');
  }

  // Verify paths
  const pathCheck = await verifyPaths(paths);
  if (!pathCheck.extension || !pathCheck.analist) {
    console.error('[App] ERROR: Required directories not found!');
  }

  // Create upwork_dna directory in home
  await fs.mkdir(paths.upworkData, { recursive: true });
  console.log('[App] Data directory:', paths.upworkData);

  // Create main window
  createMainWindow();

  // Start background services (only if paths verified)
  if (pathCheck.extension && pathCheck.analist) {
    startBackgroundServices();
  }
});

app.on('window-all-closed', () => {
  // On macOS, keep app running
  if (process.platform !== 'darwin') {
    quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createMainWindow();
  }
});

function quit() {
  console.log('[App] Shutting down...');

  // Stop auto-scrape interval
  if (autoScrapeInterval) {
    clearInterval(autoScrapeInterval);
    autoScrapeInterval = null;
  }

  // Kill Python process
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }

  app.quit();
}

// ============================================================
// WINDOW CREATION
// ============================================================

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    title: 'Upwork DNA - Market Intelligence',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      webviewTag: true
    },
    backgroundColor: '#1a1a2e',
    titleBarStyle: 'hiddenInset',
    frame: true
  });

  // Load the app UI
  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  // Show window explicitly when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
  });

  // Open DevTools in dev mode
  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function createDashboardWindow() {
  if (dashboardWindow) {
    dashboardWindow.focus();
    return;
  }

  dashboardWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    title: 'Upwork DNA - Dashboard',
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  // Load Streamlit dashboard
  const paths = getPaths();
  dashboardWindow.loadURL(paths.dashboardUrl);

  dashboardWindow.on('closed', () => {
    dashboardWindow = null;
  });
}

// ============================================================
// BACKGROUND SERVICES
// ============================================================

async function startBackgroundServices() {
  console.log('[Services] Starting background services...');

  // Start Python analysis pipeline (only if Python found)
  if (pythonExecutable) {
    startPythonPipeline();
  } else {
    console.log('[Services] Skipping Python pipeline - Python not found');
  }

  // Start file watcher for new data
  startFileWatcher();

  // Start auto-scraping cycle
  startAutoScrapingCycle();
}

function startPythonPipeline() {
  if (!pythonExecutable) {
    console.error('[Python] Cannot start - Python executable not found');
    return;
  }

  console.log('[Python] Starting analysis pipeline...');
  console.log('[Python] Using:', pythonExecutable);
  console.log('[Python] Working dir:', analistDir);

  const scriptPath = path.join(analistDir, 'dashboard', 'app.py');

  // Check if dashboard exists
  fs.access(scriptPath)
    .then(() => {
      console.log('[Python] Dashboard script found:', scriptPath);

      pythonProcess = spawn(pythonExecutable, ['-m', 'streamlit', 'run', scriptPath, '--server.headless', 'true'], {
        cwd: analistDir,
        env: { ...process.env, PYTHONUNBUFFERED: '1' },
        shell: false
      });

      pythonProcess.stdout.on('data', (data) => {
        console.log('[Python]', data.toString().trim());
        // Send to renderer for display
        if (mainWindow) {
          mainWindow.webContents.send('python-log', data.toString());
        }
      });

      pythonProcess.stderr.on('data', (data) => {
        console.error('[Python Error]', data.toString().trim());
      });

      pythonProcess.on('close', (code) => {
        console.log('[Python] Process exited with code:', code);
        pythonProcess = null;
        // Auto-restart after 10 seconds
        setTimeout(() => {
          if (app.isActive() && pythonExecutable) {
            console.log('[Python] Auto-restarting...');
            startPythonPipeline();
          }
        }, 10000);
      });

      pythonProcess.on('error', (err) => {
        console.error('[Python] Spawn error:', err.message);
        pythonProcess = null;
      });
    })
    .catch(() => {
      console.error('[Python] Dashboard script not found:', scriptPath);
      console.log('[Python] Dashboard not available - running without visualization');
    });
}

function startFileWatcher() {
  try {
    const chokidar = require('chokidar');
    const paths = getPaths();

    // Create watch directory if not exists
    fs.mkdir(paths.upworkData, { recursive: true });

    const watcher = chokidar.watch(paths.upworkData, {
      ignored: /(^|[\/\\])\../,
      persistent: true,
      awaitWriteFinish: { stabilityThreshold: 2000, pollInterval: 100 }
    });

    watcher.on('add', (filePath) => {
      console.log('[Watcher] New file:', path.basename(filePath));
      if (mainWindow) {
        mainWindow.webContents.send('new-data', { file: filePath });
      }
    });

    watcher.on('change', (filePath) => {
      console.log('[Watcher] File changed:', path.basename(filePath));
    });

    console.log('[Watcher] Monitoring:', paths.upworkData);
  } catch (err) {
    console.error('[Watcher] Failed to start:', err.message);
  }
}

let autoScrapeInterval = null;

function startAutoScrapingCycle() {
  console.log('[AutoScrape] Starting automatic scraping cycle...');

  // Check every 5 minutes for new keywords to scrape
  autoScrapeInterval = setInterval(async () => {
    const paths = getPaths();
    const recommendedPath = path.join(paths.upworkData, 'recommended_keywords.json');

    try {
      const data = await fs.readFile(recommendedPath, 'utf8');
      const recommendations = JSON.parse(data);

      if (recommendations.keywords && recommendations.keywords.length > 0) {
        console.log('[AutoScrape] Found', recommendations.keywords.length, 'new keywords');
        if (mainWindow) {
          mainWindow.webContents.send('new-recommendations', recommendations);
        }
      }
    } catch (err) {
      // No recommendations file yet - normal
    }
  }, 5 * 60 * 1000);
}

// ============================================================
// IPC HANDLERS
// ============================================================

ipcMain.handle('get-paths', async () => {
  const paths = getPaths();
  // Don't expose full paths in UI
  return {
    upworkData: paths.upworkData,
    dashboardUrl: paths.dashboardUrl,
    hasPython: !!pythonExecutable,
    hasExtension: extensionDir !== null,
    hasAnalyst: analistDir !== null
  };
});

ipcMain.handle('get-stats', async () => {
  const paths = getPaths();
  const [summary, queueStatus] = await Promise.all([
    apiGet('/v1/telemetry/summary', null),
    apiGet('/v1/telemetry/queue', null)
  ]);

  const stats = {
    queueStatus: queueStatus || {},
    totalScraped: summary ? (summary.jobs_raw + summary.talent_raw + summary.projects_raw) : 0,
    talentCount: summary ? summary.talent_raw : 0,
    jobsCount: summary ? summary.jobs_raw : 0,
    projectsCount: summary ? summary.projects_raw : 0,
    lastScrape: summary ? summary.last_ingest_at : null,
    dataFiles: await countDataFiles(paths.upworkData),
    hasPython: !!pythonExecutable,
    pythonExecutable: pythonExecutable || 'Not found',
    apiOnline: !!summary
  };
  return stats;
});

ipcMain.handle('open-dashboard', async () => {
  if (!pythonExecutable) {
    return { ok: false, error: 'Python not found' };
  }
  createDashboardWindow();
  return { ok: true };
});

ipcMain.handle('open-external', async (event, url) => {
  shell.openExternal(url);
});

ipcMain.handle('start-scraping', async (event, keywords) => {
  console.log('[IPC] Start scraping:', keywords);
  return { ok: true, message: 'Scraping started' };
});

ipcMain.handle('stop-scraping', async () => {
  console.log('[IPC] Stop scraping');
  return { ok: true, message: 'Scraping stopped' };
});

ipcMain.handle('get-queue-status', async () => {
  const queue = await apiGet('/v1/telemetry/queue', {
    total: 0,
    pending: 0,
    running: 0,
    completed: 0,
    error: 0,
    last_cycle_at: null
  });
  const opportunities = await apiGet('/v1/opportunities/jobs?limit=200', []);
  const keywords = Array.isArray(opportunities)
    ? opportunities.slice(0, 30).map((item) => ({
        id: item.job_key,
        keyword: item.keyword,
        status: item.apply_now ? 'ready' : 'review',
        results: {
          jobs: item.apply_now ? 1 : 0,
          talent: 0,
          projects: 0
        }
      }))
    : [];
  return { ...queue, keywords };
});

ipcMain.handle('get-keyword-recommendations', async () => {
  return apiGet('/v1/recommendations/keywords?limit=100', []);
});

ipcMain.handle('get-insights', async () => {
  const [recommendations, opportunities] = await Promise.all([
    apiGet('/v1/recommendations/keywords?limit=100', []),
    apiGet('/v1/opportunities/jobs?limit=100&safe_only=true', [])
  ]);

  const insights = [];
  if (Array.isArray(recommendations) && recommendations.length > 0) {
    const top = recommendations[0];
    insights.push({
      title: 'Low Competition Signal',
      description: `"${top.keyword}" fırsat skoru ${top.opportunity_score}. Talep/sunum oranı ${top.gap_ratio}.`
    });
  }
  if (Array.isArray(opportunities) && opportunities.length > 0) {
    const topJob = opportunities[0];
    insights.push({
      title: 'Apply Now Candidate',
      description: `"${topJob.title}" güvenlik ${topJob.safety_score} ve fit ${topJob.fit_score}.`
    });
  }
  if (insights.length === 0) {
    insights.push({
      title: 'Data Pending',
      description: 'Henüz yeterli veri yok. Extension scrape döngüsünü çalıştır ve tekrar yenile.'
    });
  }
  return insights;
});

ipcMain.handle('apply-keywords', async () => {
  const keywords = await apiGet('/v1/recommendations/keywords?limit=5', []);
  return { ok: true, queued: Array.isArray(keywords) ? keywords.length : 0 };
});

ipcMain.handle('export-data', async (event, format) => {
  console.log('[IPC] Export data as:', format);
  return { ok: true, message: 'Export started' };
});

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

async function countDataFiles(dir) {
  try {
    const files = await fs.readdir(dir, { recursive: true });
    return files.filter(f => f.endsWith('.csv') || f.endsWith('.json')).length;
  } catch {
    return 0;
  }
}

// ============================================================
// EXPORTS
// ============================================================

module.exports = { app, getPaths, quit };
