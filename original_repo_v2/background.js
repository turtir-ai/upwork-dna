const STATE_KEY = "upwork_scraper_state";
const ORCHESTRATOR_API_BASE = "http://127.0.0.1:8000";
const ORCHESTRATOR_API_BASES = Array.from(
  new Set([ORCHESTRATOR_API_BASE, "http://127.0.0.1:8000", "http://localhost:8000"])
);
const ORCHESTRATOR_TIMEOUT_MS = 4000;
const ORCHESTRATOR_ERROR_LOG_INTERVAL_MS = 30000;
const MAX_API_KEYWORD_INJECTION = 5;
const API_KEYWORD_SYNC_COOLDOWN_MS = 15000;
const RUN_PROGRESS_SYNC_INTERVAL_MS = 15000;
const RUN_PROGRESS_SYNC_MIN_NEW_ITEMS = 20;
const RUN_PROGRESS_SYNC_MIN_NEW_DETAILS = 5;
const RUN_PROGRESS_SYNC_ERROR_LOG_INTERVAL_MS = 15000;
const PENDING_RUN_INGEST_KEY = "upwork_pending_run_ingest";
const runProgressSyncState = {};
let activeOrchestratorBase = ORCHESTRATOR_API_BASES[0];
let lastOrchestratorErrorLogAt = 0;
let lastApiKeywordSyncAttemptAt = 0;
let pendingRunFlushInFlight = false;

async function fetchWithTimeout(url, options = {}, timeoutMs = ORCHESTRATOR_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timeoutId);
  }
}

function getOrchestratorBaseCandidates() {
  const seen = new Set();
  const ordered = [];
  [activeOrchestratorBase, ...ORCHESTRATOR_API_BASES].forEach((base) => {
    const normalized = String(base || "").trim();
    if (!normalized || seen.has(normalized)) {
      return;
    }
    seen.add(normalized);
    ordered.push(normalized);
  });
  return ordered;
}

function logOrchestratorError(message) {
  const now = Date.now();
  if (now - lastOrchestratorErrorLogAt < ORCHESTRATOR_ERROR_LOG_INTERVAL_MS) {
    return;
  }
  lastOrchestratorErrorLogAt = now;
  console.warn(message);
}

async function requestOrchestrator(endpoint, options = {}, timeoutMs = ORCHESTRATOR_TIMEOUT_MS) {
  const bases = getOrchestratorBaseCandidates();
  let lastError = "Failed to fetch";
  let lastStatus = 0;

  for (const base of bases) {
    try {
      const response = await fetchWithTimeout(`${base}${endpoint}`, options, timeoutMs);
      if (response.ok) {
        activeOrchestratorBase = base;
        return { ok: true, response, base };
      }

      lastStatus = response.status || 0;
      if (response.status === 404 || response.status === 502 || response.status === 503) {
        continue;
      }
      return {
        ok: false,
        error: `HTTP ${response.status}`,
        status: response.status,
        response,
        base
      };
    } catch (error) {
      lastError = (error && error.message) || "Failed to fetch";
    }
  }

  if (lastStatus > 0) {
    return { ok: false, error: `HTTP ${lastStatus}`, status: lastStatus };
  }

  const method = (options && options.method ? options.method : "GET").toUpperCase();
  logOrchestratorError(`[API] ${method} ${endpoint} failed: ${lastError}`);
  return { ok: false, error: lastError };
}

function storageGet(key) {
  return new Promise((resolve) => {
    chrome.storage.local.get(key, (result) => resolve(result[key]));
  });
}

function storageSet(data) {
  return new Promise((resolve) => {
    chrome.storage.local.set(data, () => resolve());
  });
}

function nowIso() {
  return new Date().toISOString();
}

function normalizeTarget(target) {
  if (!target) {
    return "";
  }
  return target.toLowerCase();
}

function sanitizeFilename(value) {
  return value.replace(/[^a-zA-Z0-9._-]+/g, "_").replace(/_+/g, "_");
}

function extractJobKey(value) {
  if (!value) {
    return "";
  }
  const match = value.match(/~[A-Za-z0-9]+/);
  return match ? match[0] : "";
}

function extractProjectId(value) {
  if (!value) {
    return "";
  }
  const match = value.match(/-(\d{6,})$/);
  if (match) {
    return match[1];
  }
  const alt = value.match(/catalog\/(\d{6,})/);
  return alt ? alt[1] : "";
}

function normalizeUrl(value) {
  if (!value) {
    return "";
  }
  try {
    const url = new URL(value);
    return `${url.origin}${url.pathname}`;
  } catch (error) {
    return value;
  }
}

function buildSearchUrl(target, keyword, pageIndex) {
  const encoded = encodeURIComponent(keyword);
  const page = pageIndex && pageIndex > 1 ? `&page=${pageIndex}` : "";

  if (target === "jobs") {
    return `https://www.upwork.com/nx/search/jobs/?nbs=1&q=${encoded}${page}`;
  }
  if (target === "talent") {
    return `https://www.upwork.com/nx/search/talent?q=${encoded}${page}`;
  }
  if (target === "projects") {
    return `https://www.upwork.com/services/search?q=${encoded}${page}`;
  }

  return "https://www.upwork.com/";
}

function buildDetailQueue(run, target) {
  const keyword = (run && run.keyword) || "";
  const seen = new Set();
  const queue = [];

  if (target === "jobs") {
    const jobs = (run && run.data && run.data.jobs) || [];
    jobs.forEach((job) => {
      if (!job) {
        return;
      }
      const jobUrl = job.url || "";
      const jobKey = job.job_key || extractJobKey(jobUrl);
      const pageUrl =
        job.page_url || buildSearchUrl("jobs", keyword, job.page_index || 1);
      const detailUrl = pageUrl || jobUrl;
      const dedupeKey = jobKey || normalizeUrl(jobUrl) || normalizeUrl(detailUrl);
      if (!dedupeKey) {
        return;
      }
      if (seen.has(dedupeKey)) {
        return;
      }
      seen.add(dedupeKey);
      queue.push({
        target: "jobs",
        url: detailUrl,
        jobKey,
        jobUrl,
        pageUrl: detailUrl
      });
    });
  } else if (target === "talent") {
    const talent = (run && run.data && run.data.talent) || [];
    talent.forEach((profile) => {
      if (!profile) {
        return;
      }
      const profileUrl = profile.url || "";
      const profileKey = profile.profile_key || extractJobKey(profileUrl);
      const pageUrl =
        profile.page_url ||
        buildSearchUrl("talent", keyword, profile.page_index || 1);
      const detailUrl = pageUrl || profileUrl;
      const dedupeKey =
        profileKey || normalizeUrl(profileUrl) || normalizeUrl(detailUrl);
      if (!dedupeKey) {
        return;
      }
      if (seen.has(dedupeKey)) {
        return;
      }
      seen.add(dedupeKey);
      queue.push({
        target: "talent",
        url: detailUrl,
        profileKey,
        profileUrl,
        pageUrl: detailUrl
      });
    });
  } else if (target === "projects") {
    const projects = (run && run.data && run.data.projects) || [];
    projects.forEach((project) => {
      if (!project) {
        return;
      }
      const projectUrl = project.url || "";
      if (!projectUrl) {
        return;
      }
      const projectId = project.project_id || extractProjectId(projectUrl);
      const pageUrl =
        project.page_url ||
        buildSearchUrl("projects", keyword, project.page_index || 1);
      const detailUrl = projectUrl;
      const dedupeKey =
        projectId || normalizeUrl(projectUrl) || normalizeUrl(detailUrl);
      if (!dedupeKey) {
        return;
      }
      if (seen.has(dedupeKey)) {
        return;
      }
      seen.add(dedupeKey);
      queue.push({
        target: "projects",
        url: detailUrl,
        projectId,
        projectUrl,
        pageUrl
      });
    });
  }

  return queue;
}

async function getState() {
  const state = await storageGet(STATE_KEY);
  return (
    state || {
      runs: {},
      active: null,
      lastRunId: null
    }
  );
}

async function setState(state) {
  await storageSet({ [STATE_KEY]: state });
}

