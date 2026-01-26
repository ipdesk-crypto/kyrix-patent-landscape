import streamlit as st
import pandas as pd
import os
import re
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import hmac
from datetime import datetime

# --- 1. PAGE CONFIG & KYRIX LUXURY THEME ---
st.set_page_config(
    page_title="Kyrix | Intangible Patent Landscape",
    page_icon="🛡️",
    layout="wide"
)

st.markdown("""
    <style>
    .stApp { background-color: #0F172A; } 
    h1, h2, h3, h4, p, span, label, .stMarkdown { color: #F1F5F9 !important; font-family: 'Inter', sans-serif; }
    
    .metric-badge {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        color: #F59E0B !important;
        padding: 15px 30px;
        border-radius: 12px;
        font-weight: 800; font-size: 20px;
        border: 1px solid #334155;
        display: inline-block; margin-bottom: 20px;
    }
    
    .section-header {
        font-size: 14px; font-weight: 900; letter-spacing: 2px; text-transform: uppercase;
        padding: 15px 20px; border-radius: 8px 8px 0 0; margin-top: 30px;
        border: 1px solid #475569; border-bottom: none;
    }
    .enriched-banner { background: linear-gradient(90deg, #1E40AF 0%, #3B82F6 100%); color: #FFFFFF !important; }
    .raw-banner { background: linear-gradient(90deg, #1E293B 0%, #334155 100%); color: #CBD5E1 !important; }
    .title-banner { background: #1E293B; border: 1px solid #F59E0B; color: #F59E0B !important; }
    
    .data-card { 
        background-color: #111827; padding: 16px; 
        border: 1px solid #1F2937; border-bottom: 1px solid #374151;
        min-height: 80px;
    }
    .label-text { font-size: 10px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 6px; }
    .value-text { font-size: 15px; color: #F8FAFC; font-weight: 500; line-height: 1.4; }
    
    .abstract-container {
        background-color: #1E293B; padding: 30px; border-radius: 0 0 12px 12px;
        border: 1px solid #334155; border-top: none;
        line-height: 1.8; font-size: 17px; color: #E2E8F0; text-align: justify;
    }
    .type-badge {
        background-color: #F59E0B; color: #0F172A; padding: 4px 12px; 
        border-radius: 4px; font-weight: 800; font-size: 12px; margin-left: 10px;
    }

    [data-testid="stSidebar"] { background-color: #020617 !important; border-right: 1px solid #1E293B; }
    .stTabs [aria-selected="true"] { background-color: #3B82F6 !important; color: #FFFFFF !important; font-weight: bold; }
    
    /* Archistrategos Metric Cards */
    .metric-card-arch {
        background-color: #001f3f; border-radius: 15px; padding: 25px;
        text-align: center; border-bottom: 6px solid #FF6600;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-bottom: 20px;
    }
    .metric-label-arch { color: #FF6600; font-size: 1.1em; font-weight: bold; text-transform: uppercase; margin-bottom: 10px; }
    .metric-value-arch { color: #ffffff; font-size: 2.5em; font-weight: 900; font-family: 'Courier New', monospace; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA & SEARCH ENGINES ---

def boolean_search(df, query):
    if not query: return pd.Series([True] * len(df))
    def check_row(row_str):
        row_str = row_str.lower()
        or_parts = query.split(' OR ')
        or_results = []
        for part in or_parts:
            and_parts = part.split(' AND ')
            and_results = []
            for sub_part in and_parts:
                if sub_part.startswith('NOT '):
                    term = sub_part.replace('NOT ', '').strip().lower()
                    and_results.append(term not in row_str)
                else:
                    term = sub_part.strip().lower()
                    and_results.append(term in row_str)
            or_results.append(all(and_results))
        return any(or_results)
    combined_series = df.astype(str).apply(lambda x: ' '.join(x), axis=1)
    return combined_series.apply(check_row)

@st.cache_data
def load_and_preprocess_all():
    path = "2026 - 01- 23_ Data Structure for Patent Search and Analysis Engine - Type 5.csv"
    if not os.path.exists(path): return None, None, None, None
    
    # Load for Search Engine (Preserve Enriched/Raw Mapping)
    df_raw = pd.read_csv(path, header=0)
    category_row = df_raw.iloc[0] 
    col_map = {col: str(category_row[col]).strip() for col in df_raw.columns}
    df_search = df_raw.iloc[1:].reset_index(drop=True)
    
    # Load and Clean for Analysis Engine
    df = df_search.copy()
    df['AppDate'] = pd.to_datetime(df['Application Date'], errors='coerce')
    df['PriorityDate'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
    df = df.dropna(subset=['AppDate', 'PriorityDate'])
    
    df['Year'] = df['AppDate'].dt.year
    df['Month_Name'] = df['AppDate'].dt.month_name()
    df['Arrival_Month'] = df['AppDate'].dt.to_period('M').dt.to_timestamp()
    df['Priority_Month'] = df['PriorityDate'].dt.to_period('M').dt.to_timestamp()
    df['Firm'] = df['Data of Agent - Name in English'].fillna("DIRECT FILING").str.strip().str.upper()
    
    # IPC Explosion Engine
    df['IPC_Raw'] = df['Classification'].astype(str).str.split(',')
    df_exp = df.explode('IPC_Raw')
    df_exp['IPC_Clean'] = df_exp['IPC_Raw'].str.strip().str.upper()
    df_exp = df_exp[~df_exp['IPC_Clean'].str.contains("NO CLASSIFICATION|NAN|NONE", na=False)]
    df_exp['IPC_Class3'] = df_exp['IPC_Clean'].str[:3] 
    df_exp['IPC_Section'] = df_exp['IPC_Clean'].str[:1]
    
    return df_search, col_map, df, df_exp

df_search, col_map, df_main, df_exp = load_and_preprocess_all()

def get_logo():
    for ext in ["png", "jpg", "jpeg"]:
        if os.path.exists(f"logo.{ext}"): return f"logo.{ext}"
    return None

# --- 3. SECURITY GATE ---
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.write("<br><br>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1.2, 1])
    with col2:
        logo = get_logo()
        if logo: st.image(logo, use_container_width=True)
        st.markdown('<div style="background:#1E293B; padding:40px; border-radius:12px; border:1px solid #334155; text-align:center;">', unsafe_allow_html=True)
        st.markdown("<h3>KYRIX INTELLIGENCE LOGIN</h3>", unsafe_allow_html=True)
        key = st.text_input("SECURITY KEY", type="password")
        if st.button("AUTHORIZE SYSTEM"):
            if key in ["Kyrix2024", "LeoGiannotti2026!"]: 
                st.session_state.auth = True; st.rerun()
            else: st.error("INVALID CREDENTIALS")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # --- 4. NAVIGATION & SIDEBAR ---
    with st.sidebar:
        logo = get_logo()
        if logo: st.image(logo)
        st.markdown("## 🛡️ SYSTEM MODE")
        app_mode = st.radio("SELECT VIEW:", ["🔍 Intelligence Search", "📈 Strategic Analysis"])
        st.markdown("---")

        if app_mode == "🔍 Intelligence Search":
            st.markdown("### 🔍 GLOBAL COMMAND")
            global_query = st.text_input("GOOGLE PATENT STYLE SEARCH", placeholder="e.g. AI AND Hydrogen")
            st.markdown("### 🛠️ FILTERS")
            field_filters = {}
            field_filters['Title in English'] = st.text_input("Search in Title")
            field_filters['Abstract in English'] = st.text_input("Search in Abstract")
            other_fields = ['Application Number', 'Data of Applicant - Legal Name in English', 'Classification']
            for field in other_fields:
                field_filters[field] = st.text_input(f"{field.split(' - ')[-1]}")
            with st.expander("Show All Other Columns"):
                for col in df_search.columns:
                    if col not in other_fields and col not in ['Abstract in English', 'Title in English']:
                        val = st.text_input(col, key=f"ex_{col}")
                        if val: field_filters[col] = val
        else:
            st.markdown("### 🏛️ ARCHISTRATEGOS FILTERS")
            all_types = sorted(df_main['Application Type (ID)'].unique())
            selected_types = st.multiselect("Select Application Types:", all_types, default=all_types)
            df_f = df_main[df_main['Application Type (ID)'].isin(selected_types)]
            df_exp_f = df_exp[df_exp['Application Type (ID)'].isin(selected_types)]
            st.success(f"Records Analyzed: {len(df_f)}")

        if st.button("RESET SYSTEM"): st.rerun()

    # --- 5. MODE: SEARCH ENGINE ---
    if app_mode == "🔍 Intelligence Search":
        mask = boolean_search(df_search, global_query)
        for field, f_query in field_filters.items():
            if f_query: mask &= df_search[field].astype(str).str.contains(f_query, case=False, na=False)
        res = df_search[mask]
        
        st.markdown(f'<div class="metric-badge">● {len(res)} IDENTIFIED RECORDS</div>', unsafe_allow_html=True)
        tab_db, tab_dossier = st.tabs(["📋 DATABASE GRID", "🔍 PATENT DOSSIER VIEW"])
        
        with tab_db:
            st.dataframe(res, use_container_width=True, hide_index=True)
        
        with tab_dossier:
            if res.empty: st.info("No records.")
            else:
                choice = st.selectbox("SELECT PATENT FILE:", res['Application Number'].unique())
                row = res[res['Application Number'] == choice].iloc[0]
                
                # Header
                st.markdown(f"## {row['Title in English']} <span class='type-badge'>TYPE: {row.get('Application Type (ID)', 'N/A')}</span>", unsafe_allow_html=True)
                
                # Enriched
                st.markdown('<div class="section-header enriched-banner">Enriched Intelligence Metrics</div>', unsafe_allow_html=True)
                e_cols = [c for c, t in col_map.items() if t == "Enriched"]
                ec = st.columns(3)
                for i, c in enumerate(e_cols):
                    with ec[i%3]: st.markdown(f"<div class='data-card' style='border-left:4px solid #3B82F6;'><div class='label-text'>{c}</div><div class='value-text'>{row[c]}</div></div>", unsafe_allow_html=True)
                
                # Raw
                st.markdown('<div class="section-header raw-banner">Raw Source Data</div>', unsafe_allow_html=True)
                r_cols = [c for c, t in col_map.items() if t == "Raw" and c not in ["Abstract in English", "Title in English", "Application Type (ID)"]]
                rc = st.columns(3)
                for i, c in enumerate(r_cols):
                    with rc[i%3]: st.markdown(f"<div class='data-card'><div class='label-text'>{c}</div><div class='value-text'>{row[c]}</div></div>", unsafe_allow_html=True)
                
                st.markdown('<div class="section-header title-banner">Technical Abstract</div>', unsafe_allow_html=True)
                st.markdown(f"<div class='abstract-container'>{row['Abstract in English']}</div>", unsafe_allow_html=True)

    # --- 6. MODE: ANALYSIS ENGINE (ARCHISTRATEGOS 9.0 FULL) ---
    else:
        st.markdown('<div class="metric-badge">🏛️ ARCHISTRATEGOS 9.0 ANALYTICS</div>', unsafe_allow_html=True)
        tabs = st.tabs(["📈 App Type Growth", "🏢 Firm Intelligence", "🔬 Firm Tech-Strengths", "🎯 STRATEGIC MAP", "📊 IPC Classification", "📉 Dynamic Moving Averages", "📅 Monthly Filing"])

        # 1. Growth
        with tabs[0]:
            st.header("Application Type Time-Series")
            growth = df_f.groupby(['Year', 'Application Type (ID)']).size().reset_index(name='Count')
            st.plotly_chart(px.line(growth, x='Year', y='Count', color='Application Type (ID)', markers=True, height=600, template="plotly_dark"), use_container_width=True)
            st.subheader("📊 Growth Summary Table")
            growth_pivot = growth.pivot(index='Year', columns='Application Type (ID)', values='Count').fillna(0).astype(int)
            st.dataframe(growth_pivot, use_container_width=True)

        # 2. Firm Intelligence
        with tabs[1]:
            st.header("🏢 Agent / Firm Intelligence")
            top_firms = df_f['Firm'].value_counts().nlargest(10).index.tolist()
            selected_firms = st.multiselect("Select Firms to Compare:", sorted(df_f['Firm'].unique()), default=top_firms[:5])
            if selected_firms:
                firm_growth = df_f[df_f['Firm'].isin(selected_firms)].groupby(['Year', 'Firm']).size().reset_index(name='Apps')
                st.plotly_chart(px.line(firm_growth, x='Year', y='Apps', color='Firm', markers=True, height=600, template="plotly_dark"), use_container_width=True)
                st.subheader("📊 Firm Volume Summary")
                firm_summary = df_f[df_f['Firm'].isin(selected_firms)].groupby(['Firm', 'Year']).size().unstack(fill_value=0)
                st.dataframe(firm_summary, use_container_width=True)

        # 3. Firm Tech-Strengths
        with tabs[2]:
            st.header("🔬 Technology Strengths by Firm")
            if selected_firms:
                firm_ipc = df_exp_f[df_exp_f['Firm'].isin(selected_firms)].groupby(['Firm', 'IPC_Class3']).size().reset_index(name='Count')
                st.plotly_chart(px.bar(firm_ipc, x='Count', y='Firm', color='IPC_Class3', orientation='h', height=600, template="plotly_dark"), use_container_width=True)
                st.subheader("📊 Tech-Class Distribution per Firm")
                tech_pivot = firm_ipc.pivot(index='Firm', columns='IPC_Class3', values='Count').fillna(0).astype(int)
                st.dataframe(tech_pivot, use_container_width=True)

        # 4. Strategic Map
        with tabs[3]:
            st.header("🎯 Strategic Innovation & Competitor Map")
            land_data = df_exp_f.groupby(['IPC_Section', 'IPC_Class3']).agg({'Application Number':'count', 'Firm':'nunique'}).reset_index()
            st.plotly_chart(px.scatter(land_data, x='IPC_Section', y='IPC_Class3', size='Application Number', color='Firm', height=600, template="plotly_dark"), use_container_width=True)
            st.subheader("📊 IPC Class Strategic Density")
            st.dataframe(land_data.rename(columns={'Application Number': 'Total Apps', 'Firm': 'Unique Agents'}).sort_values('Total Apps', ascending=False), use_container_width=True, hide_index=True)

        # 5. IPC Classification
        with tabs[4]:
            st.header("IPC Section Distribution (A-H)")
            ipc_counts = df_exp_f.groupby('IPC_Section').size().reset_index(name='Count').sort_values('IPC_Section')
            st.plotly_chart(px.bar(ipc_counts, x='IPC_Section', y='Count', color='IPC_Section', text='Count', height=600, template="plotly_dark"), use_container_width=True)

        # 6. Dynamic Moving Averages (TRUNCATED 3-CHAR) - NO SIMPLIFICATION
        with tabs[5]:
            st.header("📉 Dynamic Growth Analysis (Class-3)")
            unique_3char = sorted(df_exp_f['IPC_Class3'].unique())
            target_ipc = st.selectbox("Search/Select IPC Class (3-Digit Prefix):", ["ALL IPC"] + unique_3char)
            smooth_val = st.slider("Smoothing Window (Months):", 1, 36, 12)

            if target_ipc == "ALL IPC":
                analysis_df = df_exp_f.copy()
                work_df = df_f.copy()
            else:
                analysis_df = df_exp_f[df_exp_f['IPC_Class3'] == target_ipc]
                work_df = df_f[df_f['Application Number'].isin(analysis_df['Application Number'].unique())]

            full_range = pd.date_range(start='2010-01-01', end=df_f['AppDate'].max(), freq='MS')
            type_counts = analysis_df.groupby(['Priority_Month', 'Application Type (ID)']).size().reset_index(name='N')
            type_pivot = type_counts.pivot(index='Priority_Month', columns='Application Type (ID)', values='N').fillna(0)
            type_ma = type_pivot.reindex(full_range, fill_value=0).rolling(window=smooth_val, min_periods=1).mean()
            arr_ma = work_df.groupby('Arrival_Month').size().reset_index(name='N').set_index('Arrival_Month').reindex(full_range, fill_value=0).rolling(window=smooth_val, min_periods=1).mean()
            
            # Metrics
            m1, m2, m3 = st.columns(3)
            with m1: st.markdown(f'<div class="metric-card-arch"><div class="metric-label-arch">Peak MA</div><div class="metric-value-arch">{type_ma.sum(axis=1).max():.2f}</div></div>', unsafe_allow_html=True)
            with m2: st.markdown(f'<div class="metric-card-arch"><div class="metric-label-arch">Volume</div><div class="metric-value-arch">{len(work_df)}</div></div>', unsafe_allow_html=True)
            with m3: st.markdown(f'<div class="metric-card-arch"><div class="metric-label-arch">Smoothing</div><div class="metric-value-arch">{smooth_val}M</div></div>', unsafe_allow_html=True)

            fig = go.Figure()
            for col_name in type_ma.columns:
                fig.add_trace(go.Scatter(x=type_ma.index, y=type_ma[col_name], mode='lines', name=f'Type: {col_name}', stackgroup='one', fill='tonexty'))
            fig.add_trace(go.Scatter(x=arr_ma.index, y=arr_ma['N'], mode='lines', name='Arrival Workload', line=dict(color='#FF6600', width=3)))
            st.plotly_chart(fig, use_container_width=True)
            st.subheader("📊 Dynamic Momentum Table (Monthly MA)")
            st.dataframe(type_ma.tail(24).sort_index(ascending=False), use_container_width=True)

        # 7. Monthly Filing
        with tabs[6]:
            st.header("📅 Monthly Filing Analysis")
            sel_year = st.selectbox("Choose Year:", sorted(df_f['Year'].unique(), reverse=True))
            yr_data = df_f[df_f['Year'] == sel_year]
            m_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            counts = yr_data.groupby('Month_Name').size().reindex(m_order, fill_value=0).reset_index(name='Apps')
            st.plotly_chart(px.bar(counts, x='Month_Name', y='Apps', text='Apps', height=600, template="plotly_dark"), use_container_width=True)
