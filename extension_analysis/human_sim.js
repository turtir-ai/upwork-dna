// Upwork DNA Scraper - Human Simulation Engine v2.0
// Makes scraping behavior indistinguishable from real users

const HumanSim = {
  // Behavior profiles
  profiles: {
    casual: {
      name: 'Casual User',
      scrollSpeed: { min: 100, max: 300 },
      readingTime: { min: 2000, max: 8000 },
      clickDelay: { min: 500, max: 2000 },
      pageStayTime: { min: 15000, max: 45000 },
      breakProbability: 0.08,
      breakDuration: { min: 60000, max: 180000 }
    },
    focused: {
      name: 'Focused Researcher',
      scrollSpeed: { min: 200, max: 500 },
      readingTime: { min: 1000, max: 4000 },
      clickDelay: { min: 300, max: 1000 },
      pageStayTime: { min: 8000, max: 25000 },
      breakProbability: 0.04,
      breakDuration: { min: 30000, max: 120000 }
    },
    thorough: {
      name: 'Detail-Oriented',
      scrollSpeed: { min: 50, max: 150 },
      readingTime: { min: 5000, max: 15000 },
      clickDelay: { min: 800, max: 3000 },
      pageStayTime: { min: 30000, max: 90000 },
      breakProbability: 0.12,
      breakDuration: { min: 120000, max: 300000 }
    }
  },

  currentProfile: 'casual',
  sessionStartTime: null,
  lastBreakTime: null,
  pagesVisited: 0,
  totalScrollDistance: 0,
  clickCount: 0,

  // Initialize session
  initSession(profileName = null) {
    this.sessionStartTime = Date.now();
    this.lastBreakTime = Date.now();
    this.pagesVisited = 0;
    this.totalScrollDistance = 0;
    this.clickCount = 0;

    if (profileName && this.profiles[profileName]) {
      this.currentProfile = profileName;
    } else {
      // Random profile selection with weights
      const profiles = Object.keys(this.profiles);
      const weights = [0.5, 0.3, 0.2]; // casual most likely
      const r = Math.random();
      let sum = 0;
      for (let i = 0; i < profiles.length; i++) {
        sum += weights[i];
        if (r <= sum) {
          this.currentProfile = profiles[i];
          break;
        }
      }
    }

    console.log(`[HumanSim] Session started with profile: ${this.profiles[this.currentProfile].name}`);
  },

  // Get current profile
  getProfile() {
    return this.profiles[this.currentProfile];
  },

  // Gaussian random for more natural timing
  gaussianRandom(min, max) {
    let u = 0, v = 0;
    while (u === 0) u = Math.random();
    while (v === 0) v = Math.random();

    let num = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
    num = num / 10.0 + 0.5; // Convert to 0-1 range

    if (num > 1 || num < 0) {
      return this.gaussianRandom(min, max);
    }
    return Math.floor(num * (max - min + 1)) + min;
  },

  // Random delay with jitter
  async delay(minMs, maxMs = null) {
    const min = minMs || 1000;
    const max = maxMs || min * 1.5;
    const actualDelay = this.gaussianRandom(min, max);
    await new Promise(resolve => setTimeout(resolve, actualDelay));
  },

  // Simulate human-like mouse movement (Bezier curve)
  async simulateMouseMove(targetElement) {
    if (!targetElement || typeof document === 'undefined') return;

    const rect = targetElement.getBoundingClientRect();
    const targetX = rect.left + rect.width * (0.3 + Math.random() * 0.4);
    const targetY = rect.top + rect.height * (0.3 + Math.random() * 0.4);

    const startX = window.innerWidth * Math.random();
    const startY = window.innerHeight * Math.random();

    const steps = this.gaussianRandom(15, 30);

    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const easeT = this.easeInOutQuad(t);

      const currentX = startX + (targetX - startX) * easeT + (Math.random() - 0.5) * 10;
      const currentY = startY + (targetY - startY) * easeT + (Math.random() - 0.5) * 10;

      const moveEvent = new MouseEvent('mousemove', {
        bubbles: true,
        clientX: currentX,
        clientY: currentY
      });
      document.dispatchEvent(moveEvent);

      await this.delay(10, 30);
    }
  },

  // Simulate human scroll
  async humanScroll(direction = 'down', distance = null) {
    const profile = this.getProfile();
    const scrollDistance = distance || this.gaussianRandom(200, 600);
    const steps = this.gaussianRandom(10, 25);
    const stepDistance = scrollDistance / steps;

    for (let i = 0; i < steps; i++) {
      const scrollAmount = stepDistance + (Math.random() - 0.5) * 20;
      const actualDirection = direction === 'down' ? 1 : -1;

      window.scrollBy({
        top: scrollAmount * actualDirection,
        behavior: 'auto'
      });

      const delayMs = this.gaussianRandom(profile.scrollSpeed.min, profile.scrollSpeed.max);
      await this.delay(delayMs, delayMs * 1.2);

      // Occasional reading pause
      if (Math.random() < 0.15) {
        await this.delay(500, 2000);
      }
    }

    this.totalScrollDistance += scrollDistance;
  },

  // Simulate human click
  async humanClick(element) {
    if (!element || typeof document === 'undefined') return;

    const profile = this.getProfile();

    // Move mouse to element
    await this.simulateMouseMove(element);

    // Pre-click pause
    await this.delay(100, 300);

    // Hover effect
    element.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true }));
    await this.delay(50, 150);

    // Click
    element.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
    await this.delay(50, 150);
    element.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
    element.dispatchEvent(new MouseEvent('click', { bubbles: true }));

    this.clickCount++;
  },

  // Simulate reading content on page
  async simulateReading() {
    const profile = this.getProfile();
    const readTime = this.gaussianRandom(profile.readingTime.min, profile.readingTime.max);
    await this.delay(readTime, readTime * 1.3);
  },

  // Simulate page interaction (scroll + read)
  async simulatePageInteraction() {
    const profile = this.getProfile();

    // Initial scroll down
    await this.humanScroll('down', this.gaussianRandom(300, 800));

    // Read
    await this.simulateReading();

    // Occasional scroll up
    if (Math.random() < 0.3) {
      await this.humanScroll('up', this.gaussianRandom(100, 300));
      await this.delay(500, 1500);
    }

    // Continue scrolling
    await this.humanScroll('down', this.gaussianRandom(200, 500));

    this.pagesVisited++;
  },

  // Check if should take a break
  async checkForBreak() {
    const profile = this.getProfile();

    // Time since last break
    const timeSinceBreak = Date.now() - this.lastBreakTime;
    const minBreakInterval = 600000; // 10 minutes minimum

    if (timeSinceBreak < minBreakInterval) {
      return false;
    }

    // Calculate break probability (increases with time)
    const hoursSinceBreak = timeSinceBreak / 3600000;
    const breakChance = profile.breakProbability * Math.min(hoursSinceBreak / 0.5, 2);

    if (Math.random() < breakChance) {
      const breakDuration = this.gaussianRandom(
        profile.breakDuration.min,
        profile.breakDuration.max
      );

      console.log(`[HumanSim] Taking break for ${Math.round(breakDuration / 1000)}s`);
      await this.delay(breakDuration);

      this.lastBreakTime = Date.now();
      return true;
    }

    return false;
  },

  // Adjust behavior based on time of day
  adjustForTimeOfDay() {
    const hour = new Date().getHours();

    if (hour >= 2 && hour <= 6) {
      // Late night - very slow
      return { multiplier: 2.5, breakIncrease: 0.15 };
    } else if (hour >= 9 && hour <= 12) {
      // Morning - active
      return { multiplier: 1.0, breakIncrease: 0 };
    } else if (hour >= 13 && hour <= 17) {
      // Afternoon - normal
      return { multiplier: 1.2, breakIncrease: 0.05 };
    } else if (hour >= 18 && hour <= 22) {
      // Evening - moderate
      return { multiplier: 0.9, breakIncrease: -0.02 };
    }

    return { multiplier: 1.0, breakIncrease: 0 };
  },

  // Easing function for smooth mouse movement
  easeInOutQuad(t) {
    return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
  },

  // Get session stats
  getSessionStats() {
    const duration = this.sessionStartTime ? Date.now() - this.sessionStartTime : 0;
    return {
      duration: Math.round(duration / 1000),
      pagesVisited: this.pagesVisited,
      totalScrollDistance: Math.round(this.totalScrollDistance),
      clickCount: this.clickCount,
      profile: this.currentProfile
    };
  },

  // Smart delay between actions (considers time of day, breaks)
  async smartDelay(actionType = 'default') {
    const profile = this.getProfile();
    const timeAdjustment = this.adjustForTimeOfDay();

    let baseDelay = 1000;
    switch (actionType) {
      case 'click':
        baseDelay = this.gaussianRandom(profile.clickDelay.min, profile.clickDelay.max);
        break;
      case 'pageLoad':
        baseDelay = this.gaussianRandom(2000, 4000);
        break;
      case 'scroll':
        baseDelay = this.gaussianRandom(profile.scrollSpeed.min, profile.scrollSpeed.max);
        break;
      default:
        baseDelay = this.gaussianRandom(800, 2000);
    }

    // Apply time of day multiplier
    const adjustedDelay = baseDelay * timeAdjustment.multiplier;

    await this.delay(adjustedDelay, adjustedDelay * 1.3);

    // Check for break
    await this.checkForBreak();
  }
};

// Export for use in content script
if (typeof module !== 'undefined' && module.exports) {
  module.exports = HumanSim;
}
