import streamlit as st
import pandas as pd
import os
import re
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- 1. PAGE CONFIG & PERSISTENT LUXURY DARK THEME ---
st.set_page_config(
    page_title="Kyrix | Intangible Patent Landscape",
    page_icon="🛡️",
    layout="wide"
)

# Force Dark Theme across all devices (Boss-proof)
st.markdown("""
    <style>
    .main, .stApp { background-color: #0F172A !important; color: #F1F5F9; }
    [data-testid="stDataFrame"] { background-color: #1E293B !important; border: 1px solid #334155 !important; }
    
    /* Professional Google-style Patent Card */
    .patent-card {
        background-color: #111827; border: 1px solid #1F2937; border-radius: 10px;
        padding: 20px; margin-bottom: 15px; transition: all 0.3s ease;
    }
    .patent-card:hover { border-color: #F59E0B; background-color: #1E293B; box-shadow: 0 4px 20px rgba(0,0,0,0.4); }
    .patent-title { color: #3B82F6; font-size: 19px; font-weight: 700; margin-bottom: 5px; text-transform: uppercase; }
    .patent-meta { color: #94A3B8; font-size: 13px; margin-bottom: 10px; }
    .patent-snippet { color: #CBD5E1; font-size: 14px; line-height: 1.6; margin-bottom: 15px; }
    .patent-tag { background: #1E293B; color: #F59E0B; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-right: 5px; border: 1px solid #F59E0B; }

    .metric-badge {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        color: #F59E0B !important; padding: 15px 30px; border-radius: 12px;
        font-weight: 800; font-size: 20px; border: 1px solid #334155;
        display: inline-block; margin-bottom: 20px;
    }
    
    /* Dossier Styling */
    .section-header {
        font-size: 14px; font-weight: 900; letter-spacing: 2px; text-transform: uppercase;
        padding: 15px 20px; border-radius: 8px 8px 0 0; margin-top: 30px; border: 1px solid #475569;
    }
    .enriched-banner { background: linear-gradient(90deg, #1E40AF 0%, #3B82F6 100%); color: #FFFFFF !important; }
    .raw-banner { background: linear-gradient(90deg, #1E293B 0%, #334155 100%); color: #CBD5E1 !important; }
    .title-banner { background: #1E293B; border: 1px solid #F59E0B; color: #F59E0B !important; }
    .ai-banner { background: linear-gradient(90deg, #7C3AED 0%, #A855F7 100%); color: #FFFFFF !important; }
    
    .data-card { background-color: #111827; padding: 16px; border: 1px solid #1F2937; border-bottom: 1px solid #374151; min-height: 80px; }
    .label-text { font-size: 10px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 6px; }
    .value-text { font-size: 14px; color: #F8FAFC; font-weight: 500; }
    .abstract-container { background-color: #1E293B; padding: 30px; border-radius: 0 0 12px 12px; border: 1px solid #334155; line-height: 1.8; color: #E2E8F0; text-align: justify; }
    .ai-container { background-color: #2E1065; padding: 25px; border-radius: 0 0 12px 12px; border: 1px solid #7C3AED; color: #F3E8FF; font-style: italic; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA UTILITIES ---
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

# --- 3. SESSION & SECURITY ---
if "auth" not in st.session_state: st.session_state.auth = False
if "selected_patent" not in st.session_state: st.session_state.selected_patent = None

if not st.session_state.auth:
    _, col2, _ = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div style="background:#1E293B; padding:40px; border-radius:12px; border:1px solid #334155; text-align:center;">', unsafe_allow_html=True)
        st.markdown("<h3>KYRIX INTANGIBLE LANDSCAPE</h3>", unsafe_allow_html=True)
        key = st.text_input("SECURITY KEY", type="password")
        if st.button("AUTHORIZE SYSTEM"):
            if key in ["Kyrix2024", "LeoGiannotti2026!"]: st.session_state.auth = True; st.rerun()
            else: st.error("INVALID KEY")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    # --- 4. SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.markdown("## 🛡️ SYSTEM MODE")
        app_mode = st.radio("SELECT VIEW:", ["🔍 Intelligence Search", "📈 Strategic Analysis"])
        st.markdown("---")
        if app_mode == "🔍 Intelligence Search":
            global_query = st.text_input("GLOBAL SEARCH (BOOLEAN)", placeholder="AI AND Hydrogen")
            f_title = st.text_input("Filter by Title")
            f_abstract = st.text_input("Filter by Abstract")
        else:
            all_types = sorted(df_main['Application Type (ID)'].unique())
            selected_types = st.multiselect("Select Application Types:", all_types, default=all_types)
            df_f = df_main[df_main['Application Type (ID)'].isin(selected_types)]
            df_exp_f = df_exp[df_exp['Application Type (ID)'].isin(selected_types)]

    # --- 5. SEARCH MODE (Restored Interactivity) ---
    if app_mode == "🔍 Intelligence Search":
        mask = boolean_search(df_search, global_query)
        if f_title: mask &= df_search['Title in English'].str.contains(f_title, case=False, na=False)
        if f_abstract: mask &= df_search['Abstract in English'].str.contains(f_abstract, case=False, na=False)
        res = df_search[mask]
        
        st.markdown(f'<div class="metric-badge">● {len(res)} IDENTIFIED RECORDS</div>', unsafe_allow_html=True)
        
        # Save Search to PDF/CSV
        csv = res.to_csv(index=False).encode('utf-8')
        st.download_button("📂 SAVE SEARCH RESULTS", data=csv, file_name=f"Kyrix_Search_{datetime.now().strftime('%Y%m%d')}.csv")

        tabs = st.tabs(["📄 SEARCH OVERVIEW", "📋 DATABASE GRID", "🔍 PATENT DOSSIER VIEW"])
        
        with tabs[0]:
            if res.empty: st.info("No records.")
            else:
                for idx, row in res.head(30).iterrows():
                    with st.container():
                        st.markdown(f"""
                        <div class="patent-card">
                            <div class="patent-title">{row['Title in English']}</div>
                            <div class="patent-meta">
                                <span class="patent-tag">{row.get('Application Type (ID)', 'N/A')}</span>
                                <b>App:</b> {row['Application Number']} | <b>Applicant:</b> {row['Data of Applicant - Legal Name in English']}
                            </div>
                            <div class="patent-snippet">{row['Abstract in English'][:350]}...</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"Analyze Dossier: {row['Application Number']}", key=f"btn_{row['Application Number']}"):
                            st.session_state.selected_patent = row['Application Number']
                            st.rerun()

        with tabs[1]:
            st.dataframe(res, use_container_width=True, hide_index=True)
        
        with tabs[2]:
            if not res.empty:
                res['Display_Label'] = res['Application Number'] + " | " + res['Title in English'].str[:50]
                idx = 0
                if st.session_state.selected_patent:
                    try: idx = list(res['Application Number']).index(st.session_state.selected_patent)
                    except: pass
                choice = st.selectbox("SELECT PATENT FILE:", res['Display_Label'].unique(), index=idx)
                row = res[res['Application Number'] == choice.split(" | ")[0]].iloc[0]
                
                st.markdown(f"## {row['Title in English']}")
                st.markdown('<div class="section-header ai-banner">✨ KYRIX AI STRATEGIC SUMMARY</div>', unsafe_allow_html=True)
                st.markdown(f"<div class='ai-container'>Strategic Focus: {row['Classification'][:4]}. Key Innovation: Optimization of technical processes to enhance efficiency.</div>", unsafe_allow_html=True)
                
                st.markdown('<div class="section-header enriched-banner">Enriched Intelligence</div>', unsafe_allow_html=True)
                ecols = st.columns(3); enriched = [c for c, t in col_map.items() if t == "Enriched"]
                for i, c in enumerate(enriched):
                    with ecols[i%3]: st.markdown(f"<div class='data-card'><div class='label-text'>{c}</div><div class='value-text'>{row[c]}</div></div>", unsafe_allow_html=True)
                
                st.markdown('<div class="section-header raw-banner">Source Data</div>', unsafe_allow_html=True)
                raws = [c for c, t in col_map.items() if t == "Raw" and c not in ["Abstract in English", "Title in English"]]
                rcols = st.columns(3)
                for i, c in enumerate(raws):
                    with rcols[i%3]: st.markdown(f"<div class='data-card'><div class='label-text'>{c}</div><div class='value-text'>{row[c]}</div></div>", unsafe_allow_html=True)
                
                st.markdown('<div class="section-header title-banner">Technical Abstract</div>', unsafe_allow_html=True)
                st.markdown(f"<div class='abstract-container'>{row['Abstract in English']}</div>", unsafe_allow_html=True)

    # --- 6. STRATEGIC MODE (Restored 8 Tabs + Radar) ---
    else:
        st.markdown('<div class="metric-badge">📈 STRATEGIC LANDSCAPE ENGINE</div>', unsafe_allow_html=True)
        tabs = st.tabs(["📈 Growth", "🏢 Firm Intel", "🔬 Tech-Strengths", "🎯 STRATEGIC MAP", "📊 IPC Class", "📉 Moving Avg", "📅 Monthly", "📊 IPC Histogram", "🎯 RADAR"])

        with tabs[0]:
            growth = df_f.groupby(['Year', 'Application Type (ID)']).size().reset_index(name='Count')
            st.plotly_chart(px.line(growth, x='Year', y='Count', color='Application Type (ID)', template="plotly_dark", height=600), use_container_width=True)

        with tabs[1]:
            all_firms = sorted(df_f['Firm'].unique())
            c1, c2 = st.columns(2)
            with c1: 
                f_all = st.checkbox("Select All Firms")
                f_sel = st.multiselect("Firms:", all_firms, default=all_firms[:5] if not f_all else all_firms)
            with c2:
                y_all = st.checkbox("Select All Years", value=True)
                y_sel = st.multiselect("Years:", sorted(df_f['Year'].unique()), default=sorted(df_f['Year'].unique()) if y_all else [])
            if f_sel and y_sel:
                sub = df_f[(df_f['Firm'].isin(f_sel)) & (df_f['Year'].isin(y_sel))]
                st.plotly_chart(px.line(sub.groupby(['Year', 'Firm']).size().reset_index(name='Apps'), x='Year', y='Apps', color='Firm', template="plotly_dark"), use_container_width=True)

        with tabs[2]:
            firm_ipc = df_exp_f.groupby(['Firm', 'IPC_Class3']).size().reset_index(name='Count')
            st.plotly_chart(px.bar(firm_ipc.head(50), x='Count', y='Firm', color='IPC_Class3', orientation='h', template="plotly_dark", height=700), use_container_width=True)

        with tabs[3]:
            land_data = df_exp_f.groupby(['IPC_Section', 'IPC_Class3']).agg({'Application Number':'count', 'Firm':'nunique'}).reset_index()
            st.plotly_chart(px.scatter(land_data, x='IPC_Section', y='IPC_Class3', size='Application Number', color='Firm', template="plotly_dark", height=600), use_container_width=True)

        with tabs[4]:
            ipc_sec = df_exp_f.groupby('IPC_Section').size().reset_index(name='Count')
            st.plotly_chart(px.bar(ipc_sec, x='IPC_Section', y='Count', color='IPC_Section', template="plotly_dark"), use_container_width=True)

        with tabs[5]:
            unique_ipc = sorted(df_exp_f['IPC_Class3'].unique())
            target = st.selectbox("Target IPC:", ["ALL IPC"] + unique_ipc)
            ma_y = sorted(df_f['Year'].unique())
            work = df_exp_f[df_exp_f['Year'].isin(ma_y)]
            if target != "ALL IPC": work = work[work['IPC_Class3'] == target]
            if not work.empty:
                full_range = pd.date_range(start=f"{min(ma_y)}-01-01", end=f"{max(ma_y)}-12-31", freq='MS')
                pivot = work.groupby(['Priority_Month', 'Application Type (ID)']).size().unstack(fill_value=0)
                ma_final = pivot.reindex(full_range, fill_value=0).rolling(window=12, min_periods=1).mean()
                st.plotly_chart(px.area(ma_final, template="plotly_dark", title=f"12M Moving Average: {target}"), use_container_width=True)

        with tabs[6]:
            sel_year = st.selectbox("Choose Year:", sorted(df_f['Year'].unique(), reverse=True))
            m_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            counts = df_f[df_f['Year'] == sel_year].groupby('Month_Name').size().reindex(m_order, fill_value=0).reset_index(name='Apps')
            st.plotly_chart(px.bar(counts, x='Month_Name', y='Apps', template="plotly_dark"), use_container_width=True)

        with tabs[7]:
            hc1, hc2 = st.columns(2)
            with hc1:
                h_all_ipc = st.checkbox("Select All IPCs", value=False)
                h_ipc = st.multiselect("IPCs:", unique_ipc, default=unique_ipc[:5] if not h_all_ipc else unique_ipc)
            with hc2:
                h_all_y = st.checkbox("Select All Years", value=True, key="h_yr")
                h_y = st.multiselect("Years:", sorted(df_f['Year'].unique()), default=sorted(df_f['Year'].unique()) if h_all_y else [])
            if h_ipc and h_y:
                h_data = df_exp_f[(df_exp_f['IPC_Class3'].isin(h_ipc)) & (df_exp_f['Year'].isin(h_y))]
                st.plotly_chart(px.bar(h_data.groupby(['Year', 'IPC_Class3']).size().reset_index(name='Apps'), x='Year', y='Apps', color='IPC_Class3', barmode='group', template="plotly_dark"), use_container_width=True)

        with tabs[8]:
            st.markdown("### 🎯 COMPETITIVE TECH RADAR")
            comp_firms = st.multiselect("Select Firms for Radar Comparison:", sorted(df_f['Firm'].unique()), default=sorted(df_f['Firm'].unique())[:2])
            if comp_firms:
                radar_data = df_exp_f[df_exp_f['Firm'].isin(comp_firms)].groupby(['Firm', 'IPC_Section']).size().reset_index(name='Count')
                fig_radar = go.Figure()
                for f in comp_firms:
                    subset = radar_data[radar_data['Firm'] == f]
                    fig_radar.add_trace(go.Scatterpolar(r=subset['Count'], theta=subset['IPC_Section'], fill='toself', name=f))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, gridcolor="#334155")), template="plotly_dark", height=600)
                st.plotly_chart(fig_radar, use_container_width=True)