function buildSummary(run) {
  if (!run) {
    return null;
  }
  return {
    runId: run.id,
    keyword: run.keyword,
    status: run.status,
    startedAt: run.startedAt,
    finishedAt: run.finishedAt || "",
    counts: {
      jobs: (run.data.jobs || []).length,
      talent: (run.data.talent || []).length,
      projects: (run.data.projects || []).length
    }
  };
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function randomDelay(minMs, maxMs) {
  const min = Math.max(0, Number(minMs) || 0);
  const max = Math.max(min, Number(maxMs) || min);
  return Math.floor(min + Math.random() * (max - min + 1));
}

async function requestProjectDetailFetch(state, detailItem) {
  if (!state.active || state.active.tabId === null || state.active.tabId === undefined) {
    return false;
  }
  if (!detailItem) {
    return false;
  }

  const payload = {
    type: "FETCH_PROJECT_DETAIL",
    runId: state.active.runId,
    projectId: detailItem.projectId || "",
    projectUrl: detailItem.projectUrl || detailItem.url || "",
    pageUrl: detailItem.pageUrl || detailItem.url || ""
  };

  return new Promise((resolve) => {
    let settled = false;
    const timeoutId = setTimeout(() => {
      if (settled) {
        return;
      }
      settled = true;
      resolve(false);
    }, 3000);

    chrome.tabs.sendMessage(state.active.tabId, payload, (response) => {
      if (settled) {
        return;
      }
      clearTimeout(timeoutId);
      settled = true;
      if (chrome.runtime.lastError) {
        resolve(false);
        return;
      }
      resolve(Boolean(response && response.ok));
    });
  });
}

const DETAIL_NAV_DELAY_RANGE = { min: 5000, max: 12000 };
const DETAIL_START_DELAY_RANGE = { min: 3000, max: 6000 };
const DETAIL_ERROR_DELAY_RANGE = { min: 10000, max: 20000 };

// Session management - anti-ban
const PAGE_NAV_DELAY_RANGE = { min: 4000, max: 8000 };
const SESSION_MAX_PAGES = 50;
const SESSION_COOLDOWN_RANGE = { min: 300000, max: 600000 };
let sessionPageCount = 0;

async function startRun(config) {
  const state = await getState();

  if (state.active) {
    const previous = state.runs[state.active.runId];
    if (previous) {
      previous.status = "stopped";
      previous.finishedAt = nowIso();
    }
    state.active = null;
  }

  const keyword = (config.keyword || "").trim();
  const targets = (config.targets || []).map(normalizeTarget).filter(Boolean);
  const maxPages = Number(config.maxPages) || 0;

  if (!keyword || targets.length === 0) {
    return { ok: false, error: "Missing keyword or targets." };
  }

  const runId = `run_${Date.now()}`;
  const run = {
    id: runId,
    keyword,
    targets,
    startedAt: nowIso(),
    finishedAt: null,
    status: "running",
    data: {
      jobs: [],
      talent: [],
      projects: []
    }
  };

  state.runs[runId] = run;
  state.lastRunId = runId;
  state.active = {
    runId,
    targets,
    targetIndex: 0,
    pageIndex: 1,
    maxPages,
    keyword,
    tabId: null,
    blocked: false,
    blockedUrl: "",
    phase: "list",
    detailQueue: [],
    detailIndex: 0,
    detailTotal: 0,
    detailTarget: null,
    detailMode: null,
    queueKeywordId: config.queueKeywordId || null
  };

  await setState(state);

  const url = buildSearchUrl(targets[0], keyword, 1);
  const tab = await new Promise((resolve) => {
    chrome.tabs.create({ url, active: true }, resolve);
  });

  const newState = await getState();
  if (newState.active && tab && tab.id !== undefined) {
    newState.active.tabId = tab.id;
    await setState(newState);
  }

  return { ok: true, runId };
}

async function stopRun() {
  const state = await getState();
  if (!state.active) {
    return { ok: false, error: "No active run." };
  }

  const run = state.runs[state.active.runId];
  if (run) {
    run.status = "stopped";
    run.finishedAt = nowIso();
  }

  state.active = null;
  await setState(state);
  return { ok: true };
}

async function handlePageReady(message, sender) {
  const state = await getState();
  if (!state.active || !sender.tab) {
    return { action: "IGNORE" };
  }

  if (state.active.tabId !== sender.tab.id) {
    return { action: "IGNORE" };
  }

  const phase = state.active.phase || "list";
  const pageType = normalizeTarget(message.pageType);

  if (phase === "details") {
    const detailTarget = normalizeTarget(state.active.detailTarget || "jobs");
    if (detailTarget === "projects" && state.active.detailMode === "fetch") {
      return { action: "IGNORE" };
    }
    const allowedTypes = {
      jobs: ["job_detail", "jobs"],
      talent: ["talent_detail", "talent"],
      projects: ["project_detail", "projects"]
    };
    if (!allowedTypes[detailTarget] || !allowedTypes[detailTarget].includes(pageType)) {
      return { action: "IGNORE" };
    }
    const currentDetail =
      (state.active.detailQueue || [])[state.active.detailIndex] || null;
    return {
      action: "SCRAPE_DETAIL",
      runId: state.active.runId,
      target: detailTarget,
      jobKey: currentDetail ? currentDetail.jobKey || "" : "",
      jobUrl: currentDetail ? currentDetail.jobUrl || "" : "",
      profileKey: currentDetail ? currentDetail.profileKey || "" : "",
      profileUrl: currentDetail ? currentDetail.profileUrl || "" : "",
      projectId: currentDetail ? currentDetail.projectId || "" : "",
      projectUrl: currentDetail ? currentDetail.projectUrl || "" : "",
      pageUrl: currentDetail ? currentDetail.pageUrl || currentDetail.url || "" : "",
      detailIndex: state.active.detailIndex || 0,
      detailTotal: state.active.detailTotal || 0
    };
  }

  const currentTarget = state.active.targets[state.active.targetIndex];
  if (currentTarget !== pageType) {
    return { action: "IGNORE" };
  }

  return {
    action: "SCRAPE",
    runId: state.active.runId,
    target: currentTarget,
    pageIndex: state.active.pageIndex,
    maxPages: state.active.maxPages
  };
}

async function moveToNextTarget(state) {
  state.active.targetIndex += 1;
  state.active.pageIndex = 1;
  state.active.blocked = false;
  state.active.blockedUrl = "";
  state.active.phase = "list";
  state.active.detailQueue = [];
  state.active.detailIndex = 0;
  state.active.detailTotal = 0;
  state.active.detailTarget = null;
  state.active.detailMode = null;

  if (state.active.targetIndex >= state.active.targets.length) {
    const run = state.runs[state.active.runId];
    if (run) {
      run.status = "complete";
      run.finishedAt = nowIso();
    }
    state.active = null;
    await setState(state);
    return;
  }

  const nextTarget = state.active.targets[state.active.targetIndex];
  const url = buildSearchUrl(nextTarget, state.active.keyword, 1);
  await new Promise((resolve) => {
    chrome.tabs.update(state.active.tabId, { url }, () => resolve());
  });

  await setState(state);
}

async function startDetailPhase(state, run, target) {
  const queue = buildDetailQueue(run, target);
  if (!queue.length) {
    return false;
  }

  state.active.phase = "details";
  state.active.detailQueue = queue;
  state.active.detailIndex = 0;
  state.active.detailTotal = queue.length;
  state.active.detailTarget = target;
  state.active.detailMode = null;
  state.active.blocked = false;
  state.active.blockedUrl = "";

  await setState(state);

  if (target === "projects") {
    const sent = await requestProjectDetailFetch(state, queue[0]);
    if (sent) {
      state.active.detailMode = "fetch";
      await setState(state);
      return true;
    }
  }

  await delay(randomDelay(DETAIL_START_DELAY_RANGE.min, DETAIL_START_DELAY_RANGE.max));
  await new Promise((resolve) => {
    chrome.tabs.update(state.active.tabId, { url: queue[0].url }, () => resolve());
  });

  return true;
}

function findItemsForDetail(run, target, detailKey, detailUrl, detailId) {
  const items = (run && run.data && run.data[target]) || [];
  const normalizedUrl = normalizeUrl(detailUrl);
  return items.filter((item) => {
    if (!item) {
      return false;
    }
    if (target === "jobs") {
      if (detailKey && item.job_key && item.job_key === detailKey) {
        return true;
      }
      if (normalizedUrl && item.url && normalizeUrl(item.url) === normalizedUrl) {
        return true;
      }
      return false;
    }
    if (target === "talent") {
      if (detailKey && item.profile_key && item.profile_key === detailKey) {
        return true;
      }
      if (normalizedUrl && item.url && normalizeUrl(item.url) === normalizedUrl) {
        return true;
      }
      return false;
    }
    if (target === "projects") {
      if (detailId && item.project_id && item.project_id === detailId) {
        return true;
      }
      if (normalizedUrl && item.url && normalizeUrl(item.url) === normalizedUrl) {
        return true;
      }
      return false;
    }
    return false;
  });
}

function applyDetailToItems(items, detail, error) {
  items.forEach((item) => {
    if (!item || !detail) {
      return;
    }
    Object.assign(item, detail);
    if (error) {
      item.detail_status = "error";
      item.detail_error = error;
    } else {
      item.detail_status = "ok";
      item.detail_error = "";
    }
    item.detail_scraped_at = nowIso();
  });
}

async function handlePageResults(message) {
  const state = await getState();
  if (!state.active) {
    return { ok: false, error: "No active run." };
  }

  if (state.active.runId !== message.runId) {
    return { ok: false, error: "Run mismatch." };
  }

  const run = state.runs[state.active.runId];
  if (!run) {
    return { ok: false, error: "Run not found." };
  }

  const target = normalizeTarget(message.target);
  const activeTarget = state.active.targets[state.active.targetIndex];
  if (activeTarget !== target) {
    return { ok: false, error: "Target mismatch." };
  }
  if (!run.data[target]) {
    run.data[target] = [];
  }

  const items = Array.isArray(message.items) ? message.items : [];
  run.data[target] = run.data[target].concat(items);
  void maybeSyncRunProgressToApi(state.active.runId, run, {
    reason: "page_results"
  });

  const hasNext = Boolean(message.hasNext);
  const nextUrl = message.nextUrl || "";
  const maxPages = state.active.maxPages || 0;
  const phase = state.active.phase || "list";

  state.active.blocked = false;
  state.active.blockedUrl = "";

  if (hasNext && nextUrl) {
    state.active.pageIndex += 1;
    if (maxPages > 0 && state.active.pageIndex > maxPages) {
      if (phase === "list") {
        const started = await startDetailPhase(state, run, activeTarget);
        if (started) {
          return { ok: true, done: false };
        }
      }
      await setState(state);
      await moveToNextTarget(state);
      return { ok: true, done: false };
    }

    await setState(state);

    // Anti-ban: random delay between list pages + session cooldown
    sessionPageCount++;
    if (sessionPageCount >= SESSION_MAX_PAGES) {
      const cooldown = randomDelay(SESSION_COOLDOWN_RANGE.min, SESSION_COOLDOWN_RANGE.max);
      console.log(`[AntiBot] Session cooldown: ${Math.round(cooldown/1000)}s after ${sessionPageCount} pages`);
      await delay(cooldown);
      sessionPageCount = 0;
    } else {
      await delay(randomDelay(PAGE_NAV_DELAY_RANGE.min, PAGE_NAV_DELAY_RANGE.max));
    }
    await new Promise((resolve) => {
      chrome.tabs.update(state.active.tabId, { url: nextUrl }, () => resolve());
    });
    return { ok: true, done: false };
  }

  if (phase === "list") {
    const started = await startDetailPhase(state, run, activeTarget);
    if (started) {
      return { ok: true, done: false };
    }
  }

  await setState(state);
  await moveToNextTarget(state);
  return { ok: true, done: true };
}

async function handleDetailResults(message) {
  const state = await getState();
  if (!state.active) {
    return { ok: false, error: "No active run." };
  }

  if (state.active.runId !== message.runId) {
    return { ok: false, error: "Run mismatch." };
  }

  const run = state.runs[state.active.runId];
  if (!run) {
    return { ok: false, error: "Run not found." };
  }

  const detailTarget = normalizeTarget(message.target || state.active.detailTarget || "jobs");
  const detail = message.detail || {};
  const error = message.error || "";

  let detailKey = "";
  let detailUrl = "";
  let detailId = "";

  if (detailTarget === "jobs") {
    detailUrl = message.jobUrl || detail.detail_job_url || "";
    detailKey = message.jobKey || detail.detail_job_key || extractJobKey(detailUrl);
    if (detailUrl) {
      detail.detail_job_url = detailUrl;
    }
    if (detailKey) {
      detail.detail_job_key = detailKey;
    }
  } else if (detailTarget === "talent") {
    detailUrl = message.profileUrl || detail.detail_profile_url || "";
    detailKey = message.profileKey || detail.detail_profile_key || extractJobKey(detailUrl);
    if (detailUrl) {
      detail.detail_profile_url = detailUrl;
    }
    if (detailKey) {
      detail.detail_profile_key = detailKey;
    }
  } else if (detailTarget === "projects") {
    detailUrl = message.projectUrl || detail.detail_project_url || "";
    detailId = message.projectId || detail.detail_project_id || extractProjectId(detailUrl);
    if (detailUrl) {
      detail.detail_project_url = detailUrl;
    }
    if (detailId) {
      detail.detail_project_id = detailId;
    }
  } else {
    return { ok: false, error: "Unsupported detail target." };
  }

  const matches = findItemsForDetail(run, detailTarget, detailKey, detailUrl, detailId);
  if (matches.length) {
    applyDetailToItems(matches, detail, error);
  } else {
    const detailsKey = `${detailTarget}_details`;
    if (!run.data[detailsKey]) {
      run.data[detailsKey] = [];
    }
    run.data[detailsKey].push({
      ...detail,
      detail_status: error ? "error" : "ok",
      detail_error: error,
      detail_scraped_at: nowIso()
    });
  }

  state.active.blocked = false;
  state.active.blockedUrl = "";
  state.active.detailIndex = (state.active.detailIndex || 0) + 1;
  void maybeSyncRunProgressToApi(state.active.runId, run, {
    reason: "detail_results"
  });

  const queue = state.active.detailQueue || [];
  if (state.active.detailIndex < queue.length) {
    const next = queue[state.active.detailIndex];
    await setState(state);
    const delayRange = error ? DETAIL_ERROR_DELAY_RANGE : DETAIL_NAV_DELAY_RANGE;
    await delay(randomDelay(delayRange.min, delayRange.max));
    if (detailTarget === "projects" && state.active.detailMode === "fetch") {
      const sent = await requestProjectDetailFetch(state, next);
      if (sent) {
        return { ok: true, done: false };
      }
      state.active.detailMode = null;
      await setState(state);
    }
    await new Promise((resolve) => {
      chrome.tabs.update(state.active.tabId, { url: next.url }, () => resolve());
    });
    return { ok: true, done: false };
  }

  await setState(state);
  await moveToNextTarget(state);
  return { ok: true, done: true };
}

async function handlePageBlocked(message) {
  const state = await getState();
  if (!state.active) {
    return { ok: false };
  }

  state.active.blocked = true;
  state.active.blockedUrl = message.pageUrl || "";
  await setState(state);
  return { ok: true };
}

async function handleSessionExpired(message) {
  const state = await getState();
  if (!state.active) {
    return { ok: false };
  }

  console.warn("[UPWORK-DNA] SESSION_EXPIRED detected:", message.reason, "url:", message.pageUrl);
  state.active.blocked = true;
  state.active.blockedUrl = message.pageUrl || "";
  state.active.sessionExpired = true;
  state.active.sessionExpiredReason = message.reason || "logged_out";
  await setState(state);

  // Close the tab and stop the run to avoid further detection
  if (state.active.tabId) {
    try { chrome.tabs.remove(state.active.tabId); } catch (e) {}
  }

  return { ok: true, action: "stopped", reason: "session_expired" };
}

async function handleRateLimited(message) {
  const state = await getState();
  if (!state.active) {
    return { ok: false };
  }

  console.warn("[UPWORK-DNA] RATE_LIMITED detected, url:", message.pageUrl);
  state.active.blocked = true;
  state.active.blockedUrl = message.pageUrl || "";
  state.active.rateLimited = true;
  state.active.rateLimitedAt = Date.now();
  await setState(state);

  // Close the tab — auto-resume after 3 minutes
  if (state.active.tabId) {
    try { chrome.tabs.remove(state.active.tabId); } catch (e) {}
  }

  // Auto-resume after 3 minutes
  setTimeout(async () => {
    const st = await getState();
    if (st.active && st.active.rateLimited) {
      console.log("[UPWORK-DNA] Auto-resuming after rate-limit cooldown...");
      st.active.blocked = false;
      st.active.rateLimited = false;
      delete st.active.rateLimitedAt;
      await setState(st);
      // Re-trigger next page
      await processQueue();
    }
  }, 3 * 60 * 1000);

  return { ok: true, action: "paused", reason: "rate_limited" };
}

async function handleGetStatus() {
  const state = await getState();
  const activeRun = state.active ? state.runs[state.active.runId] : null;
  const latestRun = state.lastRunId ? state.runs[state.lastRunId] : null;

  return {
    active: state.active
      ? {
          runId: state.active.runId,
          target: state.active.targets[state.active.targetIndex],
          pageIndex: state.active.pageIndex,
          maxPages: state.active.maxPages,
          phase: state.active.phase || "list",
          detailIndex: state.active.detailIndex || 0,
          detailTotal: state.active.detailTotal || 0,
          blocked: state.active.blocked,
          blockedUrl: state.active.blockedUrl,
          sessionExpired: state.active.sessionExpired || false,
          sessionExpiredReason: state.active.sessionExpiredReason || "",
          rateLimited: state.active.rateLimited || false
        }
      : null,
    activeSummary: buildSummary(activeRun),
    latestSummary: buildSummary(latestRun)
  };
}

function normalizeValue(value) {
  if (Array.isArray(value)) {
    return value.join("; ");
  }
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
}

function toCsv(rows) {
  if (!rows || rows.length === 0) {
    return "";
  }

  const keys = Array.from(
    rows.reduce((acc, row) => {
      Object.keys(row || {}).forEach((key) => acc.add(key));
      return acc;
    }, new Set())
  );

  const lines = [keys.join(",")];
  rows.forEach((row) => {
    const values = keys.map((key) => {
      const value = normalizeValue(row[key]);
      const escaped = value.replace(/"/g, '""');
      if (escaped.includes(",") || escaped.includes("\n")) {
        return `"${escaped}"`;
      }
      return escaped;
    });
    lines.push(values.join(","));
  });

  return lines.join("\n");
}

function tryDownload(url, filename) {
  return new Promise((resolve) => {
    chrome.downloads.download(
      {
        url,
        filename,
        saveAs: false
      },
      (downloadId) => {
        if (chrome.runtime.lastError || !downloadId) {
          resolve({
            ok: false,
            error:
              (chrome.runtime.lastError && chrome.runtime.lastError.message) ||
              "Download failed."
          });
          return;
        }
        resolve({ ok: true, downloadId });
      }
    );
  });
}

async function downloadFile(filename, content, mimeType) {
  const dataUrl = `data:${mimeType};charset=utf-8,${encodeURIComponent(content)}`;
  const dataResult = await tryDownload(dataUrl, filename);
  if (dataResult.ok) {
    return dataResult;
  }

  try {
    const blob = new Blob([content], { type: mimeType });
    const blobUrl = URL.createObjectURL(blob);
    const blobResult = await tryDownload(blobUrl, filename);
    setTimeout(() => URL.revokeObjectURL(blobUrl), 4000);
    if (blobResult.ok) {
      return blobResult;
    }
    return {
      ok: false,
      error: `${dataResult.error} | ${blobResult.error}`
    };
  } catch (error) {
    return { ok: false, error: error.message || "Download failed." };
  }
}

async function handleExportJson(runId) {
  const state = await getState();
  const selectedRunId = runId || state.lastRunId;
  const run = state.runs[selectedRunId];

  if (!run) {
    return { ok: false, error: "No run data." };
  }

  const safeKeyword = sanitizeFilename(run.keyword || "keyword");
  const filename = `upwork_scrape_${safeKeyword}_${selectedRunId}.json`;
  const content = JSON.stringify(run, null, 2);

  const result = await downloadFile(filename, content, "application/json");
  if (!result.ok) {
    return result;
  }
  return { ok: true, downloadId: result.downloadId };
}

async function handleExportCsv(runId) {
  const state = await getState();
  const selectedRunId = runId || state.lastRunId;
  const run = state.runs[selectedRunId];

  if (!run) {
    return { ok: false, error: "No run data." };
  }

  const safeKeyword = sanitizeFilename(run.keyword || "keyword");
  const datasets = [
    { key: "jobs", rows: run.data.jobs || [] },
    { key: "talent", rows: run.data.talent || [] },
    { key: "projects", rows: run.data.projects || [] }
  ];

  const results = [];
  for (const dataset of datasets) {
    if (!dataset.rows.length) {
      continue;
    }
    const csv = toCsv(dataset.rows);
    const filename = `upwork_${dataset.key}_${safeKeyword}_${selectedRunId}.csv`;
    const result = await downloadFile(filename, csv, "text/csv");
    results.push({ key: dataset.key, result });
  }

  if (!results.length) {
    return { ok: false, error: "No data to export." };
  }

  const failed = results.find((entry) => !entry.result.ok);
  if (failed) {
    return {
      ok: false,
      error: `Download failed for ${failed.key}: ${failed.result.error}`
    };
  }

  return { ok: true };
}

async function handleClearData() {
  const state = await getState();
  state.runs = {};
  state.active = null;
  state.lastRunId = null;
  await setState(state);
  return { ok: true };
}

// ===== QUEUE MANAGER v3.0 - PRIORITY QUEUE =====
const QUEUE_KEY = "upwork_scraper_queue";
const QUEUE_STATS_KEY = "upwork_scraper_queue_stats";

// Priority level system
const PRIORITY_LEVELS = {
  CRITICAL: { score: 100, label: 'Premium Opportunity' },
  HIGH: { score: 75, label: 'High Value' },
  NORMAL: { score: 50, label: 'Standard' },
  LOW: { score: 25, label: 'Exploratory' }
};

// Retry configuration with exponential backoff
const RETRY_CONFIG = {
  maxRetries: 3,
  baseDelayMs: 5000,  // Base delay for exponential backoff
  maxDelayMs: 300000, // Maximum 5 minutes
  jitterRange: 0.2    // 20% jitter for randomness
};

// Calculate delay with exponential backoff and jitter
function calculateRetryDelay(retryCount) {
  const exponentialDelay = Math.min(
    RETRY_CONFIG.baseDelayMs * Math.pow(2, retryCount),
    RETRY_CONFIG.maxDelayMs
  );

  // Add jitter: ±20% randomness
  const jitter = exponentialDelay * RETRY_CONFIG.jitterRange * (Math.random() * 2 - 1);
  return Math.max(0, Math.floor(exponentialDelay + jitter));
}

// Calculate priority score for keyword sorting
function calculatePriorityScore(keyword) {
  const priority = PRIORITY_LEVELS[keyword.priority] || PRIORITY_LEVELS.NORMAL;
  let score = priority.score;

  // Add estimated value bonus (0-20 points)
  if (keyword.estimatedValue) {
    const valueBonus = Math.min(20, keyword.estimatedValue / 100);
    score += valueBonus;
  }

  // Add time-based priority (older keywords get slight boost)
  if (keyword.addedAt) {
    const ageInHours = (Date.now() - new Date(keyword.addedAt).getTime()) / (1000 * 60 * 60);
    const ageBonus = Math.min(10, ageInHours * 0.5);
    score += ageBonus;
  }

  // Reduce score for each retry to prioritize fresh items
  if (keyword.retryCount) {
    score -= keyword.retryCount * 2;
  }

  return score;
}

// Sort keywords by priority score
function sortKeywordsByPriority(keywords) {
  return [...keywords].sort((a, b) => {
    const scoreA = calculatePriorityScore(a);
    const scoreB = calculatePriorityScore(b);

    // Primary sort: priority score (descending)
    if (scoreB !== scoreA) {
      return scoreB - scoreA;
    }

    // Secondary sort: added time (ascending - older first)
    const timeA = new Date(a.addedAt || 0).getTime();
    const timeB = new Date(b.addedAt || 0).getTime();
    return timeA - timeB;
  });
}

async function getQueue() {
  const q = await storageGet(QUEUE_KEY);
  const s = await storageGet(QUEUE_STATS_KEY);
  const queue = q || {
    keywords: [],
    currentIndex: 0,
    isRunning: false,
    isPaused: false,
    settings: {
      delayBetweenKeywords: { min: 60000, max: 180000 },
      autoSave: true,
      autoExport: true,
      targets: ["jobs", "talent", "projects"],
      maxPages: 7
    },
    stats: {
      totalProcessed: 0,
      dailyProcessed: 0,
      lastResetDate: null,
      totalItems: { jobs: 0, talent: 0, projects: 0 }
    }
  };
  queue.stats = { ...queue.stats, ...s };
  return queue;
}

async function saveQueue(queue) {
  const statsToSave = {
    lastResetDate: queue.stats.lastResetDate,
    dailyProcessed: queue.stats.dailyProcessed
  };
  await storageSet({ [QUEUE_KEY]: queue, [QUEUE_STATS_KEY]: statsToSave });
  await pushQueueTelemetry(queue);
}

function summarizeQueueCounts(queue) {
  const keywords = queue && Array.isArray(queue.keywords) ? queue.keywords : [];
  return {
    total: keywords.length,
    pending: keywords.filter((k) => k.status === "pending").length,
    running: keywords.filter((k) => k.status === "running").length,
    completed: keywords.filter((k) => k.status === "completed").length,
    error: keywords.filter((k) => k.status === "error").length,
    last_cycle_at: new Date().toISOString()
  };
}

let lastQueueTelemetrySentAt = 0;

async function pushQueueTelemetry(queue, force = false) {
  const now = Date.now();
  if (!force && now - lastQueueTelemetrySentAt < 3000) {
    return;
  }

  try {
    const payload = summarizeQueueCounts(queue);
    const apiResult = await requestOrchestrator("/v1/telemetry/queue", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (apiResult.ok && apiResult.response.ok) {
      lastQueueTelemetrySentAt = now;
    }
  } catch (error) {
    // Telemetry is best-effort only; queue flow must not break.
  }
}

async function getPendingRunIngestQueue() {
  const value = await storageGet(PENDING_RUN_INGEST_KEY);
  return Array.isArray(value) ? value : [];
}

async function savePendingRunIngestQueue(queue) {
  await storageSet({ [PENDING_RUN_INGEST_KEY]: queue.slice(0, 100) });
}

async function enqueuePendingRunIngest(runId, run) {
  if (!runId || !run || !run.data) {
    return;
  }
  const queue = await getPendingRunIngestQueue();
  const index = queue.findIndex((entry) => entry && entry.runId === runId);
  const payload = {
    runId,
    run,
    queuedAt: nowIso()
  };
  if (index >= 0) {
    queue[index] = payload;
  } else {
    queue.push(payload);
  }
  await savePendingRunIngestQueue(queue);
}

async function removePendingRunIngest(runId) {
  if (!runId) {
    return;
  }
  const queue = await getPendingRunIngestQueue();
  const filtered = queue.filter((entry) => !entry || entry.runId !== runId);
  if (filtered.length !== queue.length) {
    await savePendingRunIngestQueue(filtered);
  }
}

async function syncRunResultsToApi(runId, run, options = {}) {
  if (!runId || !run || !run.data) {
    return { ok: false, error: "Missing run payload" };
  }

  const enqueueOnFailure = options.enqueueOnFailure !== false;
  try {
    const request = await requestOrchestrator(
      "/v1/ingest/run",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: runId, run })
      },
      10000
    );

    if (!request.ok) {
      if (enqueueOnFailure) {
        await enqueuePendingRunIngest(runId, run);
      }
      return { ok: false, error: request.error || "run_ingest_failed" };
    }

    const response = request.response;
    if (!response.ok) {
      if (enqueueOnFailure) {
        await enqueuePendingRunIngest(runId, run);
      }
      return { ok: false, error: `HTTP ${response.status}` };
    }

    const payload = await response.json();
    await removePendingRunIngest(runId);
    return { ok: true, payload };
  } catch (error) {
    if (enqueueOnFailure) {
      await enqueuePendingRunIngest(runId, run);
    }
    return { ok: false, error: error.message || "run_ingest_failed" };
  }
}

