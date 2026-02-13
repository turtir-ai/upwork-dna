// Upwork DNA Scraper - Storage Manager v2.0
// Auto-export with folder structure and file management

const StorageManager = {
  config: {
    autoSave: true,
    autoSaveInterval: 30000, // 30 seconds
    folderStructure: 'date', // 'date', 'keyword', 'target', 'flat'
    exportFormats: ['json', 'csv'],
    baseFolder: 'upwork_dna',
    compression: false,
    maxStorageSize: 500 * 1024 * 1024, // 500MB
    createManifest: true,
    createSummary: true
  },

  // Generate folder path based on structure preference
  generateFolderPath(keyword, target, runId) {
    const date = new Date();
    const dateStr = date.toISOString().split('T')[0]; // YYYY-MM-DD
    const timeStr = date.toTimeString().split(' ')[0].replace(/:/g, '-'); // HH-MM-SS
    const safeKeyword = this.sanitizeFilename(keyword);
    const safeRunId = this.sanitizeFilename(runId);

    const base = this.config.baseFolder;

    switch (this.config.folderStructure) {
      case 'date':
        return `${base}/${dateStr}/${safeKeyword}_${timeStr}`;

      case 'keyword':
        return `${base}/${safeKeyword}/${dateStr}`;

      case 'target':
        return `${base}/${target}/${dateStr}/${safeKeyword}`;

      case 'flat':
        return `${base}`;

      default:
        return `${base}/${dateStr}/${safeKeyword}`;
    }
  },

  // Sanitize filename for safe file system usage
  sanitizeFilename(value) {
    if (!value) return 'unknown';
    return value
      .replace(/[^a-zA-Z0-9._-]/g, '_')
      .replace(/_+/g, '_')
      .substring(0, 50);
  },

  // Auto-save a run's data
  async autoSaveRun(runId, runData) {
    const run = runData || await this.getRunData(runId);
    if (!run) return { ok: false, error: 'Run not found' };

    const folderPath = this.generateFolderPath(run.keyword, 'all', runId);
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');

    const results = {
      folderPath,
      files: [],
      totalItems: 0
    };

    // Export each target type
    const targets = ['jobs', 'talent', 'projects'];
    for (const target of targets) {
      const data = run.data?.[target] || [];
      if (data.length === 0) continue;

      const filenameBase = `${folderPath}/upwork_${target}_${run.keyword}_${timestamp}`;

      // JSON export
      if (this.config.exportFormats.includes('json')) {
        const jsonFile = await this.saveFile(
          `${filenameBase}.json`,
          JSON.stringify(data, null, 2),
          'application/json'
        );
        if (jsonFile.ok) {
          results.files.push({ type: 'json', target, path: jsonFile.filename });
        }
      }

      // CSV export
      if (this.config.exportFormats.includes('csv')) {
        const csv = this.toCsv(data);
        const csvFile = await this.saveFile(
          `${filenameBase}.csv`,
          csv,
          'text/csv'
        );
        if (csvFile.ok) {
          results.files.push({ type: 'csv', target, path: csvFile.filename });
        }
      }

      results.totalItems += data.length;
    }

    // Create manifest file
    if (this.config.createManifest) {
      await this.saveManifest(folderPath, run, results);
    }

    // Create summary file
    if (this.config.createSummary) {
      await this.saveSummary(folderPath, run, results);
    }

    return { ok: true, ...results };
  },

  // Save file using Chrome Downloads API
  async saveFile(filename, content, mimeType) {
    return new Promise((resolve) => {
      const blob = new Blob([content], { type: mimeType });
      const url = URL.createObjectURL(blob);

      chrome.downloads.download({
        url: url,
        filename: filename,
        saveAs: false // Auto-save without dialog
      }, (downloadId) => {
        setTimeout(() => URL.revokeObjectURL(url), 30000);

        if (chrome.runtime.lastError) {
          resolve({ ok: false, error: chrome.runtime.lastError.message });
        } else {
          resolve({ ok: true, downloadId, filename });
        }
      });
    });
  },

  // Create manifest file with run metadata
  async saveManifest(folderPath, run, exportResults) {
    const manifest = {
      version: '2.0',
      exportedAt: new Date().toISOString(),
      run: {
        id: run.id,
        keyword: run.keyword,
        status: run.status,
        startedAt: run.startedAt,
        finishedAt: run.finishedAt,
        targets: run.targets
      },
      export: {
        folderPath,
        fileCount: exportResults.files.length,
        totalItems: exportResults.totalItems,
        files: exportResults.files
      }
    };

    await this.saveFile(
      `${folderPath}/manifest.json`,
      JSON.stringify(manifest, null, 2),
      'application/json'
    );
  },

  // Create human-readable summary
  async saveSummary(folderPath, run, exportResults) {
    const counts = {
      jobs: (run.data?.jobs || []).length,
      talent: (run.data?.talent || []).length,
      projects: (run.data?.projects || []).length
    };

    const summary = `
# Upwork DNA Scraper - Export Summary

**Keyword:** ${run.keyword}
**Status:** ${run.status}
**Started:** ${run.startedAt}
**Finished:** ${run.finishedAt || 'In progress'}

## Results
- Jobs: ${counts.jobs}
- Talent: ${counts.talent}
- Projects: ${counts.projects}
- **Total: ${counts.jobs + counts.talent + counts.projects}**

## Files Exported
${exportResults.files.map(f => `- ${f.type.toUpperCase()}: ${f.path}`).join('\n')}

---
Generated by Upwork DNA Scraper v2.0
${new Date().toISOString()}
    `.trim();

    await this.saveFile(
      `${folderPath}/summary.md`,
      summary,
      'text/markdown'
    );
  },

  // Convert data to CSV format
  toCsv(rows) {
    if (!rows || rows.length === 0) return '';

    // Get all unique keys
    const keys = [...new Set(rows.flatMap(row => Object.keys(row || {})))];

    const lines = [keys.join(',')];

    rows.forEach(row => {
      const values = keys.map(key => {
        let value = row[key];
        if (Array.isArray(value)) value = value.join('; ');
        if (value === null || value === undefined) value = '';
        value = String(value).replace(/"/g, '""');

        if (value.includes(',') || value.includes('\n') || value.includes('"')) {
          value = `"${value}"`;
        }
        return value;
      });
      lines.push(values.join(','));
    });

    return lines.join('\n');
  },

  // Get run data from storage
  async getRunData(runId) {
    return new Promise((resolve) => {
      chrome.storage.local.get(['upwork_scraper_state'], (result) => {
        const state = result.upwork_scraper_state || {};
        resolve(state.runs?.[runId] || null);
      });
    });
  },

  // Check storage usage
  async checkStorageUsage() {
    return new Promise((resolve) => {
      chrome.storage.local.getBytesInUse(null, (bytes) => {
        const percentage = (bytes / this.config.maxStorageSize) * 100;
        resolve({
          used: bytes,
          max: this.config.maxStorageSize,
          percentage: percentage.toFixed(2),
          warning: percentage > 80,
          critical: percentage > 95
        });
      });
    });
  },

  // Clean old data
  async cleanupOldData(daysToKeep = 30) {
    const state = await new Promise(resolve => {
      chrome.storage.local.get(['upwork_scraper_state'], (result) => {
        resolve(result.upwork_scraper_state || { runs: {} });
      });
    });

    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - daysToKeep);

    const runsToDelete = [];

    Object.entries(state.runs || {}).forEach(([runId, run]) => {
      const runDate = new Date(run.startedAt);
      if (runDate < cutoffDate) {
        runsToDelete.push(runId);
      }
    });

    runsToDelete.forEach(runId => {
      delete state.runs[runId];
    });

    await new Promise(resolve => {
      chrome.storage.local.set({ upwork_scraper_state: state }, resolve);
    });

    return { deleted: runsToDelete.length, remaining: Object.keys(state.runs).length };
  },

  // Export all runs as backup
  async exportAllRuns() {
    const state = await new Promise(resolve => {
      chrome.storage.local.get(['upwork_scraper_state'], (result) => {
        resolve(result.upwork_scraper_state || { runs: {} });
      });
    });

    const dateStr = new Date().toISOString().split('T')[0];
    const filename = `${this.config.baseFolder}/backups/upwork_scraper_backup_${dateStr}.json`;

    return this.saveFile(
      filename,
      JSON.stringify(state, null, 2),
      'application/json'
    );
  },

  // Export single run
  async exportSingleRun(runId) {
    const run = await this.getRunData(runId);
    if (!run) return { ok: false, error: 'Run not found' };

    const folderPath = this.generateFolderPath(run.keyword, 'all', runId);
    const filename = `${folderPath}/upwork_scrape_${this.sanitizeFilename(run.keyword)}_${runId}.json`;

    return this.saveFile(
      filename,
      JSON.stringify(run, null, 2),
      'application/json'
    );
  },

  // Export single run as CSVs
  async exportSingleRunCsv(runId) {
    const run = await this.getRunData(runId);
    if (!run) return { ok: false, error: 'Run not found' };

    const folderPath = this.generateFolderPath(run.keyword, 'all', runId);
    const results = { files: [] };

    const targets = ['jobs', 'talent', 'projects'];
    for (const target of targets) {
      const data = run.data?.[target] || [];
      if (data.length === 0) continue;

      const csv = this.toCsv(data);
      const filename = `${folderPath}/upwork_${target}_${this.sanitizeFilename(run.keyword)}_${runId}.csv`;

      const result = await this.saveFile(filename, csv, 'text/csv');
      if (result.ok) {
        results.files.push({ target, filename: result.filename });
      }
    }

    return { ok: true, ...results };
  }
};

// Export for use in background script
if (typeof module !== 'undefined' && module.exports) {
  module.exports = StorageManager;
}
