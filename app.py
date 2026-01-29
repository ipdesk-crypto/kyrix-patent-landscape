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
    }
    </style>
    """, unsafe_allow_html=True)

def fix_chart(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#F1F5F9"),
        xaxis=dict(gridcolor="#1E293B", linecolor="#334155"),
        yaxis=dict(gridcolor="#1E293B", linecolor="#334155"),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            itemclick="toggle",
            itemdoubleclick="toggleothers"
        )
    )
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
        st.markdown("<h3 style='color:white;'>KYRIX INTANGIBLE PATENT LANDSCAPE</h3>", unsafe_allow_html=True)
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
            with st.expander("Show All Other Columns"):
                for col in df_search.columns:
                    if col not in other_fields and col not in ['Abstract in English', 'Title in English']:
                        val = st.text_input(col, key=f"ex_{col}")
                        if val: field_filters[col] = val
        else:
            st.markdown("### ANALYTICS FILTERS")
            all_types = sorted(df_main['Application Type (ID)'].unique())
            selected_types = st.multiselect("Select Application Types:", all_types, default=all_types)
            df_f = df_main[df_main['Application Type (ID)'].isin(selected_types)]
            df_exp_f = df_exp[df_exp['Application Type (ID)'].isin(selected_types)]
            st.success(f"Records Analyzed: {len(df_f)}")

        if st.button("RESET SYSTEM"): st.rerun()

    # --- 5. MODE: SEARCH ENGINE ---
    if app_mode == "Intelligence Search":
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
                            <b>Date:</b> {row['Application Date']}
                        </div>
                        <div class="patent-snippet">{row['Abstract in English']}</div>
                    </div>
                    """, unsafe_allow_html=True)

        with tab_grid:
            st.dataframe(res, use_container_width=True, hide_index=True)
        
        with tab_dossier:
            if res.empty: st.info("No records.")
            else:
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
        st.markdown('<div class="metric-badge">STRATEGIC LANDSCAPE ENGINE</div>', unsafe_allow_html=True)
        tabs = st.tabs(["APPLICATION GROWTH", "Firm Intelligence", "Firm Tech-Strengths", "STRATEGIC MAP", "IPC Classification", "Moving Averages", "Monthly Filing", "IPC Growth Histogram"])

        with tabs[0]:
            st.markdown("### 📊 Application Growth Intelligence")
            
            c1, c2, c3 = st.columns([1.5, 1, 1])
            all_years_growth = sorted(df_f['Year'].unique())
            
            with c1:
                year_filter_mode = st.radio("Year Selection Mode:", ["Specific Years", "Year Range"], horizontal=True)
                if year_filter_mode == "Specific Years":
                    sel_all_years_growth = st.checkbox("Select All Years", value=True)
                    sel_years_growth = st.multiselect("Choose Years:", all_years_growth, default=all_years_growth if sel_all_years_growth else [all_years_growth[-1]])
                else:
                    year_range = st.slider("Select Year Range:", int(min(all_years_growth)), int(max(all_years_growth)), (int(min(all_years_growth)), int(max(all_years_growth))))
                    sel_years_growth = list(range(year_range[0], year_range[1] + 1))
            
            with c2:
                all_types_growth = sorted(df_f['Application Type (ID)'].unique())
                sel_types_growth = st.multiselect("Filter Application Types:", all_types_growth, default=all_types_growth)
            
            df_growth_filtered = df_f[df_f['Year'].isin(sel_years_growth) & df_f['Application Type (ID)'].isin(sel_types_growth)]
            
            if not df_growth_filtered.empty:
                growth_year = df_growth_filtered.groupby(['Year', 'Application Type (ID)']).size().reset_index(name='Count')
                fig_year = px.bar(growth_year, x='Year', y='Count', color='Application Type (ID)', barmode='group', text='Count', title="Annual Application Volume (Histogram)")
                st.plotly_chart(fix_chart(fig_year), use_container_width=True)
                
                st.markdown("---")
                growth_month_timeline = df_growth_filtered.groupby(['Arrival_Month', 'Application Type (ID)']).size().reset_index(name='Count')
                fig_month = px.bar(growth_month_timeline, x='Arrival_Month', y='Count', color='Application Type (ID)', barmode='stack', text='Count', title="Monthly Distribution (Histogram)")
                fig_month.update_xaxes(dtick="M1", tickformat="%b\n%Y")
                st.plotly_chart(fix_chart(fig_month), use_container_width=True)

                st.subheader("Monthly Distribution Summary Matrix")
                m_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                monthly_matrix = df_growth_filtered.groupby([df_growth_filtered['Arrival_Month'].dt.year.rename('Year'), df_growth_filtered['Arrival_Month'].dt.month_name().rename('Month')]).size().unstack(fill_value=0)
                existing_months = [m for m in m_order if m in monthly_matrix.columns]
                monthly_matrix = monthly_matrix[existing_months]
                st.dataframe(monthly_matrix, use_container_width=True)

                st.subheader("Growth Summary Table")
                st.dataframe(growth_year.pivot(index='Year', columns='Application Type (ID)', values='Count').fillna(0).astype(int), use_container_width=True)
            else:
                st.warning("No data found for the selected filters.")

        with tabs[1]:
            df_firms_only = df_f[df_f['Firm'] != "DIRECT FILING"]
            all_firms = sorted(df_firms_only['Firm'].unique())
            top_firms_list = df_firms_only['Firm'].value_counts().nlargest(10).index.tolist()
            available_years = sorted(df_firms_only['Year'].unique(), reverse=True)
            
            c1, c2 = st.columns([1,1])
            with c1:
                sel_all_firms = st.checkbox("Select All Firms", key="all_firms_check")
                selected_firms = st.multiselect("Select Firms:", all_firms, default=top_firms_list[:5] if not sel_all_firms else all_firms)
                if sel_all_firms: selected_firms = all_firms
            with c2:
                sel_all_years = st.checkbox("Select All Years", value=True, key="all_years_check_firm")
                selected_years = st.multiselect("Select Years:", available_years, default=available_years if sel_all_years else [available_years[0]])
                if sel_all_years: selected_years = available_years

            if selected_firms and selected_years:
                firm_sub = df_firms_only[(df_firms_only['Firm'].isin(selected_firms)) & (df_firms_only['Year'].isin(selected_years))]
                st.markdown("### Firm Rank by Application Volume")
                st.dataframe(firm_sub['Firm'].value_counts().reset_index().rename(columns={'count':'Total Apps'}), use_container_width=True, hide_index=True)
                firm_growth = firm_sub.groupby(['Year', 'Firm']).size().reset_index(name='Apps')
                fig = px.line(firm_growth, x='Year', y='Apps', color='Firm', markers=True, height=600)
                st.plotly_chart(fix_chart(fig), use_container_width=True)
                st.subheader("Firm Annual Volume Matrix")
                st.dataframe(firm_sub.groupby(['Firm', 'Year']).size().unstack(fill_value=0), use_container_width=True)

        with tabs[2]:
            df_exp_firms_only = df_exp_f[df_exp_f['Firm'] != "DIRECT FILING"]
            if 'selected_firms' in locals() and selected_firms:
                firm_ipc = df_exp_firms_only[df_exp_firms_only['Firm'].isin(selected_firms)].groupby(['Firm', 'IPC_Class3']).size().reset_index(name='Count')
                fig = px.bar(firm_ipc, x='Count', y='Firm', color='IPC_Class3', orientation='h', height=600)
                st.plotly_chart(fix_chart(fig), use_container_width=True)
                st.subheader("Tech-Class Distribution per Firm")
                st.dataframe(firm_ipc.pivot(index='Firm', columns='IPC_Class3', values='Count').fillna(0).astype(int), use_container_width=True)

        with tabs[3]:
            land_data = df_exp_f.groupby(['IPC_Section', 'IPC_Class3']).agg({'Application Number':'count', 'Firm':'nunique'}).reset_index()
            fig = px.scatter(land_data, x='IPC_Section', y='IPC_Class3', size='Application Number', color='Firm', height=600)
            st.plotly_chart(fix_chart(fig), use_container_width=True)
            st.subheader("IPC Class Strategic Density")
            st.dataframe(land_data.rename(columns={'Application Number': 'Total Apps', 'Firm': 'Unique Agents'}).sort_values('Total Apps', ascending=False), use_container_width=True, hide_index=True)

        with tabs[4]:
            ipc_counts = df_exp_f.groupby('IPC_Section').size().reset_index(name='Count').sort_values('IPC_Section')
            fig = px.bar(ipc_counts, x='IPC_Section', y='Count', color='IPC_Section', text='Count', height=600)
            st.plotly_chart(fix_chart(fig), use_container_width=True)

        with tabs[5]:
            most_recent_date = df_main['AppDate'].max()
            date_str = most_recent_date.strftime('%d %B %Y') if pd.notnull(most_recent_date) else "N/A"
            st.markdown(f'<div class="metric-badge" style="padding:10px 20px; font-size:16px;">Most Recent Filing Date in Database: {date_str}</div>', unsafe_allow_html=True)
            
            unique_3char = sorted(df_exp_f['IPC_Class3'].unique())
            all_av_years = sorted(df_f['Year'].unique())
            c1, c2, c3 = st.columns(3)
            with c1: target_ipc = st.selectbox("IPC Class (3-Digit):", ["ALL IPC"] + unique_3char, key="ma_ipc")
            with c2:
                sel_all_ma_years = st.checkbox("Select All Years", value=True, key="all_years_ma")
                ma_years = st.multiselect("Years Range:", all_av_years, default=all_av_years if sel_all_ma_years else [all_av_years[-1]])
                if sel_all_ma_years: ma_years = all_av_years
            with c3:
                all_available_types = sorted(df_f['Application Type (ID)'].unique())
                selected_ma_types = st.multiselect("Visible Application Types:", all_available_types, default=all_available_types)

            analysis_df = df_exp_f.copy() if target_ipc == "ALL IPC" else df_exp_f[df_exp_f['IPC_Class3'] == target_ipc]
            work_df = df_f.copy() if target_ipc == "ALL IPC" else df_f[df_f['Application Number'].isin(analysis_df['Application Number'].unique())]
            work_df = work_df[(work_df['Year'].isin(ma_years)) & (work_df['Application Type (ID)'].isin(selected_ma_types))]
            analysis_df = analysis_df[(analysis_df['Year'].isin(ma_years)) & (analysis_df['Application Type (ID)'].isin(selected_ma_types))]

            if not work_df.empty:
                full_range = pd.date_range(start=f"{min(ma_years)}-01-01", end=f"{max(ma_years)}-12-31", freq='MS')
                type_counts = analysis_df.groupby(['Priority_Month', 'Application Type (ID)']).size().reset_index(name='N')
                type_pivot = type_counts.pivot(index='Priority_Month', columns='Application Type (ID)', values='N').fillna(0)
                type_ma = type_pivot.reindex(full_range, fill_value=0).rolling(window=12, min_periods=1).sum()
                
                fig = go.Figure()
                for col_name in type_ma.columns:
                    fig.add_trace(go.Scatter(x=type_ma.index, y=type_ma[col_name], mode='lines+markers', name=f'Type: {col_name}', showlegend=True))
                
                current_time = datetime.now()
                cutoff_18 = current_time - pd.DateOffset(months=18)
                cutoff_30 = current_time - pd.DateOffset(months=30)
                
                fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', line=dict(color="#F59E0B", dash="dash", width=2), name="18-Month Lag (Types 4/5)"))
                fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', line=dict(color="#EF4444", dash="dash", width=2), name="30-Month Lag (Type 1)"))
                fig.add_vline(x=cutoff_18.timestamp() * 1000, line_width=2, line_dash="dash", line_color="#F59E0B")
                fig.add_vline(x=cutoff_30.timestamp() * 1000, line_width=2, line_dash="dash", line_color="#EF4444")

                fig.update_layout(title="Moving Annual Total (Integral per 12-Month Window) by Earliest Priority", showlegend=True, legend=dict(title="Legend"), xaxis_title="Priority Date Timeline")
                st.plotly_chart(fix_chart(fig), use_container_width=True)
                
                # --- NEW: AUTOMATED SMALL REPORT SECTION ---
                st.markdown(f"""
                <div class="report-box">
                    <h4 style="color:#F59E0B; margin-top:0;">📋 PUBLICATION LAG INTELLIGENCE REPORT</h4>
                    <p style="font-size:14px; color:#CBD5E1;">Based on the real-time date of <b>{current_time.strftime('%d %B %Y')}</b>, the following legal cutoffs apply to the data visibility above:</p>
                    <table style="width:100%; border-collapse: collapse; margin-top:10px;">
                        <tr style="border-bottom: 1px solid #1E293B;">
                            <th style="text-align:left; padding:8px; color:#94A3B8;">APPLICATION TYPE</th>
                            <th style="text-align:left; padding:8px; color:#94A3B8;">LAG PERIOD</th>
                            <th style="text-align:left; padding:8px; color:#94A3B8;">CRITICAL CUTOFF DATE</th>
                            <th style="text-align:left; padding:8px; color:#94A3B8;">STATUS</th>
                        </tr>
                        <tr>
                            <td style="padding:8px; font-weight:bold;">Type 4 & 5 (Utility/Design)</td>
                            <td style="padding:8px;">18 Months</td>
                            <td style="padding:8px; color:#F59E0B; font-weight:bold;">{cutoff_18.strftime('%d %B %Y')}</td>
                            <td style="padding:8px; font-size:12px;">Data after this date is likely incomplete due to 18-month publication secrecy.</td>
                        </tr>
                        <tr>
                            <td style="padding:8px; font-weight:bold;">Type 1 (Invention)</td>
                            <td style="padding:8px;">30 Months</td>
                            <td style="padding:8px; color:#EF4444; font-weight:bold;">{cutoff_30.strftime('%d %B %Y')}</td>
                            <td style="padding:8px; font-size:12px;">Data after this date is incomplete for Invention patents (Standard PCT/National lag).</td>
                        </tr>
                    </table>
                    <p style="font-size:12px; color:#64748B; margin-top:15px;"><i>*This report updates automatically every 24 hours to maintain landscape accuracy.</i></p>
                </div>
                """, unsafe_allow_html=True)
            else: st.warning("Insufficient data.")

        with tabs[6]:
            sel_year = st.selectbox("Choose Year:", sorted(df_f['Year'].unique(), reverse=True))
            yr_data = df_f[df_f['Year'] == sel_year]
            m_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            counts = yr_data.groupby('Month_Name').size().reindex(m_order, fill_value=0).reset_index(name='Apps')
            fig = px.bar(counts, x='Month_Name', y='Apps', text='Apps', height=600)
            st.plotly_chart(fix_chart(fig), use_container_width=True)

        with tabs[7]:
            st.markdown("### IPC Growth Histogram")
            unique_ipc_list = sorted(df_exp_f['IPC_Class3'].unique())
            all_av_years_hist = sorted(df_exp_f['Year'].unique())
            hc1, hc2 = st.columns(2)
            with hc1:
                all_ipc_trigger = st.checkbox("SELECT ALL IPC IN HISTOGRAM", value=False)
                selected_ipc_hist = st.multiselect("Select IPC Classes:", unique_ipc_list, default=unique_ipc_list[:3] if not all_ipc_trigger else unique_ipc_list)
            with hc2:
                sel_all_hist_years = st.checkbox("Select All Years", value=True, key="all_years_hist")
                hist_years = st.multiselect("Select Years:", all_av_years_hist, default=all_av_years_hist if sel_all_hist_years else [all_av_years_hist[-1]])
            if selected_ipc_hist and hist_years:
                hist_data = df_exp_f[(df_exp_f['IPC_Class3'].isin(selected_ipc_hist)) & (df_exp_f['Year'].isin(hist_years))]
                hist_growth = hist_data.groupby(['Year', 'IPC_Class3']).size().reset_index(name='Apps')
                fig_hist = px.bar(hist_growth, x='Year', y='Apps', color='IPC_Class3', barmode='group', text='Apps', height=600)
                st.plotly_chart(fix_chart(fig_hist), use_container_width=True)
                st.dataframe(hist_growth.pivot(index='IPC_Class3', columns='Year', values='Apps').fillna(0).astype(int), use_container_width=True)
