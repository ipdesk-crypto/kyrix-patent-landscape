import streamlit as st
import pandas as pd
import os
import re
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import hmac
from datetime import datetime, timedelta

# --- 1. PAGE CONFIG & KYRIX LUXURY THEME ---
st.set_page_config(
    page_title="Kyrix | Intangible Patent Landscape",
    page_icon="🛡️",
    layout="wide"
)

# TOTAL DARK MODE OVERRIDE
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"], .main, [data-testid="stHeader"] {
        background-color: #0F172A !important;
        color: #F1F5F9 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #020617 !important;
        border-right: 1px solid #1E293B !important;
    }
    [data-testid="stSidebar"] * {
        color: #F1F5F9 !important;
    }
    div[data-baseweb="select"] > div, 
    div[data-baseweb="input"] > div,
    .stMultiSelect div, 
    .stSelectbox div,
    input {
        background-color: #1E293B !important;
        color: white !important;
        border-color: #334155 !important;
    }
    span[data-baseweb="tag"] {
        background-color: #3B82F6 !important;
        color: white !important;
    }
    [data-testid="stDataFrame"], [data-testid="stTable"] {
        background-color: #111827 !important;
        border: 1px solid #1F2937 !important;
    }
    .styled-table, [data-testid="stTable"] td, [data-testid="stTable"] th {
        background-color: #111827 !important;
        color: #F1F5F9 !important;
        border: 1px solid #1F2937 !important;
    }
    button[data-baseweb="tab"] {
        color: #94A3B8 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #F59E0B !important;
        border-bottom-color: #F59E0B !important;
    }
    .patent-card {
        background-color: #111827 !important;
        border: 1px solid #1F2937 !important;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        transition: transform 0.2s, border-color 0.2s;
    }
    .patent-card:hover {
        border-color: #3B82F6 !important;
        transform: translateY(-2px);
    }
    .patent-title { color: #3B82F6 !important; font-size: 18px; font-weight: 700; text-decoration: none; margin-bottom: 5px; display: block; }
    .patent-meta { color: #94A3B8 !important; font-size: 13px; margin-bottom: 10px; }
    .patent-snippet { color: #CBD5E1 !important; font-size: 14px; line-height: 1.5; }
    .patent-tag { background: #1E293B !important; color: #F59E0B !important; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }
    .metric-badge {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%) !important;
        color: #F59E0B !important;
        padding: 15px 30px;
        border-radius: 12px;
        font-weight: 800; font-size: 20px;
        border: 1px solid #334155 !important;
        display: inline-block; margin-bottom: 20px;
    }
    .section-header {
        font-size: 14px; font-weight: 900; letter-spacing: 2px; text-transform: uppercase;
        padding: 15px 20px; border-radius: 8px 8px 0 0; margin-top: 30px;
        border: 1px solid #475569 !important; border-bottom: none !important;
    }
    .enriched-banner { background: linear-gradient(90deg, #1E40AF 0%, #3B82F6 100%) !important; color: #FFFFFF !important; }
    .raw-banner { background: linear-gradient(90deg, #1E293B 0%, #334155 100%) !important; color: #CBD5E1 !important; }
    .title-banner { background: #1E293B !important; border: 1px solid #F59E0B !important; color: #F59E0B !important; }
    .data-card { 
        background-color: #111827 !important; padding: 16px; 
        border: 1px solid #1F2937 !important; border-bottom: 1px solid #374151 !important;
        min-height: 80px;
    }
    .label-text { font-size: 10px; color: #94A3B8 !important; text-transform: uppercase; font-weight: 700; }
    .value-text { font-size: 15px; color: #F8FAFC !important; font-weight: 500; }
    .abstract-container {
        background-color: #1E293B !important; padding: 30px; border-radius: 0 0 12px 12px;
        border: 1px solid #334155 !important; border-top: none !important;
        line-height: 1.8; font-size: 17px; color: #E2E8F0 !important; text-align: justify;
    }
    .type-badge {
        background-color: #F59E0B !important; color: #0F172A !important; padding: 4px 12px; 
        border-radius: 4px; font-weight: 800; font-size: 12px; margin-left: 10px;
    }
    label, p, h1, h2, h3, h4, h5, h6, .stMarkdown {
        color: #F1F5F9 !important;
    }
    .report-box {
        background-color: #020617 !important;
        border: 1px solid #334155 !important;
        padding: 20px;
        border-radius: 10px;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

def fix_chart(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#F1F5F9"),
        xaxis=dict(gridcolor="#334155", linecolor="#334155", showgrid=True),
        yaxis=dict(gridcolor="#1E293B", linecolor="#334155"),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            itemclick="toggle",
            itemdoubleclick="toggleothers"
        )
    )
    return fig

# --- STRICT YEAR AXIS FORMATTING ('95, '96...) ---
def apply_year_axis_formatting(fig):
    fig.update_xaxes(
        dtick=1,            # Force a tick for every single year
        tickformat="'%y",   # Format as '95, '96, '24 etc.
        showgrid=True,
        gridwidth=1,
        gridcolor="#334155"
    )
    return fig

# Helper to parse year input
def parse_year_input(input_str, all_available_years):
    if not input_str:
        return all_available_years
    try:
        years = [int(y.strip()) for y in input_str.split(',') if y.strip().isdigit()]
        return years if years else all_available_years
    except:
        return all_available_years

# Helper to get cutoff dates
def get_cutoff_dates():
    curr_time = datetime.now()
    c18 = curr_time - pd.DateOffset(months=18)
    c30 = curr_time - pd.DateOffset(months=30)
    return c18, c30

# Helper for vertical lines on Integer Year Axis
def add_cutoff_lines_numeric_axis(fig, c18, c30):
    c18_dec = c18.year + (c18.month - 1) / 12
    c30_dec = c30.year + (c30.month - 1) / 12
    
    fig.add_vline(x=c18_dec, line_width=2, line_dash="dash", line_color="#F59E0B", annotation_text="18m Cutoff", annotation_position="top left")
    fig.add_vline(x=c30_dec, line_width=2, line_dash="dash", line_color="#EF4444", annotation_text="30m Cutoff", annotation_position="top left")
    return fig

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
    if not os.path.exists(path) or os.stat(path).st_size == 0: 
        return pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame()
    try:
        df_raw = pd.read_csv(path, header=0, encoding='utf-8', on_bad_lines='skip')
        if df_raw.empty: return pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame()
        category_row = df_raw.iloc[0] 
        col_map = {col: str(category_row[col]).strip() for col in df_raw.columns}
        df_search = df_raw.iloc[1:].reset_index(drop=True).fillna("-")
        df = df_search.copy()
        
        # --- PARSE DATES (Enhanced with dayfirst=True for safety) ---
        df['AppDate'] = pd.to_datetime(df['Application Date'], errors='coerce', dayfirst=True)
        df['PriorityDate'] = pd.to_datetime(df['Earliest Priority Date'], errors='coerce', dayfirst=True)
        
        # --- CRITICAL FIX: Only drop rows where AppDate is missing ---
        # Do NOT drop rows if PriorityDate is missing, to preserve Application Counts
        df_analysis = df.dropna(subset=['AppDate']).copy()
        
        if not df_analysis.empty:
            # --- ANALYSIS YEAR BASED ON APPLICATION DATE (FILING DATE) ---
            df_analysis['Year'] = df_analysis['AppDate'].dt.year.astype(int)
            
            df_analysis['Month_Name'] = df_analysis['AppDate'].dt.month_name()
            df_analysis['Arrival_Month'] = df_analysis['AppDate'].dt.to_period('M').dt.to_timestamp()
            
            # Handle Priority Month (allow NaT)
            df_analysis['Priority_Month'] = df_analysis['PriorityDate'].dt.to_period('M').dt.to_timestamp()
            
            df_analysis['Firm'] = df_analysis['Data of Agent - Name in English'].replace("-", "DIRECT FILING").str.strip().str.upper()
            df_analysis['IPC_Raw'] = df_analysis['Classification'].astype(str).str.split(',')
            df_exp = df_analysis.explode('IPC_Raw')
            df_exp['IPC_Clean'] = df_exp['IPC_Raw'].str.strip().str.upper()
            df_exp = df_exp[~df_exp['IPC_Clean'].str.contains("NO CLASSIFICATION|NAN|NONE|-", na=False)]
            df_exp['IPC_Class3'] = df_exp['IPC_Clean'].str[:3] 
            df_exp['IPC_Section'] = df_exp['IPC_Clean'].str[:1]
            return df_search, col_map, df_analysis, df_exp
        else:
            return df_search, col_map, pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        return pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame()

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
        st.markdown('<div style="background:#1E293B; padding:40px; border-radius:12px; border:1px solid #F59E0B; text-align:center;">', unsafe_allow_html=True)
        st.markdown("<h3 style='color:white;'>KYRIX INTANGIBLE</h3>", unsafe_allow_html=True)
        key = st.text_input("SECURITY KEY", type="password")
        if st.button("AUTHORIZE SYSTEM"):
            if key in ["LeoGiannotti2026!", "LeoGiannotti2026!"]: 
                st.session_state.auth = True; st.rerun()
            else: st.error("INVALID KEY")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    # --- 4. NAVIGATION & SIDEBAR ---
    with st.sidebar:
        logo = get_logo()
        if logo: st.image(logo)
        st.markdown("## SYSTEM MODE")
        app_mode = st.radio("SELECT VIEW:", ["Intelligence Search", "Strategic Analysis"])
        st.markdown("---")
        if app_mode == "Intelligence Search":
            st.markdown("### GLOBAL COMMAND")
            global_query = st.text_input("GOOGLE PATENT STYLE SEARCH", placeholder="e.g. AI AND Hydrogen")
            st.markdown("### FILTERS")
            field_filters = {}
            field_filters['Title in English'] = st.text_input("Search in Title")
            field_filters['Abstract in English'] = st.text_input("Search in Abstract")
            other_fields = ['Application Number', 'Data of Applicant - Legal Name in English', 'Classification']
            for field in other_fields:
                field_filters[field] = st.text_input(f"{field.split(' - ')[-1]}")
            if df_search is not None and not df_search.empty:
                with st.expander("Show All Other Columns"):
                    for col in df_search.columns:
                        if col not in other_fields and col not in ['Abstract in English', 'Title in English']:
                            val = st.text_input(col, key=f"ex_{col}")
                            if val: field_filters[col] = val
        else:
            st.markdown("### ANALYTICS FILTERS")
            if df_main is not None and not df_main.empty:
                all_types = sorted(df_main['Application Type (ID)'].unique())
                selected_types = st.multiselect("Select Application Types:", all_types, default=all_types)
                df_f = df_main[df_main['Application Type (ID)'].isin(selected_types)]
                df_exp_f = df_exp[df_exp['Application Type (ID)'].isin(selected_types)]
                st.success(f"Records Analyzed: {len(df_f)}")
        if st.button("RESET SYSTEM"): st.rerun()

    # --- 5. MODE: SEARCH ENGINE ---
    if app_mode == "Intelligence Search":
        if df_search is not None and not df_search.empty:
            mask = boolean_search(df_search, global_query)
            for field, f_query in field_filters.items():
                if f_query: mask &= df_search[field].astype(str).str.contains(f_query, case=False, na=False)
            res = df_search[mask]
            st.markdown(f'<div class="metric-badge">● {len(res)} IDENTIFIED RECORDS</div>', unsafe_allow_html=True)
            tab_list, tab_grid, tab_dossier = st.tabs(["SEARCH OVERVIEW", "DATABASE GRID", "PATENT DOSSIER VIEW"])
            with tab_list:
                if res.empty: st.info("No records match your query.")
                else:
                    for idx, row in res.head(50).iterrows():
                        st.markdown(f"""
                        <div class="patent-card">
                            <div class="patent-title">{row['Title in English']}</div>
                            <div class="patent-meta">
                                <span class="patent-tag">{row.get('Application Type (ID)', 'N/A')}</span>
                                <b>App No:</b> {row['Application Number']} | 
                                <b>Applicant:</b> {row['Data of Applicant - Legal Name in English']} | 
                                <b>Earliest Priority Date:</b> {row['Earliest Priority Date']}
                            </div>
                            <div class="patent-snippet">{row['Abstract in English']}</div>
                        </div>
                        """, unsafe_allow_html=True)
            with tab_grid: st.dataframe(res, use_container_width=True, hide_index=True)
            with tab_dossier:
                if res.empty: st.info("No records.")
                else:
                    res = res.copy()
                    res['Display_Label'] = res.apply(lambda x: f"{x['Application Number']} | {str(x['Title in English'])[:50]}...", axis=1)
                    choice_label = st.selectbox("SELECT PATENT FILE TO DRILL DOWN:", res['Display_Label'].unique())
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

    # --- 6. MODE: STRATEGIC ANALYSIS ENGINE ---
    else:
        if df_main is not None and not df_main.empty:
            st.markdown('<div class="metric-badge">STRATEGIC LANDSCAPE ENGINE</div>', unsafe_allow_html=True)
            tabs = st.tabs(["APPLICATION GROWTH", "Firm Intelligence", "Firm Tech-Strengths", "STRATEGIC MAP", "IPC Classification", "Moving Averages", "Monthly Filing", "IPC Growth Histogram"])
            
            with tabs[0]:
                st.markdown("### 📊 Application Growth Intelligence (By Filing Year)")
                
                # REPORT BOX TOP
                c18, c30 = get_cutoff_dates()
                st.markdown(f"""<div class="report-box"><h4 style="color:#F59E0B;">📋 PUBLICATION LAG REPORT</h4>
                            Type 4 & 5 Cutoff: <b>{c18.strftime('%d %B %Y')}</b> | Type 1 Cutoff: <b>{c30.strftime('%d %B %Y')}</b><br>
                            <span style="font-size:12px; color:#94A3B8;">*Vertical lines in charts approximate these dates based on Filing Date.</span></div>""", unsafe_allow_html=True)

                c1, c2 = st.columns([1.5, 1])
                all_years_growth = sorted(df_f['Year'].unique())
                
                with c1:
                    mode_growth = st.radio("Year Selection Mode:", ["Type Specific Years", "Select Range"], horizontal=True, key="mode_growth")
                    if mode_growth == "Type Specific Years":
                        year_input_growth = st.text_input("Type Years (comma separated):", value=", ".join(map(str, all_years_growth)))
                        sel_years_growth = parse_year_input(year_input_growth, all_years_growth)
                    else:
                        min_y, max_y = min(all_years_growth), max(all_years_growth)
                        s_year, e_year = st.slider("Select Year Range:", min_y, max_y, (min_y, max_y), key="growth_slider")
                        sel_years_growth = list(range(s_year, e_year + 1))

                with c2:
                    all_types_growth = sorted(df_f['Application Type (ID)'].unique())
                    sel_types_growth = st.multiselect("Filter Application Types:", all_types_growth, default=all_types_growth, key="growth_types_sel")
                
                df_growth_filtered = df_f[df_f['Year'].isin(sel_years_growth) & df_f['Application Type (ID)'].isin(sel_types_growth)]
                
                if not df_growth_filtered.empty:
                    # REINDEX TO ENSURE ALL YEARS PRESENT
                    growth_year = df_growth_filtered.groupby(['Year', 'Application Type (ID)']).size().reset_index(name='Count')
                    
                    # 1. ORIGINAL VERSION (Grouped)
                    fig_year = px.bar(growth_year, x='Year', y='Count', color='Application Type (ID)', barmode='group', text='Count', title="Annual Application Volume (Grouped View - Filing Date)")
                    fig_year = add_cutoff_lines_numeric_axis(fig_year, c18, c30)
                    fig_year = apply_year_axis_formatting(fig_year)
                    st.plotly_chart(fix_chart(fig_year), use_container_width=True)
                    
                    # 2. NEW VERSION (Stacked)
                    fig_stacked = px.bar(growth_year, x='Year', y='Count', color='Application Type (ID)', barmode='stack', text='Count', title="Annual Application Volume (Stacked/Combined View - Filing Date)")
                    fig_stacked = add_cutoff_lines_numeric_axis(fig_stacked, c18, c30)
                    fig_stacked = apply_year_axis_formatting(fig_stacked)
                    st.plotly_chart(fix_chart(fig_stacked), use_container_width=True)

                    # 3. NEW MONTHLY STACKED BREAKDOWN
                    st.markdown("### 📅 Monthly Stacked Distribution (Filing Date)")
                    m_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                    
                    # Sort data for chronological display
                    df_growth_filtered['Month_Sort'] = df_growth_filtered['Arrival_Month'].dt.month
                    # Using Month_Name (derived from AppDate)
                    
                    monthly_stacked = df_growth_filtered.groupby(['Year', 'Month_Name', 'Application Type (ID)', 'Month_Sort']).size().reset_index(name='Count')
                    monthly_stacked = monthly_stacked.sort_values(['Year', 'Month_Sort'])
                    
                    fig_monthly_stacked = px.bar(monthly_stacked, x='Month_Name', y='Count', color='Application Type (ID)', 
                                               facet_col='Year', barmode='stack', title="Monthly Combined Volume (Stacked by Filing Year)")
                    st.plotly_chart(fix_chart(fig_monthly_stacked), use_container_width=True)

                    st.markdown("---")
                    st.subheader("Annual Summary Table")
                    summary_pivot = growth_year.pivot(index='Application Type (ID)', columns='Year', values='Count').fillna(0).astype(int)
                    summary_pivot['Total'] = summary_pivot.sum(axis=1)
                    st.dataframe(summary_pivot, use_container_width=True)

                else: st.warning("No data found.")

            with tabs[1]:
                # REPORT BOX TOP
                c18, c30 = get_cutoff_dates()
                st.markdown(f"""<div class="report-box"><h4 style="color:#F59E0B;">📋 PUBLICATION LAG REPORT</h4>
                            Type 4 & 5 Cutoff: <b>{c18.strftime('%d %B %Y')}</b> | Type 1 Cutoff: <b>{c30.strftime('%d %B %Y')}</b></div>""", unsafe_allow_html=True)
                
                df_firms_only = df_f[df_f['Firm'] != "DIRECT FILING"]
                all_firms = sorted(df_firms_only['Firm'].unique())
                top_firms_list = df_firms_only['Firm'].value_counts().nlargest(10).index.tolist()
                available_years = sorted(df_firms_only['Year'].unique(), reverse=True)
                
                c1, c2 = st.columns([1,1])
                with c1:
                    sel_all_firms = st.checkbox("Select All Firms", key="all_firms_chk")
                    selected_firms = st.multiselect("Select Firms:", all_firms, default=top_firms_list[:5] if not sel_all_firms else all_firms)
                with c2:
                    mode_firm = st.radio("Year Selection Mode:", ["Type Specific Years", "Select Range"], horizontal=True, key="mode_firm")
                    if mode_firm == "Type Specific Years":
                        year_input_firm = st.text_input("Type Years for Firm Analysis:", value=", ".join(map(str, available_years)))
                        selected_years = parse_year_input(year_input_firm, available_years)
                    else:
                        min_y, max_y = min(available_years), max(available_years)
                        s_year, e_year = st.slider("Select Year Range:", min_y, max_y, (min_y, max_y), key="firm_slider")
                        selected_years = list(range(s_year, e_year + 1))
                
                if selected_firms and selected_years:
                    firm_sub = df_firms_only[(df_firms_only['Firm'].isin(selected_firms)) & (df_firms_only['Year'].isin(selected_years))]
                    st.markdown("### Firm Rank by Application Volume")
                    st.dataframe(firm_sub['Firm'].value_counts().reset_index().rename(columns={'count':'Total Apps'}), use_container_width=True, hide_index=True)
                    firm_growth = firm_sub.groupby(['Year', 'Firm']).size().reset_index(name='Apps')
                    fig = px.line(firm_growth, x='Year', y='Apps', color='Firm', markers=True, height=800, title="Firm Filing Intelligence (Expanded View - Filing Date)")
                    fig = add_cutoff_lines_numeric_axis(fig, c18, c30)
                    fig = apply_year_axis_formatting(fig)
                    st.plotly_chart(fix_chart(fig), use_container_width=True)

            with tabs[2]:
                df_exp_firms_only = df_exp_f[df_exp_f['Firm'] != "DIRECT FILING"]
                if 'selected_firms' in locals() and selected_firms:
                    firm_ipc = df_exp_firms_only[df_exp_firms_only['Firm'].isin(selected_firms)].groupby(['Firm', 'IPC_Class3']).size().reset_index(name='Count')
                    fig = px.bar(firm_ipc, x='Count', y='Firm', color='IPC_Class3', orientation='h', height=600)
                    st.plotly_chart(fix_chart(fig), use_container_width=True)

            with tabs[3]:
                land_data = df_exp_f.groupby(['IPC_Section', 'IPC_Class3']).agg({'Application Number':'count', 'Firm':'nunique'}).reset_index()
                fig = px.scatter(land_data, x='IPC_Section', y='IPC_Class3', size='Application Number', color='Firm', height=600)
                st.plotly_chart(fix_chart(fig), use_container_width=True)

            with tabs[4]:
                ipc_counts = df_exp_f.groupby('IPC_Section').size().reset_index(name='Count').sort_values('IPC_Section')
                fig = px.bar(ipc_counts, x='IPC_Section', y='Count', color='IPC_Section', text='Count', height=600)
                st.plotly_chart(fix_chart(fig), use_container_width=True)

            with tabs[5]:
                most_recent_date = df_main['AppDate'].max()
                date_str = most_recent_date.strftime('%d %B %Y') if pd.notnull(most_recent_date) else "N/A"
                st.markdown(f'<div class="metric-badge" style="padding:10px 20px; font-size:16px;">Most Recent Filing Date: {date_str}</div>', unsafe_allow_html=True)
                
                # REPORT BOX TOP
                c18, c30 = get_cutoff_dates()
                st.markdown(f"""<div class="report-box"><h4 style="color:#F59E0B;">📋 PUBLICATION LAG REPORT</h4>
                            Type 4 & 5 Cutoff: <b>{c18.strftime('%d %B %Y')}</b> | Type 1 Cutoff: <b>{c30.strftime('%d %B %Y')}</b></div>""", unsafe_allow_html=True)

                unique_3char = sorted(df_exp_f['IPC_Class3'].unique())
                all_av_years = sorted(df_f['Year'].unique())
                
                c1, c2, c3 = st.columns(3)
                with c1: target_ipc = st.selectbox("IPC Class (3-Digit):", ["ALL IPC"] + unique_3char, key="ma_ipc")
                with c2:
                    mode_ma = st.radio("Year Selection Mode:", ["Type Specific Years", "Select Range"], horizontal=True, key="mode_ma")
                    if mode_ma == "Type Specific Years":
                        ma_year_input = st.text_input("Type Years for Moving Average:", value=", ".join(map(str, all_av_years)))
                        ma_years = parse_year_input(ma_year_input, all_av_years)
                    else:
                        min_y, max_y = min(all_av_years), max(all_av_years)
                        s_year, e_year = st.slider("Select Year Range:", min_y, max_y, (min_y, max_y), key="ma_slider")
                        ma_years = list(range(s_year, e_year + 1))
                with c3:
                    all_av_types = sorted(df_f['Application Type (ID)'].unique())
                    sel_ma_types = st.multiselect("Visible Types:", all_av_types, default=all_av_types)
                
                analysis_df = df_exp_f.copy() if target_ipc == "ALL IPC" else df_exp_f[df_exp_f['IPC_Class3'] == target_ipc]
                work_df = df_f.copy() if target_ipc == "ALL IPC" else df_f[df_f['Application Number'].isin(analysis_df['Application Number'].unique())]
                work_df = work_df[(work_df['Year'].isin(ma_years)) & (work_df['Application Type (ID)'].isin(sel_ma_types))]
                analysis_df = analysis_df[(analysis_df['Year'].isin(ma_years)) & (analysis_df['Application Type (ID)'].isin(sel_ma_types))]
                
                if not work_df.empty:
                    f_range = pd.date_range(start=f"{min(ma_years)}-01-01", end=f"{max(ma_years)}-12-31", freq='MS')
                    t_counts = analysis_df.groupby(['Arrival_Month', 'Application Type (ID)']).size().reset_index(name='N')
                    t_pivot = t_counts.pivot(index='Arrival_Month', columns='Application Type (ID)', values='N').fillna(0)
                    t_ma = t_pivot.reindex(f_range, fill_value=0).rolling(window=12, min_periods=1).sum()
                    fig = go.Figure()
                    for col in t_ma.columns:
                        fig.add_trace(go.Scatter(x=t_ma.index, y=t_ma[col], mode='lines', line=dict(shape='spline', width=3), name=f'Type: {col}', fill='tozeroy'))
                    
                    fig.add_vline(x=c18.timestamp() * 1000, line_width=2, line_dash="dash", line_color="#F59E0B")
                    fig.add_vline(x=c30.timestamp() * 1000, line_width=2, line_dash="dash", line_color="#EF4444")
                    st.plotly_chart(fix_chart(fig), use_container_width=True)
                else: st.warning("Insufficient data.")

            with tabs[6]:
                sel_yr_m = st.selectbox("Choose Year:", sorted(df_f['Year'].unique(), reverse=True), key="m_tab_sel")
                yr_data = df_f[df_f['Year'] == sel_yr_m]
                m_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                counts = yr_data.groupby('Month_Name').size().reindex(m_order, fill_value=0).reset_index(name='Apps')
                fig = px.bar(counts, x='Month_Name', y='Apps', text='Apps', height=600)
                st.plotly_chart(fix_chart(fig), use_container_width=True)

            with tabs[7]:
                st.markdown("### IPC Growth Histogram (Filing Date)")
                u_ipc_list = sorted(df_exp_f['IPC_Class3'].unique())
                a_yrs_hist = sorted(df_exp_f['Year'].unique())
                hc1, hc2 = st.columns(2)
                with hc1:
                    a_ipc_trig = st.checkbox("SELECT ALL IPC")
                    s_ipc_hist = st.multiselect("Select IPC Classes:", u_ipc_list, default=u_ipc_list[:3] if not a_ipc_trig else u_ipc_list)
                with hc2:
                    h_yrs_input = st.text_input("Type Years for IPC Histogram:", value=", ".join(map(str, a_yrs_hist)))
                    h_yrs = parse_year_input(h_yrs_input, a_yrs_hist)
                if s_ipc_hist and h_yrs:
                    h_data = df_exp_f[(df_exp_f['IPC_Class3'].isin(s_ipc_hist)) & (df_exp_f['Year'].isin(h_yrs))]
                    h_growth = h_data.groupby(['Year', 'IPC_Class3']).size().reset_index(name='Apps')
                    fig_h = px.bar(h_growth, x='Year', y='Apps', color='IPC_Class3', barmode='group', text='Apps', height=600)
                    fig_h = apply_year_axis_formatting(fig_h)
                    st.plotly_chart(fix_chart(fig_h), use_container_width=True)
                    st.dataframe(h_growth.pivot(index='IPC_Class3', columns='Year', values='Apps').fillna(0).astype(int), use_container_width=True)
        else:
            st.error("No valid data found.")