async function flushPendingRunIngestQueue(maxItems = 2) {
  if (pendingRunFlushInFlight) {
    return { ok: true, skipped: true, reason: "in_flight" };
  }
  pendingRunFlushInFlight = true;

  try {
    const queue = await getPendingRunIngestQueue();
    if (!queue.length) {
      return { ok: true, flushed: 0, pending: 0 };
    }

    let flushed = 0;
    let keep = [];

    for (let i = 0; i < queue.length; i += 1) {
      const entry = queue[i];
      if (!entry || !entry.runId || !entry.run || !entry.run.data) {
        continue;
      }
      if (flushed >= maxItems) {
        keep = keep.concat(queue.slice(i));
        break;
      }

      const result = await syncRunResultsToApi(entry.runId, entry.run, {
        enqueueOnFailure: false
      });

      if (result.ok) {
        flushed += 1;
        continue;
      }

      keep = queue.slice(i);
      break;
    }

    await savePendingRunIngestQueue(keep);
    return { ok: true, flushed, pending: keep.length };
  } finally {
    pendingRunFlushInFlight = false;
  }
}

function buildRunProgressSnapshot(run) {
  const jobs = Array.isArray(run?.data?.jobs) ? run.data.jobs : [];
  const talent = Array.isArray(run?.data?.talent) ? run.data.talent : [];
  const projects = Array.isArray(run?.data?.projects) ? run.data.projects : [];

  const countDetailed = (rows) =>
    rows.reduce((sum, row) => sum + (row && row.detail_status ? 1 : 0), 0);

  return {
    listItems: jobs.length + talent.length + projects.length,
    detailItems: countDetailed(jobs) + countDetailed(talent) + countDetailed(projects)
  };
}

