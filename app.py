import streamlit as st
import pandas as pd
import os
import re
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import hmac
from datetime import datetime
import base64

# --- 1. PAGE CONFIG & KYRIX LUXURY THEME ---
st.set_page_config(
    page_title="Kyrix | Intangible Patent Landscape",
    page_icon="🛡️",
    layout="wide"
)

# FORCE DARK THEME & PROFESSIONAL UI
st.markdown("""
    <style>
    .main, .stApp { background-color: #0F172A !important; color: #F1F5F9; }
    
    [data-testid="stDataFrame"] {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 8px;
    }

    .patent-card {
        background-color: #111827;
        border: 1px solid #1F2937;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        transition: all 0.3s ease;
    }
    .patent-card:hover {
        border-color: #F59E0B;
        background-color: #1E293B;
    }
    .patent-title { color: #3B82F6; font-size: 19px; font-weight: 700; margin-bottom: 5px; }
    .patent-meta { color: #94A3B8; font-size: 13px; margin-bottom: 10px; }
    .patent-snippet { color: #CBD5E1; font-size: 14px; line-height: 1.6; margin-bottom: 15px; }
    .patent-tag { background: #1E293B; color: #F59E0B; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-right: 5px; border: 1px solid #F59E0B; }

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
    
    .data-card { background-color: #111827; padding: 16px; border: 1px solid #1F2937; border-bottom: 1px solid #374151; min-height: 80px; }
    .label-text { font-size: 10px; color: #94A3B8; text-transform: uppercase; font-weight: 700; margin-bottom: 6px; }
    .value-text { font-size: 15px; color: #F8FAFC; font-weight: 500; line-height: 1.4; }
    
    .abstract-container { background-color: #1E293B; padding: 30px; border-radius: 0 0 12px 12px; border: 1px solid #334155; border-top: none; line-height: 1.8; font-size: 17px; color: #E2E8F0; text-align: justify; }
    .type-badge { background-color: #F59E0B; color: #0F172A; padding: 4px 12px; border-radius: 4px; font-weight: 800; font-size: 12px; margin-left: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA UTILITIES ---

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

# --- 3. SECURITY & SESSION STATE ---
if "auth" not in st.session_state: st.session_state.auth = False
if "selected_patent" not in st.session_state: st.session_state.selected_patent = None

def get_logo():
    for ext in ["png", "jpg", "jpeg"]:
        if os.path.exists(f"logo.{ext}"): return f"logo.{ext}"
    return None

if not st.session_state.auth:
    _, col2, _ = st.columns([1, 1.2, 1])
    with col2:
        logo = get_logo()
        if logo: st.image(logo, use_container_width=True)
        st.markdown('<div style="background:#1E293B; padding:40px; border-radius:12px; border:1px solid #334155; text-align:center;">', unsafe_allow_html=True)
        st.markdown("<h3>KYRIX INTANGIBLE LANDSCAPE</h3>", unsafe_allow_html=True)
        key = st.text_input("SECURITY KEY", type="password")
        if st.button("AUTHORIZE SYSTEM"):
            if key in ["Kyrix2024", "LeoGiannotti2026!"]: st.session_state.auth = True; st.rerun()
            else: st.error("INVALID KEY")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    # --- 4. NAVIGATION ---
    with st.sidebar:
        logo = get_logo()
        if logo: st.image(logo)
        st.markdown("## 🛡️ SYSTEM MODE")
        app_mode = st.radio("SELECT VIEW:", ["🔍 Intelligence Search", "📈 Strategic Analysis"])
        st.markdown("---")

        if app_mode == "🔍 Intelligence Search":
            st.markdown("### 🔍 GLOBAL COMMAND")
            global_query = st.text_input("GOOGLE PATENT STYLE SEARCH", placeholder="e.g. AI AND Hydrogen")
            field_filters = {}
            field_filters['Title in English'] = st.text_input("Search in Title")
            field_filters['Abstract in English'] = st.text_input("Search in Abstract")
            if st.button("RESET SYSTEM"): st.rerun()
        else:
            all_types = sorted(df_main['Application Type (ID)'].unique())
            selected_types = st.multiselect("Select Application Types:", all_types, default=all_types)
            df_f = df_main[df_main['Application Type (ID)'].isin(selected_types)]
            df_exp_f = df_exp[df_exp['Application Type (ID)'].isin(selected_types)]

    # --- 5. SEARCH ENGINE ---
    if app_mode == "🔍 Intelligence Search":
        mask = boolean_search(df_search, global_query)
        for field, f_query in field_filters.items():
            if f_query: mask &= df_search[field].astype(str).str.contains(f_query, case=False, na=False)
        res = df_search[mask]
        
        st.markdown(f'<div class="metric-badge">● {len(res)} IDENTIFIED RECORDS</div>', unsafe_allow_html=True)
        
        # SAVE TO PDF (CSV Sim for reliability in browser)
        csv = res.to_csv(index=False).encode('utf-8')
        st.download_button("📂 SAVE SEARCH RESULTS (CSV/PDF-READY)", data=csv, file_name=f"Kyrix_Search_{datetime.now().strftime('%Y%m%d')}.csv", mime='text/csv')

        tab_list, tab_grid, tab_dossier = st.tabs(["📄 SEARCH OVERVIEW", "📋 DATABASE GRID", "🔍 PATENT DOSSIER VIEW"])
        
        with tab_list:
            if res.empty: st.info("No records match your query.")
            else:
                for idx, row in res.head(30).iterrows():
                    with st.container():
                        st.markdown(f"""
                        <div class="patent-card">
                            <div class="patent-title">{row['Title in English']}</div>
                            <div class="patent-meta">
                                <span class="patent-tag">{row.get('Application Type (ID)', 'N/A')}</span>
                                <b>App No:</b> {row['Application Number']} | <b>Applicant:</b> {row['Data of Applicant - Legal Name in English']}
                            </div>
                            <div class="patent-snippet">{row['Abstract in English'][:350]}...</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"Open Dossier: {row['Application Number']}", key=f"btn_{row['Application Number']}"):
                            st.session_state.selected_patent = row['Application Number']
                            # Note: In Streamlit tabs, we can't force switch tab programmatically easily, 
                            # but we notify the user to click the Dossier tab which is now pre-loaded.
                            st.success(f"Dossier for {row['Application Number']} is now loaded in the next tab!")

        with tab_grid:
            st.dataframe(res, use_container_width=True, hide_index=True)
        
        with tab_dossier:
            if res.empty: st.info("No records.")
            else:
                res['Display_Label'] = res.apply(lambda x: f"{x['Application Number']} | {str(x['Title in English'])[:50]}...", axis=1)
                default_idx = 0
                if st.session_state.selected_patent:
                    try: default_idx = list(res['Application Number']).index(st.session_state.selected_patent)
                    except: pass
                
                choice_label = st.selectbox("SELECT PATENT FILE:", res['Display_Label'].unique(), index=default_idx)
                choice_number = choice_label.split(" | ")[0]
                row = res[res['Application Number'] == choice_number].iloc[0]
                
                st.markdown(f"## {row['Title in English']} <span class='type-badge'>TYPE: {row.get('Application Type (ID)', '-')}</span>", unsafe_allow_html=True)
                st.markdown('<div class="section-header enriched-banner">Enriched Intelligence Metrics</div>', unsafe_allow_html=True)
                e_cols = [c for c, t in col_map.items() if t == "Enriched"]
                ec = st.columns(3)
                for i, c in enumerate(e_cols):
                    with ec[i%3]: st.markdown(f"<div class='data-card' style='border-left:4px solid #3B82F6;'><div class='label-text'>{c}</div><div class='value-text'>{row[c]}</div></div>", unsafe_allow_html=True)
                st.markdown('<div class="section-header raw-banner">Raw Source Data</div>', unsafe_allow_html=True)
                r_cols = [c for c, t in col_map.items() if t == "Raw" and c not in ["Abstract in English", "Title in English", "Application Type (ID)"]]
                rc = st.columns(3)
                for i, c in enumerate(r_cols):
                    with rc[i%3]: st.markdown(f"<div class='data-card'><div class='label-text'>{c}</div><div class='value-text'>{row[c]}</div></div>", unsafe_allow_html=True)
                st.markdown('<div class="section-header title-banner">Technical Abstract</div>', unsafe_allow_html=True)
                st.markdown(f"<div class='abstract-container'>{row['Abstract in English']}</div>", unsafe_allow_html=True)

    # --- 6. STRATEGIC ANALYSIS ---
    else:
        st.markdown('<div class="metric-badge">📈 STRATEGIC LANDSCAPE ENGINE</div>', unsafe_allow_html=True)
        tabs = st.tabs(["📈 App Type Growth", "🏢 Firm Intelligence", "🔬 Firm Tech-Strengths", "🎯 STRATEGIC MAP", "📊 IPC Classification", "📉 Moving Averages", "📅 Monthly Filing", "📊 IPC Growth Histogram"])

        with tabs[1]:
            all_firms = sorted(df_f['Firm'].unique())
            top_firms_list = df_f['Firm'].value_counts().nlargest(10).index.tolist()
            available_years = sorted(df_f['Year'].unique(), reverse=True)
            c1, c2 = st.columns(2)
            with c1:
                sel_all_firms = st.checkbox("Select All Firms")
                selected_firms = st.multiselect("Firms:", all_firms, default=top_firms_list[:5] if not sel_all_firms else all_firms)
                if sel_all_firms: selected_firms = all_firms
            with c2:
                sel_all_years = st.checkbox("Select All Years", value=True, key="firm_all_yr")
                selected_years = st.multiselect("Years:", available_years, default=available_years if sel_all_years else [available_years[0]])
                if sel_all_years: selected_years = available_years
            
            if selected_firms and selected_years:
                firm_sub = df_f[(df_f['Firm'].isin(selected_firms)) & (df_f['Year'].isin(selected_years))]
                st.dataframe(firm_sub['Firm'].value_counts().reset_index(name='Total Apps'), use_container_width=True, hide_index=True)
                st.plotly_chart(px.line(firm_sub.groupby(['Year', 'Firm']).size().reset_index(name='Apps'), x='Year', y='Apps', color='Firm', template="plotly_dark"), use_container_width=True)

        with tabs[5]:
            unique_3char = sorted(df_exp_f['IPC_Class3'].unique())
            all_av_years = sorted(df_f['Year'].unique())
            c1, c2 = st.columns(2)
            with c1: target_ipc = st.selectbox("IPC (3-Digit):", ["ALL IPC"] + unique_3char)
            with c2:
                sel_all_ma_years = st.checkbox("Select All Years", value=True, key="ma_all_yr")
                ma_years = st.multiselect("Years Range:", all_av_years, default=all_av_years if sel_all_ma_years else [all_av_years[-1]])
                if sel_all_ma_years: ma_years = all_av_years

            analysis_df = df_exp_f.copy() if target_ipc == "ALL IPC" else df_exp_f[df_exp_f['IPC_Class3'] == target_ipc]
            work_df = analysis_df[analysis_df['Year'].isin(ma_years)]

            if not work_df.empty:
                full_range = pd.date_range(start=f"{min(ma_years)}-01-01", end=f"{max(ma_years)}-12-31", freq='MS')
                type_pivot = work_df.groupby(['Priority_Month', 'Application Type (ID)']).size().unstack(fill_value=0)
                type_ma = type_pivot.reindex(full_range, fill_value=0).rolling(window=12, min_periods=1).mean()
                fig = go.Figure()
                for col_name in type_ma.columns:
                    fig.add_trace(go.Scatter(x=type_ma.index, y=type_ma[col_name], mode='lines', name=str(col_name), stackgroup='one'))
                fig.update_layout(template="plotly_dark", title=f"12M Moving Average: {target_ipc}")
                st.plotly_chart(fig, use_container_width=True)

        with tabs[7]:
            st.markdown("### 📊 IPC Growth Histogram")
            unique_ipc_list = sorted(df_exp_f['IPC_Class3'].unique())
            all_av_years_hist = sorted(df_exp_f['Year'].unique())
            hc1, hc2 = st.columns(2)
            with hc1:
                sel_all_ipc_hist = st.checkbox("Select All IPCs", key="hist_all_ipc")
                selected_ipc_hist = st.multiselect("Compare IPC Classes:", unique_ipc_list, default=unique_ipc_list[:3] if not sel_all_ipc_hist else unique_ipc_list)
                if sel_all_ipc_hist: selected_ipc_hist = unique_ipc_list
            with hc2:
                sel_all_hist_years = st.checkbox("Select All Years", value=True, key="hist_all_yr")
                hist_years = st.multiselect("Years:", all_av_years_hist, default=all_av_years_hist if sel_all_hist_years else [all_av_years_hist[-1]])
                if sel_all_hist_years: hist_years = all_av_years_hist
            
            if selected_ipc_hist and hist_years:
                hist_data = df_exp_f[(df_exp_f['IPC_Class3'].isin(selected_ipc_hist)) & (df_exp_f['Year'].isin(hist_years))]
                hist_growth = hist_data.groupby(['Year', 'IPC_Class3']).size().reset_index(name='Apps')
                st.plotly_chart(px.bar(hist_growth, x='Year', y='Apps', color='IPC_Class3', barmode='group', template="plotly_dark"), use_container_width=True)
