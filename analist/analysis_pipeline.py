#!/usr/bin/env python3
"""
UPWORK PROFILE OPTIMIZATION PIPELINE
=====================================
Senior Data Analyst + NLP + Market Gap Analysis

Boran Oktay Stratejisi + Vibe Coding metodolojisi ile
veri-odaklı profil optimizasyonu.

Author: AI-Assisted Analysis
Date: 2024
"""

import pandas as pd
import numpy as np
import glob
import os
import re
import json
from collections import Counter
from datetime import datetime

# NLP & ML
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
import warnings
warnings.filterwarnings('ignore')

# Import new analysis modules
try:
    from analysis.market_gap_calculator import MarketGapCalculator
    from scoring.opportunity_scorer import KeywordOpportunityScorer
    from scoring.segment_scorer import SegmentScorer
    from generators.title_generator import GoldenTitleGenerator
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Some modules not available: {e}")
    MODULES_AVAILABLE = False

# ============================================================
# CONFIGURATION
# ============================================================
DATA_FOLDER = 'data'
OUTPUT_FOLDER = 'outputs'

# Elite segment thresholds
ELITE_RATE_THRESHOLD = 50  # $50/hr+ = premium segment
PREMIUM_RATE_THRESHOLD = 75  # $75/hr+ = top premium
HIGH_VALUE_FIXED_BUDGET = 500  # $500+ fixed = high value
HIGH_VALUE_HOURLY_MIN = 30  # $30/hr+ = high value

# Stop words for Turkish/English analysis
CUSTOM_STOP_WORDS = {
    'and', 'for', 'to', 'the', 'of', 'in', 'a', 'an', 'is', 'with', 'on', 'at',
    'by', 'from', 'or', 'as', 'be', 'was', 'are', 'been', 'being', 'have', 'has',
    'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
    'must', 'shall', 'can', 'need', 'dare', 'ought', 'used', 'about', 'after',
    'looking', 'needed', 'expert', 'specialist', 'professional', 'experienced',
    'seeking', 'hiring', 'wanted', 'required', 'urgent', 'asap', 'immediate'
}

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def clean_text(text):
    """Metni temizle ve normalize et"""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s\|\/\-]', ' ', text)  # Keep separators
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_rate(rate_str):
    """Rate string'inden numerik değer çıkar ($15/hr -> 15)"""
    if not isinstance(rate_str, str):
        return 0
    match = re.search(r'\$?(\d+\.?\d*)', rate_str)
    if match:
        return float(match.group(1))
    return 0

def extract_budget(budget_str):
    """Budget string'inden numerik değer çıkar"""
    if not isinstance(budget_str, str):
        return 0
    # Remove commas and extract number
    clean = re.sub(r'[,\$]', '', str(budget_str))
    match = re.search(r'(\d+\.?\d*)', clean)
    if match:
        return float(match.group(1))
    return 0

def parse_hourly_range(hourly_str):
    """'Hourly: $10.00 - $30.00' formatını parse et"""
    if not isinstance(hourly_str, str):
        return 0, 0
    matches = re.findall(r'\$(\d+\.?\d*)', hourly_str)
    if len(matches) >= 2:
        return float(matches[0]), float(matches[1])
    elif len(matches) == 1:
        return float(matches[0]), float(matches[0])
    return 0, 0

def get_top_ngrams(corpus, n=2, top_k=20):
    """En çok geçen n-gram'ları bul (Bigram/Trigram)"""
    if not corpus or len(corpus) == 0:
        return pd.DataFrame(columns=['Phrase', 'Frequency', 'Percentage'])
    
    # Clean corpus
    clean_corpus = [clean_text(str(doc)) for doc in corpus if doc]
    clean_corpus = [doc for doc in clean_corpus if len(doc) > 10]
    
    if len(clean_corpus) == 0:
        return pd.DataFrame(columns=['Phrase', 'Frequency', 'Percentage'])
    
    try:
        vec = CountVectorizer(
            ngram_range=(n, n), 
            stop_words='english',
            max_features=1000,
            min_df=2
        )
        bag_of_words = vec.fit_transform(clean_corpus)
        sum_words = bag_of_words.sum(axis=0)
        words_freq = [(word, sum_words[0, idx]) for word, idx in vec.vocabulary_.items()]
        words_freq = sorted(words_freq, key=lambda x: x[1], reverse=True)
        
        total = sum([f for _, f in words_freq])
        result = []
        for phrase, freq in words_freq[:top_k]:
            pct = (freq / total * 100) if total > 0 else 0
            result.append({
                'Phrase': phrase,
                'Frequency': int(freq),
                'Percentage': round(pct, 2)
            })
        return pd.DataFrame(result)
    except Exception as e:
        print(f"    N-gram analizi hatası: {e}")
        return pd.DataFrame(columns=['Phrase', 'Frequency', 'Percentage'])

def extract_skills_list(skills_str):
    """Skills string'ini listeye çevir"""
    if not isinstance(skills_str, str):
        return []
    # Split by semicolon or comma
    if ';' in skills_str:
        skills = skills_str.split(';')
    else:
        skills = skills_str.split(',')
    return [s.strip().lower() for s in skills if s.strip()]