function shouldSyncRunProgress(runId, snapshot, force = false) {
  if (force) {
    return true;
  }

  const tracker = runProgressSyncState[runId];
  if (!tracker) {
    return snapshot.listItems > 0 || snapshot.detailItems > 0;
  }
  if (tracker.inFlight) {
    return false;
  }

  const deltaList = snapshot.listItems - (tracker.listItems || 0);
  const deltaDetails = snapshot.detailItems - (tracker.detailItems || 0);
  if (deltaList <= 0 && deltaDetails <= 0) {
    return false;
  }
  if (deltaList >= RUN_PROGRESS_SYNC_MIN_NEW_ITEMS) {
    return true;
  }
  if (deltaDetails >= RUN_PROGRESS_SYNC_MIN_NEW_DETAILS) {
    return true;
  }

  const lastAt = tracker.lastAt || 0;
  return Date.now() - lastAt >= RUN_PROGRESS_SYNC_INTERVAL_MS;
}

async function maybeSyncRunProgressToApi(runId, run, options = {}) {
  if (!runId || !run || !run.data) {
    return { ok: false, skipped: true, error: "Missing run payload" };
  }

  const force = Boolean(options.force);
  const reason = options.reason || "progress";
  const snapshot = buildRunProgressSnapshot(run);

  if (!shouldSyncRunProgress(runId, snapshot, force)) {
    return { ok: true, skipped: true, reason: "throttled" };
  }

  const tracker = runProgressSyncState[runId] || {};
  if (tracker.inFlight && !force) {
    return { ok: true, skipped: true, reason: "in_flight" };
  }

  runProgressSyncState[runId] = {
    ...tracker,
    inFlight: true
  };

  const response = await syncRunResultsToApi(runId, run, {
    enqueueOnFailure: false
  });
  const now = Date.now();
  const current = runProgressSyncState[runId] || {};

  if (response.ok) {
    runProgressSyncState[runId] = {
      ...current,
      inFlight: false,
      listItems: snapshot.listItems,
      detailItems: snapshot.detailItems,
      lastAt: now,
      lastReason: reason,
      lastError: ""
    };
    return response;
  }

  const shouldLogError =
    !current.lastErrorAt ||
    now - current.lastErrorAt >= RUN_PROGRESS_SYNC_ERROR_LOG_INTERVAL_MS;

  runProgressSyncState[runId] = {
    ...current,
    inFlight: false,
    lastError: response.error || "run_progress_sync_failed",
    lastErrorAt: now
  };

  if (shouldLogError) {
    console.warn(`[Ingest] Progress sync failed (${reason}): ${response.error}`);
  }
  return response;
}

