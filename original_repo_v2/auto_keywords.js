/**
 * Upwork DNA - Automatic Keyword Generator
 * Generates high-value keywords based on market trends
 */

// High-value keyword categories with base keywords
const KEYWORD_CATEGORIES = {
  ai_ml: {
    base: ["AI agent", "machine learning engineer", "ChatGPT integration", "LLM development", "AI automation"],
    modifiers: ["developer", "specialist", "expert", "consultant", "architect"]
  },
  data: {
    base: ["data analyst", "data engineer", "business intelligence", "data visualization", "SQL expert"],
    modifiers: ["senior", "lead", "remote", "freelance", "contract"]
  },
  web: {
    base: ["React developer", "Full stack developer", "Node.js developer", "web scraping", "API integration"],
    modifiers: ["senior", "expert", "freelance", "remote", "startup"]
  },
  automation: {
    base: ["workflow automation", "Zapier expert", "Make automation", "Python automation", "process automation"],
    modifiers: ["specialist", "developer", "consultant", "expert", "freelance"]
  },
  mobile: {
    base: ["mobile app developer", "iOS developer", "Android developer", "React Native", "Flutter developer"],
    modifiers: ["senior", "expert", "freelance", "remote", "contract"]
  }
};

// Trending tech keywords (2025)
const TRENDING_KEYWORDS = [
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
  { keyword: "Node.js developer", priority: "NORMAL", score: 74 }
];

/**
 * Generate N high-value keywords automatically
 */
function generateAutoKeywords(count = 10) {
  const keywords = [];

  // Add trending keywords first
  for (const kw of TRENDING_KEYWORDS) {
    if (keywords.length >= count) break;
    keywords.push({
      id: `auto_${Date.now()}_${keywords.length}`,
      keyword: kw.keyword,
      priority: kw.priority,
      estimatedValue: kw.score,
      source: "auto_trending"
    });
  }

  // If we need more, generate from categories
  if (keywords.length < count) {
    const categories = Object.keys(KEYWORD_CATEGORIES);
    for (const cat of categories) {
      if (keywords.length >= count) break;
      const category = KEYWORD_CATEGORIES[cat];
      const base = category.base[Math.floor(Math.random() * category.base.length)];
      const mod = category.modifiers[Math.floor(Math.random() * category.modifiers.length)];
      keywords.push({
        id: `auto_${Date.now()}_${keywords.length}`,
        keyword: `${base} ${mod}`,
        priority: "NORMAL",
        estimatedValue: 60 + Math.floor(Math.random() * 20),
        source: "auto_generated"
      });
    }
  }

  return keywords.slice(0, count);
}

/**
 * Save auto-generated keywords to Chrome Storage
 */
async function saveAutoKeywords(count = 10) {
  const keywords = generateAutoKeywords(count);

  const queue = await getQueue();
  const now = new Date().toISOString();

  for (const kw of keywords) {
    // Check if already exists
    const exists = queue.keywords.find(k =>
      k.keyword.toLowerCase() === kw.keyword.toLowerCase()
    );

    if (!exists) {
      queue.keywords.push({
        id: kw.id,
        keyword: kw.keyword,
        targets: ["jobs", "talent", "projects"],
        maxPages: 0,
        status: "pending",
        priority: kw.priority,
        estimatedValue: kw.estimatedValue,
        addedAt: now,
        startedAt: null,
        completedAt: null,
        runId: null,
        results: { jobs: 0, talent: 0, projects: 0 },
        source: kw.source
      });
    }
  }

  await saveQueue(queue);
  console.log(`[AutoKeywords] Generated ${keywords.length} keywords`);

  return { ok: true, count: keywords.length, keywords };
}

/**
 * Get auto-generated keywords without saving
 */
function getAutoKeywords(count = 10) {
  return generateAutoKeywords(count);
}

// Export for use in background.js
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { generateAutoKeywords, saveAutoKeywords, getAutoKeywords };
}
