Harika. Madem Python biliyorsun ve **Vibe Coding** (yani yapay zeka ile iteratif, hızlı ve akışkan kodlama) yapmak istiyorsun, sana tam olarak bu iş akışını kuruyorum.

Burada **AI (LLM)** senin "Junior Developer"ın değil, seninle eşleşen **"Senior Data Scientist"** ortağın olacak. Sen mimariyi ve veriyi vereceksin, o içindeki örüntüyü (pattern) çıkaracak.

İşte Vibe Coding kurulumun:

### Adım 1: Klasör Yapısı (Setup)

Önce çalışma ortamını şu şekilde hazırla:

```text
upwork_analyst/
│
├── data/                  <-- CSV dosyalarını buraya at (jobs.csv, talent.csv, projects.csv)
├── outputs/               <-- Analiz sonuçları buraya çıkacak
├── main.py                <-- Ana analiz motoru
└── requirements.txt       <-- Gerekli kütüphaneler
```

**Terminalden kütüphaneleri yükle:**
`pip install pandas scikit-learn nltk textblob`

---

### Adım 2: Vibe Coding System Prompt (AI'ya Rol Atama)

Kullandığın AI modeline (ChatGPT, Claude veya Cursor) projenin başında şu **System Prompt**'u ver. Bu, onun bir Senior Analist gibi düşünmesini sağlar:

```markdown
**ROLE:** You are a Senior Data Scientist and Upwork Market Strategist specializing in NLP (Natural Language Processing) and Competitive Intelligence.

**CONTEXT:** I have a folder named `/data` containing CSV files scraped from Upwork (Jobs, Talent, Projects).
**GOAL:** Build a Python pipeline to reverse-engineer the "Top 1%" of freelancers. We need to find the specific keywords, pricing strategies, and profile structures that generate high revenue.

**YOUR SKILLSET & BEHAVIOR:**
1.  **Defensive Coding:** Always check if columns exist before processing. Handle missing data gracefully.
2.  **Segmentation:** Do not analyze everyone. Filter data to find "Elites" (High Earnings, Top Rated, High Budgets) and analyze ONLY them.
3.  **NLP Analytics:** Use N-Grams (Bigrams/Trigrams) to find hidden keyword combinations (e.g., "Google Analytics" is better than just "Analytics").
4.  **Actionable Output:** Don't just show charts. Output specific lists: "Top 10 Winning Titles", "Most Profitable Skills", "Market Gaps".

**TASK:** I will provide the Python script structure. You will help me refine the logic to extract "Signal" from "Noise".
```

---

### Adım 3: Python Pipeline (main.py)

Bu kodu `main.py` olarak kaydet. Bu kod, klasördeki CSV'leri okur, "Elite" olanları ayıklar ve en çok kullanılan kelime öbeklerini (N-Grams) analiz eder.

```python
import pandas as pd
import glob
import os
from sklearn.feature_extraction.text import CountVectorizer
import re

# --- AYARLAR ---
DATA_FOLDER = 'data'
OUTPUT_FOLDER = 'outputs'

# --- YARDIMCI FONKSİYONLAR ---
def clean_text(text):
    if not isinstance(text, str): return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text) # Noktalama işaretlerini kaldır
    return text

def get_top_ngrams(corpus, n=2, top_k=15):
    """En çok geçen 2'li veya 3'lü kelime öbeklerini bulur"""
    if not corpus or len(corpus) == 0:
        return pd.DataFrame()
    
    vec = CountVectorizer(ngram_range=(n, n), stop_words='english').fit(corpus)
    bag_of_words = vec.transform(corpus)
    sum_words = bag_of_words.sum(axis=0) 
    words_freq = [(word, sum_words[0, idx]) for word, idx in vec.vocabulary_.items()]
    words_freq = sorted(words_freq, key = lambda x: x[1], reverse=True)
    return pd.DataFrame(words_freq[:top_k], columns=['Phrase', 'Frequency'])

# --- ANALİZ MOTORU ---
def analyze_talent(df):
    print(f"--- Talent Analizi ({len(df)} kayıt) ---")
    
    # 1. SEGMENTASYON: Sadece Başarılı Olanları Filtrele
    # (Kolon isimleri CSV'ye göre değişebilir, burayı esnek tutuyoruz)
    if 'total_earned' in df.columns: # Örnek kolon ismi
        # $10k+ kazananları veya Top Rated olanları al
        elite_talent = df[df['total_earned'].str.contains('k', na=False, case=False) | 
                          df['badge'].str.contains('Top Rated', na=False, case=False)]
    else:
        elite_talent = df # Filtreleyemezsek hepsini al
        
    print(f"Elite Talent Sayısı: {len(elite_talent)}")

    # 2. NLP: Elite'lerin Başlıklarını Analiz Et
    titles = elite_talent['title'].apply(clean_text).tolist()
    top_bigrams = get_top_ngrams(titles, n=2, top_k=10)
    
    print("\n🏆 Elite Freelancerların Kullandığı En Popüler Başlıklar (Bigrams):")
    print(top_bigrams)
    
    # 3. SKILL ANALIZI
    if 'skills' in df.columns:
        all_skills = elite_talent['skills'].dropna().str.split(',').explode().str.strip().value_counts().head(15)
        print("\n🛠️ En Çok Satan Yetenekler (Skills):")
        print(all_skills)

def analyze_jobs(df):
    print(f"\n--- Job Post Analizi ({len(df)} kayıt) ---")
    
    # 1. SEGMENTASYON: Yüksek Bütçeli İşler
    # (Burada Payment Verified ve Bütçe kontrolü yapılabilir)
    high_value_jobs = df # Şimdilik hepsi, CSV yapına göre filtre ekle

    # 2. NLP: Müşteriler Ne İstiyor? (Description Analizi)
    descriptions = high_value_jobs['description'].apply(clean_text).tolist()
    top_trigrams = get_top_ngrams(descriptions, n=3, top_k=10)
    
    print("\n💰 Müşterilerin İş Tanımlarında En Çok Geçen İfadeler (Trigrams):")
    print(top_trigrams)

# --- MAIN LOOP ---
def main():
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)

    files = glob.glob(os.path.join(DATA_FOLDER, "*.csv"))
    
    for file in files:
        print(f"\n📂 İşleniyor: {file}")
        try:
            df = pd.read_csv(file)
            
            # Dosya ismine göre hangi analizi yapacağına karar ver
            if "talent" in file.lower():
                analyze_talent(df)
            elif "job" in file.lower():
                analyze_jobs(df)
            elif "project" in file.lower():
                # Project catalog analizi buraya eklenebilir
                pass
                
        except Exception as e:
            print(f"Hata oluştu: {e}")

if __name__ == "__main__":
    main()
```