async function handleQueueAdd(message) {
  const queue = await getQueue();
  const keywords = message.keywords || [];
  const options = message.options || {};
  const now = new Date().toISOString();

  keywords.forEach((kw, index) => {
    const keyword = typeof kw === "string" ? kw.trim() : kw.keyword || "";
    if (!keyword) return;
    if (queue.keywords.find(k => k.keyword.toLowerCase() === keyword.toLowerCase())) return;

    const priority = options.priority || (typeof kw === 'object' ? kw.priority : 'NORMAL');
    const normalizedPriority = Object.keys(PRIORITY_LEVELS).includes(priority) ? priority : 'NORMAL';

    queue.keywords.push({
      id: `kw_${Date.now()}_${index}`,
      keyword: keyword,
      targets: options.targets || (typeof kw === 'object' ? kw.targets : null) || queue.settings.targets,
      maxPages: options.maxPages ?? (typeof kw === 'object' ? kw.maxPages : null) ?? queue.settings.maxPages,
      status: "pending",
      addedAt: now,
      startedAt: null,
      completedAt: null,
      runId: null,
      results: { jobs: 0, talent: 0, projects: 0 },
      // v3.0 Enhanced fields
      priority: normalizedPriority,
      estimatedValue: options.estimatedValue || (typeof kw === 'object' ? kw.estimatedValue : 0) || 0,
      dependencies: options.dependencies || (typeof kw === 'object' ? kw.dependencies : []) || [],
      retryCount: 0,
      lastRetryAt: null
    });
  });

  await saveQueue(queue);

  // Auto-start queue processor
  await startQueueProcessor();

  return { ok: true, summary: await getQueueSummary(queue) };
}

async function getQueueSummary(queue) {
  return {
    total: queue.keywords.length,
    pending: queue.keywords.filter(k => k.status === "pending").length,
    running: queue.keywords.filter(k => k.status === "running").length,
    completed: queue.keywords.filter(k => k.status === "completed").length,
    error: queue.keywords.filter(k => k.status === "error").length,
    isRunning: queue.isRunning,
    isPaused: queue.isPaused,
    stats: queue.stats,
    keywords: queue.keywords.map(k => ({
      id: k.id,
      keyword: k.keyword,
      status: k.status,
      priority: k.priority,
      estimatedValue: k.estimatedValue,
      retryCount: k.retryCount,
      priorityScore: calculatePriorityScore(k),
      results: k.results
    }))
  };
}

async function handleQueueGetStatus() {
  const queue = await getQueue();
  return { ok: true, summary: await getQueueSummary(queue) };
}

