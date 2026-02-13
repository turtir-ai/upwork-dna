#!/usr/bin/env python3
"""
ADVANCED UPWORK MARKET INTELLIGENCE DASHBOARD
==============================================
Kapsamlı görselleştirme ve interaktif analiz paketi.

Features:
- Plotly ile interaktif grafikler
- Radar charts, Sankey diagrams, Treemaps
- Heatmaps ve correlation analysis
- Geographic distribution maps
- Rate distribution violin plots
- Market gap bubble charts
- Competitive positioning matrix
- HTML dashboard export

Author: AI-Assisted Analysis
Date: 2026-01
"""

import json
import os
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Visualization libraries
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

# Set default renderer
pio.renderers.default = "browser"

# ============================================================
# CONFIGURATION
# ============================================================
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs", "visuals_advanced")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "outputs", "analysis_report.json")
DATA_FOLDER = os.path.join(os.path.dirname(__file__), "data")

# Color palettes
COLORS = {
    'primary': '#2E86AB',
    'secondary': '#A23B72',
    'success': '#28A745',
    'warning': '#FFC107',
    'danger': '#DC3545',
    'info': '#17A2B8',
    'dark': '#343A40',
    'light': '#F8F9FA'
}

PALETTE = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#3B1F2B', 
           '#95C623', '#5C4D7D', '#E36414', '#0F4C5C', '#9B2335']

# ============================================================
# DATA LOADING
# ============================================================

