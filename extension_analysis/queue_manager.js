// Upwork DNA Scraper - Queue Manager v2.0
// Batch keyword processing with auto-resume capability

const QUEUE_KEY = "upwork_scraper_queue";
const QUEUE_STATS_KEY = "upwork_scraper_queue_stats";

const QueueManager = {
  // Default queue structure
  defaultQueue: {
    keywords: [], // {id, keyword, targets, maxPages, status, addedAt, startedAt, completedAt, errorCount, results}
    currentIndex: 0,
    isRunning: false,
    isPaused: false,
    settings: {
      delayBetweenKeywords: { min: 60000, max: 180000 }, // 1-3 min between keywords
      autoSave: true,
      autoExport: true,
      retryOnError: true,
      maxRetries: 3,
      dailyLimit: 100,
      targets: ["jobs", "talent", "projects"],
      maxPages: 0 // 0 = all pages
    },
    stats: {
      totalProcessed: 0,
      totalErrors: 0,
      dailyProcessed: 0,
      lastResetDate: null,
      startTime: null,
      totalItems: { jobs: 0, talent: 0, projects: 0 }
    }
  },

  async getQueue() {
    return new Promise((resolve) => {
      chrome.storage.local.get([QUEUE_KEY, QUEUE_STATS_KEY], (result) => {
        const queue = result[QUEUE_KEY] || JSON.parse(JSON.stringify(this.defaultQueue));
        const stats = result[QUEUE_STATS_KEY] || { lastResetDate: null, dailyProcessed: 0 };
        queue.stats = { ...queue.stats, ...stats };
        resolve(queue);
      });
    });
  },

  async saveQueue(queue) {
    return new Promise((resolve) => {
      const statsToSave = {
        lastResetDate: queue.stats.lastResetDate,
        dailyProcessed: queue.stats.dailyProcessed
      };
      chrome.storage.local.set({
        [QUEUE_KEY]: queue,
        [QUEUE_STATS_KEY]: statsToSave
      }, () => resolve());
    });
  },

  // Add multiple keywords at once
  async addKeywords(keywordList, options = {}) {
    const queue = await this.getQueue();
    const now = new Date().toISOString();

    keywordList.forEach((kw, index) => {
      const keyword = typeof kw === 'string' ? kw.trim() : kw.keyword || '';
      if (!keyword) return;

      const exists = queue.keywords.find(k => k.keyword.toLowerCase() === keyword.toLowerCase());
      if (exists) return;

      queue.keywords.push({
        id: `kw_${Date.now()}_${index}`,
        keyword: keyword,
        targets: options.targets || queue.settings.targets,
        maxPages: options.maxPages ?? queue.settings.maxPages,
        status: 'pending', // pending, running, completed, error, skipped
        addedAt: now,
        startedAt: null,
        completedAt: null,
        errorCount: 0,
        lastError: null,
        runId: null,
        results: { jobs: 0, talent: 0, projects: 0 }
      });
    });

    await this.saveQueue(queue);
    return queue;
  },

  // Clear all keywords
  async clearQueue() {
    const queue = JSON.parse(JSON.stringify(this.defaultQueue));
    queue.stats.lastResetDate = new Date().toISOString();
    await this.saveQueue(queue);
    return queue;
  },

  // Get next pending keyword
  async getNextKeyword() {
    const queue = await this.getQueue();
    this.resetDailyLimitIfNeeded(queue);

    // Check daily limit
    if (queue.stats.dailyProcessed >= queue.settings.dailyLimit) {
      return { error: 'Daily limit reached' };
    }

    const pending = queue.keywords.find(k => k.status === 'pending');
    return pending || null;
  },

  // Check and reset daily limit
  resetDailyLimitIfNeeded(queue) {
    const today = new Date().toDateString();
    if (queue.stats.lastResetDate !== today) {
      queue.stats.dailyProcessed = 0;
      queue.stats.lastResetDate = today;
    }
  },

  // Mark keyword as running
  async startKeyword(keywordId) {
    const queue = await this.getQueue();
    const kw = queue.keywords.find(k => k.id === keywordId);
    if (!kw) return null;

    kw.status = 'running';
    kw.startedAt = new Date().toISOString();
    queue.isRunning = true;
    queue.currentIndex = queue.keywords.indexOf(kw);

    await this.saveQueue(queue);
    return kw;
  },

  // Mark keyword as completed
  async completeKeyword(keywordId, results) {
    const queue = await this.getQueue();
    const kw = queue.keywords.find(k => k.id === keywordId);
    if (!kw) return null;

    kw.status = 'completed';
    kw.completedAt = new Date().toISOString();
    kw.results = results || kw.results;

    queue.stats.totalProcessed++;
    queue.stats.dailyProcessed++;
    queue.stats.totalItems.jobs += results?.jobs || 0;
    queue.stats.totalItems.talent += results?.talent || 0;
    queue.stats.totalItems.projects += results?.projects || 0;

    await this.saveQueue(queue);
    return kw;
  },

  // Mark keyword as error
  async errorKeyword(keywordId, error) {
    const queue = await this.getQueue();
    const kw = queue.keywords.find(k => k.id === keywordId);
    if (!kw) return null;

    kw.errorCount++;
    kw.lastError = error;

    if (kw.errorCount >= queue.settings.maxRetries) {
      kw.status = 'error';
      queue.stats.totalErrors++;
    } else {
      kw.status = 'pending';
    }

    await this.saveQueue(queue);
    return kw;
  },

  // Pause queue processing
  async pauseQueue() {
    const queue = await this.getQueue();
    queue.isPaused = true;
    await this.saveQueue(queue);
    return queue;
  },

  // Resume queue processing
  async resumeQueue() {
    const queue = await this.getQueue();
    queue.isPaused = false;
    await this.saveQueue(queue);
    return queue;
  },

  // Stop queue processing
  async stopQueue() {
    const queue = await this.getQueue();
    queue.isRunning = false;
    queue.isPaused = false;

    // Reset any running keywords back to pending
    queue.keywords.forEach(kw => {
      if (kw.status === 'running') {
        kw.status = 'pending';
      }
    });

    await this.saveQueue(queue);
    return queue;
  },

  // Get queue summary for UI
  async getQueueSummary() {
    const queue = await this.getQueue();
    const summary = {
      total: queue.keywords.length,
      pending: queue.keywords.filter(k => k.status === 'pending').length,
      running: queue.keywords.filter(k => k.status === 'running').length,
      completed: queue.keywords.filter(k => k.status === 'completed').length,
      error: queue.keywords.filter(k => k.status === 'error').length,
      isRunning: queue.isRunning,
      isPaused: queue.isPaused,
      currentIndex: queue.currentIndex,
      stats: queue.stats,
      keywords: queue.keywords.map(k => ({
        id: k.id,
        keyword: k.keyword,
        status: k.status,
        results: k.results
      }))
    };
    return summary;
  },

  // Get random delay between keywords (gaussian-like)
  getRandomBetweenKeywordsDelay() {
    const queue = await this.getQueue();
    const { min, max } = queue.settings.delayBetweenKeywords;
    // More realistic distribution
    const base = Math.random() * (max - min) + min;
    const jitter = (Math.random() - 0.5) * 30000; // ±15 sec jitter
    return Math.max(min, Math.min(max, base + jitter));
  },

  // Calculate progress percentage
  getProgress() {
    return new Promise(async (resolve) => {
      const queue = await this.getQueue();
      if (queue.keywords.length === 0) {
        resolve(0);
        return;
      }
      const completed = queue.keywords.filter(k => k.status === 'completed').length;
      const total = queue.keywords.length;
      resolve(Math.round((completed / total) * 100));
    });
  },

  // Export queue as JSON for backup
  async exportQueue() {
    const queue = await this.getQueue();
    return JSON.stringify(queue, null, 2);
  },

  // Import queue from JSON
  async importQueue(jsonString) {
    try {
      const imported = JSON.parse(jsonString);
      if (imported.keywords && Array.isArray(imported.keywords)) {
        await this.saveQueue(imported);
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }
};

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
  module.exports = QueueManager;
}
