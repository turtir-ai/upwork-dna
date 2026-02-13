// Upwork DNA Scraper - Anti-Bot & Challenge Detection Engine v2.0
// Advanced threat detection and smart recovery strategies

const AntiBot = {
  // Detection patterns for various threat types
  patterns: {
    cloudflare: [
      'just a moment',
      'checking your browser',
      'cf-challenge',
      'cf-turnstile',
      '__cf_chl',
      'ray id',
      'cloudflare',
      'attention required'
    ],
    captcha: [
      'recaptcha',
      'hcaptcha',
      'captcha',
      'verify you are human',
      'solve the puzzle'
    ],
    rateLimit: [
      'too many requests',
      'rate limit',
      'slow down',
      'try again later',
      'rate-limit'
    ],
    blocked: [
      'access denied',
      'forbidden',
      'blocked',
      'suspicious activity',
      'unusual activity'
    ],
    login: [
      '/login',
      '/signin',
      'sign in',
      'log in'
    ]
  },

  // DOM selectors that indicate challenges
  domSelectors: [
    '#challenge-form',
    '.cf-challenge',
    '.cf-turnstile',
    '[data-cf-challenge]',
    '#cf-wrapper',
    '.g-recaptcha',
    '.h-captcha',
    '#captcha',
    '[class*="challenge"]',
    '[id*="challenge"]'
  ],

  // Analyze current page for threats
  analyzePage() {
    if (typeof document === 'undefined') {
      return { threats: [], severity: 'none' };
    }

    const html = document.documentElement.outerHTML.toLowerCase();
    const title = document.title.toLowerCase();
    const url = window.location.href.toLowerCase();
    const threats = [];

    // Check each pattern category
    Object.entries(this.patterns).forEach(([type, patterns]) => {
      patterns.forEach(pattern => {
        if (html.includes(pattern) || title.includes(pattern) || url.includes(pattern)) {
          threats.push({
            type: type,
            pattern: pattern,
            severity: this.getSeverity(type),
            source: 'content',
            timestamp: new Date().toISOString()
          });
        }
      });
    });

    // Check DOM elements
    this.domSelectors.forEach(selector => {
      try {
        const element = document.querySelector(selector);
        if (element) {
          const type = this.inferTypeFromSelector(selector);
          threats.push({
            type: type,
            pattern: selector,
            severity: this.getSeverity(type),
            source: 'dom',
            timestamp: new Date().toISOString()
          });
        }
      } catch (e) {
        // Invalid selector, skip
      }
    });

    const overallSeverity = this.getOverallSeverity(threats);

    return {
      threats,
      severity: overallSeverity,
      url: window.location.href,
      title: document.title,
      timestamp: new Date().toISOString()
    };
  },

  // Infer threat type from DOM selector
  inferTypeFromSelector(selector) {
    const lower = selector.toLowerCase();
    if (lower.includes('cf') || lower.includes('challenge')) {
      return 'cloudflare';
    }
    if (lower.includes('captcha') || lower.includes('recaptcha')) {
      return 'captcha';
    }
    if (lower.includes('login') || lower.includes('signin')) {
      return 'login';
    }
    return 'blocked';
  },

  // Get severity level for threat type
  getSeverity(type) {
    const severities = {
      cloudflare: 'high',
      captcha: 'high',
      rateLimit: 'medium',
      blocked: 'critical',
      login: 'medium'
    };
    return severities[type] || 'low';
  },

  // Get numeric severity score
  getSeverityScore(severity) {
    const scores = { critical: 4, high: 3, medium: 2, low: 1, none: 0 };
    return scores[severity] || 0;
  },

  // Calculate overall severity from multiple threats
  getOverallSeverity(threats) {
    if (threats.length === 0) return 'none';

    const maxScore = Math.max(...threats.map(t => this.getSeverityScore(t.severity)));

    if (maxScore >= 4) return 'critical';
    if (maxScore >= 3) return 'high';
    if (maxScore >= 2) return 'medium';
    return 'low';
  },

  // Check if current page is a challenge page
  isChallengePage() {
    const analysis = this.analyzePage();
    return analysis.severity !== 'none';
  },

  // Check if current page is login page
  isLoginPage() {
    const url = typeof window !== 'undefined' ? window.location.href : '';
    const patterns = this.patterns.login;
    return patterns.some(p => url.toLowerCase().includes(p));
  },

  // Recovery strategies for each threat type
  recoveryStrategies: {
    cloudflare: async (context) => {
      console.log('[AntiBot] Cloudflare challenge detected');

      // Set state to wait for human
      context.state = 'waiting_for_human';
      context.message = 'Cloudflare challenge - Please solve manually';

      // Return instruction to pause
      return {
        action: 'pause',
        message: 'Cloudflare challenge detected. Please solve it in the Upwork tab, then click Resume.',
        autoRetry: false,
        checkInterval: 5000
      };
    },

    captcha: async (context) => {
      console.log('[AntiBot] CAPTCHA detected');

      context.state = 'waiting_for_human';
      context.message = 'CAPTCHA - Please solve manually';

      return {
        action: 'pause',
        message: 'CAPTCHA detected. Please solve it in the Upwork tab, then click Resume.',
        autoRetry: false,
        checkInterval: 5000
      };
    },

    rateLimit: async (context) => {
      console.log('[AntiBot] Rate limit detected');

      const retryCount = context.retryCount || 0;
      const backoffTime = Math.min(300000, Math.pow(2, retryCount) * 30000); // Exponential backoff, max 5 min

      context.retryCount = retryCount + 1;

      return {
        action: 'wait_and_retry',
        message: `Rate limited. Waiting ${Math.round(backoffTime / 1000)}s before retry...`,
        delay: backoffTime,
        autoRetry: true
      };
    },

    blocked: async (context) => {
      console.log('[AntiBot] Access blocked');

      context.state = 'blocked';
      context.message = 'Access blocked - Session rotation recommended';

      return {
        action: 'pause',
        message: 'Access blocked. Recommended actions: Clear cookies, use VPN, or wait a few hours.',
        autoRetry: false,
        suggestions: [
          'Clear browser cookies and cache',
          'Try using a VPN',
          'Wait a few hours before retrying',
          'Consider using a different Upwork account'
        ]
      };
    },

    login: async (context) => {
      console.log('[AntiBot] Login required');

      context.state = 'waiting_for_login';
      context.message = 'Login required';

      return {
        action: 'pause',
        message: 'Please log in to Upwork, then click Resume.',
        autoRetry: false,
        checkInterval: 5000
      };
    }
  },

  // Handle detected threat - returns recovery strategy
  async handleThreat(analysis, context = {}) {
    if (analysis.severity === 'none') {
      return { action: 'continue' };
    }

    // Find highest severity threat
    const highestThreat = analysis.threats.reduce((max, t) =>
      this.getSeverityScore(t.severity) > this.getSeverityScore(max.severity) ? t : max
    );

    const strategy = this.recoveryStrategies[highestThreat.type];

    if (strategy) {
      return await strategy(context);
    }

    // Default: pause
    return {
      action: 'pause',
      message: `Unknown threat detected: ${highestThreat.type}`,
      autoRetry: false
    };
  },

  // Check if page has recovered from challenge
  checkRecovery() {
    const analysis = this.analyzePage();
    return {
      recovered: analysis.severity === 'none',
      analysis
    };
  },

  // Smart delay that adjusts for threat level
  async smartDelay(baseDelay = 1000) {
    const analysis = this.analyzePage();

    if (analysis.severity === 'none') {
      // Normal operation
      return new Promise(resolve => setTimeout(resolve, baseDelay));
    }

    // Threat detected - get recovery strategy
    const strategy = await this.handleThreat(analysis, {});

    if (strategy.action === 'pause') {
      throw new Error(`PAUSE_REQUIRED: ${strategy.message}`);
    }

    if (strategy.action === 'wait_and_retry') {
      console.log(`[AntiBot] ${strategy.message}`);
      await new Promise(resolve => setTimeout(resolve, strategy.delay));
    }

    return strategy;
  },

  // Pre-flight check before scraping
  async preFlightCheck() {
    if (typeof document === 'undefined') {
      return { ok: true };
    }

    const analysis = this.analyzePage();

    if (analysis.severity !== 'none') {
      const strategy = await this.handleThreat(analysis, {});
      return {
        ok: false,
        analysis,
        strategy
      };
    }

    return { ok: true, analysis };
  },

  // Generate threat report for debugging
  generateThreatReport(analysis) {
    return {
      url: analysis.url,
      title: analysis.title,
      severity: analysis.severity,
      threatCount: analysis.threats.length,
      threats: analysis.threats.map(t => ({
        type: t.type,
        pattern: t.pattern,
        severity: t.severity,
        source: t.source
      })),
      timestamp: analysis.timestamp
    };
  }
};

// Export for use in content script
if (typeof module !== 'undefined' && module.exports) {
  module.exports = AntiBot;
}