def load_report() -> Dict[str, Any]:
    """Load the analysis report JSON"""
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_raw_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load raw CSV data for deeper analysis"""
    import glob
    
    jobs_files = glob.glob(os.path.join(DATA_FOLDER, "upwork_jobs_*.csv"))
    talent_files = glob.glob(os.path.join(DATA_FOLDER, "upwork_talent_*.csv"))
    projects_files = glob.glob(os.path.join(DATA_FOLDER, "upwork_projects_*.csv"))
    
    jobs_dfs = []
    for f in jobs_files:
        try:
            df = pd.read_csv(f, low_memory=False)
            # Add source file tag
            df['source'] = os.path.basename(f).replace('upwork_jobs_', '').replace('.csv', '').split('_run_')[0]
            jobs_dfs.append(df)
        except: continue
    
    talent_dfs = []
    for f in talent_files:
        try:
            df = pd.read_csv(f, low_memory=False)
            df['source'] = os.path.basename(f).replace('upwork_talent_', '').replace('.csv', '').split('_run_')[0]
            talent_dfs.append(df)
        except: continue
    
    projects_dfs = []
    for f in projects_files:
        try:
            df = pd.read_csv(f, low_memory=False)
            df['source'] = os.path.basename(f).replace('upwork_projects_', '').replace('.csv', '').split('_run_')[0]
            projects_dfs.append(df)
        except: continue
    
    jobs = pd.concat(jobs_dfs, ignore_index=True).drop_duplicates() if jobs_dfs else pd.DataFrame()
    talent = pd.concat(talent_dfs, ignore_index=True).drop_duplicates() if talent_dfs else pd.DataFrame()
    projects = pd.concat(projects_dfs, ignore_index=True).drop_duplicates() if projects_dfs else pd.DataFrame()
    
    return jobs, talent, projects

def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# DATA PROCESSING UTILITIES
# ============================================================

def extract_rate(rate_str) -> float:
    """Extract numeric rate from string"""
    import re
    if not isinstance(rate_str, str):
        return 0
    match = re.search(r'\$?(\d+\.?\d*)', rate_str)
    return float(match.group(1)) if match else 0

def extract_budget(budget_str) -> float:
    """Extract budget value"""
    import re
    if not isinstance(budget_str, str):
        return 0
    clean = re.sub(r'[,\$]', '', str(budget_str))
    match = re.search(r'(\d+\.?\d*)', clean)
    return float(match.group(1)) if match else 0

def extract_price(price_str) -> float:
    """Extract price from 'From$XX' format"""
    import re
    if not isinstance(price_str, str):
        return 0
    match = re.search(r'(\d+\.?\d*)', str(price_str).replace(',', ''))
    return float(match.group(1)) if match else 0

# ============================================================
# PLOTLY INTERACTIVE VISUALIZATIONS
# ============================================================

def create_skills_radar_chart(report: Dict) -> go.Figure:
    """Skills demand vs supply radar chart"""
    gaps = report.get('market_gaps', [])[:12]
    if not gaps:
        return None
    
    df = pd.DataFrame(gaps)
    
    # Normalize values for radar
    df['demand_norm'] = (df['demand_pct'] / df['demand_pct'].max()) * 100
    df['supply_norm'] = (df['supply_pct'] / df['supply_pct'].max()) * 100 if df['supply_pct'].max() > 0 else 0
    
    fig = go.Figure()
    
    # Demand trace
    fig.add_trace(go.Scatterpolar(
        r=df['demand_norm'].tolist() + [df['demand_norm'].iloc[0]],
        theta=df['skill'].str.title().tolist() + [df['skill'].str.title().iloc[0]],
        fill='toself',
        name='Talep (Jobs)',
        fillcolor='rgba(46, 134, 171, 0.3)',
        line=dict(color=COLORS['primary'], width=2)
    ))
    
    # Supply trace
    fig.add_trace(go.Scatterpolar(
        r=df['supply_norm'].tolist() + [df['supply_norm'].iloc[0]],
        theta=df['skill'].str.title().tolist() + [df['skill'].str.title().iloc[0]],
        fill='toself',
        name='Arz (Talent)',
        fillcolor='rgba(162, 59, 114, 0.3)',
        line=dict(color=COLORS['secondary'], width=2)
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100])
        ),
        title=dict(text='🎯 Skills Radar: Talep vs Arz Karşılaştırması', font=dict(size=18)),
        showlegend=True,
        template='plotly_white',
        height=600
    )
    
    return fig

def create_market_gap_bubble_chart(report: Dict) -> go.Figure:
    """Market gap bubble chart with gap ratio as size"""
    gaps = report.get('market_gaps', [])
    if not gaps:
        return None
    
    df = pd.DataFrame(gaps)
    df['gap_score'] = df['gap_ratio'] * 100
    df['bubble_size'] = df['gap_ratio'] * 50 + 10
    
    fig = px.scatter(
        df,
        x='supply_pct',
        y='demand_pct',
        size='bubble_size',
        color='gap_ratio',
        text='skill',
        color_continuous_scale='RdYlGn_r',
        labels={
            'supply_pct': 'Arz (Talent %, Rekabet)',
            'demand_pct': 'Talep (Jobs %)',
            'gap_ratio': 'Gap Ratio'
        },
        title='🔥 Market Opportunity Matrix: Talep vs Rekabet'
    )
    
    fig.update_traces(textposition='top center', textfont_size=9)
    
    # Add diagonal line (perfect balance)
    max_val = max(df['demand_pct'].max(), df['supply_pct'].max())
    fig.add_trace(go.Scatter(
        x=[0, max_val],
        y=[0, max_val],
        mode='lines',
        line=dict(dash='dash', color='gray', width=1),
        name='Denge Çizgisi',
        showlegend=True
    ))
    
    # Add quadrant annotations
    fig.add_annotation(x=5, y=max_val*0.9, text="🎯 FIRSAT ALANI<br>(Yüksek Talep, Düşük Rekabet)",
                      showarrow=False, font=dict(size=10, color='green'))
    fig.add_annotation(x=max_val*0.7, y=5, text="⚠️ DOYGUN PAZAR<br>(Düşük Talep, Yüksek Rekabet)",
                      showarrow=False, font=dict(size=10, color='red'))
    
    fig.update_layout(template='plotly_white', height=700)
    
    return fig

def create_rate_distribution_violin(talent_df: pd.DataFrame) -> go.Figure:
    """Violin plot of rates by location"""
    if talent_df.empty:
        return None
    
    talent_df['rate_num'] = talent_df['rate'].apply(extract_rate)
    talent_df = talent_df[talent_df['rate_num'] > 0]
    
    # Get location column
    loc_col = 'location' if 'location' in talent_df.columns else 'detail_location'
    if loc_col not in talent_df.columns:
        return None
    
    # Top 8 countries
    top_countries = talent_df[loc_col].value_counts().head(8).index.tolist()
    filtered = talent_df[talent_df[loc_col].isin(top_countries)]
    
    fig = go.Figure()
    
    for country in top_countries:
        country_data = filtered[filtered[loc_col] == country]['rate_num']
        fig.add_trace(go.Violin(
            y=country_data,
            name=country,
            box_visible=True,
            meanline_visible=True,
            fillcolor='lightseagreen',
            opacity=0.6,
            line_color=COLORS['primary']
        ))
    
    fig.update_layout(
        title='💰 Saatlik Ücret Dağılımı (Ülkelere Göre)',
        yaxis_title='Saatlik Ücret ($)',
        template='plotly_white',
        height=500,
        showlegend=False
    )
    
    return fig

def create_skills_treemap(report: Dict) -> go.Figure:
    """Treemap of skills by demand"""
    jobs_skills = report.get('jobs_analysis', {}).get('top_skills', [])[:20]
    if not jobs_skills:
        return None
    
    labels = [s[0].title() for s in jobs_skills]
    values = [s[1] for s in jobs_skills]
    
    # Create parent categories (manual grouping)
    categories = []
    for skill in labels:
        skill_lower = skill.lower()
        if any(x in skill_lower for x in ['python', 'sql', 'javascript', 'r', 'api']):
            categories.append('Programming')
        elif any(x in skill_lower for x in ['power bi', 'tableau', 'looker', 'visualization', 'dashboard']):
            categories.append('Visualization')
        elif any(x in skill_lower for x in ['excel', 'sheets', 'spreadsheet']):
            categories.append('Spreadsheets')
        elif any(x in skill_lower for x in ['ai', 'machine learning', 'data science']):
            categories.append('AI/ML')
        elif any(x in skill_lower for x in ['analytics', 'google analytics', 'analysis']):
            categories.append('Analytics')
        else:
            categories.append('Other')
    
    fig = px.treemap(
        names=labels,
        parents=categories,
        values=values,
        color=values,
        color_continuous_scale='Blues',
        title='🗂️ Skills Hiyerarşisi (İş İlanlarında)'
    )
    
    fig.update_layout(height=600, template='plotly_white')
    
    return fig

def create_budget_sunburst(jobs_df: pd.DataFrame) -> go.Figure:
    """Sunburst chart of budget ranges by job type"""
    if jobs_df.empty:
        return None
    
    jobs_df['budget_num'] = jobs_df['budget'].apply(extract_budget)
    
    # Create budget ranges
    def get_budget_range(b):
        if b == 0: return 'Belirtilmemiş'
        elif b < 100: return '$0-100'
        elif b < 500: return '$100-500'
        elif b < 1000: return '$500-1K'
        elif b < 5000: return '$1K-5K'
        elif b < 10000: return '$5K-10K'
        else: return '$10K+'
    
    jobs_df['budget_range'] = jobs_df['budget_num'].apply(get_budget_range)
    
    # Get job type
    jobs_df['type'] = jobs_df['job_type'].fillna('Unknown').apply(
        lambda x: 'Fixed' if 'fixed' in str(x).lower() else ('Hourly' if 'hourly' in str(x).lower() else 'Other')
    )
    
    agg = jobs_df.groupby(['type', 'budget_range']).size().reset_index(name='count')
    
    fig = px.sunburst(
        agg,
        path=['type', 'budget_range'],
        values='count',
        color='count',
        color_continuous_scale='Viridis',
        title='☀️ İş Türü ve Bütçe Dağılımı'
    )
    
    fig.update_layout(height=600)
    
    return fig

def create_niche_comparison_bar(jobs_df: pd.DataFrame, talent_df: pd.DataFrame) -> go.Figure:
    """Grouped bar chart comparing niches"""
    if jobs_df.empty or talent_df.empty:
        return None
    
    # Classify niches by source
    def classify_niche(source):
        source = str(source).lower()
        if 'sql' in source:
            return 'SQL Specialist'
        elif 'ai' in source or 'llm' in source or 'chatgpt' in source:
            return 'AI/Automation'
        elif 'visualization' in source or 'power_bi' in source or 'looker' in source:
            return 'Data Visualization'
        elif 'analytics' in source or 'google_analytics' in source:
            return 'Analytics'
        else:
            return 'General Data'
    
    jobs_df['niche'] = jobs_df['source'].apply(classify_niche)
    talent_df['niche'] = talent_df['source'].apply(classify_niche)
    talent_df['rate_num'] = talent_df['rate'].apply(extract_rate)
    
    # Aggregate
    job_counts = jobs_df.groupby('niche').size().reset_index(name='job_count')
    talent_rates = talent_df.groupby('niche')['rate_num'].mean().reset_index(name='avg_rate')
    
    merged = job_counts.merge(talent_rates, on='niche', how='outer').fillna(0)
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Bar(name='İş Sayısı', x=merged['niche'], y=merged['job_count'], 
               marker_color=COLORS['primary'], opacity=0.8),
        secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(name='Ortalama Rate', x=merged['niche'], y=merged['avg_rate'],
                  mode='lines+markers', line=dict(color=COLORS['secondary'], width=3),
                  marker=dict(size=12)),
        secondary_y=True
    )
    
    fig.update_layout(
        title='📊 Niche Karşılaştırması: İş Sayısı vs Ortalama Ücret',
        template='plotly_white',
        height=500,
        barmode='group'
    )
    fig.update_yaxes(title_text="İş Sayısı", secondary_y=False)
    fig.update_yaxes(title_text="Ortalama Rate ($/hr)", secondary_y=True)
    
    return fig

def create_project_price_heatmap(projects_df: pd.DataFrame) -> go.Figure:
    """Heatmap of project prices by delivery time and rating"""
    if projects_df.empty:
        return None
    
    projects_df['price_num'] = projects_df['price'].apply(extract_price)
    
    # Parse rating
    def parse_rating(r):
        try:
            return float(str(r).replace('n/a', '0'))
        except:
            return 0
    
    projects_df['rating_num'] = projects_df['rating'].apply(parse_rating)
    
    # Create buckets
    projects_df['price_bucket'] = pd.cut(projects_df['price_num'], 
                                          bins=[0, 20, 50, 100, 200, 500, float('inf')],
                                          labels=['$0-20', '$20-50', '$50-100', '$100-200', '$200-500', '$500+'])
    
    projects_df['rating_bucket'] = pd.cut(projects_df['rating_num'],
                                           bins=[0, 4.0, 4.5, 4.8, 5.0],
                                           labels=['<4.0', '4.0-4.5', '4.5-4.8', '4.8-5.0'])
    
    # Aggregate
    pivot = projects_df.groupby(['rating_bucket', 'price_bucket']).size().unstack(fill_value=0)
    
    fig = px.imshow(
        pivot.values,
        labels=dict(x='Fiyat Aralığı', y='Rating', color='Proje Sayısı'),
        x=pivot.columns.astype(str).tolist(),
        y=pivot.index.astype(str).tolist(),
        color_continuous_scale='YlOrRd',
        title='🔥 Proje Yoğunluğu: Fiyat vs Rating Heatmap'
    )
    
    fig.update_layout(height=500, template='plotly_white')
    
    return fig

def create_title_wordcloud_chart(report: Dict) -> go.Figure:
    """Bar chart representation of common title bigrams"""
    patterns = report.get('talent_analysis', {}).get('title_patterns', [])[:15]
    if not patterns:
        return None
    
    df = pd.DataFrame(patterns)
    df = df.sort_values('Frequency', ascending=True)
    
    # Color by frequency
    colors = px.colors.sample_colorscale('Viridis', df['Frequency'] / df['Frequency'].max())
    
    fig = go.Figure(go.Bar(
        x=df['Frequency'],
        y=df['Phrase'].str.title(),
        orientation='h',
        marker=dict(color=colors),
        text=df['Frequency'],
        textposition='outside'
    ))
    
    fig.update_layout(
        title='📝 Elite Freelancer Başlıklarında En Sık Geçen İfadeler',
        xaxis_title='Frekans',
        yaxis_title='',
        template='plotly_white',
        height=500
    )
    
    return fig

def create_competitive_positioning_scatter(talent_df: pd.DataFrame) -> go.Figure:
    """Scatter plot: Rate vs Success Score positioning"""
    if talent_df.empty:
        return None
    
    import re
    
    talent_df['rate_num'] = talent_df['rate'].apply(extract_rate)
    
    # Parse JSS
    jss_col = 'detail_job_success' if 'detail_job_success' in talent_df.columns else 'job_success'
    if jss_col not in talent_df.columns:
        return None
    
    def parse_jss(s):
        if not isinstance(s, str):
            return 0
        match = re.search(r'(\d+)', s)
        return int(match.group(1)) if match else 0
    
    talent_df['jss'] = talent_df[jss_col].apply(parse_jss)
    
    # Filter valid data
    valid = talent_df[(talent_df['rate_num'] > 0) & (talent_df['jss'] > 0)]
    
    if valid.empty:
        return None
    
    # Sample if too large
    if len(valid) > 500:
        valid = valid.sample(500)
    
    loc_col = 'location' if 'location' in valid.columns else 'detail_location'
    
    fig = px.scatter(
        valid,
        x='jss',
        y='rate_num',
        color=loc_col if loc_col in valid.columns else None,
        size='rate_num',
        hover_data=['title'] if 'title' in valid.columns else None,
        labels={'jss': 'Job Success Score (%)', 'rate_num': 'Saatlik Ücret ($)'},
        title='🏆 Rekabet Pozisyonlama: JSS vs Rate'
    )
    
    # Add quadrant lines
    median_rate = valid['rate_num'].median()
    median_jss = valid['jss'].median()
    
    fig.add_hline(y=median_rate, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(x=median_jss, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(template='plotly_white', height=600)
    
    return fig

def create_delivery_funnel(report: Dict) -> go.Figure:
    """Funnel chart of delivery times"""
    delivery = report.get('projects_analysis', {}).get('delivery_patterns', {})
    if not delivery:
        return None
    
    # Sort by count
    sorted_delivery = sorted(delivery.items(), key=lambda x: x[1], reverse=True)
    
    labels = [d[0] for d in sorted_delivery]
    values = [d[1] for d in sorted_delivery]
    
    fig = go.Figure(go.Funnel(
        y=labels,
        x=values,
        textinfo="value+percent initial",
        marker=dict(color=PALETTE[:len(labels)])
    ))
    
    fig.update_layout(
        title='📦 Project Catalog Teslimat Süresi Funneli',
        template='plotly_white',
        height=500
    )
    
    return fig

def create_skills_gap_waterfall(report: Dict) -> go.Figure:
    """Waterfall chart showing skill gaps"""
    gaps = report.get('market_gaps', [])[:10]
    if not gaps:
        return None
    
    df = pd.DataFrame(gaps)
    df['gap_pp'] = df['demand_pct'] - df['supply_pct']  # Percentage points
    df = df.sort_values('gap_pp', ascending=False)
    
    # Classify as positive (opportunity) or negative (saturated)
    colors = ['green' if g > 0 else 'red' for g in df['gap_pp']]
    
    fig = go.Figure(go.Waterfall(
        name="Gap",
        orientation="v",
        x=df['skill'].str.title(),
        y=df['gap_pp'],
        connector=dict(line=dict(color="rgb(63, 63, 63)")),
        decreasing=dict(marker=dict(color="red")),
        increasing=dict(marker=dict(color="green")),
        totals=dict(marker=dict(color="blue"))
    ))
    
    fig.update_layout(
        title='📈 Skill Gap Waterfall (Talep - Arz Farkı %)',
        yaxis_title='Gap (Yüzde Puanı)',
        template='plotly_white',
        height=500,
        showlegend=False
    )
    
    return fig

# ============================================================
# STATIC MATPLOTLIB VISUALIZATIONS (High-Quality PNG)
# ============================================================

def plot_comprehensive_dashboard(report: Dict, jobs_df: pd.DataFrame, talent_df: pd.DataFrame):
    """Create a comprehensive multi-panel static dashboard"""
    
    sns.set_theme(style="whitegrid")
    fig = plt.figure(figsize=(20, 16))
    
    # Create grid
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3)
    
    # 1. Top Skills Comparison (Jobs vs Talent)
    ax1 = fig.add_subplot(gs[0, 0])
    jobs_skills = dict(report.get('jobs_analysis', {}).get('top_skills', [])[:10])
    talent_skills = dict(report.get('talent_analysis', {}).get('top_skills', [])[:10])
    
    all_skills = list(set(list(jobs_skills.keys())[:8]))
    x = np.arange(len(all_skills))
    width = 0.35
    
    jobs_vals = [jobs_skills.get(s, 0) for s in all_skills]
    talent_vals = [talent_skills.get(s, 0) for s in all_skills]
    
    ax1.barh(x - width/2, jobs_vals, width, label='Talep (Jobs)', color=COLORS['primary'])
    ax1.barh(x + width/2, talent_vals, width, label='Arz (Talent)', color=COLORS['secondary'])
    ax1.set_yticks(x)
    ax1.set_yticklabels([s.title()[:15] for s in all_skills], fontsize=8)
    ax1.set_xlabel('Sayı')
    ax1.set_title('📊 Top Skills: Talep vs Arz', fontweight='bold')
    ax1.legend(fontsize=8)
    
    # 2. Rate Distribution Histogram
    ax2 = fig.add_subplot(gs[0, 1])
    if not talent_df.empty:
        talent_df['rate_num'] = talent_df['rate'].apply(extract_rate)
        rates = talent_df[talent_df['rate_num'] > 0]['rate_num']
        ax2.hist(rates, bins=30, color=COLORS['primary'], edgecolor='white', alpha=0.7)
        ax2.axvline(rates.median(), color=COLORS['secondary'], linestyle='--', linewidth=2, label=f'Medyan: ${rates.median():.0f}')
        ax2.axvline(rates.mean(), color=COLORS['warning'], linestyle='--', linewidth=2, label=f'Ortalama: ${rates.mean():.0f}')
    ax2.set_xlabel('Saatlik Ücret ($)')
    ax2.set_ylabel('Freelancer Sayısı')
    ax2.set_title('💰 Rate Dağılımı', fontweight='bold')
    ax2.legend(fontsize=8)
    
    # 3. Budget Breakdown Pie
    ax3 = fig.add_subplot(gs[0, 2])
    budget_stats = report.get('jobs_analysis', {}).get('budget_stats', {})
    if budget_stats:
        sizes = [budget_stats.get('fixed_count', 0), budget_stats.get('hourly_count', 0)]
        labels = ['Fixed Price', 'Hourly']
        explode = (0.05, 0)
        ax3.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',
               colors=[COLORS['primary'], COLORS['secondary']], startangle=90)
    ax3.set_title('📋 İş Modeli Dağılımı', fontweight='bold')
    
    # 4. Market Gap Bar Chart
    ax4 = fig.add_subplot(gs[1, :2])
    gaps = report.get('market_gaps', [])[:12]
    if gaps:
        df = pd.DataFrame(gaps)
        x = np.arange(len(df))
        width = 0.35
        ax4.bar(x - width/2, df['demand_pct'], width, label='Talep %', color=COLORS['primary'])
        ax4.bar(x + width/2, df['supply_pct'], width, label='Arz %', color=COLORS['secondary'])
        ax4.set_xticks(x)
        ax4.set_xticklabels([s[:12] for s in df['skill'].str.title()], rotation=45, ha='right', fontsize=8)
        ax4.set_ylabel('Yüzde (%)')
        ax4.set_title('🎯 Market Gap Analizi: Talep vs Arz', fontweight='bold')
        ax4.legend()
    
    # 5. Location Distribution
    ax5 = fig.add_subplot(gs[1, 2])
    locations = report.get('talent_analysis', {}).get('location_analysis', {})
    if locations:
        top_locs = dict(list(locations.items())[:8])
        colors_list = sns.color_palette("viridis", len(top_locs))
        ax5.barh(list(top_locs.keys()), list(top_locs.values()), color=colors_list)
        ax5.set_xlabel('Freelancer Sayısı')
        ax5.set_title('🌍 Elite Freelancer Lokasyonları', fontweight='bold')
    
    # 6. Title Bigrams
    ax6 = fig.add_subplot(gs[2, 0])
    bigrams = report.get('jobs_analysis', {}).get('title_ngrams', [])[:10]
    if bigrams:
        df = pd.DataFrame(bigrams)
        colors_list = sns.color_palette("Blues_r", len(df))
        ax6.barh(df['Phrase'].str.title(), df['Frequency'], color=colors_list)
        ax6.set_xlabel('Frekans')
        ax6.set_title('🔤 İş Başlığı Bigrams', fontweight='bold')
    
    # 7. Delivery Time Distribution
    ax7 = fig.add_subplot(gs[2, 1])
    delivery = report.get('projects_analysis', {}).get('delivery_patterns', {})
    if delivery:
        sorted_del = dict(sorted(delivery.items(), key=lambda x: x[1], reverse=True)[:8])
        colors_list = sns.color_palette("coolwarm", len(sorted_del))
        ax7.bar(list(sorted_del.keys()), list(sorted_del.values()), color=colors_list)
        ax7.set_xticklabels(list(sorted_del.keys()), rotation=45, ha='right', fontsize=8)
        ax7.set_ylabel('Proje Sayısı')
        ax7.set_title('⏱️ Teslimat Süreleri', fontweight='bold')
    
    # 8. Summary Stats Box
    ax8 = fig.add_subplot(gs[2, 2])
    ax8.axis('off')
    
    # Create stats text
    stats_text = f"""
    📊 ÖZET İSTATİSTİKLER
    ━━━━━━━━━━━━━━━━━━━━━
    
    💼 Toplam İş İlanı: {report.get('jobs_analysis', {}).get('total_jobs', 0):,}
    🎯 Yüksek Değerli: {report.get('jobs_analysis', {}).get('high_value_jobs', 0):,}
    
    👥 Toplam Talent: {report.get('talent_analysis', {}).get('total_talent', 0):,}
    🌟 Elite Talent: {report.get('talent_analysis', {}).get('elite_talent', 0):,}
    💎 Premium ($75+): {report.get('talent_analysis', {}).get('premium_talent', 0):,}
    
    📦 Toplam Proje: {report.get('projects_analysis', {}).get('total_projects', 0):,}
    ⭐ Top Projects: {report.get('projects_analysis', {}).get('top_projects', 0):,}
    
    💰 Ortalama Rate: ${report.get('talent_analysis', {}).get('rate_distribution', {}).get('mean', 0):.0f}/hr
    💰 Medyan Rate: ${report.get('talent_analysis', {}).get('rate_distribution', {}).get('median', 0):.0f}/hr
    """
    
    ax8.text(0.1, 0.5, stats_text, transform=ax8.transAxes, fontsize=11,
            verticalalignment='center', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Main title
    fig.suptitle('🚀 UPWORK MARKET INTELLIGENCE DASHBOARD', fontsize=18, fontweight='bold', y=0.98)
    
    plt.savefig(os.path.join(OUTPUT_DIR, 'comprehensive_dashboard.png'), dpi=150, bbox_inches='tight',
               facecolor='white', edgecolor='none')
    plt.close()
    print("  ✅ comprehensive_dashboard.png kaydedildi")

def plot_profile_recommendation_card(report: Dict):
    """Create a visual profile recommendation card"""
    blueprint = report.get('profile_blueprint', {})
    
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.axis('off')
    
    # Background
    ax.set_facecolor('#f8f9fa')
    
    # Header
    ax.text(0.5, 0.95, '🎯 PROFİL OPTİMİZASYON ÖNERİSİ', transform=ax.transAxes,
           fontsize=20, fontweight='bold', ha='center', color=COLORS['primary'])
    
    # Title recommendation
    title = blueprint.get('recommended_title', 'Data Analyst | SQL | Python')
    ax.text(0.5, 0.85, f'📝 Önerilen Başlık:', transform=ax.transAxes,
           fontsize=12, ha='center', color='gray')
    ax.text(0.5, 0.80, title, transform=ax.transAxes,
           fontsize=16, fontweight='bold', ha='center', color=COLORS['dark'],
           bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8))
    
    # Skills
    skills = blueprint.get('recommended_skills', [])[:15]
    ax.text(0.5, 0.70, '🛠️ Önerilen Skiller:', transform=ax.transAxes,
           fontsize=12, ha='center', color='gray')
    
    # Display skills in a grid-like format
    skills_text = ' • '.join(skills[:5]) + '\n' + ' • '.join(skills[5:10]) + '\n' + ' • '.join(skills[10:15])
    ax.text(0.5, 0.58, skills_text, transform=ax.transAxes,
           fontsize=10, ha='center', color=COLORS['dark'],
           bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.5))
    
    # Rate recommendation
    rate = blueprint.get('recommended_rate', {})
    ax.text(0.25, 0.40, '💰 Başlangıç Rate:', transform=ax.transAxes,
           fontsize=11, ha='center', color='gray')
    ax.text(0.25, 0.35, rate.get('starting', '$20/hr'), transform=ax.transAxes,
           fontsize=18, fontweight='bold', ha='center', color=COLORS['success'])
    
    ax.text(0.75, 0.40, '🎯 Hedef Rate:', transform=ax.transAxes,
           fontsize=11, ha='center', color='gray')
    ax.text(0.75, 0.35, rate.get('target', '$50/hr'), transform=ax.transAxes,
           fontsize=18, fontweight='bold', ha='center', color=COLORS['primary'])
    
    # Catalog ideas
    catalogs = blueprint.get('catalog_ideas', [])
    ax.text(0.5, 0.25, '📦 Project Catalog Fikirleri:', transform=ax.transAxes,
           fontsize=12, ha='center', color='gray')
    
    catalog_text = ""
    for c in catalogs[:3]:
        catalog_text += f"• {c.get('title', '')}: {c.get('starter', '')} → {c.get('premium', '')}\n"
    
    ax.text(0.5, 0.12, catalog_text, transform=ax.transAxes,
           fontsize=10, ha='center', color=COLORS['dark'],
           bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.5))
    
    # Footer
    ax.text(0.5, 0.02, 'Veri Bazlı Analiz | Upwork Market Intelligence', transform=ax.transAxes,
           fontsize=9, ha='center', color='gray', style='italic')
    
    plt.savefig(os.path.join(OUTPUT_DIR, 'profile_recommendation_card.png'), dpi=150, bbox_inches='tight',
               facecolor='#f8f9fa', edgecolor='none')
    plt.close()
    print("  ✅ profile_recommendation_card.png kaydedildi")

# ============================================================
# HTML DASHBOARD EXPORT
# ============================================================

def create_html_dashboard(report: Dict, jobs_df: pd.DataFrame, talent_df: pd.DataFrame, projects_df: pd.DataFrame):
    """Create an interactive HTML dashboard with all Plotly charts"""
    
    charts = []
    
    # Generate all charts
    print("  📊 Interaktif grafikler oluşturuluyor...")
    
    radar = create_skills_radar_chart(report)
    if radar: charts.append(('Skills Radar', radar))
    
    bubble = create_market_gap_bubble_chart(report)
    if bubble: charts.append(('Market Opportunity', bubble))
    
    violin = create_rate_distribution_violin(talent_df)
    if violin: charts.append(('Rate Distribution', violin))
    
    treemap = create_skills_treemap(report)
    if treemap: charts.append(('Skills Treemap', treemap))
    
    sunburst = create_budget_sunburst(jobs_df)
    if sunburst: charts.append(('Budget Sunburst', sunburst))
    
    niche = create_niche_comparison_bar(jobs_df, talent_df)
    if niche: charts.append(('Niche Comparison', niche))
    
    heatmap = create_project_price_heatmap(projects_df)
    if heatmap: charts.append(('Price Heatmap', heatmap))
    
    wordcloud = create_title_wordcloud_chart(report)
    if wordcloud: charts.append(('Title Patterns', wordcloud))
    
    positioning = create_competitive_positioning_scatter(talent_df)
    if positioning: charts.append(('Competitive Positioning', positioning))
    
    funnel = create_delivery_funnel(report)
    if funnel: charts.append(('Delivery Funnel', funnel))
    
    waterfall = create_skills_gap_waterfall(report)
    if waterfall: charts.append(('Gap Waterfall', waterfall))
    
    # Generate HTML
    html_content = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upwork Market Intelligence Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .header {
            text-align: center;
            color: white;
            padding: 30px;
            margin-bottom: 30px;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { font-size: 1.2em; opacity: 0.9; }
        .dashboard {
            max-width: 1600px;
            margin: 0 auto;
        }
        .chart-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(700px, 1fr));
            gap: 25px;
        }
        .chart-card {
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
            transition: transform 0.3s ease;
        }
        .chart-card:hover {
            transform: translateY(-5px);
        }
        .chart-title {
            background: linear-gradient(90deg, #2E86AB, #A23B72);
            color: white;
            padding: 15px 20px;
            font-size: 1.1em;
            font-weight: 600;
        }
        .chart-container {
            padding: 15px;
        }
        .stats-bar {
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            border-radius: 10px;
            padding: 20px 30px;
            text-align: center;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            min-width: 180px;
        }
        .stat-value { font-size: 2em; font-weight: bold; color: #2E86AB; }
        .stat-label { color: #666; font-size: 0.9em; margin-top: 5px; }
        .footer {
            text-align: center;
            color: white;
            padding: 30px;
            margin-top: 30px;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Upwork Market Intelligence Dashboard</h1>
        <p>Veri Odaklı Profil Optimizasyonu | """ + report.get('generated_at', '')[:10] + """</p>
    </div>
    
    <div class="dashboard">
        <div class="stats-bar">
            <div class="stat-card">
                <div class="stat-value">""" + f"{report.get('jobs_analysis', {}).get('total_jobs', 0):,}" + """</div>
                <div class="stat-label">💼 İş İlanı</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">""" + f"{report.get('jobs_analysis', {}).get('high_value_jobs', 0):,}" + """</div>
                <div class="stat-label">🎯 Yüksek Değerli</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">""" + f"{report.get('talent_analysis', {}).get('total_talent', 0):,}" + """</div>
                <div class="stat-label">👥 Freelancer</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">""" + f"{report.get('talent_analysis', {}).get('elite_talent', 0):,}" + """</div>
                <div class="stat-label">🌟 Elite Talent</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">$""" + f"{report.get('talent_analysis', {}).get('rate_distribution', {}).get('median', 0):.0f}" + """</div>
                <div class="stat-label">💰 Medyan Rate</div>
            </div>
        </div>
        
        <div class="chart-grid">
"""
    
    # Add each chart
    for i, (title, fig) in enumerate(charts):
        chart_html = pio.to_html(fig, full_html=False, include_plotlyjs=False)
        html_content += f"""
            <div class="chart-card">
                <div class="chart-title">{title}</div>
                <div class="chart-container" id="chart-{i}">
                    {chart_html}
                </div>
            </div>
"""
    
    html_content += """
        </div>
    </div>
    
    <div class="footer">
        <p>📊 Powered by AI-Assisted Market Analysis | Data-Driven Insights</p>
    </div>
</body>
</html>
"""
    
    # Save HTML
    html_path = os.path.join(OUTPUT_DIR, 'interactive_dashboard.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"  ✅ interactive_dashboard.html kaydedildi")
    
    return html_path

# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    print("=" * 60)
    print("🚀 ADVANCED VISUALIZATION DASHBOARD")
    print("=" * 60)
    
    ensure_output_dir()
    
    # Load data
    print("\n📂 Veriler yükleniyor...")
    report = load_report()
    jobs_df, talent_df, projects_df = load_raw_data()
    print(f"  ✅ Report: {len(report)} section")
    print(f"  ✅ Jobs: {len(jobs_df)} satır")
    print(f"  ✅ Talent: {len(talent_df)} satır")
    print(f"  ✅ Projects: {len(projects_df)} satır")
    
    # Generate static visualizations
    print("\n🎨 Statik görseller oluşturuluyor...")
    plot_comprehensive_dashboard(report, jobs_df, talent_df)
    plot_profile_recommendation_card(report)
    
    # Generate interactive HTML dashboard
    print("\n🌐 İnteraktif dashboard oluşturuluyor...")
    html_path = create_html_dashboard(report, jobs_df, talent_df, projects_df)
    
    # Save individual Plotly charts as HTML
    print("\n💾 Bireysel grafikler kaydediliyor...")
    
    charts_to_save = [
        ('skills_radar', create_skills_radar_chart(report)),
        ('market_opportunity_bubble', create_market_gap_bubble_chart(report)),
        ('rate_violin', create_rate_distribution_violin(talent_df)),
        ('skills_treemap', create_skills_treemap(report)),
        ('budget_sunburst', create_budget_sunburst(jobs_df)),
        ('niche_comparison', create_niche_comparison_bar(jobs_df, talent_df)),
        ('price_heatmap', create_project_price_heatmap(projects_df)),
        ('title_patterns', create_title_wordcloud_chart(report)),
        ('competitive_positioning', create_competitive_positioning_scatter(talent_df)),
        ('delivery_funnel', create_delivery_funnel(report)),
        ('gap_waterfall', create_skills_gap_waterfall(report))
    ]
    
    for name, fig in charts_to_save:
        if fig:
            fig.write_html(os.path.join(OUTPUT_DIR, f'{name}.html'))
            print(f"  ✅ {name}.html")
    
    print("\n" + "=" * 60)
    print("✅ TÜM GÖRSELLEŞTİRMELER TAMAMLANDI!")
    print("=" * 60)
    print(f"\n📁 Çıktı klasörü: {OUTPUT_DIR}")
    print(f"🌐 Dashboard: {html_path}")
    print("\nOluşturulan dosyalar:")
    for f in os.listdir(OUTPUT_DIR):
        if not f.startswith('.'):
            print(f"  • {f}")

if __name__ == "__main__":
    main()
