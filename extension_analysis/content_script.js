// ===== HUMAN SIMULATION ENGINE =====
const HumanSim = {
  profiles: {
    casual: {
      scrollSpeed: { min: 100, max: 300 },
      readingTime: { min: 2000, max: 8000 },
      clickDelay: { min: 500, max: 2000 },
      breakProbability: 0.08,
      breakDuration: { min: 60000, max: 180000 }
    },
    focused: {
      scrollSpeed: { min: 200, max: 500 },
      readingTime: { min: 1000, max: 4000 },
      clickDelay: { min: 300, max: 1000 },
      breakProbability: 0.04,
      breakDuration: { min: 30000, max: 120000 }
    }
  },

  currentProfile: 'casual',

  gaussianRandom(min, max) {
    let u = 0, v = 0;
    while (u === 0) u = Math.random();
    while (v === 0) v = Math.random();
    let num = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
    num = num / 10.0 + 0.5;
    if (num > 1 || num < 0) return this.gaussianRandom(min, max);
    return Math.floor(num * (max - min + 1)) + min;
  },

  async delay(minMs, maxMs = null) {
    const min = minMs || 1000;
    const max = maxMs || min * 1.5;
    const actualDelay = this.gaussianRandom(min, max);
    await new Promise(resolve => setTimeout(resolve, actualDelay));
  },

  async simulateMouseMove(targetElement) {
    if (!targetElement) return;
    const rect = targetElement.getBoundingClientRect();
    const targetX = rect.left + rect.width * (0.3 + Math.random() * 0.4);
    const targetY = rect.top + rect.height * (0.3 + Math.random() * 0.4);

    for (let i = 0; i <= 20; i++) {
      const t = i / 20;
      const easeT = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      const currentX = window.innerWidth * Math.random() * (1 - easeT) + targetX * easeT;
      const currentY = window.innerHeight * Math.random() * (1 - easeT) + targetY * easeT;

      document.dispatchEvent(new MouseEvent('mousemove', {
        bubbles: true,
        clientX: currentX,
        clientY: currentY
      }));
      await this.delay(10, 30);
    }
  },

  async simulatePageInteraction() {
    const profile = this.profiles[this.currentProfile];

    // Scroll down with human-like pattern
    const scrollDistance = this.gaussianRandom(300, 800);
    const steps = this.gaussianRandom(10, 25);
    const stepDistance = scrollDistance / steps;

    for (let i = 0; i < steps; i++) {
      const scrollAmount = stepDistance + (Math.random() - 0.5) * 20;
      window.scrollBy({ top: scrollAmount, behavior: 'auto' });

      const delayMs = this.gaussianRandom(profile.scrollSpeed.min, profile.scrollSpeed.max);
      await this.delay(delayMs, delayMs * 1.2);

      // Occasional reading pause
      if (Math.random() < 0.15) {
        await this.delay(500, 2000);
      }
    }

    // Reading time
    const readTime = this.gaussianRandom(profile.readingTime.min, profile.readingTime.max);
    await this.delay(readTime, readTime * 1.3);
  },

  async smartDelay(actionType = 'default') {
    const profile = this.profiles[this.currentProfile];

    let baseDelay = 1000;
    switch (actionType) {
      case 'click': baseDelay = this.gaussianRandom(profile.clickDelay.min, profile.clickDelay.max); break;
      case 'pageLoad': baseDelay = this.gaussianRandom(2000, 4000); break;
      case 'scroll': baseDelay = this.gaussianRandom(profile.scrollSpeed.min, profile.scrollSpeed.max); break;
      default: baseDelay = this.gaussianRandom(800, 2000);
    }

    await this.delay(baseDelay, baseDelay * 1.3);
  }
};

// ===== ANTI-BOT DETECTION ENGINE =====
const AntiBot = {
  patterns: {
    cloudflare: ['just a moment', 'checking your browser', 'cf-challenge', 'cf-turnstile', '__cf_chl', 'ray id', 'cloudflare', 'attention required'],
    captcha: ['recaptcha', 'hcaptcha', 'captcha', 'verify you are human', 'solve the puzzle'],
    rateLimit: ['too many requests', 'rate limit', 'slow down', 'try again later'],
    blocked: ['access denied', 'forbidden', 'blocked', 'suspicious activity'],
    login: ['/login', '/signin', 'sign in', 'log in']
  },

  domSelectors: ['#challenge-form', '.cf-challenge', '.cf-turnstile', '[data-cf-challenge]', '#cf-wrapper', '.g-recaptcha', '.h-captcha'],

  analyzePage() {
    const html = document.documentElement.outerHTML.toLowerCase();
    const title = document.title.toLowerCase();
    const url = window.location.href.toLowerCase();
    const threats = [];

    Object.entries(this.patterns).forEach(([type, patterns]) => {
      patterns.forEach(pattern => {
        if (html.includes(pattern) || title.includes(pattern) || url.includes(pattern)) {
          threats.push({ type, pattern, severity: this.getSeverity(type), timestamp: new Date().toISOString() });
        }
      });
    });

    this.domSelectors.forEach(selector => {
      try {
        if (document.querySelector(selector)) {
          const type = this.inferTypeFromSelector(selector);
          threats.push({ type, pattern: selector, severity: this.getSeverity(type), source: 'dom' });
        }
      } catch (e) {}
    });

    const severity = this.getOverallSeverity(threats);
    return { threats, severity, url: window.location.href };
  },

  inferTypeFromSelector(selector) {
    const lower = selector.toLowerCase();
    if (lower.includes('cf') || lower.includes('challenge')) return 'cloudflare';
    if (lower.includes('captcha')) return 'captcha';
    return 'blocked';
  },

  getSeverity(type) {
    const severities = { cloudflare: 'high', captcha: 'high', rateLimit: 'medium', blocked: 'critical', login: 'medium' };
    return severities[type] || 'low';
  },

  getSeverityScore(severity) {
    const scores = { critical: 4, high: 3, medium: 2, low: 1, none: 0 };
    return scores[severity] || 0;
  },

  getOverallSeverity(threats) {
    if (threats.length === 0) return 'none';
    const maxScore = Math.max(...threats.map(t => this.getSeverityScore(t.severity)));
    if (maxScore >= 4) return 'critical';
    if (maxScore >= 3) return 'high';
    if (maxScore >= 2) return 'medium';
    return 'low';
  },

  isChallengePage() {
    const analysis = this.analyzePage();
    return analysis.severity !== 'none';
  },

  checkRecovery() {
    const analysis = this.analyzePage();
    return { recovered: analysis.severity === 'none', analysis };
  },

  async preFlightCheck() {
    const analysis = this.analyzePage();
    if (analysis.severity !== 'none') {
      return { ok: false, analysis, needsIntervention: true };
    }
    return { ok: true, analysis };
  }
};

// ===== ORIGINAL FUNCTIONS (ENHANCED) =====
function detectPageType() {
  const url = window.location.href;
  if (isJobDetailRoute(url)) {
    return "job_detail";
  }
  if (isTalentDetailRoute(url)) {
    return "talent_detail";
  }
  if (isProjectDetailRoute(url)) {
    return "project_detail";
  }
  if (url.includes("/nx/search/jobs/")) {
    return "jobs";
  }
  if (url.includes("/nx/search/talent") || url.includes("/nx/search/talents")) {
    return "talent";
  }
  if (url.includes("/services/search")) {
    return "projects";
  }
  return "";
}

// Use AntiBot for challenge detection
function isChallengePage() {
  return AntiBot.isChallengePage();
}