def analyze_title_structure(titles):
    """Başlık yapısını analiz et (separator kullanımı vs.)"""
    results = {
        'pipe_separator': 0,  # |
        'dash_separator': 0,  # -
        'slash_separator': 0,  # /
        'no_separator': 0,
        'avg_word_count': 0,
        'avg_char_count': 0
    }
    
    word_counts = []
    char_counts = []
    
    for title in titles:
        if not isinstance(title, str):
            continue
        
        char_counts.append(len(title))
        word_counts.append(len(title.split()))
        
        if '|' in title:
            results['pipe_separator'] += 1
        elif ' - ' in title or ' – ' in title:
            results['dash_separator'] += 1
        elif ' / ' in title:
            results['slash_separator'] += 1
        else:
            results['no_separator'] += 1
    
    total = len(titles)
    if total > 0:
        results['avg_word_count'] = round(np.mean(word_counts), 1)
        results['avg_char_count'] = round(np.mean(char_counts), 1)
        
        # Convert to percentages
        results['pipe_separator'] = round(results['pipe_separator'] / total * 100, 1)
        results['dash_separator'] = round(results['dash_separator'] / total * 100, 1)
        results['slash_separator'] = round(results['slash_separator'] / total * 100, 1)
        results['no_separator'] = round(results['no_separator'] / total * 100, 1)
    
    return results

# ============================================================
# DATA LOADING
# ============================================================

def load_all_csvs():
    """Tüm CSV dosyalarını kategorize ederek yükle"""
    print("=" * 60)
    print("📂 VERİ YÜKLEME")
    print("=" * 60)
    
    files = glob.glob(os.path.join(DATA_FOLDER, "*.csv"))
    
    data = {
        'jobs': [],
        'talent': [],
        'projects': []
    }
    
    for file in files:
        try:
            df = pd.read_csv(file, low_memory=False)
            filename = os.path.basename(file).lower()
            
            # Kategorize
            if 'job' in filename:
                data['jobs'].append(df)
                print(f"  ✅ JOBS: {filename} ({len(df)} satır)")
            elif 'talent' in filename:
                data['talent'].append(df)
                print(f"  ✅ TALENT: {filename} ({len(df)} satır)")
            elif 'project' in filename:
                data['projects'].append(df)
                print(f"  ✅ PROJECTS: {filename} ({len(df)} satır)")
            else:
                print(f"  ⚠️ UNKNOWN: {filename}")
                
        except Exception as e:
            print(f"  ❌ HATA: {file} - {e}")
    
    # Birleştir
    result = {}
    for category, dfs in data.items():
        if dfs:
            result[category] = pd.concat(dfs, ignore_index=True)
            print(f"\n  📊 {category.upper()} TOPLAM: {len(result[category])} satır")
        else:
            result[category] = pd.DataFrame()
    
    return result

# ============================================================
# JOBS ANALYSIS
# ============================================================