async function handleQueueClear() {
  const queue = {
    keywords: [],
    currentIndex: 0,
    isRunning: false,
    isPaused: false,
    settings: {
      delayBetweenKeywords: { min: 60000, max: 180000 },
      autoSave: true,
      autoExport: true,
      targets: ["jobs", "talent", "projects"],
      maxPages: 7,
      defaultPriority: "NORMAL"
    },
    stats: {
      totalProcessed: 0,
      dailyProcessed: 0,
      lastResetDate: new Date().toDateString(),
      totalItems: { jobs: 0, talent: 0, projects: 0 }
    }
  };
  await saveQueue(queue);
  await stopRun();
  return { ok: true, summary: await getQueueSummary(queue) };
}

// ===== QUEUE MANAGEMENT API =====

// Update keyword priority
async function handleQueueUpdatePriority(message) {
  const queue = await getQueue();
  const { keywordId, priority } = message;

  if (!keywordId || !priority) {
    return { ok: false, error: "Missing keywordId or priority" };
  }

  if (!Object.keys(PRIORITY_LEVELS).includes(priority)) {
    return { ok: false, error: `Invalid priority. Use: ${Object.keys(PRIORITY_LEVELS).join(", ")}` };
  }

  const keyword = queue.keywords.find(k => k.id === keywordId);
  if (!keyword) {
    return { ok: false, error: "Keyword not found" };
  }

  keyword.priority = priority;
  await saveQueue(queue);

  return { ok: true, summary: await getQueueSummary(queue) };
}

// Get queue statistics
async function handleQueueGetStats() {
  const queue = await getQueue();
  const sortedKeywords = sortKeywordsByPriority(queue.keywords);

  const stats = {
    byPriority: {
      CRITICAL: queue.keywords.filter(k => k.priority === 'CRITICAL').length,
      HIGH: queue.keywords.filter(k => k.priority === 'HIGH').length,
      NORMAL: queue.keywords.filter(k => k.priority === 'NORMAL').length,
      LOW: queue.keywords.filter(k => k.priority === 'LOW').length
    },
    byStatus: {
      pending: queue.keywords.filter(k => k.status === 'pending').length,
      running: queue.keywords.filter(k => k.status === 'running').length,
      completed: queue.keywords.filter(k => k.status === 'completed').length,
      error: queue.keywords.filter(k => k.status === 'error').length
    },
    topPriorities: sortedKeywords.slice(0, 5).map(k => ({
      id: k.id,
      keyword: k.keyword,
      priority: k.priority,
      score: calculatePriorityScore(k).toFixed(1),
      status: k.status
    })),
    retryStats: {
      totalRetries: queue.keywords.reduce((sum, k) => sum + (k.retryCount || 0), 0),
      maxRetriesReached: queue.keywords.filter(k => k.retryCount >= RETRY_CONFIG.maxRetries).length
    }
  };

  return { ok: true, stats };
}

// ===== QUEUE PROCESSOR =====
let queueProcessorInterval = null;
let currentQueueKeywordId = null;

async function recoverFinishedRunWithoutActive(state) {
  if (!state || state.active) {
    return false;
  }

  const queue = await getQueue();
  const runningKeywords = queue.keywords.filter((item) => item.status === "running");
  if (!runningKeywords.length) {
    return false;
  }

  for (const runningKeyword of runningKeywords) {
    let candidateRunId = runningKeyword.runId || "";
    if (
      !candidateRunId &&
      currentQueueKeywordId &&
      runningKeyword.id === currentQueueKeywordId &&
      state.lastRunId
    ) {
      candidateRunId = state.lastRunId;
      runningKeyword.runId = candidateRunId;
      await saveQueue(queue);
    }

    if (!candidateRunId) {
      continue;
    }

    const run = state.runs[candidateRunId];
    if (!run || (run.status !== "complete" && run.status !== "stopped")) {
      continue;
    }

    console.log(`[Queue] Recovering finished run without active state: ${candidateRunId}`);
    await handleQueueRunComplete(candidateRunId, run);
    return true;
  }

  return false;
}

async function startQueueProcessor() {
  if (queueProcessorInterval) return;

  console.log("[Queue] Starting queue processor...");

  queueProcessorInterval = setInterval(async () => {
    const state = await getState();
    void flushPendingRunIngestQueue(2);

    // Eğer şu an bir run çalışıyorsa kontrol et
    if (state.active) {
      const run = state.runs[state.active.runId];
      if (run && (run.status === "complete" || run.status === "stopped")) {
        // Run bitti, queue'yu güncelle
        console.log(`[Queue] Run finished: ${state.active.runId}`);
        await handleQueueRunComplete(state.active.runId, run);
        // Hemen sonrakini baslatmak icin delay ekledik
        setTimeout(() => processNextPendingKeyword(), 3000);
      }
      return;
    }

    // Aktif run yoksa, bir sonrakini baslatmayi dene
    const recovered = await recoverFinishedRunWithoutActive(state);
    if (recovered) {
      return;
    }
    await processNextPendingKeyword();

  }, 3000);
}

async function processNextPendingKeyword() {
  const queue = await getQueue();
  const state = await getState();

  // Eğer şu an bir run çalışıyorsa bekle
  if (state.active) return;

  // Get all pending keywords and sort by priority
  const pendingKeywords = queue.keywords.filter(k => k.status === "pending");
  if (pendingKeywords.length === 0) {
    // No pending keywords - check for retryable errors
    await checkRetryableErrors(queue);
    const now = Date.now();
    if (now - lastApiKeywordSyncAttemptAt >= API_KEYWORD_SYNC_COOLDOWN_MS) {
      lastApiKeywordSyncAttemptAt = now;
      const apiSync = await syncRecommendedKeywordsFromApi(MAX_API_KEYWORD_INJECTION);
      if (apiSync.ok && apiSync.addedCount > 0) {
        return;
      }
    }

    const recycled = await recycleCompletedKeywords(queue, 5);
    if (recycled > 0) {
      console.log(`[Queue] Recycled ${recycled} completed keywords for 24/7 loop.`);
    }
    return;
  }

  // Sort by priority score
  const sortedKeywords = sortKeywordsByPriority(pendingKeywords);
  const nextKw = sortedKeywords[0];

  // Check dependencies
  if (nextKw.dependencies && nextKw.dependencies.length > 0) {
    const dependenciesMet = await checkDependencies(nextKw.dependencies, queue);
    if (!dependenciesMet) {
      console.log(`[Queue] Dependencies not met for: ${nextKw.keyword}`);
      // Move to end of queue temporarily
      return;
    }
  }

  console.log(`[Queue] Starting keyword: ${nextKw.keyword} (Priority: ${nextKw.priority}, Score: ${calculatePriorityScore(nextKw).toFixed(1)})`);

  // Başlat - queue.isRunning kontrolünü kaldırdık
  nextKw.status = "running";
  nextKw.startedAt = new Date().toISOString();
  currentQueueKeywordId = nextKw.id;

  await saveQueue(queue);

  // Run'ı başlat
  const result = await startRun({
    keyword: nextKw.keyword,
    targets: nextKw.targets,
    maxPages: nextKw.maxPages,
    queueKeywordId: nextKw.id
  });

  if (!result.ok) {
    console.error(`[Queue] Failed to start: ${result.error}`);
    nextKw.status = "error";
    nextKw.errorCount = (nextKw.errorCount || 0) + 1;
    nextKw.lastError = result.error;
    nextKw.retryCount = (nextKw.retryCount || 0) + 1;
    nextKw.lastRetryAt = new Date().toISOString();
    currentQueueKeywordId = null;
    await saveQueue(queue);
  } else {
    nextKw.runId = result.runId;
    await saveQueue(queue);
    console.log(`[Queue] Started run: ${result.runId}`);
  }
}

// Check if dependencies are met
async function checkDependencies(dependencies, queue) {
  if (!dependencies || dependencies.length === 0) return true;

  // All dependencies must be completed
  for (const depId of dependencies) {
    const depKeyword = queue.keywords.find(k => k.id === depId);
    if (!depKeyword || depKeyword.status !== 'completed') {
      return false;
    }
  }
  return true;
}

