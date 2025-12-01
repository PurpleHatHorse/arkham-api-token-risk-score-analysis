import streamlit as st
import pandas as pd
import os
import glob
import re
from datetime import datetime

# --- CONFIGURATION ---
# Path to your data folder. Change this if your folder structure is different.
DATA_FOLDER = 'outputs/risk_score_analysis'

st.set_page_config(
    page_title="Token Risk Analysis Dashboard",
    page_icon="🛡️",
    layout="wide"
)

# --- HELPER FUNCTIONS ---

def parse_filename(filename):
    """
    Parses filenames like 'TRUMP_risk_analysis_20251130_230334.csv'
    Returns: (token_name, date_str, file_type)
    """
    # Regex to capture Token, Type (analysis/report), and Date
    # Matches: <Token>_risk_<type>_<date>.<ext>
    match = re.search(r'(.+)_risk_(analysis|report)_(\d{8}_\d{6})\.(csv|txt)', filename)
    if match:
        return match.group(1), match.group(3), match.group(2)
    return None, None, None

def get_available_data(folder_path):
    """
    Scans the folder and groups files by Token and Date.
    Returns a dictionary: { 'Token': { 'Date': { 'csv': path, 'txt': path } } }
    """
    data_map = {}
    
    if not os.path.exists(folder_path):
        return data_map

    files = os.listdir(folder_path)
    
    for f in files:
        token, date_str, ftype = parse_filename(f)
        if token and date_str:
            if token not in data_map:
                data_map[token] = {}
            if date_str not in data_map[token]:
                data_map[token][date_str] = {}
            
            full_path = os.path.join(folder_path, f)
            data_map[token][date_str][ftype] = full_path
            
    print (data_map)
    return data_map

def parse_risk_report(file_path):
    """
    Parses the .txt report file to extract key metrics using Regex.
    """
    metrics = {
        'global_health': 0.0,
        'global_risk': 0.0,
        'concentration_risk': 0.0,
        'bot_risk': 0.0,
        'wash_trading_risk': 0.0,
        'dist_critical': 0,
        'dist_high': 0,
        'dist_medium': 0,
        'dist_low': 0
    }
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
            # Extract Global Scores
            health_match = re.search(r'TOKEN GLOBAL HEALTH SCORE:\s*([\d\.]+)', content)
            if health_match: metrics['global_health'] = float(health_match.group(1))
            
            risk_match = re.search(r'Global Risk Score:\s*([\d\.]+)', content)
            if risk_match: metrics['global_risk'] = float(risk_match.group(1))
            
            # Extract Breakdown
            conc_match = re.search(r'Concentration Risk:\s*([\d\.]+)', content)
            if conc_match: metrics['concentration_risk'] = float(conc_match.group(1))
            
            bot_match = re.search(r'Bot Activity Risk:\s*([\d\.]+)', content)
            if bot_match: metrics['bot_risk'] = float(bot_match.group(1))
            
            wash_match = re.search(r'Wash Trading Risk:\s*([\d\.]+)', content)
            if wash_match: metrics['wash_trading_risk'] = float(wash_match.group(1))
            
            # Extract Distribution Counts
            crit_match = re.search(r'CRITICAL\s*:\s*(\d+)\s*wallets', content)
            if crit_match: metrics['dist_critical'] = int(crit_match.group(1))
            
            high_match = re.search(r'HIGH\s*:\s*(\d+)\s*wallets', content)
            if high_match: metrics['dist_high'] = int(high_match.group(1))
            
            med_match = re.search(r'MEDIUM\s*:\s*(\d+)\s*wallets', content)
            if med_match: metrics['dist_medium'] = int(med_match.group(1))
            
            low_match = re.search(r'LOW\s*:\s*(\d+)\s*wallets', content)
            if low_match: metrics['dist_low'] = int(low_match.group(1))
        
    except Exception as e:
        st.error(f"Error parsing text report: {e}")
        
    return metrics