def analyze_jobs(df, search_term="sql data analyst"):
    """İş ilanlarını analiz et"""
    print("\n" + "=" * 60)
    print("💼 İŞ İLANLARI ANALİZİ")
    print("=" * 60)
    
    if df.empty:
        print("  ⚠️ Jobs verisi bulunamadı!")
        return {}
    
    results = {
        'total_jobs': len(df),
        'high_value_jobs': 0,
        'top_skills': [],
        'title_ngrams': None,
        'description_ngrams': None,
        'budget_stats': {},
        'client_quality': {}
    }
    
    # 1. BUDGET PARSING
    print("\n  📊 Bütçe Analizi...")
    
    df['parsed_budget'] = df['budget'].apply(lambda x: extract_budget(str(x)) if pd.notna(x) else 0)
    df['hourly_min'], df['hourly_max'] = zip(*df['budget'].apply(
        lambda x: parse_hourly_range(str(x)) if pd.notna(x) else (0, 0)
    ))
    
    # Fixed vs Hourly
    fixed_jobs = df[df['job_type'].str.contains('Fixed', na=False, case=False)]
    hourly_jobs = df[df['job_type'].str.contains('Hourly', na=False, case=False)]
    
    results['budget_stats'] = {
        'fixed_count': len(fixed_jobs),
        'hourly_count': len(hourly_jobs),
        'avg_fixed_budget': fixed_jobs['parsed_budget'].mean() if len(fixed_jobs) > 0 else 0,
        'max_fixed_budget': fixed_jobs['parsed_budget'].max() if len(fixed_jobs) > 0 else 0,
        'avg_hourly_max': hourly_jobs['hourly_max'].mean() if len(hourly_jobs) > 0 else 0
    }
    
    print(f"    Fixed Price İşler: {results['budget_stats']['fixed_count']}")
    print(f"    Hourly İşler: {results['budget_stats']['hourly_count']}")
    print(f"    Ortalama Fixed Bütçe: ${results['budget_stats']['avg_fixed_budget']:.0f}")
    print(f"    Ortalama Hourly Max: ${results['budget_stats']['avg_hourly_max']:.0f}/hr")
    
    # 2. HIGH-VALUE JOBS SEGMENTATION
    print("\n  🎯 Yüksek Değerli İşler (Segmentasyon)...")
    
    # Payment verified check
    if 'payment_verified' in df.columns:
        verified_mask = df['payment_verified'].astype(str).str.lower().isin(['true', '1', 'yes'])
    else:
        verified_mask = pd.Series([True] * len(df))
    
    # Budget thresholds
    high_fixed = df['parsed_budget'] >= HIGH_VALUE_FIXED_BUDGET
    high_hourly = df['hourly_max'] >= HIGH_VALUE_HOURLY_MIN
    
    high_value_df = df[verified_mask & (high_fixed | high_hourly)]
    results['high_value_jobs'] = len(high_value_df)
    
    print(f"    Yüksek Değerli İş Sayısı: {results['high_value_jobs']} ({results['high_value_jobs']/len(df)*100:.1f}%)")
    
    # 3. CLIENT QUALITY ANALYSIS
    print("\n  👤 Müşteri Kalite Analizi...")
    
    if 'total_spent' in df.columns:
        # Parse total_spent ($100K+, $10K+, etc.)
        def parse_spent(s):
            if not isinstance(s, str):
                return 0
            s = s.upper()
            if '100K' in s or 'M' in s:
                return 100000
            elif '50K' in s:
                return 50000
            elif '30K' in s:
                return 30000
            elif '20K' in s:
                return 20000
            elif '10K' in s:
                return 10000
            elif 'K' in s:
                match = re.search(r'(\d+)K', s)
                return int(match.group(1)) * 1000 if match else 0
            return 0
        
        df['parsed_spent'] = df['total_spent'].apply(parse_spent)
        
        # Premium clients ($10K+)
        premium_clients = df[df['parsed_spent'] >= 10000]
        results['client_quality'] = {
            'premium_client_jobs': len(premium_clients),
            'premium_percentage': len(premium_clients) / len(df) * 100 if len(df) > 0 else 0
        }
        print(f"    $10K+ Harcamış Müşteri İşleri: {results['client_quality']['premium_client_jobs']}")
    
    # 4. SKILLS FREQUENCY ANALYSIS
    print("\n  🛠️ Skills Frekans Analizi...")
    
    if 'skills' in df.columns:
        all_skills = []
        for skills_str in high_value_df['skills'].dropna():
            all_skills.extend(extract_skills_list(skills_str))
        
        skill_counts = Counter(all_skills)
        results['top_skills'] = skill_counts.most_common(25)
        
        print("\n  📋 EN ÇOK ARANAN SKİLLER (High-Value Jobs):")
        for i, (skill, count) in enumerate(results['top_skills'][:15], 1):
            pct = count / len(high_value_df) * 100 if len(high_value_df) > 0 else 0
            print(f"    {i:2}. {skill.title()}: {count} iş ({pct:.1f}%)")
    
    # 5. TITLE N-GRAM ANALYSIS
    print("\n  📝 İş Başlığı N-Gram Analizi...")
    
    if 'title' in df.columns:
        titles = high_value_df['title'].dropna().tolist()
        
        # Bigrams
        bigrams = get_top_ngrams(titles, n=2, top_k=15)
        results['title_ngrams'] = bigrams
        
        if not bigrams.empty:
            print("\n  🔤 EN SIK GEÇEN İKİLİ KELİME GRUPLARI (Bigrams):")
            for _, row in bigrams.head(10).iterrows():
                print(f"    • {row['Phrase']}: {row['Frequency']} ({row['Percentage']}%)")
    
    # 6. DESCRIPTION TRIGRAM ANALYSIS
    print("\n  📄 İş Açıklaması Trigram Analizi...")
    
    if 'description' in df.columns or 'detail_summary' in df.columns:
        desc_col = 'detail_summary' if 'detail_summary' in df.columns else 'description'
        descriptions = high_value_df[desc_col].dropna().tolist()
        
        trigrams = get_top_ngrams(descriptions, n=3, top_k=15)
        results['description_ngrams'] = trigrams
        
        if not trigrams.empty:
            print("\n  🔤 EN SIK GEÇEN ÜÇLÜ KELİME GRUPLARI (Trigrams):")
            for _, row in trigrams.head(10).iterrows():
                print(f"    • {row['Phrase']}: {row['Frequency']}")
    
    return results

# ============================================================
# TALENT ANALYSIS
# ============================================================