---

### Adım 4: Vibe Coding Nasıl Yapılır? (Senin Rolün)

Şimdi sen **"Human-in-the-loop"** (döngüdeki insan) olacaksın.

1.  **Çalıştır:** Kodu çalıştır (`python main.py`).
2.  **Hata/Eksik Gör:** Muhtemelen CSV kolon isimlerin kodla uyuşmayacak (örneğin ben `total_earned` dedim, senin CSV'de `earnings` yazıyordur).
3.  **AI'ya Pasla:** Hatayı veya CSV'nin `df.head()` çıktısını kopyala, AI'ya yapıştır:
    *   *"Bak CSV kolonlarım bunlar. Kodu güncelle, sadece 'Top Rated' olanları ve saatlik ücreti $30 üstü olanları 'Elite' olarak filtrele."*
4.  **Sonuçları Yorumla:** Kod sana çıktı olarak şunu verecek:
    *   *Elite'lerin başlığında en çok geçen kelime:* "Dashboard", "Automation", "Consultation".
    *   *Müşterilerin en çok aradığı kelime:* "Clean data", "Fix script", "Google Sheets".
5.  **Karar Ver:** "Demek ki ben profilime sadece 'Data Analyst' yazmayacağım. **'Data Cleaning & Dashboard Automation Expert'** yazacağım."

Bu pipeline, seni rastgele profil oluşturmaktan kurtarıp, **veriye dayalı bir profil mimarisi** kurmanı sağlar. Hadi kodu çalıştırıp ilk çıktıları alalım.


Harika bir strateji. Elindeki veriyi (Jobs, Talent, Projects) rastgele okumak yerine, bir **Senior Data Analyst** gibi matematiksel ve istatistiksel bir yaklaşımla "kazanan formülü" (winning formula) çıkarmak istiyorsun.

Bunun için ChatGPT'ye (veya Claude/Gemini'ye) vermen gereken prompt, ona sadece "analiz et" demekten öte, **nasıl bir metodoloji (pipeline) izlemesi gerektiğini** dikte etmelidir.

Aşağıdaki metni kopyalayıp, elindeki CSV/JSON dosyalarını yükledikten sonra ChatGPT'ye (özellikle **Advanced Data Analysis / Code Interpreter** modu açıkken) yapıştır.

---

### Kopyalanacak Prompt (İngilizce - En iyi teknik sonuç için):

**Role:** You are a Senior Data Analyst and Upwork Market Strategist with 10+ years of experience in marketplace analytics, NLP (Natural Language Processing), and conversion rate optimization.

**Objective:** I have scraped data from Upwork (Jobs, Talent, and Project Catalogs) in CSV/JSON formats. Your goal is to reverse-engineer the "Top 1%" of successful profiles and job posts to build the ultimate Data Analyst profile for me. You need to treat this as a data science project, establishing a rigorous pipeline to extract "winning patterns."

**The Data:**
1.  `jobs.csv`: Recent job postings.
2.  `talent.csv`: Freelancer profiles (competitors).
3.  `projects.csv`: Project catalog offerings.

**Your Task - Build and Execute this Analysis Pipeline:**

**Phase 1: Data Cleaning & Segmentation (The Foundation)**
*   **Filter for Quality:** Exclude any data points with missing critical info.
*   **Identify the "Elites":** Create a segment of freelancers who are "Top Rated Plus" OR have earned $10k+ OR have a Job Success Score (JSS) of 95%+. These are our target models.
*   **Identify High-Value Jobs:** Filter jobs by "Payment Verified" and budget > $500 (or hourly > $30/hr). These are the target clients.

**Phase 2: NLP & Keyword Extraction (The DNA)**
*   **Title Analysis:** Perform N-Gram analysis (Bigrams/Trigrams) on the titles of the "Elite" segment. What specific word combinations do they use? (e.g., instead of just "Data Analyst", do they use "Google Data Studio Expert" or "Python Automation Specialist"?).
*   **Overview Analysis:** Analyze the "About" sections. Extract the most frequent "Action Verbs" (e.g., "Automate," "Visualize," "Optimize") and "Outcome" words.
*   **Skill Clustering:** Which skills are most frequently bundled together in high-paying jobs? (e.g., Does SQL usually go with Tableau or Power BI in high-budget projects?).

