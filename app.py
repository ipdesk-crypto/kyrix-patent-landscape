import streamlit as st
import pandas as pd
import os
import re
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import hmac
from datetime import datetime

# --- 1. PAGE CONFIG & LUXURY THEME (KYRIX BRANDING) ---
st.set_page_config(
    page_title="Kyrix | Intelligence Command",
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
    
    .metric-card-analysis {
        background-color: #1E293B; border-radius: 15px; padding: 25px; text-align: center;
        border-bottom: 6px solid #F59E0B; box-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE UTILS & DATA ENGINE ---

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
def load_and_preprocess():
    path = "2026 - 01- 23_ Data Structure for Patent Search and Analysis Engine - Type 5.csv"
    if not os.path.exists(path): return None, None, None, None
    
    df_raw = pd.read_csv(path, header=0)
    category_row = df_raw.iloc[0] 
    col_map = {col: str(category_row[col]).strip() for col in df_raw.columns}
    df = df_raw.iloc[1:].reset_index(drop=True)
    
    # Analysis Preprocessing (From Code 2)
    df_p = df.copy()
    df_p['AppDate'] = pd.to_datetime(df_p['Application Date'], errors='coerce')
    df_p['PriorityDate'] = pd.to_datetime(df_p['Earliest Priority Date'], errors='coerce')
    df_p['Year'] = df_p['AppDate'].dt.year
    df_p['Month_Name'] = df_p['AppDate'].dt.month_name()
    df_p['Arrival_Month'] = df_p['AppDate'].dt.to_period('M').dt.to_timestamp()
    df_p['Priority_Month'] = df_p['PriorityDate'].dt.to_period('M').dt.to_timestamp()
    df_p['Firm'] = df_p['Data of Agent - Name in English'].fillna("DIRECT FILING").str.strip().str.upper()
    
    # IPC Engine
    df_p['IPC_Raw'] = df_p['Classification'].astype(str).str.split(',')
    df_exp = df_p.explode('IPC_Raw')
    df_exp['IPC_Clean'] = df_exp['IPC_Raw'].str.strip().str.upper()
    df_exp = df_exp[~df_exp['IPC_Clean'].str.contains("NO CLASSIFICATION|NAN|NONE", na=False)]
    df_exp['IPC_Class3'] = df_exp['IPC_Clean'].str[:3] 
    df_exp['IPC_Section'] = df_exp['IPC_Clean'].str[:1]
    
    return df, col_map, df_p, df_exp

def get_logo():
    for ext in ["png", "jpg", "jpeg"]:
        if os.path.exists(f"logo.{ext}"): return f"logo.{ext}"
    return None

# --- 3. AUTHENTICATION ---
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
            if key in ["Kyrix2024", "LeoGiannotti2026!"]: st.session_state.auth = True; st.rerun()
            else: st.error("INVALID CREDENTIALS")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    df, col_map, df_main, df_exp = load_and_preprocess()
    
    if df is not None:
        # --- SIDEBAR FILTERS ---
        with st.sidebar:
            logo = get_logo()
            if logo: st.image(logo)
            st.markdown("### 🔍 GLOBAL COMMAND")
            global_query = st.text_input("GOOGLE PATENT STYLE SEARCH", placeholder="e.g. Hydrogen AND Saline")
            
            st.markdown("---")
            st.markdown("### 🛠️ TECHNICAL FILTERS")
            field_filters = {}
            field_filters['Title in English'] = st.text_input("Search in Title", key="f_t")
            field_filters['Abstract in English'] = st.text_input("Search in Abstract", key="f_a")
            
            other_fields = ['Application Number', 'Data of Applicant - Legal Name in English', 'Classification']
            for field in other_fields:
                if field in df.columns:
                    field_filters[field] = st.text_input(f"{field.split(' - ')[-1]}", key=f"f_{field}")

            with st.expander("Show All Other Columns"):
                for col in df.columns:
                    if col not in other_fields and col not in ['Abstract in English', 'Title in English']:
                        val = st.text_input(col, key=f"ex_{col}")
                        if val: field_filters[col] = val

            if st.button("RESET ALL"): st.rerun()

        # Apply Filtering
        mask = boolean_search(df, global_query)
        for field, f_query in field_filters.items():
            if f_query: mask &= df[field].astype(str).str.contains(f_query, case=False, na=False)
        res = df[mask]
        res_main = df_main[mask]
        res_exp = df_exp[df_exp['Application Number'].isin(res['Application Number'])]

        # --- 4. MAIN TABS ---
        st.markdown(f'<div class="metric-badge">● {len(res)} IDENTIFIED RECORDS</div>', unsafe_allow_html=True)
        tab_db, tab_dossier, tab_analysis = st.tabs(["📋 DATABASE GRID", "🔍 PATENT DOSSIER VIEW", "📊 STRATEGIC ANALYSIS ENGINE"])

        # TAB 1: GRID
        with tab_db:
            st.dataframe(res, use_container_width=True, hide_index=True)

        # TAB 2: DOSSIER
        with tab_dossier:
            if res.empty: st.info("No records.")
            else:
                choice = st.selectbox("SELECT PATENT FILE:", res['Application Number'].unique())
                row = res[res['Application Number'] == choice].iloc[0]
                st.markdown(f"## {row['Title in English']} <span class='type-badge'>TYPE: {row.get('Application Type (ID)', 'N/A')}</span>", unsafe_allow_html=True)
                
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

        # TAB 3: NESTED ANALYSIS ENGINE (CODE 2 FULL FUNCTIONALITY)
        with tab_analysis:
            st.markdown("### 🏛️ ARCHISTRATEGOS ANALYSIS CORE")
            a_tabs = st.tabs(["📈 App Type Growth", "🏢 Firm Intelligence", "🔬 Firm Tech-Strengths", "🎯 STRATEGIC MAP", "📊 IPC Classification", "📉 Dynamic Moving Averages", "📅 Monthly Filing"])
            
            # 1. Growth
            with a_tabs[0]:
                growth = res_main.groupby(['Year', 'Application Type (ID)']).size().reset_index(name='Count')
                st.plotly_chart(px.line(growth, x='Year', y='Count', color='Application Type (ID)', markers=True, template="plotly_dark"), use_container_width=True)

            # 2. Firm IQ
            with a_tabs[1]:
                top_firms = res_main['Firm'].value_counts().nlargest(10).index.tolist()
                selected_firms = st.multiselect("Compare Firms:", sorted(res_main['Firm'].unique()), default=top_firms[:5])
                if selected_firms:
                    f_growth = res_main[res_main['Firm'].isin(selected_firms)].groupby(['Year', 'Firm']).size().reset_index(name='Apps')
                    st.plotly_chart(px.line(f_growth, x='Year', y='Apps', color='Firm', markers=True, template="plotly_dark"), use_container_width=True)

            # 3. Tech Strengths
            with a_tabs[2]:
                if not res_exp.empty:
                    firm_ipc = res_exp.groupby(['Firm', 'IPC_Class3']).size().reset_index(name='Count')
                    st.plotly_chart(px.bar(firm_ipc, x='Count', y='Firm', color='IPC_Class3', orientation='h', template="plotly_dark"), use_container_width=True)

            # 4. Strategic Map
            with a_tabs[3]:
                land_data = res_exp.groupby(['IPC_Section', 'IPC_Class3']).agg({'Application Number':'count', 'Firm':'nunique'}).reset_index()
                st.plotly_chart(px.scatter(land_data, x='IPC_Section', y='IPC_Class3', size='Application Number', color='Firm', template="plotly_dark"), use_container_width=True)

            # 5. IPC Class
            with a_tabs[4]:
                ipc_counts = res_exp.groupby('IPC_Section').size().reset_index(name='Count').sort_values('IPC_Section')
                st.plotly_chart(px.bar(ipc_counts, x='IPC_Section', y='Count', color='IPC_Section', text='Count', template="plotly_dark"), use_container_width=True)

            # 6. Moving Averages
            with a_tabs[5]:
                target_ipc = st.selectbox("IPC Class (3-Digit):", ["ALL IPC"] + sorted(res_exp['IPC_Class3'].unique()))
                smooth_val = st.slider("Smoothing (Months):", 1, 36, 12)
                
                analysis_df = res_exp if target_ipc == "ALL IPC" else res_exp[res_exp['IPC_Class3'] == target_ipc]
                work_df = res_main if target_ipc == "ALL IPC" else res_main[res_main['Application Number'].isin(analysis_df['Application Number'])]
                
                full_range = pd.date_range(start='2010-01-01', end=res_main['AppDate'].max(), freq='MS')
                t_counts = analysis_df.groupby(['Priority_Month', 'Application Type (ID)']).size().unstack(fill_value=0)
                t_ma = t_counts.reindex(full_range, fill_value=0).rolling(window=smooth_val, min_periods=1).mean()
                
                fig = go.Figure()
                for c in t_ma.columns:
                    fig.add_trace(go.Scatter(x=t_ma.index, y=t_ma[c], mode='lines', name=c, stackgroup='one', fill='tonexty'))
                st.plotly_chart(fig, use_container_width=True)

            # 7. Monthly
            with a_tabs[6]:
                sel_year = st.selectbox("Year:", sorted(res_main['Year'].unique(), reverse=True))
                m_data = res_main[res_main['Year'] == sel_year]
                m_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                m_counts = m_data.groupby('Month_Name').size().reindex(m_order, fill_value=0).reset_index(name='Apps')
                st.plotly_chart(px.bar(m_counts, x='Month_Name', y='Apps', template="plotly_dark"), use_container_width=True)

    else:
        st.error("FATAL ERROR: CSV File not found.")