def analyze_talent(df, search_term="sql data analyst"):
    """Freelancer profillerini analiz et"""
    print("\n" + "=" * 60)
    print("👥 FREELANCER (TALENT) ANALİZİ")
    print("=" * 60)
    
    if df.empty:
        print("  ⚠️ Talent verisi bulunamadı!")
        return {}
    
    results = {
        'total_talent': len(df),
        'elite_talent': 0,
        'premium_talent': 0,
        'rate_distribution': {},
        'top_skills': [],
        'title_patterns': None,
        'title_structure': {},
        'location_analysis': {},
        'badge_analysis': {}
    }
    
    # 1. RATE PARSING
    print("\n  💰 Rate Analizi...")
    
    df['parsed_rate'] = df['rate'].apply(extract_rate)
    
    rate_stats = df['parsed_rate'][df['parsed_rate'] > 0]
    results['rate_distribution'] = {
        'min': rate_stats.min() if len(rate_stats) > 0 else 0,
        'max': rate_stats.max() if len(rate_stats) > 0 else 0,
        'mean': rate_stats.mean() if len(rate_stats) > 0 else 0,
        'median': rate_stats.median() if len(rate_stats) > 0 else 0
    }
    
    print(f"    Rate Aralığı: ${results['rate_distribution']['min']:.0f} - ${results['rate_distribution']['max']:.0f}/hr")
    print(f"    Ortalama Rate: ${results['rate_distribution']['mean']:.0f}/hr")
    print(f"    Medyan Rate: ${results['rate_distribution']['median']:.0f}/hr")
    
    # 2. ELITE SEGMENTATION
    print("\n  🏆 Elite Segment Analizi...")
    
    # Badge check
    badge_col = 'detail_badges' if 'detail_badges' in df.columns else 'badge'
    if badge_col in df.columns:
        top_rated_mask = df[badge_col].astype(str).str.contains('Top Rated', na=False, case=False)
        expert_mask = df[badge_col].astype(str).str.contains('Expert', na=False, case=False)
        badge_mask = top_rated_mask | expert_mask
        
        results['badge_analysis'] = {
            'top_rated_count': top_rated_mask.sum(),
            'expert_count': expert_mask.sum()
        }
        print(f"    Top Rated Badge: {results['badge_analysis']['top_rated_count']}")
        print(f"    Expert Badge: {results['badge_analysis']['expert_count']}")
    else:
        badge_mask = pd.Series([False] * len(df))
    
    # JSS check
    jss_col = 'detail_job_success' if 'detail_job_success' in df.columns else 'job_success'
    if jss_col in df.columns:
        def parse_jss(s):
            if not isinstance(s, str):
                return 0
            match = re.search(r'(\d+)', s)
            return int(match.group(1)) if match else 0
        
        df['parsed_jss'] = df[jss_col].apply(parse_jss)
        high_jss_mask = df['parsed_jss'] >= 95
        jss_100_count = (df['parsed_jss'] == 100).sum()
        print(f"    100% JSS: {jss_100_count}")
        print(f"    95%+ JSS: {high_jss_mask.sum()}")
    else:
        high_jss_mask = pd.Series([False] * len(df))
    
    # Rate-based elite
    elite_rate_mask = df['parsed_rate'] >= ELITE_RATE_THRESHOLD
    premium_rate_mask = df['parsed_rate'] >= PREMIUM_RATE_THRESHOLD
    
    # Combined elite (badge OR high JSS OR high rate)
    elite_mask = badge_mask | high_jss_mask | elite_rate_mask
    elite_df = df[elite_mask]
    premium_df = df[premium_rate_mask]
    
    results['elite_talent'] = len(elite_df)
    results['premium_talent'] = len(premium_df)
    
    print(f"\n    🌟 Elite Talent: {results['elite_talent']} ({results['elite_talent']/len(df)*100:.1f}%)")
    print(f"    💎 Premium ($75+/hr): {results['premium_talent']}")
    
    # 3. LOCATION ANALYSIS
    print("\n  🌍 Lokasyon Analizi...")
    
    loc_col = 'location' if 'location' in df.columns else 'detail_location'
    if loc_col in df.columns:
        location_counts = elite_df[loc_col].value_counts().head(15)
        results['location_analysis'] = location_counts.to_dict()
        
        print("  📍 Elite Freelancer Lokasyonları:")
        for loc, count in list(results['location_analysis'].items())[:10]:
            avg_rate = elite_df[elite_df[loc_col] == loc]['parsed_rate'].mean()
            print(f"    • {loc}: {count} kişi (Ort. ${avg_rate:.0f}/hr)")
    
    # 4. TITLE PATTERN ANALYSIS
    print("\n  📝 Başlık Yapısı Analizi...")
    
    if 'title' in df.columns:
        elite_titles = elite_df['title'].dropna().tolist()
        
        # Structure analysis
        results['title_structure'] = analyze_title_structure(elite_titles)
        
        print(f"    Pipe (|) Separator: {results['title_structure']['pipe_separator']}%")
        print(f"    Dash (-) Separator: {results['title_structure']['dash_separator']}%")
        print(f"    Ortalama Kelime Sayısı: {results['title_structure']['avg_word_count']}")
        print(f"    Ortalama Karakter: {results['title_structure']['avg_char_count']}")
        
        # N-gram analysis
        bigrams = get_top_ngrams(elite_titles, n=2, top_k=20)
        results['title_patterns'] = bigrams
        
        if not bigrams.empty:
            print("\n  🔤 ELİT BAŞLIKLARDA EN SIK GEÇEN İKİLİLER:")
            for _, row in bigrams.head(15).iterrows():
                print(f"    • {row['Phrase']}: {row['Frequency']} ({row['Percentage']}%)")
    
    # 5. SKILLS ANALYSIS
    print("\n  🛠️ Elite Skills Analizi...")
    
    if 'skills' in df.columns:
        all_skills = []
        for skills_str in elite_df['skills'].dropna():
            all_skills.extend(extract_skills_list(skills_str))
        
        skill_counts = Counter(all_skills)
        results['top_skills'] = skill_counts.most_common(25)
        
        print("\n  📋 ELİT FREELANCERLARDAKİ EN YAYGIN SKİLLER:")
        for i, (skill, count) in enumerate(results['top_skills'][:15], 1):
            pct = count / len(elite_df) * 100 if len(elite_df) > 0 else 0
            print(f"    {i:2}. {skill.title()}: {count} ({pct:.1f}%)")
    
    # 6. TOP PERFORMERS SHOWCASE
    print("\n  🏆 EN YÜKSEK RATE'Lİ PROFİLLER:")
    
    top_performers = df.nlargest(10, 'parsed_rate')[['title', 'location', 'rate', 'skills']].head(10)
    for _, row in top_performers.iterrows():
        print(f"    💎 ${extract_rate(row['rate'])}/hr | {row.get('location', 'N/A')}")
        print(f"       {row['title'][:60]}...")
    
    return results

# ============================================================
# PROJECTS (CATALOG) ANALYSIS
# ============================================================