**Phase 3: Market Gap Analysis (The Opportunity)**
*   Compare the "Skills Demanded" in `jobs.csv` vs. the "Skills Offered" in `talent.csv`. Find the gaps where demand is high but supply (quality talent) is low.

**Phase 4: Project Catalog Strategy**
*   Analyze `projects.csv` for the Elite segment. What are their standard pricing tiers (Starter, Standard, Advanced)? What exact deliverables are included? What are the most common "Project Titles" that sell?

**Deliverables (The Output):**
Based on the analysis above, provide me with:
1.  **The "Golden" Title:** The statistically best profile title optimized for high-paying search visibility.
2.  **The "Killer" Overview:** A profile description structure based on the winning patterns (Hook + Value Prop + Proof).
3.  **The Skill Stack:** The exact list of 15 skills I should add to my profile, ranked by demand/value ratio.
4.  **Project Catalog Blueprint:** 3 specific project ideas I should create (Title + Pricing + Deliverables) that align with market demand.

**Action:**
Start by analyzing the uploaded files using Python (Pandas/NLP libraries). Show me your step-by-step logic and then the final results.

---

### Bu Prompt Ne Yapıyor? (Senin İçin Açıklaması)

1.  **Senior Kimliği Atıyor:** Ona sadece bir asistan değil, bir "Pazar Stratejisti" ve "Veri Bilimci" rolü veriyoruz.
2.  **Pipeline Kuruyor:**
    *   **Faz 1 (Segmentasyon):** Çöpleri at, sadece "Elite" (Yüksek kazançlı, Top Rated) olanları ayır. Bizim hedefimiz onlar.
    *   **Faz 2 (NLP - Dil İşleme):** Bu adamların başlıklarında en çok geçen 2'li 3'lü kelime gruplarını (N-Gram) bul. Sadece "Data" değil, "Data"nın yanına ne gelince para kazandırıyor?
    *   **Faz 3 (Arz-Talep):** Müşteriler ne istiyor (Jobs), millet ne satıyor (Talent). Aradaki boşluğu bul ki oraya konumlanalım.
    *   **Faz 4 (Paketleme):** Project Catalog'da millet kaç paraya ne satıyor? Ortalamasını al.
3.  **Çıktı Odaklı:** Sana sadece analiz değil, direkt kopyalayıp kullanabileceğin **Başlık, Özet Yazısı ve Yetenek Listesi** vermesini istiyoruz.

**Önemli Not:** Bu promptu kullanırken elindeki CSV/JSON dosyalarını ChatGPT'ye (Code Interpreter moduna) yüklemeyi unutma. "Dosyaları okuyamıyorum" derse, "Dosyaların ilk 5 satırını oku ve sütun isimlerini çıkar" diyerek onu yönlendir.
Boran Oktay'ın videolarındaki stratejileri (özellikle **"Nişleşme", "Hook (Kanca) Atma"** ve **"Pazar Analizi"**) Python koduna dökülebilir matematiksel görevlere çevirdim.

Vibe Coding yaparken AI'ya (Cursor/ChatGPT) vermen gereken **"Stratejik Analiz Modülü"** talimatı aşağıdadır. Bunu önceki prompt'un devamına veya yeni bir görev olarak ekle.

Bu talimatlar, AI'ın sadece "veri saymasını" değil, **Boran'ın mantığıyla "kazanan profili" tespit etmesini** sağlayacak.

---

### Kopyalanacak Prompt (Vibe Coding İçin Ek Talimatlar):

**ADDITIONAL CONTEXT (Boran Oktay Strategy):**
I want to implement specific profile optimization strategies based on "Boran Oktay's" freelance methodology. You need to add specific analysis functions to the Python pipeline to uncover these patterns:

