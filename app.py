import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="BatchMaster Pro Enterprise", layout="wide", page_icon="🏢")

# Custom CSS for Attractive KPI Cards (Matching Chart Colors)
st.markdown("""
<style>
.kpi-card {
    background-color: #f0f8ff; /* Light Blue Background */
    border-left: 6px solid #1f77b4; /* Dark Blue Border */
    padding: 20px;
    border-radius: 8px;
    box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}
.kpi-title { font-size: 16px; color: #555; font-weight: bold; margin-bottom: 5px; }
.kpi-value { font-size: 28px; font-weight: bold; color: #1f77b4; }
.kpi-alert { border-left: 6px solid #ff4b4b; background-color: #ffeeee; }
.kpi-alert-val { color: #ff4b4b; }
</style>
""", unsafe_allow_html=True)

# 2. Main Title
st.markdown("<h1 style='color: orange; text-align: center;'>BatchMaster Pro Enterprise V5</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Phase 2: Interactive Dashboard & Digital Logbook</p>", unsafe_allow_html=True)
st.divider()

# 3. Sidebar - Lab Selection Filter
st.sidebar.header("🌐 Global Access")
lab_names = [
    "All Labs", 
    "Pharmaceutics Lab", 
    "BMS Lab", 
    "Industrial Pharmacy Lab", 
    "Chemistry Lab 1", 
    "Chemistry Lab 2", 
    "Micro Lab", 
    "Pharmacognosy Lab",
    "Animal House" # Newly Added Lab
]
selected_site = st.sidebar.selectbox("Select Laboratory / Site", lab_names)

st.sidebar.divider()

# 4. Sidebar - Excel/CSV File Uploader
st.sidebar.header("📂 Bulk Data Upload")
st.sidebar.caption("Upload annual budget for Chemicals, Glassware & Live Animals via Excel/CSV.")
uploaded_file = st.sidebar.file_uploader("Choose file", type=["xlsx", "xls", "csv"])
if uploaded_file is not None:
    st.sidebar.success("✅ File loaded! Ready for database sync.")

# --- DUMMY DATA (Includes Animal House Data) ---
data = {
    'Item Name': ['Ethanol 95%', 'Glass Beakers', 'Sulfuric Acid', 'Petri Dishes', 'White Mice', 'Wistar Rats', 'Rabbits', 'Microscope'],
    'Category': ['Chemical', 'Glassware', 'Chemical', 'Glassware', 'Live Animals', 'Live Animals', 'Live Animals', 'Instrument'],
    'Lab': ['Chemistry Lab 1', 'Pharmaceutics Lab', 'Chemistry Lab 2', 'Micro Lab', 'Animal House', 'Animal House', 'Animal House', 'Micro Lab'],
    'Total Budget Qty': [1000, 500, 200, 2000, 100, 50, 20, 5],
    'Issued Qty': [200, 380, 150, 500, 80, 10, 5, 1],
}
df = pd.DataFrame(data)
df['Remaining Stock'] = df['Total Budget Qty'] - df['Issued Qty']
df['Stock Percentage'] = (df['Remaining Stock'] / df['Total Budget Qty']) * 100

# Apply Filter based on selected Lab
if selected_site != "All Labs":
    df = df[df['Lab'] == selected_site]

# --- KPI CARDS (Attractive Custom HTML) ---
st.markdown("### 🎯 Key Performance Indicators")
total_items = len(df)
total_budget_qty = df['Total Budget Qty'].sum()
total_remaining = df['Remaining Stock'].sum()
critical_items = len(df[df['Stock Percentage'] <= 30])

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total Item Categories</div><div class='kpi-value'>{total_items}</div></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total Budgeted Quantity</div><div class='kpi-value'>{total_budget_qty:,}</div></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Available Stock Quantity</div><div class='kpi-value'>{total_remaining:,}</div></div>", unsafe_allow_html=True)
with col4:
    st.markdown(f"<div class='kpi-card kpi-alert'><div class='kpi-title'>⚠️ Critical Alerts (<30%)</div><div class='kpi-value kpi-alert-val'>{critical_items}</div></div>", unsafe_allow_html=True)

# --- CORE PLATFORM TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Executive Dashboard", 
    "📦 Inventory & Procurement", 
    "🔔 Notification Center", 
    "🛡️ Compliance & Audit"
])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.markdown("### 📈 Live Consumption & Budget Overview")
    
    # Chart colors matched with KPI cards
    fig = px.bar(df, x='Item Name', y=['Total Budget Qty', 'Remaining Stock'], 
                 barmode='group', 
                 color_discrete_sequence=['#1f77b4', '#87CEFA'], # Dark Blue & Light Blue
                 title=f"Current Stock vs Total Budget - {selected_site}")
    
    fig.update_layout(
        title_font_color="orange",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text='Quantity Status'
    )
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: INVENTORY & PROCUREMENT ---
with tab2:
    st.markdown("### 📦 Lab Indent & Log Register")
    st.dataframe(df[['Item Name', 'Category', 'Total Budget Qty', 'Remaining Stock', 'Stock Percentage']], use_container_width=True, hide_index=True)

# --- TAB 3: NOTIFICATION CENTER ---
with tab3:
    st.markdown("### 🔔 Automated Alerts (30% Threshold)")
    alerts_found = False
    for index, row in df.iterrows():
        if row['Stock Percentage'] <= 30:
            st.error(f"🚨 **CRITICAL ALERT:** {row['Item Name']} is at {row['Stock Percentage']:.1f}% capacity! Auto-email dispatched to Store Manager.")
            alerts_found = True
    if not alerts_found:
        st.success("✅ All items in the selected laboratory are well above the safety threshold.")

# --- TAB 4: COMPLIANCE & AUDIT ---
with tab4:
    st.markdown("### 🛡️ Audit Trail (ALCOA+ & 21 CFR Part 11)")
    audit_data = pd.DataFrame({
        "Timestamp": ["2026-07-03 08:15 AM", "2026-07-03 09:30 AM", "2026-07-03 10:45 AM"],
        "User": ["Admin", "Lab Assistant", "QC Manager"],
        "Action": ["Uploaded Annual Budget Excel", "Issued 5 White Mice", "Approved replacement indent"],
        "Module": ["Master Data", "Inventory", "Procurement"]
    })
    st.dataframe(audit_data, use_container_width=True, hide_index=True)