def analyze_projects(df):
    """Project Catalog'u analiz et"""
    print("\n" + "=" * 60)
    print("📦 PROJECT CATALOG ANALİZİ")
    print("=" * 60)
    
    if df.empty:
        print("  ⚠️ Projects verisi bulunamadı!")
        return {}
    
    results = {
        'total_projects': len(df),
        'top_projects': 0,
        'price_distribution': {},
        'delivery_patterns': {},
        'top_titles': [],
        'seller_badges': {}
    }
    
    # 1. PRICE PARSING
    print("\n  💰 Fiyat Analizi...")
    
    def parse_price(price_str):
        if not isinstance(price_str, str):
            return 0
        match = re.search(r'(\d+)', price_str.replace(',', ''))
        return int(match.group(1)) if match else 0
    
    df['parsed_price'] = df['price'].apply(parse_price)
    
    price_stats = df['parsed_price'][df['parsed_price'] > 0]
    results['price_distribution'] = {
        'min': price_stats.min() if len(price_stats) > 0 else 0,
        'max': price_stats.max() if len(price_stats) > 0 else 0,
        'mean': price_stats.mean() if len(price_stats) > 0 else 0,
        'median': price_stats.median() if len(price_stats) > 0 else 0
    }
    
    print(f"    Fiyat Aralığı: ${results['price_distribution']['min']} - ${results['price_distribution']['max']}")
    print(f"    Ortalama Fiyat: ${results['price_distribution']['mean']:.0f}")
    print(f"    Medyan Fiyat: ${results['price_distribution']['median']:.0f}")
    
    # 2. RATING & REVIEWS ANALYSIS
    print("\n  ⭐ Rating & Review Analizi...")
    
    if 'rating' in df.columns:
        def parse_rating(r):
            if not isinstance(r, str) and not isinstance(r, (int, float)):
                return 0
            try:
                match = re.search(r'(\d+\.?\d*)', str(r))
                return float(match.group(1)) if match else 0
            except:
                return 0
        
        df['parsed_rating'] = df['rating'].apply(parse_rating)
        
        # Top projects = 4.8+ rating & 10+ reviews
        if 'reviews' in df.columns:
            df['parsed_reviews'] = df['reviews'].apply(lambda x: int(re.search(r'(\d+)', str(x)).group(1)) if re.search(r'(\d+)', str(x)) else 0)
            top_projects_mask = (df['parsed_rating'] >= 4.8) & (df['parsed_reviews'] >= 10)
            top_df = df[top_projects_mask]
            results['top_projects'] = len(top_df)
            print(f"    Top Projects (4.8+, 10+ reviews): {results['top_projects']}")
    else:
        top_df = df
    
    # 3. SELLER BADGE ANALYSIS
    print("\n  🏅 Satıcı Badge Analizi...")
    
    if 'seller_badge' in df.columns:
        badge_counts = df['seller_badge'].value_counts()
        results['seller_badges'] = badge_counts.to_dict()
        
        for badge, count in results['seller_badges'].items():
            if pd.notna(badge) and badge:
                print(f"    • {badge}: {count}")
    
    # 4. DELIVERY TIME PATTERNS
    print("\n  ⏱️ Teslimat Süresi Analizi...")
    
    if 'delivery_time' in df.columns:
        delivery_counts = df['delivery_time'].value_counts().head(10)
        results['delivery_patterns'] = delivery_counts.to_dict()
        
        for delivery, count in results['delivery_patterns'].items():
            print(f"    • {delivery}: {count}")
    
    # 5. TOP SELLING PROJECT TITLES
    print("\n  📋 En Çok Satan Proje Başlıkları:")
    
    if 'title' in df.columns and 'parsed_reviews' in df.columns:
        top_by_reviews = df.nlargest(10, 'parsed_reviews')[['title', 'price', 'rating', 'reviews']]
        
        for _, row in top_by_reviews.iterrows():
            title = str(row['title'])[:60] if pd.notna(row['title']) else "N/A"
            print(f"    💰 {row['price']} | ⭐{row['rating']} | 📝{row['reviews']}")
            print(f"       {title}...")
    
    return results

# ============================================================
# MARKET GAP ANALYSIS
# ============================================================

