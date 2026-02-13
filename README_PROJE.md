# 🚀 Upwork DNA - Otonom Market Intelligence Sistemi

## 📋 Proje Özeti

**Upwork DNA**, Upwork platformundan otomatik veri toplama, NLP analizi ve keyword keşfi yapan otonom bir sistemdir. Sistem, Chrome Extension + Python + Electron entegrasyonu ile tam otomatik çalışır.

### 🎯 Ana Hedefler

1. **Otonom Scraping**: Extension otomatik olarak jobs, talent ve projects verilerini toplar
2. **NLP Keyword Generation**: Toplanan veriden yeni yüksek değerli keyword'lar üretir
3. **Data Flywheel**: Analiz → Keywords → Scraping döngüsü ile sürekli kendini geliştirir
4. **Dashboard Monitoring**: Tüm süreçleri gerçek zamanlı izleme imkanı

---

## 🏗️ Mimari

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CHROME EXTENSION LAYER                          │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐   │
│  │ Queue Syst. │───▶│  Scraper     │───▶│ Auto Export (CSV)   │   │
│  │ (Priority)  │    │ (Content)    │    │ Downloads/          │   │
│  └─────────────┘    └──────────────┘    └─────────────────────┘   │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FILE SYSTEM BRIDGE                              │
│  /Users/dev/Downloads/upwork_dna/ (CSV + JSON files)              │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PYTHON ANALYSIS ENGINE                          │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐   │
│  │ Auto-Sync   │───▶│ NLP Engine   │───▶│ Keyword Generator   │   │
│  │ (Watchdog)  │    │ (pandas/NLP) │    │ (recommended.json)   │   │
│  └─────────────┘    └──────────────┘    └─────────────────────┘   │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      EXTENSION FEEDBACK                             │
│  Extension reads recommended_keywords.json → Queue → Scraping       │
└─────────────────────────────────────┬───────────────────────────────┘
                                      │
                                      ▼ (DÖNGÜ DEVAM EDER)
┌─────────────────────────────────────────────────────────────────────┐
│                      STREAMLIT DASHBOARD                            │
│  http://localhost:8501 - Real-time monitoring & analytics          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Proje Yapısı

```
/Users/dev/Documents/upworkextension/
│
├── 📂 original_repo/                    # Orijinal çalışan extension (947 satır)
│   ├── manifest.json
│   ├── background.js
│   ├── content_script.js
│   ├── popup.html/js/css
│   └── (Basit, güvenilir scraping)
│
├── 📂 original_repo_v2/                 # Geliştirilmiş extension (1721 satır)
│   ├── manifest.json                    # Queue sistemi + NLP entegrasyonu
│   ├── background.js                    # Priority queue management
│   ├── content_script.js                # Context invalidated fix
│   ├── popup.html/js/css
│   └── auto_keywords.js
│
├── 📂 analist/                          # Python analiz motoru
│   ├── 📂 data/dataanalist/             # Scraped data storage (76 CSV)
│   ├── 📂 dashboard/
│   │   └── app.py                       # Streamlit dashboard
│   ├── nlp_keyword_generator.py         # NLP keyword generation
│   └── (pandas, scikit-learn, NLP tools)
│
├── 📄 auto_sync_extension.py            # Downloads → Dashboard sync
├── 📄 launch_manager.py                 # Tüm servisleri yönetir
│
└── 📂 /Applications/Upwork DNA.app/     # Electron desktop app
    ├── Contents/Resources/
    │   ├── main.js                      # Electron main process
    │   ├── index.html                   # Embedded dashboard (iframe)
    │   └── node_modules/electron/       # Embedded Electron
    └── (Dashboard birleşik uygulama içinde)
```

---

## 🔄 Data Flywheel (Tam Otonom Döngü)

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. SCRAPING BAŞLAT                                                  │
│    Extension queue'dan bir keyword alır                            │
│    → Upwork'te jobs/talent/projects arar                          │
│    → 7 sayfa → ~50-100 item toplar                                 │
│    → CSV olarak /Users/dev/Downloads/upwork_dna/ klasörüne kaydeder│
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. AUTO-SYNC                                                        │
│    Python watchdog (auto_sync_extension.py) çalışır                │
│    → Yeni CSV/JSON dosyalarını algılar                             │
│    → /Users/dev/Documents/upworkextension/analist/data/dataanalist/│
│      klasörüne kopyalar                                             │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. NLP ANALİZ                                                      │
│    nlp_keyword_generator.py çalışır                                │
│    → CSV'leri okur (pandas)                                        │
│    → Skill/technology extraction (regex patterns)                  │
│    → Frequency analysis                                            │
│    → Opportunity scoring (demand vs supply gap)                    │
│    → recommended_keywords.json üretir                             │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. KEYWORD INJECTION                                               │
│    Extension Downloads API ile recommended_keywords.json'u okur   │
│    → Yeni keyword'ları queue'ya ekler                              │
│    → Priority scoring (CRITICAL > HIGH > NORMAL > LOW)            │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. DÖNGÜ DEVAM EDER                                                │
│    Queue bir sonraki keyword'u otomatik başlatır                  │
│    → Scraping → Sync → NLP → Keywords → Scraping (tekrar)          │
│    → 7/24 otonom çalışır                                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎛️ Kullanım

