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

function setStatus(text) {
  statusEl.textContent = text;
}

function formatSummary(summary) {
  if (!summary) {
    return "";
  }
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
      const detailCurrent =
        detailTotal > 0 ? Math.min(active.detailIndex + 1, detailTotal) : 0;
      phaseInfo += ` | Detail: ${detailCurrent}/${detailTotal}`;
    } else {
      phaseInfo += ` | Page: ${active.pageIndex}`;
    }
    const maxInfo =
      phase === "list" && active.maxPages > 0 ? ` | Max pages: ${active.maxPages}` : "";
    const targetInfo = `Target: ${active.target}`;
    let text = `${base}\n${targetInfo} | ${phaseInfo}${maxInfo}`;

    if (active.blocked) {
      text += `\nBlocked: solve challenge at ${active.blockedUrl}`;
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
  chrome.runtime.sendMessage({ type: "GET_STATUS" }, (response) => {
    renderStatus(response);
  });
}

startButton.addEventListener("click", () => {
  const keyword = keywordInput.value.trim();
  const targets = [];
  if (targetJobs.checked) {
    targets.push("jobs");
  }
  if (targetTalent.checked) {
    targets.push("talent");
  }
  if (targetProjects.checked) {
    targets.push("projects");
  }

  const maxPages = Number(maxPagesInput.value) || 0;

  chrome.runtime.sendMessage(
    {
      type: "START_RUN",
      config: {
        keyword,
        targets,
        maxPages
      }
    },
    (response) => {
      if (!response || !response.ok) {
        const error = response && response.error ? response.error : "Failed to start.";
        setStatus(`Error: ${error}`);
        return;
      }
      setStatus(`Started: ${response.runId}`);
      updateStatus();
    }
  );
});

stopButton.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "STOP_RUN" }, (response) => {
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
  chrome.runtime.sendMessage({ type: "EXPORT_JSON" }, (response) => {
    if (!response || !response.ok) {
      const error = response && response.error ? response.error : "Export failed.";
      setStatus(`Error: ${error}`);
      return;
    }
    setStatus("JSON export started.");
  });
});

exportCsvButton.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "EXPORT_CSV" }, (response) => {
    if (!response || !response.ok) {
      const error = response && response.error ? response.error : "Export failed.";
      setStatus(`Error: ${error}`);
      return;
    }
    setStatus("CSV export started.");
  });
});

clearButton.addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "CLEAR_DATA" }, (response) => {
    if (!response || !response.ok) {
      setStatus("Error: failed to clear.");
      return;
    }
    setStatus("Data cleared.");
  });
});

updateStatus();
setInterval(updateStatus, 2000);