def analyze_market_gaps(jobs_results, talent_results):
    """Talep vs Arz boşluk analizi - Now with statistical significance testing"""
    print("\n" + "=" * 60)
    print("🎯 MARKET GAP ANALİZİ (Fırsat Alanları)")
    print("=" * 60)

    if not jobs_results.get('top_skills') or not talent_results.get('top_skills'):
        print("  ⚠️ Skill verisi yetersiz!")
        return {}

    # Use new statistical calculator if available
    if MODULES_AVAILABLE:
        print("  📊 Using statistical significance testing...")
        calculator = MarketGapCalculator()

        # Extract demand and supply data
        job_skills = {skill: count for skill, count in jobs_results['top_skills']}
        talent_skills = {skill: count for skill, count in talent_results['top_skills']}

        # Format data for calculate_multiple_gaps: {skill: {'demand': [...], 'supply': [...]}}
        # Since we have count data, we create single-value arrays for each skill
        skill_data = {}
        all_skills = set(job_skills.keys()) | set(talent_skills.keys())

        for skill in all_skills:
            skill_data[skill] = {
                'demand': [float(job_skills.get(skill, 0))],
                'supply': [float(talent_skills.get(skill, 0))]
            }

        # Calculate gaps with statistical testing
        gaps = calculator.calculate_multiple_gaps(skill_data)

        # Filter by significance - fix: use min_effect_size parameter instead of p_threshold
        significant_gaps = calculator.filter_significant_gaps(gaps, min_effect_size=0.2)

        print("\n  🔥 STATISTIKSEL OLARAK ANLAMLI FIRSATLAR (p < 0.05):")
        print("  " + "-" * 55)

        for gap in significant_gaps[:15]:
            # Calculate percentages for display
            total_demand = sum(job_skills.values()) or 1
            total_supply = sum(talent_skills.values()) or 1
            demand_pct = (job_skills.get(gap['skill'], 0) / total_demand) * 100
            supply_pct = (talent_skills.get(gap['skill'], 0) / total_supply) * 100

            print(f"    📈 {gap['skill'].title()}")
            print(f"       Talep: {job_skills.get(gap['skill'], 0)} ({demand_pct:.1f}%)")
            print(f"       Arz: {talent_skills.get(gap['skill'], 0)} ({supply_pct:.1f}%)")
            print(f"       Gap Ratio: {gap['gap_ratio']:.2f}x")
            print(f"       P-value: {gap['p_value']:.4f} | Effect Size: {gap['effect_size']:.2f}")
            print()

        return significant_gaps
    else:
        # Fallback to original logic
        print("  ⚠️ Statistical calculator not available, using basic analysis...")

        job_skills = {skill: count for skill, count in jobs_results['top_skills']}
        talent_skills = {skill: count for skill, count in talent_results['top_skills']}

        total_jobs = jobs_results.get('high_value_jobs', 1)
        total_talent = talent_results.get('elite_talent', 1)

        all_skills = set(job_skills.keys()) | set(talent_skills.keys())

        gaps = []
        for skill in all_skills:
            demand = job_skills.get(skill, 0) / total_jobs if total_jobs > 0 else 0
            supply = talent_skills.get(skill, 0) / total_talent if total_talent > 0 else 0

            if supply > 0:
                gap_ratio = demand / supply
            else:
                gap_ratio = demand * 10 if demand > 0 else 0

            gaps.append({
                'skill': skill,
                'demand_count': job_skills.get(skill, 0),
                'supply_count': talent_skills.get(skill, 0),
                'demand_pct': demand * 100,
                'supply_pct': supply * 100,
                'gap_ratio': gap_ratio,
                'p_value': None,
                'is_significant': None
            })

        gaps.sort(key=lambda x: x['gap_ratio'], reverse=True)

        print("\n  🔥 YÜKSEK TALEP - DÜŞÜK ARZ (FIRSAT ALANLARI):")
        print("  " + "-" * 55)

        for gap in gaps[:15]:
            if gap['demand_count'] >= 5:
                print(f"    📈 {gap['skill'].title()}")
                print(f"       Talep: {gap['demand_count']} iş ({gap['demand_pct']:.1f}%)")
                print(f"       Arz: {gap['supply_count']} freelancer ({gap['supply_pct']:.1f}%)")
                print(f"       Gap Ratio: {gap['gap_ratio']:.2f}x")
                print()

        return gaps

# ============================================================
# KEYWORD RECOMMENDER (DATA FLYWHEEL)
# ============================================================

def recommend_next_keywords(jobs_df, current_search_term="sql data analyst"):
    """Sonraki tarama için keyword önerileri - Now with opportunity scoring"""
    print("\n" + "=" * 60)
    print("🚀 SONRAKI TARAMA İÇİN KEYWORD ÖNERİLERİ")
    print("=" * 60)

    if jobs_df.empty:
        print("  ⚠️ Jobs verisi bulunamadı!")
        return []

    # Use new opportunity scorer if available
    if MODULES_AVAILABLE:
        print("  📊 Using composite opportunity scoring...")
        scorer = KeywordOpportunityScorer()

        # Extract keywords from jobs data
        keywords_data = []
        seen_keywords = set()

        # From skills
        if 'skills' in jobs_df.columns:
            for skills_str in jobs_df['skills'].dropna():
                skills_list = extract_skills_list(skills_str)
                for skill in skills_list:
                    if skill not in seen_keywords and len(skill) > 2:
                        seen_keywords.add(skill)
                        keywords_data.append({
                            'keyword': skill,
                            'source': 'skills'
                        })

        # From titles
        if 'title' in jobs_df.columns:
            for title in jobs_df['title'].dropna():
                words = clean_text(title).split()
                for word in words:
                    if word not in seen_keywords and len(word) > 2 and word not in CUSTOM_STOP_WORDS:
                        seen_keywords.add(word)
                        keywords_data.append({
                            'keyword': word,
                            'source': 'title'
                        })

        # Score keywords with market data
        scored_keywords = []
        for kw_data in keywords_data[:100]:  # Limit for performance
            keyword = kw_data['keyword']

            # Build market data from jobs_df
            market_data = {
                'job_count': len(jobs_df),
                'avg_budget': jobs_df.get('parsed_budget', pd.Series([0])).mean(),
                'total_freelancers': 100,  # Would come from talent data
                'avg_proposals': 10,  # Would come from jobs data
                'payment_verified_pct': 85,  # Would come from jobs data
                'growth_rate': 0.1  # Would come from historical data
            }

            score_result = scorer.score_keyword_opportunity(keyword, market_data)
            # Convert dataclass to dict for compatibility
            scored_keywords.append({
                'keyword': keyword,
                'opportunity_score': score_result.opportunity_score,
                'recommended_priority': score_result.recommended_priority,
                'demand_score': score_result.demand_score,
                'supply_score': score_result.supply_score,
                'budget_score': score_result.budget_score,
                'competition_score': score_result.competition_score
            })

        # Sort by opportunity score
        scored_keywords.sort(key=lambda x: x['opportunity_score'], reverse=True)

        print(f"\n  '{current_search_term}' araması yaptın.")
        print("  Veri setini genişletmek için şu keyword'leri tara (opportunity score ile sıralı):\n")

        for i, kw in enumerate(scored_keywords[:15], 1):
            priority_label = kw['recommended_priority']
            emoji = "🔥" if priority_label == "HIGH" else "📈" if priority_label == "MEDIUM" else "📊"
            print(f"    {i:2}. {emoji} '{kw['keyword']}' | Score: {kw['opportunity_score']:.1f}/100 | {priority_label}")

        return [kw['keyword'] for kw in scored_keywords[:15]]
    else:
        # Fallback to original logic
        print("  ⚠️ Opportunity scorer not available, using frequency analysis...")

        all_text = []

        if 'skills' in jobs_df.columns:
            for skills_str in jobs_df['skills'].dropna():
                all_text.extend(extract_skills_list(skills_str))

        if 'title' in jobs_df.columns:
            for title in jobs_df['title'].dropna():
                words = clean_text(title).split()
                all_text.extend(words)

        counts = Counter(all_text)

        current_words = set(current_search_term.lower().split())
        ignore = current_words | CUSTOM_STOP_WORDS

        recommendations = []
        for word, count in counts.most_common(100):
            if word.lower() not in ignore and len(word) > 2 and count >= 5:
                recommendations.append((word, count))
                if len(recommendations) >= 15:
                    break

        print(f"\n  '{current_search_term}' araması yaptın.")
        print("  Veri setini genişletmek için şu keyword'leri tara:\n")

        for i, (word, count) in enumerate(recommendations, 1):
            print(f"    {i:2}. '{word}' → {count} yüksek değerli işte geçiyor")

        return [word for word, _ in recommendations]

