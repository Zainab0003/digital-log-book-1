import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="BatchMaster Pro Enterprise", layout="wide", page_icon="🏢")

# 2. Main Title (Orange as per your design preference)
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
    "Pharmacognosy Lab"
]
selected_site = st.sidebar.selectbox("Select Laboratory / Site", lab_names)

st.sidebar.divider()

# 4. Sidebar - Excel/CSV File Uploader
st.sidebar.header("📂 Bulk Data Upload")
st.sidebar.caption("Upload annual budget for Chemicals, Glassware & Instruments via Excel/CSV.")
uploaded_file = st.sidebar.file_uploader("Choose file", type=["xlsx", "xls", "csv"])
if uploaded_file is not None:
    st.sidebar.success("✅ File loaded! Ready for database sync.")

# --- DUMMY DATA (Includes Categories and Labs for Filtering) ---
data = {
    'Item Name': ['Ethanol 95%', 'Glass Beakers (250ml)', 'Sulfuric Acid', 'Petri Dishes', 'HPLC Vials', 'Microscope', 'pH Meter', 'Sodium Chloride'],
    'Category': ['Chemical', 'Glassware', 'Chemical', 'Glassware', 'Glassware', 'Instrument', 'Instrument', 'Chemical'],
    'Lab': ['Chemistry Lab 1', 'Pharmaceutics Lab', 'Chemistry Lab 2', 'Micro Lab', 'BMS Lab', 'Micro Lab', 'Industrial Pharmacy Lab', 'Pharmacognosy Lab'],
    'Total Budget Qty': [1000, 500, 200, 2000, 5000, 5, 10, 800],
    'Issued Qty': [200, 380, 150, 500, 1000, 1, 2, 600],
}
df = pd.DataFrame(data)
df['Remaining Stock'] = df['Total Budget Qty'] - df['Issued Qty']
df['Stock Percentage'] = (df['Remaining Stock'] / df['Total Budget Qty']) * 100

# Apply Filter based on selected Lab
if selected_site != "All Labs":
    df = df[df['Lab'] == selected_site]

# --- KPI CARDS (Makes it a true Dashboard) ---
st.markdown("### 🎯 Key Performance Indicators")
col1, col2, col3, col4 = st.columns(4)

total_items = len(df)
total_budget_qty = df['Total Budget Qty'].sum()
total_remaining = df['Remaining Stock'].sum()
critical_items = len(df[df['Stock Percentage'] <= 30])

col1.metric("Total Item Categories", total_items)
col2.metric("Total Budgeted Quantity", f"{total_budget_qty:,}")
col3.metric("Available Stock Quantity", f"{total_remaining:,}")
col4.metric("⚠️ Critical Alerts (<30%)", critical_items)

st.write("") # Spacing

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
    
    # Safe Plotly implementation (No gridlines, Orange title)
    fig = px.bar(df, x='Item Name', y=['Total Budget Qty', 'Remaining Stock'], 
                 barmode='group', 
                 title=f"Current Stock vs Total Budget - {selected_site}")
    
    fig.update_layout(
        title_font_color="orange",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text='Quantity Status'
    )
    # use_container_width=True is perfectly safe and recommended for st.plotly_chart
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: INVENTORY & PROCUREMENT ---
with tab2:
    st.markdown("### 📦 Lab Indent & Log Register")
    st.write("Live database records of chemicals, glassware, and instruments.")
    
    # Using st.dataframe instead of st.table. use_container_width=True is safe here.
    st.dataframe(df[['Item Name', 'Category', 'Total Budget Qty', 'Remaining Stock', 'Stock Percentage']], use_container_width=True, hide_index=True)
    
    st.divider()
    st.markdown("#### 📝 Quick Log Entry (Manual Issue)")
    col_a, col_b, col_c = st.columns([2, 1, 1])
    with col_a:
        st.selectbox("Select Item for Issue", df['Item Name'])
    with col_b:
        st.number_input("Quantity to Deduct", min_value=1)
    with col_c:
        st.write("") # Spacing
        st.write("")
        st.button("Record Consumption", type="primary", use_container_width=True)

# --- TAB 3: NOTIFICATION CENTER ---
with tab3:
    st.markdown("### 🔔 Automated Alerts (30% Threshold)")
    st.write("System automatically detects items below 30% and triggers purchase demand.")
    
    # Alert Logic
    alerts_found = False
    for index, row in df.iterrows():
        if row['Stock Percentage'] <= 30:
            st.error(f"🚨 **CRITICAL ALERT:** {row['Item Name']} is at {row['Stock Percentage']:.1f}% capacity! Auto-email dispatched to Store Manager.")
            alerts_found = True
        elif row['Stock Percentage'] <= 50:
            st.warning(f"⚠️ **WARNING:** {row['Item Name']} is at {row['Stock Percentage']:.1f}%. Keep an eye on consumption.")
            alerts_found = True
            
    if not alerts_found:
        st.success("✅ All items in the selected laboratory are well above the safety threshold.")

# --- TAB 4: COMPLIANCE & AUDIT ---
with tab4:
    st.markdown("### 🛡️ Audit Trail (ALCOA+ & 21 CFR Part 11)")
    st.write("Immutable log of all transactions to ensure complete data integrity.")
    
    audit_data = pd.DataFrame({
        "Timestamp": ["2026-07-03 08:15 AM", "2026-07-03 09:30 AM", "2026-07-03 10:45 AM"],
        "User": ["Admin", "Lab Assistant", "QC Manager"],
        "Action": ["Uploaded Annual Budget Excel", "Issued 20 Beakers", "Approved replacement indent"],
        "Module": ["Master Data", "Inventory", "Procurement"]
    })
    
    # Using st.dataframe for safety and a clean look
    st.dataframe(audit_data, use_container_width=True, hide_index=True)