### 1. Extension'ı Başlatma

```bash
# 1. Chrome'da git: chrome://extensions/
# 2. Developer mode aç
# 3. "Load unpacked" ile bu klasörü yükle:
#    /Users/dev/Documents/upworkextension/original_repo_v2/
```

### 2. Servisleri Başlatma (Launch Manager)

```bash
cd /Users/dev/Documents/upworkextension
python3 launch_manager.py start
```

Bu başlatır:
- ✅ Orchestrator API (http://127.0.0.1:8000)
- ✅ Auto-sync (Downloads izleme)
- ✅ Streamlit Dashboard (http://localhost:8501)

Not: `8501` doluysa dashboard atlanır, API yine başlar.

Yenileme döngüsü (backend analiz cycle) varsayılanı `5 dk`:

```bash
cd /Users/dev/Documents/upworkextension/backend
# 300 = 5 dakika
ORCHESTRATOR_CYCLE_SECONDS=300
```

### 2.1 Backend API Otomatik Başlatma (macOS Login)

```bash
cd /Users/dev/Documents/upworkextension
./install_backend_autostart_macos.sh
```

Bu kurulum artık 2 servis kurar:
- `com.upworkdna.backend.api` (FastAPI)
- `com.upworkdna.backend.watchdog` (`/health` cevap vermezse backend'i otomatik restart eder)
- `com.upworkdna.dashboard` (Streamlit, http://localhost:8501)

Kontrol:

```bash
./status_backend_autostart_macos.sh
```

Kaldırma:

```bash
./uninstall_backend_autostart_macos.sh
```

### 2.2 Dayanıklılık Ayarları (backend/.env)

```bash
ORCHESTRATOR_CYCLE_SECONDS=300
SQLITE_BUSY_TIMEOUT_MS=5000
DB_WRITE_LOCK_TIMEOUT_SECONDS=45
RUN_INGEST_MIN_PROCESS_SECONDS=12
RUN_INGEST_REFRESH_SECONDS=90
RUN_INGEST_MIN_NEW_ITEMS=20
RUN_INGEST_RETRY_INTERVAL_SECONDS=2
RUN_INGEST_RETRY_MAX_BACKOFF_SECONDS=60
RUN_INGEST_RETRY_MAX_QUEUE=3000
RUN_INGEST_WRITE_TIMEOUT_FINAL_SECONDS=4.0
RUN_INGEST_WRITE_TIMEOUT_PROGRESS_SECONDS=1.0
```

Not: `/health` ve `/v1/telemet` artık `ingest_retry_queue` alanını döner. Bu değer `0` değilse backend kilitlenme anında gelen ingest payload'larını sıraya alıp otomatik tekrar yazıyor demektir.

### 3. Electron App

```bash
# /Applications klasörüne zaten kurulu
open "Upwork DNA.app"
```

Dashboard'u uygulama içinde gösterir (ayrı browser gerekmez).

### 4. Queue'yu Başlatma

Extension popup'ında:
- **Queue'yu başlat** butonuna tıkla
- 20+ otomatik keyword yüklenir
- Scraping otomatik başlar

---

## 📊 Dashboard

**URL**: http://localhost:8501

**Özellikler**:
- 📈 Jobs, Talent, Projects istatistikleri
- 🔄 Real-time updates
- 📁 CSV dosya listesi
- 🤖 NLP keywords
- 📊 Market gap analizi

---

## 🔧 Teknik Detaylar

### Chrome Extension (Manifest V3)

**Dosya**: `original_repo_v2/manifest.json`

```json
{
  "manifest_version": 3,
  "name": "Upwork DNA Scraper",
  "version": "2.6.0",
  "permissions": ["storage", "downloads", "tabs", "unlimitedStorage"],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [...]
}
```

### Queue Sistemi (Priority Queue v3.0)

**Özellikler**:
- 4 Priority seviyesi: CRITICAL, HIGH, NORMAL, LOW
- Exponential backoff retry
- Dependency management
- Auto-export on completion

**Keyword yapısı**:
```javascript
{
  id: "kw_auto_1234567890_0",
  keyword: "AI agent",
  targets: ["jobs", "talent", "projects"],
  maxPages: 7,
  status: "pending|running|completed|error",
  priority: "CRITICAL",
  estimatedValue: 95,
  source: "auto_generated|nlp_generated"
}
```

### NLP Keyword Generator

**Dosya**: `analist/nlp_keyword_generator.py`

**Algorithm**:
1. Load latest CSV files (jobs, talent, projects)
2. Extract skills using regex patterns
3. Calculate frequency scores
4. Generate opportunity scores
5. Save to `recommended_keywords.json`

**Patterns**:
```python
TECH_PATTERNS = [
    r'AI\s+\w+', r'machine learning', r'deep learning', r'LLM', r'GPT',
    r'ChatGPT', r'Python', r'JavaScript', r'TypeScript', r'React',
    r'API\s+\w+', r'web scraping', r'automation', r'data\s+\w+',
    # ... 20+ patterns
]
```

---

## 🐛 Bilinen Sorunlar ve Çözümler

### 1. "Extension context invalidated" Hatası

**Sorun**: Extension reload sonrası eski content script'ler crash olur

**Çözüm**: Content script'e context kontrolü eklendi
```javascript
if (!chrome.runtime || !chrome.runtime.sendMessage) {
  console.warn("Extension context invalidated");
  return;
}
```

**Kullanıcı için**: Extension reload sonrası Upwork sekmelerini yenileyin (F5)

### 2. 1 Sayfada Takılma

**Sorun**: repo_v2'de karmaşık queue sistemi bazen takılıyor

**Çözüm**: original_repo'yu kullanmak veya repo_v2'yi debug etmek

---

## 📈 Veri Hacmi

**Mevcut durum** (2026-02-07):
- 📁 76 CSV dosyası
- 📊 ~294K jobs
- 👤 ~2.5K talent
- 📁 ~25K projects
- 🤖 15 NLP keywords (latest)

---

## 🚀 Geliştirme Roadmap

### ✅ Tamamlanan
- [x] Chrome Extension scraping
- [x] Auto-sync system
- [x] NLP keyword generator
- [x] Streamlit dashboard
- [x] Electron desktop app
- [x] Queue management system
- [x] Data flywheel (partial)

### 🔄 Devam Eden
- [ ] Full autonomous flywheel (testing)
- [ ] Statistical significance testing
- [ ] Hook analysis
- [ ] Pricing psychology
- [ ] A/B testing framework

### 📋 Planlanan
- [ ] Profile optimizer (title generator)
- [ ] Market gap calculator (Cohen's d)
- [ ] Opportunity scoring algorithm

---

## 🛠️ Troubleshooting

### Extension Çalışmıyor

```bash
# 1. Console'da hata kontrolü
chrome://extensions/ → Upwork DNA → "Errors" butonu

# 2. Service worker restart
chrome://extensions/ → Details → Service Worker → "Stop" → "Start"

# 3. Content script'in yüklendiğini kontrol et
Upwork sayfasında → F12 → Console → "[Content Script]" mesajları
```

### Dashboard Çalışmıyor

```bash
# Dashboard'i manuel başlat
cd /Users/dev/Documents/upworkextension/analist
streamlit run dashboard/app.py --server.headless true
```

### Auto-sync Çalışmıyor

```bash
# Auto-sync'i manuel başlat
cd /Users/dev/Documents/upworkextension
python3 auto_sync_extension.py
```

---

## 📝 Notlar

1. **Cloudflare Koruması**: Headless browser çalışmaz, gerçek Chrome gerekli
2. **Rate Limiting**: 2.5-4.5 saniye aralıklarla request
3. **Max Pages**: Her keyword için 7 sayfa (prevent overload)
4. **Data Storage**: Chrome Storage + CSV + JSON hibrit

---

## 👤 Kullanıcı Profili

- **İsim**: Tuncer Timur
- **Rol**: Security Researcher / Freelancer
- **Amaç**: Upwork'te maksimum iş almak, en iyi profili oluşturmak
- **Hedefler**:
  - En yüksek value jobs'ları bulmak
  - En az competition alanlarında uzmanlaşmak
  - Profitability最大化

---

## 📞 Destek

**Proje Dizini**: `/Users/dev/Documents/upworkextension/`
**Dashboard**: http://localhost:8501
**Extension**: chrome://extensions/

---

*Son güncelleme: 2026-02-08*
*Version: 2.6.0*