// Check and retry error keywords
async function checkRetryableErrors(queue) {
  const errorKeywords = queue.keywords.filter(k =>
    k.status === 'error' &&
    k.retryCount < RETRY_CONFIG.maxRetries &&
    (!k.nextRetryAt || new Date(k.nextRetryAt) <= new Date())
  );

  if (errorKeywords.length === 0) return;

  // Sort errors by priority
  const sortedErrors = sortKeywordsByPriority(errorKeywords);
  const nextError = sortedErrors[0];

  console.log(`[Queue] Retrying error keyword: ${nextError.keyword} (Attempt ${nextError.retryCount + 1}/${RETRY_CONFIG.maxRetries})`);

  const delay = calculateRetryDelay(nextError.retryCount || 0);
  console.log(`[Queue] Retry delay: ${delay}ms`);

  // Schedule retry with delay
  setTimeout(async () => {
    const state = await getState();
    if (state.active) return; // Don't retry if something is running

    nextError.status = "pending";
    nextError.nextRetryAt = null;
    await saveQueue(queue);
    await processNextPendingKeyword();
  }, delay);

  // Set next retry time
  nextError.nextRetryAt = new Date(Date.now() + delay).toISOString();
  await saveQueue(queue);
}

async function recycleCompletedKeywords(queue, maxItems = 5) {
  const completed = queue.keywords
    .filter((k) => k.status === "completed")
    .sort((a, b) => {
      const aTime = new Date(a.completedAt || a.addedAt || 0).getTime();
      const bTime = new Date(b.completedAt || b.addedAt || 0).getTime();
      return aTime - bTime;
    })
    .slice(0, maxItems);

  if (!completed.length) {
    return 0;
  }

  const now = new Date().toISOString();
  completed.forEach((item) => {
    item.status = "pending";
    item.startedAt = null;
    item.completedAt = null;
    item.runId = null;
    item.recycledAt = now;
  });

  await saveQueue(queue);
  return completed.length;
}

async function handleQueueRunComplete(runId, run) {
  console.log(`[Queue] Processing completed run: ${runId}`);

  const queue = await getQueue();

  // Ensure auto-export is enabled by default
  if (!queue.settings) {
    queue.settings = {};
  }
  if (queue.settings.autoExport === undefined) {
    queue.settings.autoExport = true;
  }

  // Bu run hangi keyword'e ait?
  const keyword = queue.keywords.find(k => k.runId === runId || k.id === currentQueueKeywordId);
  if (!keyword) {
    console.log(`[Queue] Keyword not found for run: ${runId}`);
    const apiIngest = await syncRunResultsToApi(runId, run);
    if (apiIngest.ok) {
      console.log(`[Ingest] Orphaned run synced to API: ${runId}`);
    } else {
      console.warn(`[Ingest] Orphaned run API sync failed: ${apiIngest.error}`);
    }
    // Still try to export even if keyword not found
    if (queue.settings.autoExport) {
      console.log(`[Queue] Auto-exporting orphaned run...`);
      await autoSaveRun(runId, run);
    }
    delete runProgressSyncState[runId];
    return;
  }

  // Keyword'ü güncelle
  keyword.status = "completed";
  keyword.completedAt = new Date().toISOString();
  keyword.results = {
    jobs: (run.data?.jobs || []).length,
    talent: (run.data?.talent || []).length,
    projects: (run.data?.projects || []).length
  };
  keyword.runId = runId;

  queue.stats.totalProcessed++;
  queue.stats.totalItems.jobs += keyword.results.jobs;
  queue.stats.totalItems.talent += keyword.results.talent;
  queue.stats.totalItems.projects += keyword.results.projects;

  console.log(`[Queue] Completed: ${keyword.keyword} (${keyword.results.jobs}J, ${keyword.results.talent}T, ${keyword.results.projects}P)`);

  // Direct ingest to API so dashboard updates even if file-download ingest path is delayed.
  const apiIngest = await syncRunResultsToApi(runId, run);
  if (apiIngest.ok) {
    keyword.apiIngestedAt = new Date().toISOString();
    keyword.apiIngestSummary = apiIngest.payload || {};
    console.log(`[Ingest] ✅ Run synced to API (${keyword.keyword})`);
  } else {
    keyword.apiIngestError = apiIngest.error;
    console.warn(`[Ingest] API sync failed (${keyword.keyword}): ${apiIngest.error}`);
  }

  // CRITICAL FIX: Always auto-export, regardless of settings
  console.log(`[Queue] Auto-exporting...`);
  try {
    const exportResult = await autoSaveRun(runId, run);
    console.log(`[Queue] Export complete:`, exportResult);
    keyword.exportPath = exportResult.folderPath;
    keyword.exportedAt = new Date().toISOString();
  } catch (error) {
    console.error(`[Queue] Export failed:`, error);
    keyword.exportError = error.message;
  }

  // AUTO-FLYWHEEL: Check orchestrator API for new keywords after each completion
  console.log(`[Flywheel] Checking API recommendations...`);
  setTimeout(async () => {
    try {
      const apiResult = await syncRecommendedKeywordsFromApi(MAX_API_KEYWORD_INJECTION);
      if (apiResult.ok) {
        console.log(`[Flywheel] ✅ Added ${apiResult.addedCount} API keywords to queue!`);
      } else {
        console.log(`[Flywheel] ${apiResult.message || "No new API keywords"}`);
      }
    } catch (error) {
      console.error(`[Flywheel] Error checking API recommendations:`, error);
    }
  }, 5000); // Wait 5 seconds for NLP to generate new keywords

  // Şu anki run'ı temizle
  currentQueueKeywordId = null;

  await saveQueue(queue);
  await pushQueueTelemetry(queue, true);
  delete runProgressSyncState[runId];
}

function stopQueueProcessor() {
  if (queueProcessorInterval) {
    clearInterval(queueProcessorInterval);
    queueProcessorInterval = null;
  }
}

// Auto-export with folder structure - FIXED to ensure all downloads complete
async function autoSaveRun(runId, run) {
  console.log(`[Export] Starting auto-save for run: ${runId}`);

  const date = new Date();
  const dateStr = date.toISOString().split("T")[0];
  const timeStr = date.toTimeString().split(" ")[0].replace(/:/g, "-");
  const safeKeyword = sanitizeFilename(run.keyword);
  const folderPath = `upwork_dna/${dateStr}/${safeKeyword}_${timeStr}`;

  const targets = ["jobs", "talent", "projects"];
  const downloadResults = [];

  for (const target of targets) {
    const data = run.data?.[target] || [];
    if (data.length === 0) {
      console.log(`[Export] Skipping ${target} - no data`);
      continue;
    }

    console.log(`[Export] Processing ${target}: ${data.length} items`);

    // Add unique counter to prevent filename collisions
    const counter = Date.now() + Math.floor(Math.random() * 1000);

    // JSON - with delay
    const jsonFilename = `${folderPath}/upwork_${target}_${safeKeyword}_${timeStr}_${counter}.json`;
    const jsonContent = JSON.stringify(data, null, 2);
    console.log(`[Export] Downloading JSON: ${jsonFilename}`);
    const jsonResult = await downloadFile(jsonFilename, jsonContent, "application/json");
    downloadResults.push({ file: jsonFilename, type: 'json', result: jsonResult });

    // Wait for download to complete - CRITICAL FIX
    await delay(800); // 800ms delay between downloads

    // CSV - with delay
    const csvFilename = `${folderPath}/upwork_${target}_${safeKeyword}_${timeStr}_${counter}.csv`;
    const csvContent = toCsv(data);
    console.log(`[Export] Downloading CSV: ${csvFilename}`);
    const csvResult = await downloadFile(csvFilename, csvContent, "text/csv");
    downloadResults.push({ file: csvFilename, type: 'csv', result: csvResult });

    // Wait for download to complete - CRITICAL FIX
    await delay(800); // 800ms delay between downloads
  }

  // Summary - with delay
  const summaryCounter = Date.now();
  const summary = `# Upwork DNA Export\n\nKeyword: ${run.keyword}\nStatus: ${run.status}\n\n## Results\n- Jobs: ${run.data?.jobs?.length || 0}\n- Talent: ${run.data?.talent?.length || 0}\n- Projects: ${run.data?.projects?.length || 0}\n\n## Downloads\n${downloadResults.map(r => `- ${r.type.toUpperCase()}: ${r.file} (${r.result.ok ? 'OK' : 'FAILED'})`).join('\n')}\n\nGenerated: ${date.toISOString()}`;
  await delay(400); // Smaller delay for small summary file
  await downloadFile(`${folderPath}/summary_${summaryCounter}.md`, summary, "text/markdown");

  console.log(`[Export] Auto-save complete: ${downloadResults.length} files`);

  return { ok: true, folderPath, downloadResults };
}