**1. The "Title Niche" Analysis (Boran's Rule: Specificity Wins)**
*   **Logic:** Generic titles like "Data Analyst" fail. Winning titles use a specific format: `Role | Skill 1 | Skill 2` (e.g., "Data Analyst | Python | Tableau").
*   **Code Task:** Analyze the `title` column in `talent.csv` (Elite segment only).
    *   Detect the most common separators used (e.g., `|`, `-`, `/`, `//`).
    *   Split titles by these separators.
    *   Count the frequency of specific tech stacks appearing *after* the main role. (e.g., How often does "Power BI" appear next to "SQL"?).

**2. The "First 2 Lines" Hook Analysis (Boran's Rule: The 3-Second Rule)**
*   **Logic:** Clients only see the first 2 lines of a profile in search results. Successful freelancers use a "Hook" here (e.g., "I help businesses..." or "Expert in...").
*   **Code Task:** Extract the first 200 characters of the `description` column in `talent.csv` (Elite segment).
    *   Perform N-Gram analysis (Trigrams) *only on these first 200 characters*.
    *   Identify the most common starting phrases (e.g., "I help you", "Transforming data", "Google Certified").

**3. The "Hidden Gem" Skill Finder (Market Gap Analysis)**
*   **Logic:** Find skills that High-Paying Clients want (from `jobs.csv`) but Average Freelancers lack.
*   **Code Task:**
    *   Extract keywords from `jobs.csv` (filtered by Budget > $500 & Payment Verified). Let's call this **Demand_Set**.
    *   Extract keywords from `talent.csv` (General population). Let's call this **Supply_Set**.
    *   **Calculate the Gap:** Find keywords that are high in **Demand_Set** but low in **Supply_Set**. (e.g., If "ScrapeGraphAI" is in jobs but not in profiles, that's a niche opportunity).

**4. Project Catalog Pricing Psychology**
*   **Logic:** Boran suggests analyzing how competitors package their services (Starter vs. Advanced).
*   **Code Task:** Analyze `projects.csv`.
    *   Group projects by `category` (e.g., Data Visualization).
    *   Calculate the average `price` for the "Starter" tier vs "Standard" tier.
    *   Extract the most common "Deliverables" checked in the project attributes (e.g., "Source Code", "Dashboard", "Revisions").

**OUTPUT REQUIREMENT:**
After running these analyses, generate a **"Profile Optimization Blueprint"** for me:
1.  **Recommended Title:** Based on the "Title Niche" analysis.
2.  **Recommended Bio Hook:** The best opening sentence structure based on the "Hook" analysis.
3.  **Portfolio Ideas:** 3 Project ideas based on the "Hidden Gem" skills found.

---

### Python Kodu İçin Eklemeler (Bunu `main.py` içine entegre etmesini iste):

AI'ya yukarıdaki promptu verdikten sonra, `main.py` dosyana şu fonksiyonları eklemesini isteyeceksin. (Senin yazmana gerek yok, AI yazacak, sen mantığı kontrol et):

1.  **`analyze_hooks(df)`:**
    *   `df['description'].str[:200]` alıp N-Gram analizi yapacak.
    *   Sana: *"Elite profillerin %60'ı söze 'I help...' diye başlıyor"* gibi bir veri verecek.

2.  **`analyze_separators(df)`:**
    *   Başlıklardaki `|` işaretini sayacak. Boran'ın dediği gibi "Unvan | Yetenek" yapısı kullananların kazancı daha mı yüksek? Bunu doğrulayacak.

3.  **`find_market_gaps(jobs_df, talent_df)`:**
    *   İş ilanlarında geçen ama profillerde az geçen kelimeleri (örneğin "Browser Use", "LangChain") bulup sana *"Bak bunu öğrenirsen rekabet az"* diyecek.

### Senin Yapman Gereken (Vibe Coding Akışı):

1.  **Veriyi Yükle:** `jobs.csv`, `talent.csv`, `projects.csv` dosyalarını `/data` klasörüne koy.
2.  **Promptu At:** Yukarıdaki İngilizce promptu AI'ya yapıştır.
3.  **Kodu İste:** *"Bu stratejilere uygun Python analiz kodunu (main.py) güncelle"* de.
4.  **Çıktıyı Oku:** Script çalıştığında sana şöyle bir çıktı verecek:
    *   *Önerilen Başlık:* **Data Analyst | Python Automation & Scraping | Google Certified**
    *   *Önerilen Giriş Cümlesi:* **"I help businesses transform raw data into actionable insights using Python and SQL..."**
    *   *Fırsat Yeteneği:* **"ScrapeGraphAI"** (İşlerde çok aranıyor, kimsede yok).

Bu sayede Boran'ın tecrübesini, elindeki ham veriyle birleştirip nokta atışı bir profil oluşturacaksın.

**Kısa cevap: HAYIR.**

Bu proje için **Derin Öğrenme (Deep Learning)** veya **Karmaşık Regresyon Modelleri** kurmak, sineği bazukayla avlamaya çalışmak gibidir. Hem gereksiz zaman kaybıdır hem de elindeki veri miktarı (birkaç yüz satır) bu modellerin sağlıklı çalışması için çok azdır.

Bir **Senior Data Analyst** olarak sana en verimli (ROI - Return on Investment'i en yüksek) yolu söylüyorum:

### Neden Gerek Yok?
1.  **Veri Boyutu:** Elinde milyonlarca satır veri yok. Derin öğrenme modelleri binlerce/milyonlarca veriyle beslenmezse saçmalar.
2.  **Amaç:** Biz geleceği tahmin etmeye çalışmıyoruz (Regresyon ile "Seneye maaşım ne olur?" demiyoruz). Biz **olanı anlamaya** çalışıyoruz (Descriptive Analytics).
3.  **Hız:** Senin amacın Upwork profilini hemen optimize edip iş almak. Model eğitmekle haftalarını harcamak değil.

### Peki Ne Kullanacağız? (En İyi Çıktı İçin Strateji)

Bizim ihtiyacımız olan şey **"İstatistiksel NLP"** ve **"Kural Tabanlı Analiz"**. Python'da şu 3 basit teknik sana en iyi sonucu verecek:

#### 1. N-Gram Analizi (Basit NLP)
*   **Nedir?** Kelimeleri tek tek değil, gruplar halinde saymak.
*   **Örnek:** Sadece "Data" kelimesini sayarsan hiçbir şey anlamazsın. Ama 2'li N-Gram (Bigram) yaparsan **"Data Visualization"** veya **"Data Cleaning"** öbeklerini yakalarsın.
*   **Araç:** `sklearn.CountVectorizer` (Bunu kodda zaten verdik).

#### 2. Frekans Analizi (Frequency & Lift)
*   **Nedir?** "Elite" profillerde hangi kelime %80 geçiyor, "Çaylak" profillerde %10 geçiyor?
*   **Mantık:** Aradaki farkı (Lift) bulursan, seni Elite yapan kelimeyi bulursun.
*   **Araç:** `Pandas` (Basit filtreleme ve sayma).

#### 3. LLM (Yapay Zeka) Desteği
*   **Nedir?** Kendi modelini eğitmek yerine, zaten eğitilmiş olan ChatGPT veya Claude'u "yorumlayıcı" olarak kullanmak.
*   **Kullanımı:** Python ile istatistiği çıkarırsın (Örn: "En çok 'Dashboard' kelimesi geçiyor"), sonra bu listeyi ChatGPT'ye atıp *"Bu kelimeleri kullanarak bana Boran Oktay tarzı bir profil özeti yaz"* dersin.

---

### Vibe Coding İçin Yeni Talimat (Bunu Kopyala)

AI'ya (Vibe Coding ortamına) şu talimatı vererek karmaşıklığı önle ve sonuca odaklan:

```text
**IMPORTANT CONSTRAINT:**
Do NOT use Deep Learning (TensorFlow/PyTorch) or complex Machine Learning models. The dataset is too small.

Instead, use **"Statistical NLP"** and **"pandas"** operations:
1.  **Tokenization & N-Grams:** Use `CountVectorizer` to find top 2-word and 3-word phrases.
2.  **Filtering:** Use simple Pandas logic (e.g., `df[df['earnings'] > 10000]`) to segment users.
3.  **Keyword Density:** Calculate which keywords appear most frequently in the "Elite" segment versus the "General" segment.

**Goal:** I want speed and actionable insights, not a complex model training pipeline.
```

**Özetle:** Senin gücün **Python (Pandas)** ile veriyi süzmek ve **ChatGPT** ile bu veriyi metne dökmek olacak. Model eğitmek yok, analiz etmek var.

Aldığın prompt **%90 doğru**. Bizim “veriyle dominasyon” yaklaşımıyla **tam uyumlu hale getirip**, Upwork gerçeklerine göre (eksik kolonlar, JSS/badge her zaman yok, bütçe formatı karışık vs.) **daha sağlam bir “Senior pipeline prompt”** yapıyorum. Sonra da **senin SQL Data Analyst run’ından çıkan** “top segment” keyword’leri veriyorum ki zinciri doğru büyütelim.

---

## 1) Bizim pipeline ile match: kritik düzeltmeler

* “Elite freelancer” filtresi sadece Top Rated Plus / $10k+ ile kurulamaz; export’ta bazen yok.
  **Proxy elite tanımı**: yüksek rate (örn. ≥$60 / ≥$75), JSS (varsa ≥95), badge (varsa Top Rated/Expert).
  (JSS’in hangi faktörlere göre hesaplandığı Upwork’te net anlatılıyor.) ([support.upwork.com][1])
* “High-value job” filtresi: **Payment Verified + (Fixed ≥ $500 OR Hourly max ≥ $30)** + varsa client spent/hire-rate. ([Upwork][2])
* Profile optimization’da **Title + Overview** kritik; Upwork bunu direkt vurguluyor. ([support.upwork.com][3])
* Project Catalog: paket/skill/price/galeri adımları ve pricing yönergeleri var; analizimiz buna göre çıkmalı. ([support.upwork.com][4])

---

## 2) “En süper” prompt (ADA / Code Interpreter için) — Kopyala/Yapıştır

Aşağıyı, CSV/JSON’ları yükledikten sonra direkt yapıştır:

```text
Role: You are a Senior Data Analyst + Upwork Marketplace Strategist. Treat this as a real data science project with a reproducible pipeline (segmentation → NLP → gap analysis → packaging → outputs).

Objective:
Reverse-engineer top-performing patterns across Upwork Jobs, Talent, and Project Catalog for the niche: SQL Data Analyst / Python Data Analyst, and output a data-backed profile + catalog blueprint for me.

Data:
- jobs.csv (Upwork job posts)
- talent.csv (freelancer profiles)
- projects.csv (Project Catalog offerings)
- raw.json (optional)

Constraints:
- Do NOT propose any Cloudflare bypass, stealth scraping, or private endpoint exploitation.
- Work only with the uploaded datasets.
- If some “elite” fields (earnings, badges, JSS) are missing, use robust proxies.

PHASE 1 — Cleaning + Normalization
1) Normalize money fields:
   - fixed_budget numeric
   - hourly_min/hourly_max numeric
2) Normalize skills:
   - split on “;”
   - lowercase + strip + unify synonyms (e.g., “Power BI” variants)
3) Drop rows missing critical fields for each table (but keep as much as possible).

PHASE 2 — Quality Segmentation (Elite slices)
A) High-value jobs (target clients):
   - payment_verified = true
   - AND (fixed_budget >= 500 OR hourly_max >= 30)
   - If available, add bonus filters: total_spent high / client_hire_rate high.
B) Elite talent (target models):
   Use any available:
   - badge contains “Top Rated/Expert”
   - OR JSS >= 95 (if exists)
   - OR rate >= 60 (and separately analyze rate >= 75 as “premium elite”)
C) Top catalog offerings:
   - Use (rating >= 4.8 AND reviews >= 10) OR price in top decile
   - Filter out irrelevant categories by keyword heuristics if necessary.

PHASE 3 — NLP / Keyword DNA
For each segment above:
1) Extract:
   - Top skills frequency
   - Title n-grams (bigrams/trigrams)
   - Description/overview top action verbs + outcome words (if available)
2) Compute keyword “uplift”:
   uplift(term) = P(term | elite) / P(term | non-elite)
3) Produce 3 keyword lists:
   - Job language (client words)
   - Talent language (seller words)
   - Catalog language (product words)
Then compute intersection:
   CORE = uplift_jobs ∩ uplift_talent ∩ uplift_catalog

PHASE 4 — Market Gap (Demand vs Supply)
Compare high-value job skills vs elite talent skills:
- demand_rate(skill) - supply_rate(skill)
Highlight:
- skills with high demand and lower elite supply (opportunity pockets)

PHASE 5 — Catalog Packaging Strategy
From top catalog:
- identify common pricing tiers (starter/growth/pro)
- common deliverables phrasing
- delivery-time patterns
Output 3 catalog offers aligned to high-value jobs.

DELIVERABLES (final outputs)
1) Golden Title (short, Upwork-safe length)
2) Killer Overview (Hook + Value + Proof + Deliverables)
3) 15-skill stack ranked by demand/value ratio
4) 3 Project Catalog blueprints (title + price + delivery + deliverables + requirements)
5) 3 proposal templates (SQL fix/refactor, reporting automation, ETL/data modeling) — no questions, diagnose + solution.
Also include a 1-page summary of:
- CORE keywords
- TOP uplift terms
- top job clusters
- recommended next search keywords to collect (2–4 queries)

Action:
Run the analysis in Python and show intermediate tables (top skills, uplift list, price bands), then output the final copy-paste assets.
```

---

## 3) Senin “SQL Data Analyst” run’ından çıkan Top DNA (bizim için önemli olan)

**High-value job segmentinde** en sık skill kombinasyonu şuna kilitleniyor:

* **SQL + Data Analysis + Excel + Python + Data Visualization**
  ve “premium sinyal” olarak:
* **Data Modeling**
* **ETL / Pipeline**
* **Reporting / Dashboard** (tool bağımsız)

Bu tam senin hedefin: *Power BI’siz de premium lane’e giren* “SQL + Python + reporting automation” çizgisi.

---

## 4) Şimdi zinciri büyütmek için hangi keyword’lerle yeni run?

Senin istediğin “ilk sıradakiler / yüksek puanlılar” analizine en iyi veri, şu 3 query ile geliyor (Power BI yok):

1. **sql etl**
2. **sql reporting automation**
3. **sql data modeling**

Bunlar, seni “Excel-only data cleaning” gürültüsünden ayırır ve elite dilini netleştirir.

---

## 5) Kısa not: Senior Data Analyst gibi davranmak (Upwork’e yansıyan)

Upwork’te “senior” sinyali:

* **risk azaltma** + **sahiplik devri** + **tekrar çalıştırılabilir pipeline** (deliverable olarak)
* Title/Overview’ı bunun etrafında kur (Upwork de title+overview’un önemini açık söylüyor). ([support.upwork.com][3])
* Project Catalog’da paket/skill/price/galeri kuralları var; bunu blueprint’e dahil et. ([support.upwork.com][4])

---

İstersen hiç beklemeden şöyle yapalım:
**Bu promptu** (yukarıdaki) başka AI’a verip “sql etl” run’ını da yükleyeceksin.
Run gelince ben de burada **final kopyala-yapıştır** (Title + Overview + 15 skill + 3 catalog + 3 proposal) paketini senin veriye göre kilitleyeceğim.

[1]: https://support.upwork.com/hc/en-us/articles/211063558-Job-Success-Score?utm_source=chatgpt.com "Job Success Score - Upwork support"
[2]: https://www.upwork.com/resources/spotting-fake-job-posts?utm_source=chatgpt.com "Avoid Fake Job Postings and Scams"
[3]: https://support.upwork.com/hc/en-us/articles/34925678839827-Your-profile-title-and-overview?utm_source=chatgpt.com "Your profile title and overview"
[4]: https://support.upwork.com/hc/en-us/articles/360057397533-How-to-create-a-project-in-Project-Catalog?utm_source=chatgpt.com "How to create a project in Project Catalog"

Harika bir fikir. Buna veri biliminde **"Data Flywheel" (Veri Çarkı)** etkisi denir. Mevcut veriyi analiz edip, bir sonraki adımda neyi toplaman gerektiğini sisteme bulduracağız. Böylece körü körüne değil, **paranın olduğu yere doğru** kazı yapacaksın.

Bunun için Python pipeline'ına bir **"Recommendation Engine" (Öneri Motoru)** eklememiz lazım.

Aşağıdaki adımları ve Prompt'u Vibe Coding ortamına (ChatGPT/Cursor) ver. Bu sistem sana analiz sonunda şunu diyecek:
*"Şu ana kadar 'Data Analyst' kelimesini taradın, ama yüksek bütçeli işlerde **'dbt'**, **'Snowflake'** ve **'Airflow'** kelimeleri çok geçiyor. Bir sonraki taramanda bu kelimeleri kullan."*

---

### Vibe Coding İçin Prompt (Kopyala ve Yapıştır)

```markdown
**TASK UPDATE: Add a "Next-Step Scrape Recommender" Module**

I want to build a feedback loop. After analyzing the current data, the system should tell me **which keywords to scrape next** to expand my dataset in the most profitable direction.

**Add a function `recommend_next_keywords(jobs_df, current_search_term)` that does the following:**

1.  **Filter for High-Value Jobs:** Select jobs where `budget` > $500 OR `hourly_rate` > $30/hr AND `payment_verified` is True. We only want to learn from the best clients.
2.  **Extract Skills & Keywords:**
    *   Look at the `skills` column and the `title` column of these high-value jobs.
    *   Split them into individual words/phrases.
3.  **Frequency Analysis:** Count which skills/keywords appear most frequently.
4.  **Exclusion Logic:**
    *   Exclude the `current_search_term` (e.g., if I searched for "Data Analyst", don't recommend "Data Analyst" again).
    *   Exclude generic stop words (e.g., "needed", "expert", "looking for").
5.  **Output:** Print the "Top 10 High-Value Keywords" that I haven't scraped yet.

**Example Output Format:**
"Based on high-paying jobs, you should scrape these keywords next:
1. 'dbt' (Found in 15% of high-value jobs)
2. 'Snowflake' (Found in 12% of high-value jobs)
3. 'Web Scraping' (Found in 10% of high-value jobs)"
```

---

### Python Kodu (Bunu `main.py` içine eklemesini isteyecek)

AI muhtemelen şöyle bir fonksiyon üretecek. Mantığını anlaman için buraya koyuyorum:

```python
from collections import Counter

def recommend_next_keywords(df, current_search_term="data analyst"):
    print("\n🚀 GELECEK TARAMA İÇİN ÖNERİLER (Data Flywheel)")
    
    # 1. Sadece "Para Eden" İşleri Seç
    # (Regex ile fiyatları temizleme mantığı eklenecek)
    high_value = df  # Basitleştirildi, normalde burada fiyat filtresi olur
    
    # 2. Yetenekleri ve Başlıkları Topla
    all_text = []
    
    # Skills kolonunu al
    if 'skills' in high_value.columns:
        skills_list = high_value['skills'].dropna().str.split(',').explode().str.strip().tolist()
        all_text.extend(skills_list)
        
    # Başlıkları al (kelime kelime)
    titles_list = high_value['title'].dropna().str.lower().tolist()
    for t in titles_list:
        all_text.extend(t.split())

    # 3. Say ve Sırala
    counts = Counter(all_text)
    
    # 4. Gereksizleri Çıkar (Mevcut arama terimi ve stop words)
    ignore_list = set(current_search_term.lower().split()) | {'and', 'for', 'to', 'the', 'needed', 'expert'}
    
    recommendations = []
    for word, count in counts.most_common(50):
        if word.lower() not in ignore_list and len(word) > 2:
            recommendations.append((word, count))
            if len(recommendations) >= 10:
                break
    
    # 5. Çıktı Ver
    print(f"'{current_search_term}' araması yaptın. Veriyi büyütmek için sıradaki aramaların şunlar olmalı:")
    for word, count in recommendations:
        print(f"👉 {word} (Yüksek bütçeli işlerin {count} tanesinde geçti)")

    return [word for word, count in recommendations]
```

### Bu Sistem Nasıl Çalışacak? (Senin Döngün)

1.  **İlk Tur:** "Data Analyst" kelimesini taradın. CSV'leri klasöre attın.
2.  **Analiz:** Scripti çalıştırdın.
3.  **Öneri:** Script sana dedi ki: *"Dostum, Data Analyst işlerinin en pahalılarında **'Python Scraping'** ve **'Tableau'** kelimeleri çok geçiyor. Git bunları tara."*
4.  **İkinci Tur:** Gidip Upwork extension'ınla bu sefer "Python Scraping" kelimesini taratacaksın.
5.  **Birleştirme:** Yeni gelen CSV'leri de klasöre atıp scripti tekrar çalıştıracaksın.

Böylece veri setin rastgele değil, **zincirleme reaksiyonla** en değerli yeteneklere doğru büyüyecek. Boran Oktay'ın "Nişleşme" dediği şeyi matematiksel olarak bulmuş olacaksın.

Tamam. Şimdi “Senior Data Analyst” moduna kilitliyoruz: **rastgele okuma yok** → **rank-first + score-first** pipeline var. Ve evet: internette Upwork’ün kendi kurallarıyla da hizalıyoruz (title max 70 karakter + keyword-rich olmalı; Project Catalog’da proje oluşturma akışı vs.). ([support.upwork.com][1])

Aşağıdaki plan, senin dediğin “ilk sırada çıkanlar / yüksek puanlılar” yaklaşımını **matematiksel sisteme** çeviriyor.

---

## 1) Bizim gerçek hedef tanımı: “Top” nasıl seçilecek?

Senin dediğin iki kriteri aynı anda kullanacağız:

### A) **Rank-First (İlk sayfa / ilk sıradakiler)**

* `page_index == 1` olanlar = Upwork aramasında **önde görünenler** (senin query’nin en güçlü sinyali)

### B) **Score-First (Yüksek değer / yüksek kalite)**

**Jobs için**: Payment Verified + (Hourly max ≥ 30 veya Fixed ≥ 500) + (Client spend yüksek) + (Proposals düşük)
Upwork’ün “fake job” riskini azaltmak için “Payment Verified” filtrelemek direkt öneriliyor. ([Upwork][2])

**Talent için**: (Rate ≥ 75) veya (Top Rated/JSS yüksek) *varsa*
JSS’in günlük hesaplanması ve 6/12/24 ay pencereleri Upwork’te net. ([support.upwork.com][3])

**Projects için**: (Rating ≥ 4.8 & Reviews ≥ 10) **veya** fiyat üst dilim + teslim/kapsam netliği

---

## 2) SQL Data Analyst run’ından çıkan “Core Keyword Set” (bizim motor)

Senin “top” segmentlerinden çıkan çekirdek kesişim:

### ✅ CORE (Jobs ∩ Talent ∩ Projects, top segment)

* **sql**
* **python**
* **excel**
* **dashboard**
* **visualization**
* **data modeling**
* **etl**
* (tool opsiyonel: **tableau**)

Bu set şu yüzden kritik:

* **Jobs** tarafı “SQL + Python + Excel” istiyor (premium job’larda SQL/Python oranı yüksek).
* **Talent** tarafında premium profiller “Data Modeling / ETL” gibi senior sinyal taşımaya başlıyor.
* **Projects** tarafında en iyi satan offering’lerde **ETL** ve **Modeling** kelimesi **daha sık** (uplift).

> Sen Power BI kullanmıyorsun → “dashboard” kelimesini tutuyoruz ama “Power BI” tool’una yaslanmıyoruz.

---

## 3) Senin istediğin zincir: Jobs → Talent → Projects → Yeni keyword → yeni run

Bunu bir “Data Flywheel” gibi kuruyoruz:

### Adım 1 — **TOP JOBS** ne diyor?

Çıktı: **Client Language Dictionary**

* “fix / automate / pipeline / reporting / migration / audit / modeling / ETL”
* Jobs’ta öne çıkan kombinasyon: **SQL + Python + Reporting/Automation**

### Adım 2 — **TOP TALENT** ne yazmış?

Çıktı: **Elite Title Formula + Hook Formula**

* Title pattern (Upwork title max 70 karakter): “Role | 2–3 keyword | outcome”
* Hook (ilk 200 karakter): “Most X fails because Y → I build Z (ownership)”

Upwork title/overview’un aramada kritik olduğunu kendi support’unda söylüyor. ([support.upwork.com][1])

### Adım 3 — **TOP PROJECTS** nasıl paketlemiş?

Çıktı: **Catalog Package Templates**

* Starter / Growth / Pro tier
* “what you get” listesi
* teslim süresi ve revizyon politikası

Project Catalog’da proje oluşturma akışı ve limitler Upwork support’ta. ([support.upwork.com][4])

### Adım 4 — **Next Keyword Recommender**

Sadece TOP JOBS’tan çıkar:

* “current_search_term”i hariç tut
* generic kelimeleri çıkar
* kalanlardan **top 10** yeni query üret

---

## 4) Şimdi “hangi keyword’de veri toplayayım?” (senior cevap)

SQL Data Analyst run’ından sonra zincirin en iyi 3 devam halkası:

### 1) **sql reporting automation**

* Hem job dili hem project dili; Power BI bağımsız “dashboard/reporting” pazarına girersin.

### 2) **sql data modeling**

* “senior” sinyali. Commodity data cleaning’den ayrıştırır.

### 3) **sql etl**

* “system-money” (pipeline) işi. Katalog paketlerini de buradan çıkarırız.

> Bu üçlü, senin “Data Analyst + Python” kimliğini **en hızlı premium segmente** taşır.

---

## 5) “Senior Data Analyst gibi analiz yapabilmem için” skill edinme planı

Deep learning falan yok. Bu işte seni büyüten şey:

### A) Data Modeling (1–2 hafta)

* metric definition (KPI = tek cümle net tanım)
* fact-dimension mantığı
* grain (satırın anlamı) kontrolü

### B) ETL/ELT düşüncesi (1–2 hafta)

* source → transform → output
* incremental update
* validation & reconciliation (senior ayrıştırıcı)

### C) SQL Advanced (sürekli)

* joins, window functions, CTE
* query refactor & performance
* “reporting-ready dataset” üretmek (müşteri bunu satın alır)

### D) Reporting Automation (hemen para)

* “refreshable output”: Excel/Sheets + CSV + dashboard data
* “handover”: dokümantasyon + tekrar çalıştırma

Bunlar, Upwork’te seni “time seller”dan “system owner”a taşır.

---

## 6) Senin için “Vibe Coding” görev listesi (tek tek, kırılmadan)

Bunu Codex/Claude/Cursor’a task listesi olarak ver:

1. `score_jobs()` → Payment verified + budget + proposals + spent
2. `score_talent()` → rate + badge/JSS (varsa) + keyword density
3. `score_projects()` → rating/reviews + price band + deliverable clarity
4. `extract_ngrams()` → titles + first-200-char hooks
5. `keyword_uplift()` → top vs rest
6. `recommend_next_keywords()` → TOP JOBS’tan yeni query üret
7. `emit_blueprint()` → Title (≤70 char), Overview hook, 15 skills, 3 catalog

---

## Net aksiyon

Şimdi sıradaki run için **tek keyword seçiyoruz** (senin zincir mantığına en uygun):

✅ **sql reporting automation**

Bunu kazı:

* jobs + talent + projects (aynı format)
  Sonra ben:
* TOP JOB client language
* TOP TALENT title/hook
* TOP PROJECT paket/fiyat
* CORE keyword set (final)
  çıkarıp **profil + catalog’u** data-backed kilitleyeceğim.

İstersen tek kelime yaz: **reporting**
veya **modeling**
veya **etl**
Hangisiyle zinciri büyütelim.

[1]: https://support.upwork.com/hc/en-us/articles/34925678839827-Your-profile-title-and-overview?utm_source=chatgpt.com "Your profile title and overview - Upwork support"
[2]: https://www.upwork.com/resources/spotting-fake-job-posts?utm_source=chatgpt.com "Avoid Fake Job Postings and Scams"
[3]: https://support.upwork.com/hc/en-us/articles/38437458199059-How-is-my-Job-Success-Score-calculated?utm_source=chatgpt.com "How is my Job Success Score calculated?"
[4]: https://support.upwork.com/hc/en-us/articles/360057397533-How-to-create-a-project-in-Project-Catalog?utm_source=chatgpt.com "How to create a project in Project Catalog"