# ============================================================
# PROFILE BLUEPRINT GENERATOR
# ============================================================

def generate_profile_blueprint(jobs_results, talent_results, projects_results, gaps):
    """Profil optimizasyon önerisi oluştur - Now with Golden Title Generator"""
    print("\n" + "=" * 60)
    print("🎯 PROFİL OPTİMİZASYON ÖNERİSİ")
    print("=" * 60)

    blueprint = {
        'recommended_title': '',
        'recommended_titles': [],  # Multiple options
        'recommended_skills': [],
        'recommended_rate': '',
        'catalog_ideas': []
    }

    # 1. TITLE RECOMMENDATION - Use Golden Title Generator if available
    print("\n  📝 ÖNERİLEN BAŞLIKLAR (Elite Pattern Analysis):")

    if MODULES_AVAILABLE:
        generator = GoldenTitleGenerator(elite_threshold=50.0)

        # Build profile data from results
        profile_data = {
            'role': 'Data Analyst',
            'primary_skills': [],
            'outcomes': []
        }

        # Extract top skills from jobs
        if jobs_results.get('top_skills'):
            for skill, _ in jobs_results['top_skills'][:5]:
                profile_data['primary_skills'].append(skill.title())

        # Extract outcomes from gap analysis
        if gaps:
            for gap in gaps[:3]:
                if isinstance(gap, dict) and 'skill' in gap:
                    profile_data['outcomes'].append(gap['skill'].title())

        # Generate multiple title options
        titles = generator.generate_titles(profile_data, count=5)

        if titles:
            for i, title_info in enumerate(titles, 1):
                score_emoji = "🏆" if title_info.get('predicted_score', 0) > 80 else "⭐" if title_info.get('predicted_score', 0) > 60 else "📝"
                print(f"    {score_emoji} Option {i}: {title_info['title']}")
                print(f"       Pattern: {title_info.get('pattern', 'N/A')} | Score: {title_info.get('predicted_score', 0)}/100")
                blueprint['recommended_titles'].append(title_info)

            # Set primary title to best option
            blueprint['recommended_title'] = titles[0]['title']
        else:
            # Fallback to original logic
            _generate_fallback_title(blueprint, talent_results)
    else:
        print("  ⚠️ Golden Title Generator not available, using basic analysis...")
        _generate_fallback_title(blueprint, talent_results)

    # 2. SKILLS RECOMMENDATION
    print("\n  🛠️ ÖNERİLEN 15 SKİLL (Sıralı):")

    # Combine job skills (demand) with gap analysis
    if jobs_results.get('top_skills'):
        for i, (skill, count) in enumerate(jobs_results['top_skills'][:15], 1):
            blueprint['recommended_skills'].append(skill.title())
            print(f"    {i:2}. {skill.title()}")

    # 3. RATE RECOMMENDATION
    print("\n  💰 ÖNERİLEN RATE:")

    if talent_results.get('rate_distribution'):
        median = talent_results['rate_distribution'].get('median', 20)
        mean = talent_results['rate_distribution'].get('mean', 25)

        # For new freelancers: start below median
        starting_rate = max(15, median * 0.6)
        target_rate = mean

        blueprint['recommended_rate'] = {
            'starting': f"${starting_rate:.0f}/hr",
            'target': f"${target_rate:.0f}/hr"
        }

        print(f"    Başlangıç: ${starting_rate:.0f}/hr (ilk 3-5 iş için)")
        print(f"    Hedef: ${target_rate:.0f}/hr (Rising Talent sonrası)")

    # 4. CATALOG IDEAS
    print("\n  📦 PROJECT CATALOG FİKİRLERİ:")

    if projects_results.get('price_distribution'):
        starter_price = max(30, projects_results['price_distribution'].get('min', 25))
        standard_price = projects_results['price_distribution'].get('median', 75)

        catalog_ideas = [
            {
                'title': 'SQL Data Analysis & Business Report',
                'starter': f'${starter_price}',
                'standard': f'${standard_price}',
                'premium': f'${standard_price * 2}'
            },
            {
                'title': 'Google Looker Studio Dashboard',
                'starter': f'${starter_price}',
                'standard': f'${standard_price}',
                'premium': f'${standard_price * 2}'
            },
            {
                'title': 'Excel/Sheets Automation & Reporting',
                'starter': f'${starter_price}',
                'standard': f'${standard_price}',
                'premium': f'${standard_price * 2}'
            }
        ]

        blueprint['catalog_ideas'] = catalog_ideas

        for idea in catalog_ideas:
            print(f"\n    📊 {idea['title']}")
            print(f"       Starter: {idea['starter']} | Standard: {idea['standard']} | Premium: {idea['premium']}")

    return blueprint


