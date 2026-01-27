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

# FORCE DARK THEME & PROFESSIONAL UI
st.markdown("""
    <style>
    /* Global Background and Text */
    .main, .stApp { background-color: #0F172A !important; color: #F1F5F9; }
    
    /* Force Dataframe into Dark Mode */
    [data-testid="stDataFrame"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 8px;
    }

    /* Professional Google-style Patent Card */
    .patent-card {
        background-color: #111827;
        border: 1px solid #1F2937;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 5px;
        border-bottom: none;
        border-bottom-left-radius: 0;
        border-bottom-right-radius: 0;
    }
    .patent-title { color: #3B82F6; font-size: 18px; font-weight: 700; text-decoration: none; margin-bottom: 5px; display: block; }
    .patent-meta { color: #94A3B8; font-size: 13px; margin-bottom: 10px; }
    .patent-snippet { color: #CBD5E1; font-size: 14px; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
    .patent-tag { background: #1E293B; color: #F59E0B; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-right: 5px; }

    /* Custom Metric Badges */
    .metric-badge {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        color: #F59E0B !important;
        padding: 15px 30px;
        border-radius: 12px;
        font-weight: 800; font-size: 20px;
        border: 1px solid #334155;
        display: inline-block; margin-bottom: 20px;
    }
    
    /* Form and Sidebar */
    [data-testid="stSidebar"] { background-color: #020617 !important; border-right: 1px solid #1E293B; }
    .stTextInput>div>div>input { background-color: #1E293B !important; color: white !important; border: 1px solid #334155 !important; }
    
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
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PROCESSING ---

@st.cache_data
def load_and_preprocess_all():
    path = "2026 - 01- 23_ Data Structure for Patent Search and Analysis Engine - Type 5.csv"
    if not os.path.exists(path): return None, None, None, None
    
    df_raw = pd.read_csv(path, header=0)
    category_row = df_raw.iloc[0] 
    col_map = {col: str(category_row[col]).strip() for col in df_raw.columns}
    
    df_search = df_raw.iloc[1:].reset_index(drop=True).fillna("-")
    
    df = df_search.copy()
    df['AppDate'] = pd.to_datetime(df['Application Date'], errors='coerce')
    df['PriorityDate'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
    df = df.dropna(subset=['AppDate', 'PriorityDate'])
    
    df['Year'] = df['AppDate'].dt.year
    df['Month_Name'] = df['AppDate'].dt.month_name()
    df['Arrival_Month'] = df['AppDate'].dt.to_period('M').dt.to_timestamp()
    df['Priority_Month'] = df['PriorityDate'].dt.to_period('M').dt.to_timestamp()
    df['Firm'] = df['Data of Agent - Name in English'].replace("-", "DIRECT FILING").str.strip().str.upper()
    
    df['IPC_Raw'] = df['Classification'].astype(str).str.split(',')
    df_exp = df.explode('IPC_Raw')
    df_exp['IPC_Clean'] = df_exp['IPC_Raw'].str.strip().str.upper()
    df_exp = df_exp[~df_exp['IPC_Clean'].str.contains("NO CLASSIFICATION|NAN|NONE|-", na=False)]
    df_exp['IPC_Class3'] = df_exp['IPC_Clean'].str[:3] 
    df_exp['IPC_Section'] = df_exp['IPC_Clean'].str[:1]
    
    return df_search, col_map, df, df_exp

df_search, col_map, df_main, df_exp = load_and_preprocess_all()

# --- INITIALIZE STATE ---
if "auth" not in st.session_state: st.session_state.auth = False
if "selected_patent_id" not in st.session_state: st.session_state.selected_patent_id = None

def get_logo():
    for ext in ["png", "jpg", "jpeg"]:
        if os.path.exists(f"logo.{ext}"): return f"logo.{ext}"
    return None

# --- 3. SECURITY GATE ---
if not st.session_state.auth:
    st.write("<br><br>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1.2, 1])
    with col2:
        logo = get_logo()
        if logo: st.image(logo, use_container_width=True)
        st.markdown('<div style="background:#1E293B; padding:40px; border-radius:12px; border:1px solid #334155; text-align:center;">', unsafe_allow_html=True)
        st.markdown("<h3>KYRIX INTANGIBLE LANDSCAPE</h3>", unsafe_allow_html=True)
        key = st.text_input("SECURITY KEY", type="password")
        if st.button("AUTHORIZE SYSTEM"):
            if key in ["Kyrix2024", "LeoGiannotti2026!"]: 
                st.session_state.auth = True; st.rerun()
            else: st.error("INVALID KEY")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    # --- 4. SIDEBAR NAVIGATION ---
    with st.sidebar:
        logo = get_logo()
        if logo: st.image(logo)
        st.markdown("## 🛡️ SYSTEM MODE")
        app_mode = st.radio("SELECT VIEW:", ["🔍 Intelligence Search", "📈 Strategic Analysis"])
        st.markdown("---")

        if app_mode == "🔍 Intelligence Search":
            st.markdown("### 🔍 GLOBAL COMMAND")
            global_query = st.text_input("GOOGLE PATENT STYLE SEARCH", placeholder="e.g. AI AND Hydrogen")
            
            st.markdown("### 🛠️ MULTI-FIELD SEARCH")
            field_filters = {}
            field_filters['Title in English'] = st.text_input("Search in Title")
            field_filters['Abstract in English'] = st.text_input("Search in Abstract")
            
            with st.expander("Show All Searchable Columns"):
                for col in df_search.columns:
                    if col not in ['Abstract in English', 'Title in English']:
                        val = st.text_input(col, key=f"src_{col}")
                        if val: field_filters[col] = val
        else:
            st.markdown("### 📊 ANALYTICS FILTERS")
            all_types = sorted(df_main['Application Type (ID)'].unique())
            selected_types = st.multiselect("Select Application Types:", all_types, default=all_types)
            df_f = df_main[df_main['Application Type (ID)'].isin(selected_types)]
            df_exp_f = df_exp[df_exp['Application Type (ID)'].isin(selected_types)]
            st.success(f"Records Analyzed: {len(df_f)}")

        if st.button("RESET SYSTEM"): 
            st.session_state.selected_patent_id = None
            st.rerun()

    # --- 5. SEARCH ENGINE ---
    if app_mode == "🔍 Intelligence Search":
        # Search Engine Core
        def run_search(df, g_query, f_filters):
            mask = pd.Series([True] * len(df))
            if g_query:
                combined = df.astype(str).apply(lambda x: ' '.join(x), axis=1).str.lower()
                terms = g_query.lower().split(' AND ')
                for t in terms: mask &= combined.str.contains(t.strip(), na=False)
            
            for field, val in f_filters.items():
                if val: mask &= df[field].astype(str).str.contains(val, case=False, na=False)
            return df[mask]

        res = run_search(df_search, global_query, field_filters)
        st.markdown(f'<div class="metric-badge">● {len(res)} IDENTIFIED RECORDS</div>', unsafe_allow_html=True)
        
        tab_list, tab_grid, tab_dossier = st.tabs(["📄 SEARCH OVERVIEW", "📋 DATABASE GRID", "🔍 PATENT DOSSIER VIEW"])
        
        with tab_list:
            if res.empty: st.info("No records found.")
            else:
                for idx, row in res.head(50).iterrows():
                    st.markdown(f"""
                    <div class="patent-card">
                        <div class="patent-title">{row['Title in English']}</div>
                        <div class="patent-meta">
                            <span class="patent-tag">{row.get('Application Type (ID)', 'N/A')}</span>
                            <b>App No:</b> {row['Application Number']} | <b>Date:</b> {row['Application Date']}
                        </div>
                    </div>""", unsafe_allow_html=True)
                    # The "Clickable" Mechanism
                    if st.button(f"DRILL DOWN: {row['Application Number']}", key=f"drill_{row['Application Number']}", use_container_width=True):
                        st.session_state.selected_patent_id = row['Application Number']
                        st.rerun()
                    st.markdown(f"<div class='patent-snippet' style='margin-bottom:20px;'>{row['Abstract in English']}</div>", unsafe_allow_html=True)

        with tab_grid:
            st.dataframe(res, use_container_width=True)
        
        with tab_dossier:
            if res.empty: st.warning("Please search for a patent first.")
            else:
                res['Display_Label'] = res['Application Number'] + " | " + res['Title in English'].str[:50]
                # Persist selection from Overview
                current_list = res['Application Number'].tolist()
                default_idx = 0
                if st.session_state.selected_patent_id in current_list:
                    default_idx = current_list.index(st.session_state.selected_patent_id)
                
                choice = st.selectbox("ACTIVE DOSSIER:", res['Display_Label'], index=default_idx)
                sel_no = choice.split(" | ")[0]
                row = res[res['Application Number'] == sel_no].iloc[0]

                st.markdown(f"## {row['Title in English']} <span class='type-badge'>{row.get('Application Type (ID)', '-')}</span>", unsafe_allow_html=True)
                
                st.markdown('<div class="section-header enriched-banner">Enriched Intelligence Metrics</div>', unsafe_allow_html=True)
                e_cols = [c for c, t in col_map.items() if t == "Enriched"]
                ec = st.columns(3)
                for i, c in enumerate(e_cols):
                    with ec[i%3]: st.markdown(f"<div class='data-card' style='border-left:4px solid #3B82F6;'><div class='label-text'>{c}</div><div class='value-text'>{row[c]}</div></div>", unsafe_allow_html=True)
                
                st.markdown('<div class="section-header raw-banner">Raw Source Data</div>', unsafe_allow_html=True)
                r_cols = [c for c, t in col_map.items() if t == "Raw" and c not in ["Abstract in English", "Title in English"]]
                rc = st.columns(3)
                for i, c in enumerate(r_cols):
                    with rc[i%3]: st.markdown(f"<div class='data-card'><div class='label-text'>{c}</div><div class='value-text'>{row[c]}</div></div>", unsafe_allow_html=True)
                
                st.markdown('<div class="section-header title-banner">Technical Abstract</div>', unsafe_allow_html=True)
                st.markdown(f"<div class='abstract-container'>{row['Abstract in English']}</div>", unsafe_allow_html=True)

    # --- 6. STRATEGIC ANALYSIS ENGINE (ALL TABS) ---
    else:
        st.markdown('<div class="metric-badge">📈 STRATEGIC LANDSCAPE ENGINE</div>', unsafe_allow_html=True)
        t0, t1, t2, t3, t4, t5, t6, t7 = st.tabs([
            "📈 App Type Growth", "🏢 Firm Intelligence", "🔬 Tech-Strengths", 
            "🎯 STRATEGIC MAP", "📊 IPC Classification", "📉 Moving Averages", 
            "📅 Monthly Filing", "📊 IPC Growth Histogram"
        ])

        with t0:
            growth = df_f.groupby(['Year', 'Application Type (ID)']).size().reset_index(name='Count')
            fig = px.line(growth, x='Year', y='Count', color='Application Type (ID)', markers=True, height=600, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(growth.pivot(index='Year', columns='Application Type (ID)', values='Count').fillna(0).astype(int), use_container_width=True)

        with t1:
            top_firms = df_f['Firm'].value_counts().nlargest(10).index.tolist()
            sel_firms = st.multiselect("Compare Firms:", sorted(df_f['Firm'].unique()), default=top_firms[:5])
            if sel_firms:
                f_data = df_f[df_f['Firm'].isin(sel_firms)].groupby(['Year', 'Firm']).size().reset_index(name='Apps')
                st.plotly_chart(px.line(f_data, x='Year', y='Apps', color='Firm', markers=True, template="plotly_dark"), use_container_width=True)

        with t2:
            if 'sel_firms' in locals() and sel_firms:
                firm_ipc = df_exp_f[df_exp_f['Firm'].isin(sel_firms)].groupby(['Firm', 'IPC_Class3']).size().reset_index(name='Count')
                st.plotly_chart(px.bar(firm_ipc, x='Count', y='Firm', color='IPC_Class3', orientation='h', height=600, template="plotly_dark"), use_container_width=True)

        with t3:
            land_data = df_exp_f.groupby(['IPC_Section', 'IPC_Class3']).agg({'Application Number':'count', 'Firm':'nunique'}).reset_index()
            st.plotly_chart(px.scatter(land_data, x='IPC_Section', y='IPC_Class3', size='Application Number', color='Firm', height=600, template="plotly_dark"), use_container_width=True)

        with t4:
            ipc_counts = df_exp_f.groupby('IPC_Section').size().reset_index(name='Count').sort_values('Count', ascending=False)
            st.plotly_chart(px.bar(ipc_counts, x='IPC_Section', y='Count', color='IPC_Section', template="plotly_dark"), use_container_width=True)

        with t5:
            target_ipc = st.selectbox("Trend Analysis for IPC Class:", ["ALL IPC"] + sorted(df_exp_f['IPC_Class3'].unique()))
            ma_df = df_exp_f if target_ipc == "ALL IPC" else df_exp_f[df_exp_f['IPC_Class3'] == target_ipc]
            ma_data = ma_df.groupby('Priority_Month').size().rolling(window=12).mean().reset_index(name='MA12')
            st.plotly_chart(px.line(ma_data, x='Priority_Month', y='MA12', title=f"12-Month Moving Average: {target_ipc}", template="plotly_dark"), use_container_width=True)

        with t6:
            sel_yr = st.selectbox("Select Year for Seasonality:", sorted(df_f['Year'].unique(), reverse=True))
            m_data = df_f[df_f['Year'] == sel_yr].groupby('Month_Name').size().reindex([
                "January", "February", "March", "April", "May", "June", 
                "July", "August", "September", "October", "November", "December"
            ], fill_value=0).reset_index(name='Apps')
            st.plotly_chart(px.bar(m_data, x='Month_Name', y='Apps', template="plotly_dark"), use_container_width=True)

        with t7:
            # ADDED ALL IPC OPTION
            ipc_options = ["ALL IPC"] + sorted(df_exp_f['IPC_Class3'].unique())
            sel_ipc_hist = st.multiselect("Compare IPC Growth:", ipc_options, default=["ALL IPC"])
            if sel_ipc_hist:
                h_df = df_exp_f if "ALL IPC" in sel_ipc_hist else df_exp_f[df_exp_f['IPC_Class3'].isin(sel_ipc_hist)]
                h_data = h_df.groupby(['Year', 'IPC_Class3']).size().reset_index(name='Apps')
                st.plotly_chart(px.bar(h_data, x='Year', y='Apps', color='IPC_Class3', barmode='group', template="plotly_dark"), use_container_width=True)