def load_csv_data(file_path):
    """
    Loads the CSV data and prepares it for the Top 10 table.
    """
    try:
        df = pd.read_csv(file_path)
        # Ensure numeric for sorting
        df['risk_score'] = pd.to_numeric(df['risk_score'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return pd.DataFrame()

# --- MAIN UI LAYOUT ---

st.title("🛡️ Token Risk Analysis Dashboard")

# 1. SCANNING & SELECTION
data_tree = get_available_data(DATA_FOLDER)
tokens = list(data_tree.keys())

if not tokens:
    st.warning(f"No data files found in folder: `{DATA_FOLDER}`. Please ensure your files follow the naming convention: `<Token>_risk_<type>_<date>.<ext>`")
    st.stop()

# Sidebar controls
with st.sidebar:
    st.header("Configuration")
    selected_token = st.selectbox("Select Token", tokens)
    
    # Get dates for selected token
    dates = list(data_tree[selected_token].keys())
    # Sort dates descending (newest first)
    dates.sort(reverse=True)
    
    selected_date = st.selectbox("Select Analysis Date", dates)
    
    files = data_tree[selected_token][selected_date]
    
    st.markdown("---")
    st.markdown("### Files Detected")
    st.caption(f"Report: {'✅ Found' if files['report'] else '❌ Missing'}")
    st.caption(f"Data: {'✅ Found' if files['analysis'] else '❌ Missing'}")

# Load Data
report_metrics = {}
csv_df = pd.DataFrame()

if files['report']:
    report_metrics = parse_risk_report(files['report'])
else:
    st.error("Text report file missing for this selection.")

if files['analysis']:
    csv_df = load_csv_data(files['analysis'])
else:
    st.error("CSV analysis file missing for this selection.")


# 2. METRIC CARDS (MATRIX VIEW)
if report_metrics:
    st.subheader(f"Analysis for {selected_token}")
    
    # Row 1: Global Health & Risk (Big Impact)
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="Token Global Health Score (Higher is Better)", 
            value=f"{report_metrics['global_health']}/100",
            delta=None,
            help="Overall health rating of the token ecosystem."
        )
    with col2:
        st.metric(
            label="Global Risk Score (Lower is Better)", 
            value=f"{report_metrics['global_risk']}/100",
            delta_color="inverse", # Red is bad (high number)
            help="Aggregated risk score based on all factors."
        )
    
    st.markdown("---")

    # Row 2: Risk Breakdown (Matrix of 3)
    st.markdown("### 📊 Risk Breakdown")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.metric("Concentration Risk", f"{report_metrics['concentration_risk']}/100")
    with c2:
        st.metric("Bot Activity Risk", f"{report_metrics['bot_risk']}/100")
    with c3:
        st.metric("Wash Trading Risk", f"{report_metrics['wash_trading_risk']}/100")

    st.markdown("---")
    
    # Row 3: Risk Distribution Chart
    st.markdown("### 📈 Risk Distribution")
    
    # Create a simple DataFrame for the bar chart
    dist_data = pd.DataFrame({
        'Risk Level': ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
        'Wallets': [
            report_metrics['dist_critical'],
            report_metrics['dist_high'],
            report_metrics['dist_medium'],
            report_metrics['dist_low']
        ]
    })
    
    # Using columns to put chart next to summary
    chart_col, stat_col = st.columns([2, 1])
    
    with chart_col:
        st.bar_chart(dist_data.set_index('Risk Level'))
        
    with stat_col:
        st.write(" **Wallet Counts**")
        st.write(f"🔴 Critical: {report_metrics['dist_critical']}")
        st.write(f"🟠 High: {report_metrics['dist_high']}")
        st.write(f"🟡 Medium: {report_metrics['dist_medium']}")
        st.write(f"🟢 Low: {report_metrics['dist_low']}")

# 3. TOP 10 WALLETS TABLE
if not csv_df.empty:
    st.markdown("---")
    st.subheader("🚨 Top 10 Highest Risk Wallets")
    
    # Filter/Sort logic
    # Assuming 'risk_score' exists based on user prompt snippet
    # If columns are slightly different, adjust here
    cols_to_show = ['wallet', 'risk_score', 'risk_level', 'bot_classification', 'wash_trading_flags']
    
    # Handle missing columns gracefully
    available_cols = [c for c in cols_to_show if c in csv_df.columns]
    
    # Sort by risk_score descending
    top_10 = csv_df.sort_values(by='risk_score', ascending=False).head(10)
    
    # Styling the dataframe (highlighting high risk)
    st.dataframe(
        top_10[available_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "risk_score": st.column_config.ProgressColumn(
                "Risk Score",
                help="Risk score from 0 to 100",
                format="%f",
                min_value=0,
                max_value=100,
            ),
             "wallet": "Wallet Address"
        }
    )