import streamlit as st
import pandas as pd
import os
import re
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import hmac
from datetime import datetime

# --- 1. PAGE CONFIG & LUXURY THEME (EXACTLY FROM CODE 1) ---
st.set_page_config(
    page_title="Kyrix | Intelligence Command",
    page_icon="🛡️",
    layout="wide"
)

st.markdown("""
    <style>
    .stApp { background-color: #0F172A; } 
    .logo-container { display: flex; justify-content: center; padding: 25px 0; }
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
    
    .stDownloadButton button {
        background-color: #F59E0B !important; color: #0F172A !important;
        font-weight: 700 !important; border: none !important; width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SEARCH & DATA UTILS (RESTORED FROM CODE 1) ---

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
def load_data():
    path = "2026 - 01- 23_ Data Structure for Patent Search and Analysis Engine - Type 5.csv"
    if not os.path.exists(path): return None, None, None
    df_raw = pd.read_csv(path, header=0)
    category_row = df_raw.iloc[0] 
    col_map = {col: str(category_row[col]).strip() for col in df_raw.columns}
    df = df_raw.iloc[1:].reset_index(drop=True)
    
    # Pre-processing for the Analysis Engine (Code 2 logic)
    df_clean = df.copy()
    df_clean['AppDate'] = pd.to_datetime(df_clean['Application Date'], errors='coerce')
    df_clean['Year'] = df_clean['AppDate'].dt.year
    df_clean['Month_Name'] = df_clean['AppDate'].dt.month_name()
    df_clean['Firm'] = df_clean['Data of Agent - Name in English'].fillna("DIRECT FILING").str.strip().str.upper()
    
    return df, col_map, df_clean

def get_logo():
    for ext in ["png", "jpg", "jpeg"]:
        if os.path.exists(f"logo.{ext}"): return f"logo.{ext}"
    return None

# --- 3. AUTHENTICATION (KYRIX BRANDING) ---
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
                st.session_state.auth = True
                st.rerun()
            else: st.error("INVALID CREDENTIALS")
        st.markdown('</div>', unsafe_allow_html=True)

else:
    df, col_map, df_analytics = load_data()
    
    if df is not None:
        # --- SIDEBAR: ALL FIELD FILTERS (RESTORED FROM CODE 1) ---
        with st.sidebar:
            logo = get_logo()
            if logo: st.image(logo)
            st.markdown("### 🔍 GLOBAL COMMAND")
            global_query = st.text_input("GOOGLE PATENT STYLE SEARCH", placeholder="e.g. Hydrogen AND Saline")
            
            st.markdown("---")
            st.markdown("### 🛠️ TECHNICAL FILTERS")
            field_filters = {}
            field_filters['Title in English'] = st.text_input("Search in Title", key="filter_title")
            field_filters['Abstract in English'] = st.text_input("Search in Abstract", key="filter_abstract")
            
            st.markdown("---")
            st.markdown("### 🏢 ENTITY FILTERS")
            other_fields = ['Application Number', 'Data of Applicant - Legal Name in English', 'Classification']
            for field in other_fields:
                if field in df.columns:
                    field_filters[field] = st.text_input(f"{field.split(' - ')[-1]}", key=f"filter_{field}")

            with st.expander("Show All Other Columns"):
                for col in df.columns:
                    if col not in other_fields and col not in ['Abstract in English', 'Title in English']:
                        val = st.text_input(f"{col}", key=f"extra_{col}")
                        if val: field_filters[col] = val

            if st.button("RESET ALL"): st.rerun()

        # Apply logic
        mask = boolean_search(df, global_query)
        for field, f_query in field_filters.items():
            if f_query:
                mask &= df[field].astype(str).str.contains(f_query, case=False, na=False)
        res = df[mask]

        # --- 4. MAIN INTERFACE TABS ---
        st.markdown(f'<div class="metric-badge">● {len(res)} IDENTIFIED RECORDS</div>', unsafe_allow_html=True)
        
        tab_db, tab_dossier, tab_analysis = st.tabs(["📋 DATABASE GRID", "🔍 PATENT DOSSIER VIEW", "📈 STRATEGIC ANALYSIS"])

        with tab_db:
            st.dataframe(res, use_container_width=True, hide_index=True)

        with tab_dossier:
            if res.empty:
                st.info("No records to display.")
            else:
                choice = st.selectbox("SELECT PATENT FILE:", res['Application Number'].unique())
                row = res[res['Application Number'] == choice].iloc[0]

                st.markdown("---")
                d1, d2 = st.columns([3, 1])
                with d1:
                    app_type = row['Application Type (ID)'] if pd.notna(row['Application Type (ID)']) else "N/A"
                    st.markdown(f"## {row['Title in English']} <span class='type-badge'>TYPE: {app_type}</span>", unsafe_allow_html=True)
                with d2:
                    st.download_button("📥 EXPORT DOSSIER", f"KYRIX REPORT\n{row['Title in English']}", f"{choice}.txt")

                # ENRICHED SECTION (From Code 1)
                st.markdown('<div class="section-header enriched-banner">Enriched Intelligence Metrics</div>', unsafe_allow_html=True)
                e_cols = [c for c, t in col_map.items() if t == "Enriched"]
                ec1, ec2, ec3 = st.columns(3)
                for i, col in enumerate(e_cols):
                    val = row[col] if pd.notna(row[col]) else "—"
                    with [ec1, ec2, ec3][i % 3]:
                        st.markdown(f"<div class='data-card' style='border-left: 4px solid #3B82F6;'><div class='label-text'>{col}</div><div class='value-text'>{val}</div></div>", unsafe_allow_html=True)

                # RAW DATA SECTION (From Code 1)
                st.markdown('<div class="section-header raw-banner">Raw Source Data</div>', unsafe_allow_html=True)
                r_cols = [c for c, t in col_map.items() if t == "Raw" and c not in ["Abstract in English", "Title in English", "Application Type (ID)"]]
                rc1, rc2, rc3 = st.columns(3)
                for i, col in enumerate(r_cols):
                    val = row[col] if pd.notna(row[col]) else "—"
                    with [rc1, rc2, rc3][i % 3]:
                        st.markdown(f"<div class='data-card'><div class='label-text'>{col}</div><div class='value-text'>{val}</div></div>", unsafe_allow_html=True)

                # ABSTRACT (From Code 1)
                st.markdown('<div class="section-header title-banner">Technical Abstract & Description</div>', unsafe_allow_html=True)
                abstract_text = row['Abstract in English'] if pd.notna(row['Abstract in English']) else "No technical abstract provided."
                st.markdown(f"<div class='abstract-container'>{abstract_text}</div>", unsafe_allow_html=True)

        with tab_analysis:
            st.markdown("### 🏛️ KYRIX STRATEGIC ENGINE")
            # Filtering the analytics dataframe based on current search results
            df_a_filtered = df_analytics[df_analytics['Application Number'].isin(res['Application Number'])]
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("Application Type Growth")
                growth = df_a_filtered.groupby(['Year', 'Application Type (ID)']).size().reset_index(name='Count')
                fig1 = px.line(growth, x='Year', y='Count', color='Application Type (ID)', template="plotly_dark")
                st.plotly_chart(fig1, use_container_width=True)
            
            with col_b:
                st.subheader("Top Filing Agents")
                firms = df_a_filtered['Firm'].value_counts().nlargest(10).reset_index()
                fig2 = px.bar(firms, x='count', y='Firm', orientation='h', template="plotly_dark", color_discrete_sequence=['#F59E0B'])
                st.plotly_chart(fig2, use_container_width=True)

            st.subheader("Filing Momentum (Monthly)")
            monthly = df_a_filtered.groupby('Month_Name').size().reindex(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], fill_value=0)
            st.bar_chart(monthly)

    else:
        st.error("FATAL ERROR: CSV File not found.")