def _generate_fallback_title(blueprint, talent_results):
    """Fallback title generation when Golden Title Generator is not available"""
    if talent_results.get('title_patterns') is not None and not talent_results['title_patterns'].empty:
        top_phrases = talent_results['title_patterns']['Phrase'].head(5).tolist()

        title_parts = []
        for phrase in top_phrases[:3]:
            words = phrase.split()
            for w in words:
                if w.title() not in title_parts and w not in CUSTOM_STOP_WORDS:
                    title_parts.append(w.title())

        recommended_title = "Data Analyst | SQL | Python | " + " | ".join(title_parts[:2])
        blueprint['recommended_title'] = recommended_title[:70]
        blueprint['recommended_titles'] = [{'title': blueprint['recommended_title'], 'pattern': 'fallback'}]

        print(f"\n    {blueprint['recommended_title']}")

# ============================================================
# REPORT GENERATION
# ============================================================

def save_report(jobs_results, talent_results, projects_results, gaps, blueprint, output_file):
    """Analiz raporunu dosyaya kaydet"""
    print("\n" + "=" * 60)
    print("💾 RAPOR KAYDEDİLİYOR...")
    print("=" * 60)
    
    report = {
        'generated_at': datetime.now().isoformat(),
        'jobs_analysis': jobs_results,
        'talent_analysis': talent_results,
        'projects_analysis': projects_results,
        'market_gaps': gaps[:20] if gaps else [],
        'profile_blueprint': blueprint
    }
    
    # Convert DataFrames to dicts
    for key, value in report['jobs_analysis'].items():
        if isinstance(value, pd.DataFrame):
            report['jobs_analysis'][key] = value.to_dict('records')
    
    for key, value in report['talent_analysis'].items():
        if isinstance(value, pd.DataFrame):
            report['talent_analysis'][key] = value.to_dict('records')
    
    # Save JSON
    json_path = os.path.join(OUTPUT_FOLDER, output_file)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"  ✅ Rapor kaydedildi: {json_path}")
    
    return json_path

# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    """Ana analiz pipeline'ı"""
    print("\n" + "=" * 60)
    print("🚀 UPWORK PROFILE OPTIMIZATION PIPELINE")
    print("   Senior Data Analyst + NLP + Market Gap Analysis")
    print("=" * 60)
    print(f"   Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # Create output folder
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    
    # 1. Load Data
    data = load_all_csvs()
    
    if all(df.empty for df in data.values()):
        print("\n❌ Hiç veri bulunamadı! /data klasörüne CSV dosyalarını ekleyin.")
        return
    
    # 2. Analyze Jobs
    jobs_results = analyze_jobs(data['jobs'], "sql data analyst")
    
    # 3. Analyze Talent
    talent_results = analyze_talent(data['talent'], "sql data analyst")
    
    # 4. Analyze Projects
    projects_results = analyze_projects(data['projects'])
    
    # 5. Market Gap Analysis
    gaps = analyze_market_gaps(jobs_results, talent_results)
    
    # 6. Keyword Recommendations
    next_keywords = recommend_next_keywords(data['jobs'], "sql data analyst")
    
    # 7. Generate Blueprint
    blueprint = generate_profile_blueprint(
        jobs_results, 
        talent_results, 
        projects_results, 
        gaps
    )
    
    # 8. Save Report
    save_report(
        jobs_results, 
        talent_results, 
        projects_results, 
        gaps, 
        blueprint,
        'analysis_report.json'
    )
    
    # 9. Summary
    print("\n" + "=" * 60)
    print("✅ ANALİZ TAMAMLANDI!")
    print("=" * 60)
    print(f"""
    📊 Özet:
    ├── Jobs Analiz Edildi: {jobs_results.get('total_jobs', 0)}
    ├── Yüksek Değerli İşler: {jobs_results.get('high_value_jobs', 0)}
    ├── Talent Analiz Edildi: {talent_results.get('total_talent', 0)}
    ├── Elite Talent: {talent_results.get('elite_talent', 0)}
    ├── Projects Analiz Edildi: {projects_results.get('total_projects', 0)}
    └── Market Gap Fırsatları: {len(gaps) if gaps else 0}
    
    📝 Önerilen Başlık:
    {blueprint.get('recommended_title', 'N/A')}
    
    💰 Önerilen Rate:
    {blueprint.get('recommended_rate', 'N/A')}
    
    🚀 Sonraki Keyword Taramaları:
    {', '.join(next_keywords[:5]) if next_keywords else 'N/A'}
    """)

if __name__ == "__main__":
    main()
