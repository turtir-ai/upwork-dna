const STATE_KEY = "upwork_scraper_state";

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

const DETAIL_NAV_DELAY_RANGE = { min: 2500, max: 4500 };
const DETAIL_START_DELAY_RANGE = { min: 1500, max: 2500 };
const DETAIL_ERROR_DELAY_RANGE = { min: 3500, max: 6000 };

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
    detailMode: null
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
    await delay(1200);
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
          blockedUrl: state.active.blockedUrl
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
        saveAs: true
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

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const type = message && message.type;

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
