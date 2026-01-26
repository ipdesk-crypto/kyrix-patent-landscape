import streamlit as st
import pandas as pd
import os
import re
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import hmac
from datetime import datetime

# --- 1. PAGE CONFIG & BRANDING ---
st.set_page_config(
    page_title="Kyrix | Intangible Patent Landscape",
    page_icon="🛡️",
    layout="wide"
)

# --- 2. UNIFIED SECURITY GATE ---
def check_password():
    def password_entered():
        # Supports both keys from the combined scripts
        if hmac.compare_digest(st.session_state["password"], "Kyrix2024") or \
           hmac.compare_digest(st.session_state["password"], "LeoGiannotti2026!"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    # Luxury Login UI
    st.write("<br><br>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
            <div style="background:#1E293B; padding:40px; border-radius:12px; border:1px solid #F59E0B; text-align:center;">
                <h2 style="color:#F59E0B;">KYRIX INTANGIBLE LANDSCAPE</h2>
                <p style="color:#94A3B8;">INTELLIGENCE COMMAND & ANALYTICS ENGINE</p>
            </div>
        """, unsafe_allow_html=True)
        st.text_input("SECURITY KEY", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("INVALID CREDENTIALS")
    return False

if not check_password():
    st.stop()

# --- 3. LUXURY STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: #0F172A; } 
    h1, h2, h3, h4, p, span, label, .stMarkdown { color: #F1F5F9 !important; font-family: 'Inter', sans-serif; }
    
    /* Metrics & Cards */
    .metric-badge {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        color: #F59E0B !important; padding: 15px 30px; border-radius: 12px;
        font-weight: 800; font-size: 20px; border: 1px solid #334155; margin-bottom: 20px;
    }
    .metric-card-analytics {
        background-color: #1E293B; border-radius: 15px; padding: 25px;
        text-align: center; border-bottom: 6px solid #F59E0B;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-bottom: 20px;
    }
    .section-header {
        font-size: 14px; font-weight: 900; letter-spacing: 2px; text-transform: uppercase;
        padding: 15px 20px; border-radius: 8px 8px 0 0; margin-top: 30px; border: 1px solid #475569;
    }
    .enriched-banner { background: linear-gradient(90deg, #1E40AF 0%, #3B82F6 100%); }
    .raw-banner { background: linear-gradient(90deg, #1E293B 0%, #334155 100%); }
    .title-banner { background: #1E293B; border: 1px solid #F59E0B; color: #F59E0B !important; }
    
    .data-card { background-color: #111827; padding: 16px; border: 1px solid #1F2937; min-height: 80px; }
    .abstract-container { background-color: #1E293B; padding: 30px; border-radius: 0 0 12px 12px; border: 1px solid #334155; text-align: justify; }
    
    /* Sidebar & Tabs */
    [data-testid="stSidebar"] { background-color: #020617 !important; border-right: 1px solid #334155; }
    .stTabs [aria-selected="true"] { background-color: #F59E0B !important; color: #0F172A !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. CORE DATA ENGINE ---
@st.cache_data
def load_all_data():
    path = "2026 - 01- 23_ Data Structure for Patent Search and Analysis Engine - Type 5.csv"
    if not os.path.exists(path): return None, None, None
    
    raw_df = pd.read_csv(path, header=0)
    category_row = raw_df.iloc[0]
    col_map = {col: str(category_row[col]).strip() for col in raw_df.columns}
    
    df = raw_df.iloc[1:].copy().reset_index(drop=True)
    
    # Preprocessing for Analytics
    df['AppDate'] = pd.to_datetime(df['Application Date'], errors='coerce')
    df['PriorityDate'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce')
    df['Year'] = df['AppDate'].dt.year
    df['Month_Name'] = df['AppDate'].dt.month_name()
    df['Arrival_Month'] = df['AppDate'].dt.to_period('M').dt.to_timestamp()
    df['Priority_Month'] = df['PriorityDate'].dt.to_period('M').dt.to_timestamp()
    df['Firm'] = df['Data of Agent - Name in English'].fillna("DIRECT FILING").str.strip().str.upper()
    
    # IPC Engine
    df['IPC_Raw'] = df['Classification'].astype(str).str.split(',')
    df_exp = df.explode('IPC_Raw')
    df_exp['IPC_Clean'] = df_exp['IPC_Raw'].str.strip().str.upper()
    df_exp = df_exp[~df_exp['IPC_Clean'].str.contains("NO CLASSIFICATION|NAN|NONE", na=False)]
    df_exp['IPC_Class3'] = df_exp['IPC_Clean'].str[:3]
    df_exp['IPC_Section'] = df_exp['IPC_Clean'].str[:1]
    
    return df, df_exp, col_map

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

df_main, df_exp, col_map = load_all_data()

if df_main is not None:
    # --- 5. SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.markdown("## 🛡️ KYRIX COMMAND")
        app_mode = st.radio("SELECT OPERATIONAL MODE:", ["🔍 Intelligence Search", "📈 Strategic Analytics"])
        st.markdown("---")
        
        if app_mode == "🔍 Intelligence Search":
            st.markdown("### 🔍 GLOBAL SEARCH")
            global_query = st.text_input("QUERY (e.g. AI AND Healthcare)", placeholder="Boolean Search...")
            st.markdown("---")
            st.markdown("### 🛠️ FILTERS")
            f_title = st.text_input("Title Search")
            f_abstract = st.text_input("Abstract Search")
            if st.button("RESET ENGINE"): st.rerun()
        else:
            all_types = sorted(df_main['Application Type (ID)'].dropna().unique())
            selected_types = st.multiselect("Application Types:", all_types, default=all_types)
            st.success(f"Processing {len(df_main[df_main['Application Type (ID)'].isin(selected_types)])} Records")

    # --- 6. MODE 1: INTELLIGENCE SEARCH ---
    if app_mode == "🔍 Intelligence Search":
        mask = boolean_search(df_main, global_query)
        if f_title: mask &= df_main['Title in English'].str.contains(f_title, case=False, na=False)
        if f_abstract: mask &= df_main['Abstract in English'].str.contains(f_abstract, case=False, na=False)
        
        res = df_main[mask]
        st.markdown(f'<div class="metric-badge">● {len(res)} IDENTIFIED RECORDS</div>', unsafe_allow_html=True)
        
        tab_db, tab_dossier = st.tabs(["📋 DATABASE GRID", "🔍 PATENT DOSSIER VIEW"])
        
        with tab_db:
            st.dataframe(res, use_container_width=True)
            
        with tab_dossier:
            if not res.empty:
                choice = st.selectbox("SELECT PATENT:", res['Application Number'].unique())
                row = res[res['Application Number'] == choice].iloc[0]
                
                # Dossier Header
                st.markdown(f"## {row['Title in English']}")
                st.markdown(f"**App No:** {row['Application Number']} | **Date:** {row['Application Date']}")
                
                # Enriched Section
                st.markdown('<div class="section-header enriched-banner">Enriched Intelligence Metrics</div>', unsafe_allow_html=True)
                e_cols = [c for c, t in col_map.items() if t == "Enriched"]
                cols = st.columns(3)
                for i, c in enumerate(e_cols):
                    with cols[i%3]: st.markdown(f"<div class='data-card'><div style='color:#3B82F6; font-size:10px;'>{c}</div>{row[c]}</div>", unsafe_allow_html=True)
                
                # Abstract
                st.markdown('<div class="section-header title-banner">Technical Abstract</div>', unsafe_allow_html=True)
                st.markdown(f"<div class='abstract-container'>{row['Abstract in English']}</div>", unsafe_allow_html=True)
            else:
                st.info("No records found.")

    # --- 7. MODE 2: STRATEGIC ANALYTICS (ARCHISTRATEGOS) ---
    else:
        df_f = df_main[df_main['Application Type (ID)'].isin(selected_types)]
        df_exp_f = df_exp[df_exp['Application Type (ID)'].isin(selected_types)]
        
        a_tabs = st.tabs(["📈 Growth", "🏢 Firm IQ", "🎯 Strategic Map", "📊 IPC Distribution", "📉 Momentum"])
        
        with a_tabs[0]:
            growth = df_f.groupby(['Year', 'Application Type (ID)']).size().reset_index(name='Count')
            st.plotly_chart(px.line(growth, x='Year', y='Count', color='Application Type (ID)', template="plotly_dark"), use_container_width=True)

        with a_tabs[1]:
            top_firms = df_f['Firm'].value_counts().nlargest(10).reset_index()
            st.plotly_chart(px.bar(top_firms, x='count', y='Firm', orientation='h', template="plotly_dark", color_discrete_sequence=['#F59E0B']), use_container_width=True)

        with a_tabs[2]:
            land_data = df_exp_f.groupby(['IPC_Section', 'IPC_Class3']).agg({'Application Number':'count', 'Firm':'nunique'}).reset_index()
            st.plotly_chart(px.scatter(land_data, x='IPC_Section', y='IPC_Class3', size='Application Number', color='Firm', template="plotly_dark"), use_container_width=True)

        with a_tabs[3]:
            ipc_counts = df_exp_f.groupby('IPC_Section').size().reset_index(name='Count')
            st.plotly_chart(px.pie(ipc_counts, values='Count', names='IPC_Section', hole=.3, template="plotly_dark"), use_container_width=True)
            
        with a_tabs[4]:
            st.subheader("Monthly Filing Momentum")
            smooth_val = st.slider("Smoothing Window:", 1, 24, 6)
            counts = df_f.groupby('Arrival_Month').size().rolling(window=smooth_val).mean()
            st.line_chart(counts)

else:
    st.error("FATAL ERROR: CSV File Missing.")