// ===== AUTO KEYWORD GENERATION =====
// Built-in trending keywords (no external file needed)
const AUTO_KEYWORDS = [
  { keyword: "AI agent", priority: "CRITICAL", score: 95 },
  { keyword: "machine learning", priority: "HIGH", score: 90 },
  { keyword: "Chrome extension", priority: "HIGH", score: 88 },
  { keyword: "data analyst", priority: "HIGH", score: 85 },
  { keyword: "React developer", priority: "HIGH", score: 83 },
  { keyword: "API integration", priority: "NORMAL", score: 78 },
  { keyword: "web scraping", priority: "NORMAL", score: 75 },
  { keyword: "workflow automation", priority: "HIGH", score: 82 },
  { keyword: "business intelligence", priority: "NORMAL", score: 72 },
  { keyword: "Python automation", priority: "HIGH", score: 80 },
  { keyword: "ChatGPT integration", priority: "CRITICAL", score: 92 },
  { keyword: "LLM development", priority: "CRITICAL", score: 94 },
  { keyword: "data engineer", priority: "HIGH", score: 84 },
  { keyword: "full stack developer", priority: "NORMAL", score: 76 },
  { keyword: "Node.js developer", priority: "NORMAL", score: 74 },
  { keyword: "mobile app developer", priority: "NORMAL", score: 71 },
  { keyword: "Zapier expert", priority: "HIGH", score: 79 },
  { keyword: "Make automation", priority: "HIGH", score: 77 },
  { keyword: "data visualization", priority: "NORMAL", score: 73 },
  { keyword: "SQL expert", priority: "NORMAL", score: 70 }
];

// Auto-generate and add keywords to queue
async function loadAutoKeywords() {
  console.log("[Queue] Auto-generating keywords...");

  try {
    const queue = await getQueue();
    const now = new Date().toISOString();
    let addedCount = 0;

    for (const kw of AUTO_KEYWORDS) {
      // Check if already exists
      const exists = queue.keywords.find(k =>
        k.keyword.toLowerCase() === kw.keyword.toLowerCase()
      );

      if (!exists) {
        queue.keywords.push({
          id: `kw_auto_${Date.now()}_${addedCount}`,
          keyword: kw.keyword,
          targets: ["jobs", "talent", "projects"],
          maxPages: 7,
          status: "pending",
          priority: kw.priority,
          estimatedValue: kw.score,
          addedAt: now,
          startedAt: null,
          completedAt: null,
          runId: null,
          results: { jobs: 0, talent: 0, projects: 0 },
          source: "auto_generated"
        });
        addedCount++;
        console.log(`[Queue] Auto-added: ${kw.keyword} (Priority: ${kw.priority}, Score: ${kw.score})`);
      }
    }

    if (addedCount > 0) {
      await saveQueue(queue);
      console.log(`[Queue] Auto-generated ${addedCount} keywords`);
      return { ok: true, addedCount };
    }

    console.log("[Queue] All auto-keywords already in queue");
    return { ok: false, message: "Already loaded" };

  } catch (error) {
    console.error("[Queue] Error auto-generating keywords:", error);
    return { ok: false, error: error.message };
  }
}

async function syncRecommendedKeywordsFromApi(limit = MAX_API_KEYWORD_INJECTION) {
  console.log("[Queue] Syncing recommended keywords from local orchestrator API...");

  try {
    await flushPendingRunIngestQueue(1);
    const boundedLimit = Math.max(1, Math.min(limit, 20));
    const request = await requestOrchestrator(
      `/v1/recommendations/keywords?limit=${boundedLimit}`,
      { method: "GET" },
      5000
    );
    if (!request.ok) {
      return { ok: false, message: `API unavailable (${request.error || "unreachable"})` };
    }

    const response = request.response;
    if (!response.ok) {
      return { ok: false, message: `API unavailable (${response.status})` };
    }

    const payload = await response.json();
    const recommended = Array.isArray(payload) ? payload : [];
    if (recommended.length === 0) {
      return { ok: false, message: "No recommended keywords from API" };
    }

    const queue = await getQueue();
    const now = new Date().toISOString();
    let addedCount = 0;

    for (const rec of recommended.slice(0, limit)) {
      const keyword = (rec && rec.keyword ? String(rec.keyword) : "").trim();
      if (!keyword) {
        continue;
      }
      const exists = queue.keywords.find(
        (k) => k.keyword.toLowerCase() === keyword.toLowerCase()
      );
      if (exists) {
        continue;
      }

      const priority = Object.keys(PRIORITY_LEVELS).includes(rec.recommended_priority)
        ? rec.recommended_priority
        : "NORMAL";
      const score = Number(rec.opportunity_score || 50);

      queue.keywords.push({
        id: `kw_api_${Date.now()}_${addedCount}`,
        keyword,
        targets: ["jobs", "talent", "projects"],
        maxPages: 7,
        status: "pending",
        priority,
        estimatedValue: score,
        addedAt: now,
        startedAt: null,
        completedAt: null,
        runId: null,
        results: { jobs: 0, talent: 0, projects: 0 },
        source: "orchestrator_api"
      });
      addedCount += 1;
    }

    if (addedCount > 0) {
      await saveQueue(queue);
      console.log(`[Queue] ✅ Added ${addedCount} API keywords to queue`);
      return { ok: true, addedCount };
    }
    return { ok: false, message: "All API keywords already in queue" };
  } catch (error) {
    logOrchestratorError(`[Queue] API keyword sync failed: ${(error && error.message) || "unknown_error"}`);
    return { ok: false, error: (error && error.message) || "api_sync_failed" };
  }
}

// Backward-compatible alias for old call sites
async function loadNLPKeywords() {
  return syncRecommendedKeywordsFromApi(MAX_API_KEYWORD_INJECTION);
}

// Handler for manual keyword generation
async function handleQueueInjectRecommended() {
  // First try to load NLP keywords, fall back to auto keywords
  const nlpResult = await loadNLPKeywords();
  if (nlpResult.ok) {
    return nlpResult;
  }
  return await loadAutoKeywords();
}

// ===== START QUEUE PROCESSOR ON SERVICE WORKER START =====
// Auto-start queue processor when extension loads
startQueueProcessor();

// Startup sync: first API recommendations, then built-in fallback keywords.
setTimeout(async () => {
  console.log("[Queue] Startup keyword sync...");
  lastApiKeywordSyncAttemptAt = Date.now();
  const apiResult = await syncRecommendedKeywordsFromApi(MAX_API_KEYWORD_INJECTION);
  if (apiResult.ok) {
    console.log(`[Queue] ✅ API added ${apiResult.addedCount} keywords`);
    return;
  }
  const fallback = await loadAutoKeywords();
  if (fallback.ok) {
    console.log(`[Queue] ✅ Fallback auto-keywords added: ${fallback.addedCount}`);
  }
}, 2000);

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const type = message && message.type;

  // Queue handlers first
  if (type === "QUEUE_ADD") {
    handleQueueAdd(message).then(sendResponse);
    return true;
  }

  if (type === "QUEUE_GET_STATUS") {
    handleQueueGetStatus().then(sendResponse);
    return true;
  }

  if (type === "QUEUE_CLEAR") {
    handleQueueClear().then(sendResponse);
    return true;
  }

  if (type === "QUEUE_UPDATE_PRIORITY") {
    handleQueueUpdatePriority(message).then(sendResponse);
    return true;
  }

  if (type === "QUEUE_GET_STATS") {
    handleQueueGetStats().then(sendResponse);
    return true;
  }

  if (type === "QUEUE_INJECT_RECOMMENDED") {
    handleQueueInjectRecommended().then(sendResponse);
    return true;
  }

  if (type === "QUEUE_SYNC_RECOMMENDED_API") {
    syncRecommendedKeywordsFromApi(MAX_API_KEYWORD_INJECTION).then(sendResponse);
    return true;
  }

  if (type === "QUEUE_START") {
    // Just trigger queue processor, it will handle the rest
    startQueueProcessor();
    sendResponse({ ok: true, message: "Queue processor started" });
    return true;
  }

  if (type === "START_RUN") {
    startRun(message.config || {}).then(sendResponse);
    return true;
  }

  if (type === "STOP_RUN") {
    stopRun().then(sendResponse);
    return true;
  }

  if (type === "PAGE_READY") {
    handlePageReady(message, sender).then(sendResponse);
    return true;
  }

  if (type === "PAGE_RESULTS") {
    handlePageResults(message).then(sendResponse);
    return true;
  }

  if (type === "DETAIL_RESULTS") {
    handleDetailResults(message).then(sendResponse);
    return true;
  }

  if (type === "PAGE_BLOCKED") {
    handlePageBlocked(message).then(sendResponse);
    return true;
  }

  if (type === "SESSION_EXPIRED") {
    handleSessionExpired(message).then(sendResponse);
    return true;
  }

  if (type === "RATE_LIMITED") {
    handleRateLimited(message).then(sendResponse);
    return true;
  }

  if (type === "GET_STATUS") {
    handleGetStatus().then(sendResponse);
    return true;
  }

  if (type === "EXPORT_JSON") {
    handleExportJson(message.runId).then(sendResponse);
    return true;
  }

  if (type === "EXPORT_CSV") {
    handleExportCsv(message.runId).then(sendResponse);
    return true;
  }

  if (type === "CLEAR_DATA") {
    handleClearData().then(sendResponse);
    return true;
  }

  return false;
});