function waitForSelector(selector, timeoutMs) {
  return new Promise((resolve) => {
    if (document.querySelector(selector)) {
      resolve(true);
      return;
    }

    const start = Date.now();
    const interval = setInterval(() => {
      if (document.querySelector(selector)) {
        clearInterval(interval);
        resolve(true);
        return;
      }
      if (Date.now() - start > timeoutMs) {
        clearInterval(interval);
        resolve(false);
      }
    }, 400);
  });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchWithTimeout(url, options = {}, timeoutMs = 20000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

function getText(element) {
  return element ? element.textContent.trim() : "";
}

function cleanLocation(value) {
  if (!value) {
    return "";
  }
  return value.replace(/^Location\\s+/i, "").trim();
}

function getHref(element) {
  if (!element) {
    return "";
  }
  const href = element.getAttribute("href");
  if (!href) {
    return "";
  }
  return new URL(href, window.location.origin).toString();
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

function parseRating(tile) {
  const ratingRoot = tile.querySelector("[data-test*='feedback-rating']");
  if (!ratingRoot) {
    return { rating: "", ratingText: "", feedbackCount: "" };
  }

  const described = ratingRoot.getAttribute("aria-describedby");
  let ratingText = "";
  if (described) {
    const popper = document.getElementById(described);
    if (popper) {
      ratingText = popper.textContent.trim();
    }
  }

  const match = ratingText.match(/([0-9.]+)\s*Stars?/i);
  const feedbackMatch = ratingText.match(/based on\s+([0-9,]+)\s+feedback/i);
  return {
    rating: match ? match[1] : "",
    ratingText,
    feedbackCount: feedbackMatch ? feedbackMatch[1].replace(/,/g, "") : ""
  };
}

function parseProjectRating(card) {
  const ratingRoot =
    card.querySelector(".user-rating") || card.querySelector("[data-test*='rating']");
  if (!ratingRoot) {
    return { rating: "", reviewCount: "" };
  }
  const text = ratingRoot.textContent.replace(/\s+/g, " ").trim();
  const ratingMatch = text.match(/([0-5](?:\.[0-9])?)/);
  const reviewMatch = text.match(/\((\d+)\)/);
  return {
    rating: ratingMatch ? ratingMatch[1] : "",
    reviewCount: reviewMatch ? reviewMatch[1] : ""
  };
}

function isJobDetailRoute(url) {
  if (!url) {
    return false;
  }
  if (url.includes("/nx/search/jobs/details/")) {
    return true;
  }
  if (url.includes("/jobs/") && extractJobKey(url)) {
    return true;
  }
  return false;
}

function extractProfileContext() {
  const isProfilePage = /\/freelancers\//.test(window.location.href) || /\/profile\//.test(window.location.href);
  if (!isProfilePage) {
    return { ok: false, error: "Open an Upwork freelancer profile page first." };
  }

  const headline = getText(
    document.querySelector(
      "[data-qa='freelancer-profile-title'], [data-qa='title'], h1, h2"
    )
  );

  const overview = getText(
    document.querySelector(
      "[data-qa='overview'], [data-qa='freelancer-profile-overview'], section p"
    )
  );

  const skillNodes = Array.from(
    document.querySelectorAll(
      "[data-qa='skill-name'], [data-qa='skills'] span, a[href*='/skills/'], .air3-token"
    )
  );
  const skills = [...new Set(skillNodes.map((el) => getText(el)).filter(Boolean))].slice(0, 40);

  const fallbackText = (document.body?.innerText || "").replace(/\s+/g, " ").trim().slice(0, 6000);
  const profileText = [headline, overview, skills.join(" "), fallbackText]
    .filter(Boolean)
    .join("\n\n")
    .trim();

  if (!profileText) {
    return { ok: false, error: "Could not extract profile text from this page." };
  }

  return {
    ok: true,
    upworkUrl: window.location.href,
    headline,
    skills,
    profileText
  };
}

function isTalentDetailRoute(url) {
  if (!url) {
    return false;
  }
  if (url.includes("/nx/search/talent/details/")) {
    return true;
  }
  if (url.includes("/nx/search/talents/details/")) {
    return true;
  }
  if (url.includes("/freelancers/")) {
    return true;
  }
  if (url.includes("/profile/")) {
    return true;
  }
  return false;
}

function isProjectDetailRoute(url) {
  if (!url) {
    return false;
  }
  if (url.includes("/services/product/")) {
    return true;
  }
  if (url.includes("/services/consultation/")) {
    return true;
  }
  return false;
}

function findNextPageUrl() {
  const candidates = [
    "a[data-test='next-page']",
    "a[aria-label='Next page']",
    "a[aria-label*='Next']",
    "a[rel='next']"
  ];

  for (const selector of candidates) {
    const link = document.querySelector(selector);
    if (!link) {
      continue;
    }
    const disabled =
      link.getAttribute("aria-disabled") === "true" ||
      link.classList.contains("is-disabled");
    const href = link.getAttribute("href");
    if (!disabled && href) {
      return new URL(href, window.location.origin).toString();
    }
  }

  return "";
}

async function scrollToBottom() {
  window.scrollTo(0, document.body.scrollHeight);
  await sleep(800);
  window.scrollTo(0, document.body.scrollHeight);
  await sleep(800);
}

async function waitForListGrowth(selector, previousCount, attempts = 8, delayMs = 600) {
  for (let i = 0; i < attempts; i += 1) {
    await sleep(delayMs);
    const count = document.querySelectorAll(selector).length;
    if (count > previousCount) {
      return true;
    }
  }
  return false;
}

function normalizeLabel(value) {
  return value.replace(/\s+/g, " ").replace(/:\s*$/, "").trim();
}

function getFirstText(element, selector) {
  if (!element) {
    return "";
  }
  const found = element.querySelector(selector);
  return getText(found);
}

function getListText(root, selector) {
  if (!root) {
    return [];
  }
  return Array.from(root.querySelectorAll(selector))
    .map((el) => el.textContent.trim())
    .filter(Boolean);
}

function uniqueStrings(values) {
  const seen = new Set();
  const output = [];
  values.forEach((value) => {
    const trimmed = String(value || "").trim();
    if (!trimmed) {
      return;
    }
    const key = trimmed.toLowerCase();
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    output.push(trimmed);
  });
  return output;
}

function getTextFromSelectors(selectors, scope = document) {
  for (const selector of selectors) {
    const found = scope.querySelector(selector);
    const text = getText(found);
    if (text) {
      return text;
    }
  }
  return "";
}

function getListFromSelectors(selectors, scope = document) {
  const items = [];
  selectors.forEach((selector) => {
    items.push(
      ...Array.from(scope.querySelectorAll(selector))
        .map((el) => el.textContent.trim())
        .filter(Boolean)
    );
  });
  return uniqueStrings(items);
}

function findJobLink(jobKey) {
  if (!jobKey) {
    return null;
  }
  return (
    document.querySelector(
      `a[data-test*='job-tile-title-link'][href*='${jobKey}']`
    ) || document.querySelector(`a[href*='${jobKey}']`)
  );
}

function findTalentLink(profileKey) {
  if (!profileKey) {
    return null;
  }
  return (
    document.querySelector(`a[href*='${profileKey}'][href*='/freelancers/']`) ||
    document.querySelector(`a[href*='${profileKey}'][href*='/profile/']`) ||
    document.querySelector(`a[href*='${profileKey}']`)
  );
}

function getNuxtJobs() {
  const nuxt = window.__NUXT__;
  if (!nuxt || !nuxt.state || !nuxt.state.jobsSearch) {
    return [];
  }
  return Array.isArray(nuxt.state.jobsSearch.jobs) ? nuxt.state.jobsSearch.jobs : [];
}

function getNuxtProjects() {
  const nuxt = window.__NUXT__;
  if (!nuxt || !nuxt.state || !nuxt.state.search) {
    return [];
  }
  const projects = nuxt.state.search.projects;
  return Array.isArray(projects) ? projects : [];
}

function formatProjectPrice(start, end) {
  const startNum = Number(start);
  const endNum = Number(end);
  if (Number.isFinite(startNum) && startNum > 0) {
    if (Number.isFinite(endNum) && endNum > 0) {
      return `$${startNum} - $${endNum}`;
    }
    return `From $${startNum}`;
  }
  return "";
}

function formatProjectDelivery(days) {
  const value = Number(days);
  if (!Number.isFinite(value) || value <= 0) {
    return "";
  }
  const label = value === 1 ? "day" : "days";
  return `${value} ${label} delivery`;
}

function formatProjectRating(value) {
  const rating = Number(value);
  if (!Number.isFinite(rating)) {
    return "";
  }
  return rating.toFixed(1);
}

function applyNuxtFallback(detail, jobKey) {
  if (!jobKey) {
    return false;
  }

  const jobs = getNuxtJobs();
  const match = jobs.find((job) => job && job.ciphertext === jobKey);
  if (!match) {
    return false;
  }

  const setIfEmpty = (key, value) => {
    if (detail[key]) {
      return;
    }
    if (value === null || value === undefined || value === "") {
      return;
    }
    detail[key] = value;
  };

  setIfEmpty("detail_title", match.title);
  setIfEmpty("detail_summary", match.description);
  setIfEmpty("detail_job_type_code", match.type);
  setIfEmpty("detail_duration_label", match.durationLabel);
  setIfEmpty("detail_engagement", match.engagement);
  if (match.hourlyBudget) {
    setIfEmpty("detail_hourly_min", match.hourlyBudget.min);
    setIfEmpty("detail_hourly_max", match.hourlyBudget.max);
  }
  if (match.weeklyBudget) {
    setIfEmpty("detail_weekly_budget", match.weeklyBudget.amount);
  }
  if (Array.isArray(match.attrs)) {
    const skills = match.attrs
      .map((attr) => attr && attr.prettyName)
      .filter(Boolean);
    if (skills.length) {
      setIfEmpty("detail_mandatory_skills", skills);
    }
  }
  if (match.client) {
    if (typeof match.client.isPaymentVerified !== "undefined") {
      setIfEmpty(
        "detail_client_payment_verified",
        match.client.isPaymentVerified ? "true" : "false"
      );
    }
    if (match.client.totalSpent) {
      setIfEmpty("detail_client_total_spent", match.client.totalSpent);
    }
    if (match.client.totalReviews) {
      setIfEmpty("detail_client_total_reviews", match.client.totalReviews);
    }
    if (match.client.totalFeedback) {
      setIfEmpty("detail_client_total_feedback", match.client.totalFeedback);
    }
    if (match.client.location && match.client.location.country) {
      setIfEmpty("detail_client_location_country", match.client.location.country);
    }
  }

  setIfEmpty("detail_source", "nuxt_state");
  return true;
}

function parseJsonLd(rootDoc = document) {
  const items = [];
  rootDoc
    .querySelectorAll("script[type='application/ld+json']")
    .forEach((script) => {
      const text = script.textContent;
      if (!text) {
        return;
      }
      try {
        const data = JSON.parse(text);
        if (Array.isArray(data)) {
          data.forEach((entry) => {
            if (entry) {
              items.push(entry);
            }
          });
        } else if (data) {
          items.push(data);
        }
      } catch (error) {
        return;
      }
    });
  return items;
}

function jsonLdHasType(item, type) {
  if (!item || !item["@type"]) {
    return false;
  }
  const value = item["@type"];
  if (Array.isArray(value)) {
    return value.includes(type);
  }
  return value === type;
}

function applyJsonLdPerson(detail, rootDoc = document) {
  const items = parseJsonLd(rootDoc);
  const person = items.find((item) => jsonLdHasType(item, "Person"));
  if (!person) {
    return false;
  }

  let used = false;
  const setIfEmpty = (key, value) => {
    if (detail[key]) {
      return;
    }
    if (value === null || value === undefined || value === "") {
      return;
    }
    detail[key] = value;
    used = true;
  };

  setIfEmpty("detail_name", person.name);
  setIfEmpty("detail_title", person.jobTitle || person.title);
  setIfEmpty("detail_overview", person.description);
  if (person.address) {
    setIfEmpty(
      "detail_location",
      person.address.addressLocality || person.address.addressCountry
    );
  }
  if (person.url) {
    setIfEmpty("detail_profile_url", person.url);
  }
  if (person.knowsAbout) {
    const skills = Array.isArray(person.knowsAbout)
      ? person.knowsAbout
      : [person.knowsAbout];
    const cleaned = uniqueStrings(
      skills.map((item) => String(item || "").trim()).filter(Boolean)
    );
    if (cleaned.length && !detail.detail_skills) {
      detail.detail_skills = cleaned;
      used = true;
    }
  }

  if (used && !detail.detail_source) {
    detail.detail_source = "json_ld";
  }
  return used;
}

function applyJsonLdProduct(detail, rootDoc = document) {
  const items = parseJsonLd(rootDoc);
  const product =
    items.find((item) => jsonLdHasType(item, "Product")) ||
    items.find((item) => jsonLdHasType(item, "Service"));
  if (!product) {
    return false;
  }

  let used = false;
  const setIfEmpty = (key, value) => {
    if (detail[key]) {
      return;
    }
    if (value === null || value === undefined || value === "") {
      return;
    }
    detail[key] = value;
    used = true;
  };

  setIfEmpty("detail_project_title", product.name);
  setIfEmpty("detail_project_description", product.description);
  setIfEmpty("detail_project_url", product.url);
  setIfEmpty("detail_project_category", product.category);

  const offers = Array.isArray(product.offers) ? product.offers[0] : product.offers;
  if (offers) {
    setIfEmpty("detail_project_price", offers.price);
    setIfEmpty("detail_project_currency", offers.priceCurrency);
    if (offers.seller && offers.seller.name) {
      setIfEmpty("detail_seller_name", offers.seller.name);
    }
  }
  if (product.brand && product.brand.name) {
    setIfEmpty("detail_seller_name", product.brand.name);
  }
  if (product.aggregateRating) {
    setIfEmpty("detail_project_rating", product.aggregateRating.ratingValue);
    setIfEmpty("detail_project_reviews", product.aggregateRating.reviewCount);
  }

  if (used && !detail.detail_source) {
    detail.detail_source = "json_ld";
  }
  return used;
}

function getNuxtProjectDetail() {
  const nuxt = window.__NUXT__;
  if (!nuxt || !nuxt.state || !nuxt.state.projects) {
    return null;
  }
  const projectsState = nuxt.state.projects;
  return (
    projectsState.projectSelected ||
    projectsState.projectTileSelected ||
    projectsState.project ||
    null
  );
}

function applyProjectNuxtFallback(detail) {
  const project = getNuxtProjectDetail();
  if (!project) {
    return false;
  }

  let used = false;
  const setIfEmpty = (key, value) => {
    if (detail[key]) {
      return;
    }
    if (value === null || value === undefined || value === "") {
      return;
    }
    detail[key] = value;
    used = true;
  };

  setIfEmpty("detail_project_title", project.title || project.name);
  setIfEmpty(
    "detail_project_description",
    project.description || project.overview || project.summary
  );

  const price = formatProjectPrice(project.priceStart, project.priceEnd);
  setIfEmpty("detail_project_price", price || project.price || project.priceStart);

  const delivery = formatProjectDelivery(
    project.deliveryTime || project.minDaysToFulfill
  );
  setIfEmpty("detail_project_delivery_time", delivery);

  const person = project.person || project.seller || project.freelancer;
  if (person) {
    setIfEmpty("detail_seller_name", person.name || person.shortName);
    setIfEmpty("detail_project_rating", formatProjectRating(person.rating));
    setIfEmpty(
      "detail_project_reviews",
      person.totalFeedback || person.reviewsCount
    );
    if (person.ciphertext) {
      setIfEmpty(
        "detail_seller_profile_url",
        new URL(`/freelancers/${person.ciphertext}`, window.location.origin).toString()
      );
    }
  }

  if (Array.isArray(project.skills)) {
    const skills = project.skills
      .map((skill) => (skill && (skill.name || skill.label || skill.title)) || skill)
      .map((skill) => String(skill || "").trim())
      .filter(Boolean);
    if (skills.length) {
      setIfEmpty("detail_project_skills", uniqueStrings(skills));
    }
  }

  if (used && !detail.detail_source) {
    detail.detail_source = "nuxt_state";
  }
  return used;
}

async function scrapeJobs() {
  // Pre-flight check for challenges
  const preFlight = await AntiBot.preFlightCheck();
  if (!preFlight.ok) {
    return { items: [], error: "Challenge detected - please solve manually", blocked: true };
  }

  const ready = await waitForSelector("[data-test='JobTile']", 15000);
  if (!ready) {
    return { items: [], error: "Job tiles not found." };
  }

  // Human-like scroll to bottom
  await scrollToBottom();
  await HumanSim.simulatePageInteraction();

  const tiles = Array.from(document.querySelectorAll("[data-test='JobTile']"));
  const pageUrl = window.location.href;
  const pageIndex = Number(new URL(pageUrl).searchParams.get("page")) || 1;

  const items = tiles.map((tile) => {
    const jobId =
      tile.getAttribute("data-ev-job-uid") || tile.getAttribute("data-test-key") || "";
    const titleLink = tile.querySelector("a[data-test*='job-tile-title-link']");
    const title = getText(titleLink);
    const url = getHref(titleLink);
    const jobKey = extractJobKey(url);
    const posted = getText(tile.querySelector("small[data-test='job-pubilshed-date']"));
    const ratingInfo = parseRating(tile);
    const totalSpent = getText(tile.querySelector("li[data-test='total-spent'] strong"));
    const location = cleanLocation(getText(tile.querySelector("li[data-test='location']")));
    const jobType = getText(tile.querySelector("li[data-test='job-type-label']"));
    const fixedBudget =
      getText(tile.querySelector("li[data-test='is-fixed-price'] strong.rr-mask")) ||
      getText(tile.querySelector("li[data-test='is-fixed-price'] strong:last-of-type"));
    const paymentBadge = tile.querySelector(
      "li[data-test='payment-verified'] [data-test='UpCVerifiedBadge']"
    );
    const paymentVerified = paymentBadge
      ? paymentBadge.classList.contains("is-verified")
      : "";
    const experience = getText(tile.querySelector("li[data-test='experience-level']"));
    const duration = getText(tile.querySelector("li[data-test='duration-label']"));
    const description = getText(tile.querySelector("[data-test='JobDescription'] p"));
    const proposals = getText(tile.querySelector("li[data-test='proposals-tier'] strong"));

    const skills = Array.from(tile.querySelectorAll("[data-test='token'] span"))
      .map((el) => el.textContent.trim())
      .filter(Boolean);

    return {
      id: jobId,
      job_key: jobKey,
      title,
      url,
      posted,
      client_rating: ratingInfo.rating,
      client_rating_text: ratingInfo.ratingText,
      client_feedback_count: ratingInfo.feedbackCount,
      payment_verified: paymentVerified,
      total_spent: totalSpent,
      location,
      job_type: jobType,
      budget: fixedBudget || jobType,
      fixed_budget: fixedBudget,
      experience_level: experience,
      duration,
      description,
      skills,
      proposals,
      page_url: pageUrl,
      page_index: pageIndex
    };
  });

  const nextUrl = findNextPageUrl();
  return {
    items,
    pageUrl,
    pageIndex,
    nextUrl,
    hasNext: Boolean(nextUrl)
  };
}

async function scrapeTalent() {
  const preFlight = await AntiBot.preFlightCheck();
  if (!preFlight.ok) {
    return { items: [], error: "Challenge detected - please solve manually", blocked: true };
  }

  const ready = await waitForSelector(
    "[data-test='ProfilesList'], [data-test='FreelancerTile']",
    15000
  );
  if (!ready) {
    return { items: [], error: "Talent section not found." };
  }

  await scrollToBottom();
  await HumanSim.simulatePageInteraction();

  let cards = Array.from(
    document.querySelectorAll("[data-test='ProfilesList'] [data-test='FreelancerTile']")
  );
  if (!cards.length) {
    cards = Array.from(document.querySelectorAll("[data-test='FreelancerTile']"));
  }
  const pageUrl = window.location.href;
  const pageIndex = Number(new URL(pageUrl).searchParams.get("page")) || 1;

  const items = cards.map((card) => {
    const name = getTextFromSelectors(
      ["h5.name", "[data-test='FreelancerTileIdentity'] h5", "a.profile-link"],
      card
    );
    const title = getTextFromSelectors(
      ["h4.title", "[data-test='FreelancerTileIdentity'] h4"],
      card
    );
    const rateValue = getText(card.querySelector("[data-test='rate-per-hour']"));
    const rateLabel = getText(card.querySelector("[data-test='rate-per-hour-label']"));
    let rate = "";
    if (rateValue) {
      rate = `${rateValue}${rateLabel || ""}`.trim();
    } else {
      rate = getText(card.querySelector("[data-test*='freelancer-tile-rate']"));
    }
    const location = cleanLocation(
      getText(
        card.querySelector(
          ".freelancer-info .location, [data-test='FreelancerTileIdentity'] .location"
        )
      )
    );

    const skills = Array.from(
      card.querySelectorAll("[data-test='FreelancerTileSkills'] .air3-token")
    )
      .map((el) => el.textContent.trim())
      .filter((skill) => skill && !skill.startsWith("+"));

    let profileUrl = "";
    const link = card.querySelector(
      "a.profile-link[href*='/freelancers/'], a.profile-link[href*='/profile/']"
    );
    if (link) {
      profileUrl = getHref(link);
    } else {
      profileUrl = getHref(card.querySelector("a[href]"));
    }
    const profileKey = extractJobKey(profileUrl);

    return {
      name,
      title,
      rate,
      location,
      skills,
      profile_key: profileKey,
      url: profileUrl,
      page_url: pageUrl,
      page_index: pageIndex
    };
  });

  const nextUrl = findNextPageUrl();
  return {
    items,
    pageUrl,
    pageIndex,
    nextUrl,
    hasNext: Boolean(nextUrl)
  };
}

async function scrapeProjects(context = {}) {
  const ready = await waitForSelector(
    ".project-tile__title-link, .project-tile, [data-test='project-card']",
    15000
  );
  const initialNuxt = getNuxtProjects();
  if (!ready && !initialNuxt.length) {
    return { items: [], error: "Projects section not found." };
  }

  await scrollToBottom();

  const cardSelector = ".project-tile, [data-test='project-card']";
  const loadMoreSelector = [
    "button[data-qa='extended-results-load-more-link']",
    "button[aria-label='Load More Results']",
    "button.load-more-btn"
  ].join(", ");

  const pageUrl = window.location.href;
  const urlPageIndex = Number(new URL(pageUrl).searchParams.get("page")) || 1;
  const pageIndex = Number(context.pageIndex) || urlPageIndex;
  const maxPages = Number(context.maxPages) || 0;
  const maxAllowed = maxPages > 0 ? maxPages : pageIndex + 39;

  const items = [];
  const seen = new Set();

  const buildItemFromNuxt = (project, itemPageIndex) => {
    if (!project) {
      return null;
    }
    const projectId = project.uid ? String(project.uid) : "";
    const slug = project.slug || "";
    let projectUrl = "";
    if (slug) {
      projectUrl = new URL(
        `/services/product/${slug}`,
        window.location.origin
      ).toString();
    } else if (project.url) {
      try {
        projectUrl = new URL(project.url, window.location.origin).toString();
      } catch (error) {
        projectUrl = project.url;
      }
    }

    const price = formatProjectPrice(project.priceStart, project.priceEnd);
    const delivery = formatProjectDelivery(
      project.deliveryTime || project.minDaysToFulfill
    );
    const person = project.person || {};
    let badge = "";
    if (person.topRatedPlus) {
      badge = "Top Rated Plus";
    } else if (person.topRated) {
      badge = "Top Rated";
    } else if (person.risingTalent) {
      badge = "Rising Talent";
    }

    return {
      title: project.title || project.name || "",
      seller_name: person.name || person.shortName || "",
      seller_badge: badge,
      price,
      delivery_time: delivery,
      rating: formatProjectRating(person.rating),
      reviews: person.totalFeedback ? String(person.totalFeedback) : "",
      project_id: projectId || extractProjectId(projectUrl),
      url: projectUrl,
      page_url: pageUrl,
      page_index: itemPageIndex
    };
  };

  const buildItemFromCard = (card, itemPageIndex) => {
    const titleLink =
      card.querySelector(".project-tile__title-link") ||
      card.querySelector("a[href*='/services/product/']");
    const title =
      getText(titleLink) ||
      getText(card.querySelector(".project-tile__title")) ||
      getText(card.querySelector("h3"));
    const projectUrl = getHref(
      titleLink || card.querySelector("a[href*='/services/']")
    );
    const projectId = extractProjectId(projectUrl);

    const seller = getText(card.querySelector(".user-name")) ||
      getText(card.querySelector("[data-test='seller-name']"));
    const price =
      getText(card.querySelector(".price")) ||
      getText(card.querySelector("[data-test*='price']"));
    const delivery =
      getText(card.querySelector(".project-tile__delivery-time")) ||
      getText(card.querySelector("[data-test*='delivery']"));
    const ratingInfo = parseProjectRating(card);
    const sellerBadge = getText(card.querySelector(".user-badge__quality"));

    return {
      title,
      seller_name: seller,
      seller_badge: sellerBadge,
      price,
      delivery_time: delivery,
      rating: ratingInfo.rating,
      reviews: ratingInfo.reviewCount,
      project_id: projectId,
      url: projectUrl,
      page_url: pageUrl,
      page_index: itemPageIndex
    };
  };

  const addItems = (newItems, itemPageIndex, builder) => {
    newItems.forEach((item) => {
      const built = builder(item, itemPageIndex);
      if (!built) {
        return;
      }
      const key = built.project_id || built.url;
      if (key) {
        if (seen.has(key)) {
          return;
        }
        seen.add(key);
      }
      items.push(built);
    });
  };

  const addCards = (cardList, itemPageIndex) => {
    addItems(cardList, itemPageIndex, buildItemFromCard);
  };

  const addNuxtProjects = (projectList, itemPageIndex) => {
    addItems(projectList, itemPageIndex, buildItemFromNuxt);
  };

  const waitForProjectGrowth = async (
    previousDomCount,
    previousNuxtCount,
    attempts = 8,
    delayMs = 600
  ) => {
    for (let i = 0; i < attempts; i += 1) {
      await sleep(delayMs);
      const domCount = document.querySelectorAll(cardSelector).length;
      const nuxtCount = getNuxtProjects().length;
      if (domCount > previousDomCount || nuxtCount > previousNuxtCount) {
        return { domCount, nuxtCount };
      }
    }
    return {
      domCount: document.querySelectorAll(cardSelector).length,
      nuxtCount: getNuxtProjects().length
    };
  };

  const initialCards = Array.from(document.querySelectorAll(cardSelector));
  const currentProjects = getNuxtProjects();
  if (currentProjects.length) {
    addNuxtProjects(currentProjects, pageIndex);
  } else {
    addCards(initialCards, pageIndex);
  }

  let currentPage = pageIndex;
  let lastDomCount = initialCards.length;
  let lastNuxtCount = currentProjects.length;
  let stalled = 0;

  while (currentPage < maxAllowed) {
    await scrollToBottom();
    const button = document.querySelector(loadMoreSelector);
    if (!button) {
      break;
    }
    const disabled =
      button.disabled ||
      button.getAttribute("aria-disabled") === "true" ||
      button.classList.contains("is-disabled");
    if (!disabled) {
      button.scrollIntoView({ block: "center" });
      button.click();
    }

    await sleep(500);
    await waitForProjectGrowth(lastDomCount, lastNuxtCount);
    const updatedProjects = getNuxtProjects();
    const updatedCards = Array.from(document.querySelectorAll(cardSelector));
    let grew = false;

    if (updatedProjects.length > lastNuxtCount) {
      const newProjects = updatedProjects.slice(lastNuxtCount);
      currentPage += 1;
      addNuxtProjects(newProjects, currentPage);
      grew = true;
    } else if (updatedCards.length > lastDomCount) {
      const newCards = updatedCards.slice(lastDomCount);
      currentPage += 1;
      addCards(newCards, currentPage);
      grew = true;
    }

    lastNuxtCount = updatedProjects.length;
    lastDomCount = updatedCards.length;

    if (!grew) {
      stalled += 1;
      if (stalled >= 2) {
        break;
      }
      continue;
    }
    stalled = 0;
  }

  const nextUrl = findNextPageUrl();
  const hasLoadMore = Boolean(document.querySelector(loadMoreSelector));
  return {
    items,
    pageUrl,
    pageIndex,
    nextUrl,
    hasNext: !hasLoadMore && Boolean(nextUrl)
  };
}

async function scrapeJobDetail(detailContext = {}) {
  const pageUrl = window.location.href;
  const jobUrl = detailContext.jobUrl || pageUrl;
  const jobKey = detailContext.jobKey || extractJobKey(jobUrl) || extractJobKey(pageUrl);
  const detail = {
    detail_job_url: jobUrl,
    detail_page_url: pageUrl,
    detail_job_key: jobKey
  };

  const hasDetailContent = () =>
    Boolean(
      document.querySelector(
        "[data-test='Description Description'], [data-test='Description'], [data-test='JobDescription']"
      )
    );

  const detailSelector =
    "[data-test='Description Description'], [data-test='Description'], [data-test='JobDetailsLoader'], [data-test='JobDescription'], [data-test='UpCSliderBody'][data-test-route*='job-details']";

  if (!hasDetailContent() && jobKey) {
    let link = findJobLink(jobKey);
    if (!link) {
      await scrollToBottom();
      link = findJobLink(jobKey);
    }
    if (link) {
      link.scrollIntoView({ block: "center" });
      await sleep(600);
      link.click();
      await sleep(800);
      await waitForSelector(
        "[data-test='UpCSliderBody'][data-test-route*='job-details'], [data-test='JobDetailsLoader']",
        20000
      );
      await waitForSelector(
        "[data-test='Description Description'], [data-test='Description'], [data-test='JobDescription']",
        20000
      );
    }
  }

  if (!hasDetailContent()) {
    const ready = await waitForSelector(detailSelector, 15000);
    if (!ready || !hasDetailContent()) {
      const usedFallback = applyNuxtFallback(detail, jobKey);
      if (usedFallback) {
        return { detail, error: "" };
      }
      return { detail, error: "Job details not found." };
    }
  }

  const title =
    getText(document.querySelector("[data-test='JobDetailsLoader'] h4 span")) ||
    getText(document.querySelector("h1")) ||
    getText(document.querySelector("h2"));
  if (title) {
    detail.detail_title = title;
  }

  const posted = getText(document.querySelector("[data-test='PostedOn']"));
  if (posted) {
    detail.detail_posted = posted.replace(/\s+/g, " ").trim();
  }

  const jobLocation = getText(document.querySelector("[data-test='LocationLabel'] p"));
  if (jobLocation) {
    detail.detail_location = jobLocation;
  }

  const connectsSection = document.querySelector("[data-test='ConnectsAuction']");
  if (connectsSection) {
    const connectsText = getText(connectsSection);
    const connectsMatch = connectsText.match(/Send a proposal for:\s*([0-9]+)/i);
    if (connectsMatch) {
      detail.detail_connects = connectsMatch[1];
    }
  }

  const descriptionSection = document.querySelector(
    "[data-test='Description Description'], [data-test='Description']"
  );
  if (descriptionSection) {
    const summary = getListText(descriptionSection, "p").join("\n").trim();
    if (summary) {
      detail.detail_summary = summary;
    }
  } else {
    const jobDescription = document.querySelector("[data-test='JobDescription']");
    if (jobDescription) {
      const summary =
        getListText(jobDescription, "p").join("\n").trim() || getText(jobDescription);
      if (summary) {
        detail.detail_summary = summary;
      }
    }
  }

  const featuresSection = document.querySelector("[data-test='Features']");
  if (featuresSection) {
    const featureItems = Array.from(featuresSection.querySelectorAll("li"));
    featureItems.forEach((item) => {
      const cy = item.querySelector("[data-cy]")?.getAttribute("data-cy") || "";
      const strongText = getText(item.querySelector("strong"));
      const descText = getFirstText(item, ".description");

      if (cy === "clock-hourly") {
        detail.detail_hours = strongText;
        if (descText) {
          detail.detail_payment_type = descText;
        }
        return;
      }

      if (cy === "duration2") {
        detail.detail_duration = strongText;
        return;
      }

      if (cy === "expertise") {
        detail.detail_experience_level = strongText;
        if (descText) {
          detail.detail_experience_note = descText;
        }
        return;
      }

      if (item.querySelector("[data-test='BudgetAmount']")) {
        const budgetText = getText(item.querySelector("[data-test='BudgetAmount']"));
        if (budgetText) {
          detail.detail_budget = budgetText;
        }
        return;
      }

      if (/contract-to-hire/i.test(strongText)) {
        detail.detail_contract_to_hire = "true";
        if (descText) {
          detail.detail_contract_to_hire_note = descText;
        }
      }
    });
  }

  const segmentationSection = document.querySelector("[data-test='Segmentations']");
  if (segmentationSection) {
    const projectTypeItem = segmentationSection.querySelector("li");
    if (projectTypeItem) {
      const projectType = getFirstText(projectTypeItem, "span");
      if (projectType) {
        detail.detail_project_type = projectType;
      }
    }
  }

  const questionsSection = document.querySelector("[data-test='Questions']");
  if (questionsSection) {
    const questions = getListText(questionsSection, "ol li");
    if (questions.length) {
      detail.detail_questions = questions;
    }
  }

  const expertiseSection = document.querySelector("[data-test='Expertise']");
  if (expertiseSection) {
    const mandatorySkills = getListText(expertiseSection, "[data-test='Skill']");
    if (mandatorySkills.length) {
      detail.detail_mandatory_skills = mandatorySkills;
    }
  }

  const qualificationsSection = document.querySelector("[data-test='Qualifications']");
  if (qualificationsSection) {
    const items = Array.from(qualificationsSection.querySelectorAll("li"));
    items.forEach((item) => {
      const label = normalizeLabel(getText(item.querySelector("strong")));
      const value = getFirstText(item, "span");
      if (!label || !value) {
        return;
      }
      const normalized = label.toLowerCase();
      if (normalized.includes("talent type")) {
        detail.detail_talent_type = value;
      } else if (normalized.includes("english level")) {
        detail.detail_english_level = value;
      } else if (normalized.includes("location")) {
        detail.detail_required_location = value;
      }
    });
  }

  const activitySection = document.querySelector("[data-test='ClientActivity']");
  if (activitySection) {
    const items = Array.from(activitySection.querySelectorAll("li"));
    items.forEach((item) => {
      const label = normalizeLabel(getFirstText(item, ".title"));
      const value = getFirstText(item, ".value") || getFirstText(item, "div.value");
      if (!label || !value) {
        return;
      }
      const normalized = label.toLowerCase();
      if (normalized.includes("proposals")) {
        detail.detail_activity_proposals = value;
      } else if (normalized.includes("last viewed")) {
        detail.detail_activity_last_viewed = value;
      } else if (normalized.includes("interviewing")) {
        detail.detail_activity_interviewing = value;
      } else if (normalized.includes("invites sent")) {
        detail.detail_activity_invites_sent = value;
      } else if (normalized.includes("unanswered invites")) {
        detail.detail_activity_unanswered_invites = value;
      }
    });
  }

  const aboutClientSection = document.querySelector(
    "[data-test*='about-client-container']"
  );
  if (aboutClientSection) {
    const paymentText = getListText(aboutClientSection, "strong").join(" | ");
    if (paymentText) {
      if (paymentText.includes("Payment method verified")) {
        detail.detail_client_payment_verified = "true";
      }
      if (paymentText.includes("Phone number verified")) {
        detail.detail_client_phone_verified = "true";
      }
    }

    const clientLocation = getText(
      aboutClientSection.querySelector("[data-qa='client-location'] strong")
    );
    if (clientLocation) {
      detail.detail_client_location = clientLocation;
    }
    const clientLocalTime = getText(
      aboutClientSection.querySelector("[data-qa='client-location'] [data-test='LocalTime']")
    );
    if (clientLocalTime) {
      detail.detail_client_local_time = clientLocalTime;
    }

    const clientJobsPosted = getText(
      aboutClientSection.querySelector("[data-qa='client-job-posting-stats'] strong")
    );
    if (clientJobsPosted) {
      detail.detail_client_jobs_posted = clientJobsPosted;
    }

    const clientHireStats = getText(
      aboutClientSection.querySelector("[data-qa='client-job-posting-stats'] div")
    );
    if (clientHireStats) {
      const hireMatch = clientHireStats.match(/([0-9]+%[^,]*)/i);
      const openMatch = clientHireStats.match(/([0-9]+\\s+open\\s+job[s]?)/i);
      if (hireMatch) {
        detail.detail_client_hire_rate = hireMatch[1].trim();
      }
      if (openMatch) {
        detail.detail_client_open_jobs = openMatch[1].trim();
      }
    }

    const memberSince = getText(
      aboutClientSection.querySelector("[data-qa='client-contract-date']")
    );
    if (memberSince) {
      detail.detail_client_member_since = memberSince;
    }
  }

  const jobUid =
    document.querySelector("[data-test='SaveJob'][job-uid]")?.getAttribute("job-uid") ||
    "";
  if (jobUid) {
    detail.detail_job_uid = jobUid;
  }

  return { detail, error: "" };
}

async function scrapeTalentDetail(detailContext = {}) {
  const pageUrl = window.location.href;
  const profileUrl = detailContext.profileUrl || pageUrl;
  const profileKey =
    detailContext.profileKey || extractJobKey(profileUrl) || extractJobKey(pageUrl);
  const detail = {
    detail_profile_url: profileUrl,
    detail_page_url: pageUrl,
    detail_profile_key: profileKey
  };

  const detailSelector = [
    "[data-test='profile-overview']",
    "[data-test='profile-summary']",
    "[data-test='profile-description']",
    "[data-test='ProfileOverview']",
    "[data-test='UpCSliderBody']",
    "[data-test='UpCSliderBody'][data-test-route*='profile']",
    "[data-test='ProfileViewer']",
    "[data-test='ProfileViewerPreview']",
    "[data-test='profile-identity']",
    "[data-test='summary-stats']",
    "[data-test='hourly-rate']"
  ].join(", ");
  const hasDetailContent = () => Boolean(document.querySelector(detailSelector));

  if (!hasDetailContent() && profileKey && !isTalentDetailRoute(pageUrl)) {
    let link = findTalentLink(profileKey);
    if (!link) {
      await scrollToBottom();
      link = findTalentLink(profileKey);
    }
    if (link) {
      link.scrollIntoView({ block: "center" });
      await sleep(600);
      link.click();
      await sleep(800);
      await waitForSelector("[data-test='UpCSliderBody']", 20000);
      await waitForSelector(detailSelector, 20000);
    }
  }

  if (!hasDetailContent() && !isTalentDetailRoute(pageUrl)) {
    const usedFallback = applyJsonLdPerson(detail);
    if (usedFallback) {
      return { detail, error: "" };
    }
    return { detail, error: "Talent details not found." };
  }

  const detailRoot = document.querySelector("[data-test='UpCSliderBody']") || document;

  const name = getTextFromSelectors(
    [
      "[data-test='profile-name']",
      "[data-test='freelancer-name']",
      "[data-test='ProfileName']",
      "[data-test='profile-identity'] h2",
      "h2[itemprop='name']",
      "h1"
    ],
    detailRoot
  );
  if (name) {
    detail.detail_name = name;
  }

  const title = getTextFromSelectors(
    [
      "[data-test='profile-title']",
      "[data-test='freelancer-title']",
      "[data-test='ProfileTitle']",
      "[data-test='ProfileViewerPreview'] h3.mb-0.h4",
      "[data-test='ProfileViewerPreview'] h3",
      "h2:not([itemprop='name'])"
    ],
    detailRoot
  );
  if (title) {
    detail.detail_title = title;
  }

  const rate = getTextFromSelectors(
    [
    "[data-test='profile-rate']",
    "[data-test='freelancer-rate']",
    "[data-test='profile-hourly-rate']",
    "[data-test='hourly-rate']",
    "[data-qa='hourly-rate']"
    ],
    detailRoot
  );
  if (rate) {
    detail.detail_rate = rate;
  }

  const location = getTextFromSelectors(
    [
    "[data-test='profile-location']",
    "[data-test='freelancer-location']",
    "[data-test='Location']",
    "[data-qa='location']"
    ],
    detailRoot
  );
  if (location) {
    detail.detail_location = location;
  }

  const jobSuccess = getTextFromSelectors(
    [
    "[data-test='job-success-score']",
    "[data-test='job-success']",
    "[data-qa='job-success']"
    ],
    detailRoot
  );
  if (jobSuccess) {
    detail.detail_job_success = jobSuccess;
  }

  const totalEarned = getTextFromSelectors(
    [
      "[data-test='total-earned']",
      "[data-test='total-earnings']",
      "[data-test='earned-amount-formatted']",
      "[data-qa='total-earned']"
    ],
    detailRoot
  );
  if (totalEarned) {
    detail.detail_total_earned = totalEarned;
  }

  const totalHours = getTextFromSelectors(
    [
    "[data-test='total-hours']",
    "[data-test='hours']",
    "[data-qa='hours']"
    ],
    detailRoot
  );
  if (totalHours) {
    detail.detail_total_hours = totalHours;
  }

  if (!detail.detail_total_earned || !detail.detail_total_hours) {
    const summaryStats = detailRoot.querySelector("[data-test='summary-stats']");
    if (summaryStats) {
      const statBlocks = Array.from(summaryStats.querySelectorAll(".col-compact"));
      statBlocks.forEach((block) => {
        const label = getText(block.querySelector(".text-base-sm"));
        const value = getText(
          block.querySelector(".stat-amount span, .stat-amount")
        );
        if (!label || !value) {
          return;
        }
        const normalized = label.toLowerCase();
        if (!detail.detail_total_earned && normalized.includes("total earnings")) {
          detail.detail_total_earned = value;
        }
        if (!detail.detail_total_hours && normalized.includes("total hours")) {
          detail.detail_total_hours = value;
        }
      });
    }
  }

  const availability = getTextFromSelectors(
    [
    "[data-test='availability']",
    "[data-test='freelancer-availability']",
    "[data-test='profile-availability']",
    "[data-qa='availability']"
    ],
    detailRoot
  );
  if (availability) {
    detail.detail_availability = availability;
  }

  let overview = getTextFromSelectors(
    [
    "[data-test='profile-overview']",
    "[data-test='profile-summary']",
    "[data-test='profile-description']",
    "[data-test='overview']",
    "[data-test='description']"
    ],
    detailRoot
  );
  if (!overview) {
    const previewRoot =
      detailRoot.querySelector("[data-test='ProfileViewerPreview']") || detailRoot;
    const lineClamp = previewRoot.querySelector("[data-test='up-c-line-clamp']");
    overview = getText(lineClamp);
    if (!overview && lineClamp) {
      overview = (lineClamp.getAttribute("data-test-key") || "").trim();
    }
  }
  if (overview) {
    detail.detail_overview = overview;
  }

  const skills = getListFromSelectors(
    [
    "[data-test='skill-item']",
    "[data-test='Skill']",
    "[data-test='skill']",
    "[data-test='skill-tag']",
    ".air3-token"
    ],
    detailRoot
  );
  if (skills.length) {
    detail.detail_skills = skills;
  }

  const languages = getListFromSelectors(
    [
    "[data-test='language-item']",
    "[data-test='language']",
    "[data-qa='language']"
    ],
    detailRoot
  );
  if (languages.length) {
    detail.detail_languages = languages;
  }

  const badges = getListFromSelectors(
    [
    ".user-badge__quality",
    ".air3-badge-tagline",
    "[data-test='freelancer-badge']",
    "[data-test='profile-badge']"
    ],
    detailRoot
  );
  if (badges.length) {
    detail.detail_badges = badges;
  }

  applyJsonLdPerson(detail);
  return { detail, error: "" };
}

function buildProjectDetailShell(detailContext = {}, pageUrlOverride = "") {
  const pageUrl = pageUrlOverride || window.location.href;
  const projectUrl = detailContext.projectUrl || pageUrl;
  const projectId =
    detailContext.projectId || extractProjectId(projectUrl) || extractProjectId(pageUrl);
  return {
    detail_project_url: projectUrl,
    detail_page_url: pageUrl,
    detail_project_id: projectId
  };
}

function populateProjectDetailFromDocument(detail, doc) {
  const title = getTextFromSelectors([
    "[data-test='project-title']",
    "[data-test='ProjectTitle']",
    "h1"
  ], doc);
  if (title) {
    detail.detail_project_title = title;
  }

  const description = getTextFromSelectors([
    "[data-test='project-description']",
    "[data-test='ProjectDescription']",
    "[data-test='project-overview']",
    "[data-test='Description']",
    "section[data-test*='Description']"
  ], doc);
  if (description) {
    detail.detail_project_description = description;
  }

  const price = getTextFromSelectors([
    "[data-test='project-price']",
    "[data-test='ProjectPrice']",
    "[data-test='price']",
    ".price"
  ], doc);
  if (price) {
    detail.detail_project_price = price;
  }

  const delivery = getTextFromSelectors([
    "[data-test='project-delivery-time']",
    "[data-test='delivery-time']",
    ".project-tile__delivery-time"
  ], doc);
  if (delivery) {
    detail.detail_project_delivery_time = delivery;
  }

  const rating = getTextFromSelectors([
    "[data-test='rating-value']",
    "[data-test='rating']",
    ".user-rating .text-body-sm"
  ], doc);
  if (rating) {
    detail.detail_project_rating = rating.replace(/[()]/g, "");
  }

  const reviews = getTextFromSelectors([
    "[data-test='rating-count']",
    ".feedback-count"
  ], doc);
  if (reviews) {
    detail.detail_project_reviews = reviews.replace(/[()]/g, "");
  }

  const sellerName = getTextFromSelectors([
    "[data-test='seller-name']",
    "[data-test='SellerName']",
    ".user-name"
  ], doc);
  if (sellerName) {
    detail.detail_seller_name = sellerName;
  }

  let sellerProfileUrl = "";
  const sellerRoot =
    doc.querySelector("[data-test*='seller']") ||
    doc.querySelector("[data-test*='Seller']");
  if (sellerRoot) {
    sellerProfileUrl = getHref(
      sellerRoot.querySelector("a[href*='/freelancers/'], a[href*='/profile/']")
    );
  }
  if (!sellerProfileUrl) {
    sellerProfileUrl = getHref(
      doc.querySelector("a[href*='/freelancers/'], a[href*='/profile/']")
    );
  }
  if (sellerProfileUrl) {
    detail.detail_seller_profile_url = sellerProfileUrl;
  }

  const breadcrumb =
    doc.querySelector("[data-test='Breadcrumb']") ||
    doc.querySelector(".air3-breadcrumb");
  if (breadcrumb) {
    const items = uniqueStrings(getListText(breadcrumb, "a, span"));
    if (items.length) {
      detail.detail_project_category = items.join(" > ");
    }
  }

  const packages = [];
  const packageCards = doc.querySelectorAll(
    "[data-test*='package-card'], [data-test='package-card'], [data-test*='Package']"
  );
  packageCards.forEach((card) => {
    const name = getTextFromSelectors(["h3", "h4", "strong"], card);
    const pkgPrice = getTextFromSelectors(
      ["[data-test*='price']", ".price"],
      card
    );
    const pkgDelivery = getTextFromSelectors(
      ["[data-test*='delivery']", "[data-test*='duration']"],
      card
    );
    const pkgRevisions = getTextFromSelectors(
      ["[data-test*='revision']"],
      card
    );
    const summary = [name, pkgPrice, pkgDelivery, pkgRevisions].filter(Boolean).join(
      " | "
    );
    if (summary) {
      packages.push(summary);
    }
  });
  if (packages.length) {
    detail.detail_project_packages = uniqueStrings(packages);
  }

  const detailRoot = doc.querySelector("main") || doc;
  const skills = getListFromSelectors(
    [
      "[data-test='project-skill']",
      "[data-test='project-skill-tag']",
      "[data-test='skill']",
      "[data-test='Skill']",
      "[data-test='token']",
      ".air3-token"
    ],
    detailRoot
  );
  if (skills.length) {
    detail.detail_project_skills = skills;
  }
}

async function scrapeProjectDetail(detailContext = {}, detailDoc = null) {
  const doc = detailDoc || document;
  const pageUrl = detailDoc
    ? detailContext.pageUrl || detailContext.projectUrl || ""
    : window.location.href;
  const detail = buildProjectDetailShell(detailContext, pageUrl);

  const detailSelector =
    "[data-test='project-title'], [data-test='ProjectTitle'], h1";
  if (!detailDoc) {
    const ready = await waitForSelector(detailSelector, 15000);
    if (!ready) {
      const usedNuxt = applyProjectNuxtFallback(detail);
      if (usedNuxt) {
        applyJsonLdProduct(detail, doc);
        return { detail, error: "" };
      }
      const usedFallback = applyJsonLdProduct(detail, doc);
      if (usedFallback) {
        return { detail, error: "" };
      }
      return { detail, error: "Project details not found." };
    }
  } else {
    const ready = Boolean(doc.querySelector(detailSelector));
    if (!ready) {
      const usedFallback = applyJsonLdProduct(detail, doc);
      if (usedFallback) {
        return { detail, error: "" };
      }
      return { detail, error: "Project details not found." };
    }
  }

  populateProjectDetailFromDocument(detail, doc);

  if (!detailDoc) {
    applyProjectNuxtFallback(detail);
  }
  applyJsonLdProduct(detail, doc);
  return { detail, error: "" };
}

async function scrapeProjectDetailFromUrl(detailContext = {}) {
  const projectUrl = detailContext.projectUrl || detailContext.pageUrl || "";
  const detail = buildProjectDetailShell(detailContext, projectUrl);
  if (!projectUrl) {
    return { detail, error: "Project URL missing." };
  }

  let response;
  try {
    response = await fetchWithTimeout(
      projectUrl,
      { credentials: "include" },
      20000
    );
  } catch (error) {
    return {
      detail,
      error: error.message || "Project detail fetch failed."
    };
  }

  if (!response.ok) {
    return {
      detail,
      error: `Project detail fetch failed (${response.status}).`
    };
  }

  const html = await response.text();
  if (!html) {
    return { detail, error: "Project detail empty response." };
  }
  const lower = html.toLowerCase();
  if (lower.includes("just a moment") || lower.includes("checking your browser")) {
    return { detail, error: "Project detail blocked." };
  }
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, "text/html");
  if (!doc) {
    return { detail, error: "Project detail parse failed." };
  }

  return scrapeProjectDetail(
    { ...detailContext, pageUrl: projectUrl },
    doc
  );
}

async function scrapeByType(pageType, context = {}) {
  if (pageType === "jobs") {
    return scrapeJobs(context);
  }
  if (pageType === "talent") {
    return scrapeTalent(context);
  }
  if (pageType === "projects") {
    return scrapeProjects(context);
  }

  return { items: [], error: "Unsupported page." };
}

async function startScrapeFlow() {
  const isProfilePage = /\/freelancers\//.test(window.location.href) || /\/profile\//.test(window.location.href);
  if (isProfilePage) {
    const profile = extractProfileContext();
    if (profile.ok) {
      chrome.runtime.sendMessage({
        type: "PROFILE_CONTEXT_UPDATED",
        upworkUrl: profile.upworkUrl,
        headline: profile.headline || "",
        skills: profile.skills || [],
        profileText: profile.profileText || ""
      });
    }
    return;
  }

  const pageType = detectPageType();
  if (!pageType) {
    return;
  }

  // Check for challenges before starting
  const preFlight = await AntiBot.preFlightCheck();
  if (!preFlight.ok) {
    // Notify background about challenge
    chrome.runtime.sendMessage({
      type: "PAGE_BLOCKED",
      pageType,
      pageUrl: window.location.href,
      threatInfo: preFlight.analysis
    });
    return;
  }

  chrome.runtime.sendMessage(
    {
      type: "PAGE_READY",
      pageType,
      url: window.location.href
    },
    async (response) => {
      if (!response) {
        return;
      }

      // Add human-like delay before processing
      await HumanSim.smartDelay('pageLoad');

      if (response.action === "SCRAPE_DETAIL") {
        const detailTarget = response.target || "jobs";
        if (isChallengePage()) {
          chrome.runtime.sendMessage({
            type: "PAGE_BLOCKED",
            runId: response.runId,
            target: detailTarget,
            pageUrl: window.location.href
          });
          return;
        }

        let detailResult = { detail: {}, error: "Unsupported detail target." };
        if (detailTarget === "jobs") {
          detailResult = await scrapeJobDetail({
            jobKey: response.jobKey || "",
            jobUrl: response.jobUrl || "",
            pageUrl: response.pageUrl || ""
          });
        } else if (detailTarget === "talent") {
          detailResult = await scrapeTalentDetail({
            profileKey: response.profileKey || "",
            profileUrl: response.profileUrl || "",
            pageUrl: response.pageUrl || ""
          });
        } else if (detailTarget === "projects") {
          detailResult = await scrapeProjectDetail({
            projectId: response.projectId || "",
            projectUrl: response.projectUrl || "",
            pageUrl: response.pageUrl || ""
          });
        }

        chrome.runtime.sendMessage({
          type: "DETAIL_RESULTS",
          runId: response.runId,
          target: detailTarget,
          jobUrl: detailResult.detail?.detail_job_url || response.jobUrl || "",
          jobKey: detailResult.detail?.detail_job_key || response.jobKey || "",
          profileUrl:
            detailResult.detail?.detail_profile_url || response.profileUrl || "",
          profileKey:
            detailResult.detail?.detail_profile_key || response.profileKey || "",
          projectUrl:
            detailResult.detail?.detail_project_url || response.projectUrl || "",
          projectId:
            detailResult.detail?.detail_project_id || response.projectId || "",
          detail: detailResult.detail || {},
          error: detailResult.error || ""
        });
        return;
      }

      if (response.action !== "SCRAPE") {
        return;
      }

      if (isChallengePage()) {
        chrome.runtime.sendMessage({
          type: "PAGE_BLOCKED",
          runId: response.runId,
          target: pageType,
          pageUrl: window.location.href
        });
        return;
      }

      const result = await scrapeByType(pageType, {
        pageIndex: response.pageIndex,
        maxPages: response.maxPages
      });
      chrome.runtime.sendMessage({
        type: "PAGE_RESULTS",
        runId: response.runId,
        target: pageType,
        items: result.items || [],
        pageUrl: result.pageUrl || window.location.href,
        pageIndex: result.pageIndex || 1,
        nextUrl: result.nextUrl || "",
        hasNext: result.hasNext || false,
        error: result.error || ""
      });
    }
  );
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message) {
    return false;
  }

  if (message.type === "EXTRACT_PROFILE_CONTEXT") {
    sendResponse(extractProfileContext());
    return true;
  }

  if (message.type !== "FETCH_PROJECT_DETAIL") {
    return false;
  }

  const detailContext = {
    projectId: message.projectId || "",
    projectUrl: message.projectUrl || "",
    pageUrl: message.pageUrl || ""
  };

  sendResponse({ ok: true });

  scrapeProjectDetailFromUrl(detailContext).then((detailResult) => {
    chrome.runtime.sendMessage({
      type: "DETAIL_RESULTS",
      runId: message.runId || "",
      target: "projects",
      projectUrl:
        detailResult.detail?.detail_project_url || detailContext.projectUrl || "",
      projectId:
        detailResult.detail?.detail_project_id || detailContext.projectId || "",
      detail: detailResult.detail || {},
      error: detailResult.error || ""
    });
  });

  return true;
});

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", startScrapeFlow);
} else {
  startScrapeFlow();
}
