import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import plotly.express as px

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("labtrack.db")
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS Items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT CHECK(category IN ('Chemicals', 'Glassware', 'Instruments')) NOT NULL, quantity REAL DEFAULT 0, unit TEXT NOT NULL, expiry_date DATE, is_quarantined BOOLEAN DEFAULT 0, is_deleted BOOLEAN DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER, transaction_type TEXT, quantity_changed REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, user_id INTEGER, FOREIGN KEY(item_id) REFERENCES Items(id))''')
    
    # INDENTS TABLE
    cursor.execute('''CREATE TABLE IF NOT EXISTS Indents (id INTEGER PRIMARY KEY AUTOINCREMENT, item_requested TEXT, quantity REAL, status TEXT DEFAULT 'Request', requested_by INTEGER, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute("PRAGMA table_info(Indents)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'indent_type' not in columns:
        cursor.execute("ALTER TABLE Indents ADD COLUMN indent_type TEXT DEFAULT 'New Demand'")
    if 'category' not in columns:
        cursor.execute("ALTER TABLE Indents ADD COLUMN category TEXT DEFAULT 'Chemicals'")

    # BREAKAGE TABLE
    cursor.execute('''CREATE TABLE IF NOT EXISTS Breakage (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER, user_id INTEGER, breakage_date DATE, reason TEXT, FOREIGN KEY(item_id) REFERENCES Items(id))''')
    cursor.execute("PRAGMA table_info(Breakage)")
    breakage_cols = [col[1] for col in cursor.fetchall()]
    if 'quantity' not in breakage_cols:
        cursor.execute("ALTER TABLE Breakage ADD COLUMN quantity REAL DEFAULT 0")

    # USERS & AUDIT LOG TABLES
    cursor.execute('''CREATE TABLE IF NOT EXISTS Users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, role TEXT CHECK(role IN ('Admin', 'HOD', 'Operator')) NOT NULL, is_active BOOLEAN DEFAULT 1)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS AuditLog (id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL, table_name TEXT NOT NULL, record_id INTEGER, changed_by TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    # Seed an default admin if Users table is empty
    cursor.execute("SELECT COUNT(*) FROM Users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO Users (username, role, is_active) VALUES ('admin_fops', 'Admin', 1)")

    conn.commit()
    conn.close()

# --- DATABASE HELPER FUNCTIONS ---
def log_audit(action, table_name, record_id, changed_by):
    conn = sqlite3.connect("labtrack.db")
    cursor = conn.cursor()
    cursor.execute('INSERT INTO AuditLog (action, table_name, record_id, changed_by) VALUES (?, ?, ?, ?)', 
                   (action, table_name, record_id, changed_by))
    conn.commit()
    conn.close()

def add_item(name, category, quantity, unit, expiry_date, operator):
    is_quarantined = 1 if expiry_date and expiry_date < str(date.today()) else 0
    conn = sqlite3.connect("labtrack.db")
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Items (name, category, quantity, unit, expiry_date, is_quarantined) VALUES (?, ?, ?, ?, ?, ?)', (name, category, quantity, unit, expiry_date, is_quarantined))
    last_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_audit(f"Added New Item: {name}", "Items", last_id, operator)

def get_all_items():
    conn = sqlite3.connect("labtrack.db")
    df = pd.read_sql_query("SELECT * FROM Items WHERE is_deleted=0", conn)
    conn.close()
    return df

def auto_update_quarantine():
    conn = sqlite3.connect("labtrack.db")
    cursor = conn.cursor()
    cursor.execute('UPDATE Items SET is_quarantined = 1 WHERE expiry_date < ? AND is_quarantined = 0 AND is_deleted = 0', (str(date.today()),))
    conn.commit()
    conn.close()

def process_transaction(item_id, item_name, transaction_type, input_qty, operator):
    conn = sqlite3.connect("labtrack.db")
    cursor = conn.cursor()
    actual_qty_change = abs(input_qty) if transaction_type == 'Stock In' else -abs(input_qty)
    cursor.execute('INSERT INTO Transactions (item_id, transaction_type, quantity_changed, user_id) VALUES (?, ?, ?, 1)', (item_id, transaction_type, actual_qty_change))
    cursor.execute('UPDATE Items SET quantity = quantity + ? WHERE id = ?', (actual_qty_change, item_id))
    last_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_audit(f"Posted {transaction_type} of {abs(input_qty)} units for {item_name}", "Transactions", last_id, operator)

def get_transactions():
    conn = sqlite3.connect("labtrack.db")
    query = '''SELECT t.id as Transaction_ID, i.name as Item_Name, i.category as Category, t.transaction_type as Type, t.quantity_changed as Qty_Change, i.unit as Unit, t.timestamp as Date FROM Transactions t JOIN Items i ON t.item_id = i.id ORDER BY t.timestamp DESC'''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def create_indent(item_requested, category, quantity, indent_type, operator):
    conn = sqlite3.connect("labtrack.db")
    cursor = conn.cursor()
    cursor.execute('INSERT INTO Indents (item_requested, category, quantity, indent_type, status, requested_by) VALUES (?, ?, ?, ?, \'Request\', 1)', (item_requested, category, quantity, indent_type))
    last_id = cursor.lastrowid
    conn.commit()
    conn.close()
    log_audit(f"Raised {indent_type} for {item_requested}", "Indents", last_id, operator)

def get_indents():
    conn = sqlite3.connect("labtrack.db")
    df = pd.read_sql_query("SELECT * FROM Indents ORDER BY timestamp DESC", conn)
    conn.close()
    return df

def update_indent_status(indent_id, item_name, new_status, operator):
    conn = sqlite3.connect("labtrack.db")
    cursor = conn.cursor()
    cursor.execute('UPDATE Indents SET status = ? WHERE id = ?', (new_status, indent_id))
    conn.commit()
    conn.close()
    log_audit(f"Shifted Indent status to [{new_status}] for {item_name}", "Indents", indent_id, operator)

def log_breakage(item_id, item_name, category, quantity, reason, operator):
    conn = sqlite3.connect("labtrack.db")
    cursor = conn.cursor()
    breakage_date = str(date.today())
    cursor.execute('INSERT INTO Breakage (item_id, user_id, breakage_date, reason, quantity) VALUES (?, 1, ?, ?, ?)', (item_id, breakage_date, reason, quantity))
    last_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    log_audit(f"Reported breakage/loss of {quantity} units for {item_name}", "Breakage", last_id, operator)
    process_transaction(item_id, item_name, 'Stock Out', quantity, operator)
    create_indent(f"{item_name} (Auto-Replacement)", category, quantity, "Replacement", operator)

def get_breakage_logs():
    conn = sqlite3.connect("labtrack.db")
    query = '''SELECT b.id as Breakage_ID, i.name as Item_Name, i.category as Category, b.quantity as Qty_Lost, i.unit as Unit, b.reason as Incident_Reason, b.breakage_date as Date FROM Breakage b JOIN Items i ON b.item_id = i.id ORDER BY b.breakage_date DESC'''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# --- ADMIN PANEL LOGIC ---
def add_user(username, role):
    try:
        conn = sqlite3.connect("labtrack.db")
        cursor = conn.cursor()
        cursor.execute('INSERT INTO Users (username, role) VALUES (?, ?)', (username, role))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def get_users():
    conn = sqlite3.connect("labtrack.db")
    df = pd.read_sql_query("SELECT * FROM Users", conn)
    conn.close()
    return df

def get_audit_logs():
    conn = sqlite3.connect("labtrack.db")
    df = pd.read_sql_query("SELECT id as Log_ID, action as Activity, table_name as Section, record_id as Row_ID, changed_by as Triggered_By, timestamp as Date_Time FROM AuditLog ORDER BY timestamp DESC", conn)
    conn.close()
    return df

# Helper Function for Category Tabs
def render_categorized_tabs(dataframe, highlight_func=None, subset_cols=None):
    if dataframe.empty:
        st.info("No data available.")
        return
    tab_chem, tab_glass, tab_inst = st.tabs(["🧪 Chemicals", "⚗️ Glassware", "🔬 Instruments"])
    cats = [("Chemicals", tab_chem), ("Glassware", tab_glass), ("Instruments", tab_inst)]
    for cat_name, tab in cats:
        with tab:
            df_cat = dataframe[dataframe['Category' if 'Category' in dataframe.columns else 'category'] == cat_name]
            if not df_cat.empty:
                if highlight_func:
                    st.dataframe(df_cat.style.applymap(highlight_func, subset=subset_cols) if subset_cols else df_cat.style.apply(highlight_func, axis=1), use_container_width=True, hide_index=True)
                else:
                    st.dataframe(df_cat, use_container_width=True, hide_index=True)
            else:
                st.caption(f"No {cat_name} records found.")


# --- STREAMLIT CONFIG & DESIGN ---
st.set_page_config(page_title="LabTrack Pro", layout="wide")

st.markdown("""
<style>
    .kpi-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        border-left: 5px solid #FF8C00;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 20px;
    }
    .kpi-title {
        color: #FF8C00;
        font-size: 16px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .kpi-value {
        font-size: 34px;
        font-weight: 800;
        color: #2c3e50;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

init_db()
auto_update_quarantine()

# --- SIDEBAR PANEL NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: #FF8C00;'>🧪 LabTrack Pro</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 13px;'>FOPS Inventory Panel</p>", unsafe_allow_html=True)
    st.divider()
    
    # SYSTEM SIMULATION USER SELECTOR
    df_current_users = get_users()
    user_list = df_current_users['username'].tolist() if not df_current_users.empty else ['admin_fops']
    current_active_user = st.selectbox("🔑 Active Session Operator", options=user_list)
    
    st.divider()
    menu_selection = st.radio("Navigation Menu", ["📦 Item Master", "🔄 Transactions Ledger", "📋 Indent Management", "💔 Breakage Register", "📊 Analytics Reports", "⚙️ Control Admin"])
    st.divider()
    st.caption("System Version: v1.7.0 (Stable Build)")
    st.caption("Environment: Python 3.11 | 4GB Target Optimized")

# --- TOP STATS CARDS ---
df_items = get_all_items()
total_resources = len(df_items) if not df_items.empty else 0
quarantined_count = len(df_items[df_items['is_quarantined'] == 1]) if not df_items.empty else 0
pending_indents = len(get_indents()[get_indents()['status'] == 'Request'])

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">Total Active Resources</div><div class="kpi-value">{total_resources}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">🚨 Quarantined Items</div><div class="kpi-value">{quarantined_count}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">📋 Pending Indents</div><div class="kpi-value">{pending_indents}</div></div>', unsafe_allow_html=True)

st.divider()

# --- MENU ROUTING ---

# 1. ITEM MASTER PAGE
if menu_selection == "📦 Item Master":
    st.title("📦 Item Master & Stock Entry")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Add New Resource")
        with st.form("add_item_form", clear_on_submit=True):
            name = st.text_input("Item Name")
            category = st.selectbox("Category", ["Chemicals", "Glassware", "Instruments"])
            num_col1, num_col2 = st.columns(2)
            with num_col1:
                quantity = st.number_input("Opening Quantity", min_value=0.0, step=1.0)
            with num_col2:
                unit = st.selectbox("Unit of Measure", ["mg", "g", "kg", "mL", "L", "pcs", "box"])
            has_expiry = st.checkbox("Item has an expiry date?")
            expiry_date = st.date_input("Expiry Date") if has_expiry else None
            
            if st.form_submit_button("Save Item"):
                if not name.strip() or quantity <= 0:
                    st.error("⚠️ Invalid inputs.")
                else:
                    expiry_str = expiry_date.strftime("%Y-%m-%d") if has_expiry else None
                    add_item(name, category, quantity, unit, expiry_str, current_active_user)
                    st.success(f"✅ '{name}' added successfully!")
                    st.rerun()

    with col2:
        st.subheader("Current Store Inventory (Categorized)")
        def highlight_quarantined(row):
            return ['background-color: #ffcccc'] * len(row) if row['is_quarantined'] == 1 else [''] * len(row)
        render_categorized_tabs(df_items, highlight_func=highlight_quarantined)

# 2. TRANSACTIONS PAGE
elif menu_selection == "🔄 Transactions Ledger":
    st.title("🔄 Inventory Audit Transactions")
    if df_items.empty:
        st.warning("⚠️ No items available.")
    else:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Post New Ledger Entry")
            with st.form("transaction_form", clear_on_submit=True):
                item_options = {f"{row['name']} ({row['category']} - Stock: {row['quantity']})": (row['id'], row['name']) for index, row in df_items.iterrows()}
                selected_item_display = st.selectbox("Select Item", options=list(item_options.keys()))
                trans_type = st.selectbox("Transaction Type", ["Stock In", "Stock Out", "Adjustment", "Transfer"])
                trans_qty = st.number_input("Quantity", step=1.0)
                
                if st.form_submit_button("Submit Transaction"):
                    if trans_qty == 0:
                        st.error("⚠️ Quantity cannot be 0.")
                    else:
                        selected_id, selected_name = item_options[selected_item_display]
                        process_transaction(selected_id, selected_name, trans_type, trans_qty, current_active_user)
                        st.success("✅ Ledger entry updated!")
                        st.rerun()
                        
        with col2:
            st.subheader("Logged Audit Trails (Categorized)")
            df_trans = get_transactions()
            render_categorized_tabs(df_trans, highlight_func=lambda val: f"color: {'green' if val > 0 else 'red' if val < 0 else 'black'}; font-weight: bold", subset_cols=['Qty_Change'])

# 3. INDENT MANAGEMENT PAGE
elif menu_selection == "📋 Indent Management":
    st.title("📋 Indent Requests & Procurement Workflow")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Raise Demand")
        with st.form("indent_form", clear_on_submit=True):
            item_req = st.text_input("Item / Reagent Requested")
            req_cat = st.selectbox("Category", ["Chemicals", "Glassware", "Instruments"])
            req_qty = st.number_input("Requested Volume/Qty", min_value=0.0, step=1.0)
            indent_type = st.radio("Indent Logic", ["New Demand", "Replacement"])
            
            if st.form_submit_button("Log Demand Request"):
                if not item_req.strip() or req_qty <= 0:
                    st.error("⚠️ Invalid entry.")
                else:
                    create_indent(item_req, req_cat, req_qty, indent_type, current_active_user)
                    st.success("✅ Indent workflow initialized!")
                    st.rerun()

    with col2:
        st.subheader("Multi-Stage Verification Track")
        df_indents = get_indents()
        if not df_indents.empty:
            color_map = {'Request': 'orange', 'HOD Approval': 'blue', 'Store Issued': 'purple', 'Received': 'green'}
            render_categorized_tabs(df_indents, highlight_func=lambda val: f'color: {color_map.get(val, "black")}; font-weight: bold', subset_cols=['status'])
            
            st.divider()
            st.markdown("##### Change Verification Node")
            indent_options = {f"Node ID {row['id']}: {row['item_requested']} [{row['status']}]": (row['id'], row['item_requested']) for index, row in df_indents.iterrows()}
            ca, cb = st.columns(2)
            with ca: selected_indent_display = st.selectbox("Select Target Indent", options=list(indent_options.keys()))
            with cb: new_status = st.selectbox("Transition Node", ["Request", "HOD Approval", "Store Issued", "Received"])
            
            if st.button("Authorize Status Update"):
                selected_id, selected_name = indent_options[selected_indent_display]
                update_indent_status(selected_id, selected_name, new_status, current_active_user)
                st.success("🎯 Workflow state shifted!")
                st.rerun()
        else:
            st.info("No active demand workflows present.")

# 4. BREAKAGE REGISTER
elif menu_selection == "💔 Breakage Register":
    st.title("💔 Breakage Register & Auto-Replacement")
    if df_items.empty:
        st.warning("⚠️ No items available.")
    else:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("Report Damaged Item")
            with st.form("breakage_form", clear_on_submit=True):
                item_options = {f"{row['name']} ({row['category']} - Stock: {row['quantity']})": (row['id'], row['name'], row['category']) for index, row in df_items.iterrows()}
                selected_item_display = st.selectbox("Select Damaged Resource", options=list(item_options.keys()))
                breakage_qty = st.number_input("Quantity Damaged/Lost", min_value=0.0, step=1.0)
                reason = st.text_area("Reason / Incident Details")
                
                if st.form_submit_button("Log Breakage"):
                    if breakage_qty <= 0 or not reason.strip():
                        st.error("⚠️ Invalid entry.")
                    else:
                        i_id, i_name, i_cat = item_options[selected_item_display]
                        log_breakage(i_id, i_name, i_cat, breakage_qty, reason, current_active_user)
                        st.success(f"✅ Breakage logged! Auto-Replacement generated.")
                        st.rerun()

        with col2:
            st.subheader("Breakage History (Categorized)")
            df_breakage = get_breakage_logs()
            render_categorized_tabs(df_breakage)

# 5. ANALYTICS REPORTS
elif menu_selection == "📊 Analytics Reports":
    st.title("📊 Data Analytics & Reporting Hub")
    if df_items.empty:
        st.warning("⚠️ No data available to generate reports.")
    else:
        st.markdown("### Stock Level Distribution")
        fig = px.bar(df_items, x='name', y='quantity', color='category', text_auto=True)
        fig.update_layout(
            title={'text': "Current Stock Levels by Item", 'font': {'color': '#FF8C00', 'size': 22, 'family': 'Arial'}},
            xaxis=dict(showgrid=False, title="Item Name"),
            yaxis=dict(showgrid=False, title="Quantity"),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=True
        )
        st.plotly_chart(fig, use_container_width=True)

# 6. CONTROL ADMIN & AUDIT LOG VAULT (PHASE 7 ACTIVE)
elif menu_selection == "⚙️ Control Admin":
    st.title("⚙️ Control Admin & Audit Log Vault")
    
    adm_col1, adm_col2 = st.columns([1, 2])
    
    with adm_col1:
        st.subheader("User Management")
        with st.form("create_user_form", clear_on_submit=True):
            new_username = st.text_input("New Username (Unique)")
            new_role = st.selectbox("Assign Security Role", ["Operator", "HOD", "Admin"])
            
            if st.form_submit_button("Register User"):
                if not new_username.strip():
                    st.error("⚠️ Username cannot be empty.")
                else:
                    success = add_user(new_username.strip(), new_role)
                    if success:
                        log_audit(f"Created new user portfolio for '{new_username}' as '{new_role}'", "Users", None, current_active_user)
                        st.success(f"✅ User '{new_username}' registered successfully!")
                        st.rerun()
                    else:
                        st.error("⚠️ Username already exists. Use a unique name.")
        
        st.divider()
        st.markdown("##### Registered User Directory")
        st.dataframe(get_users(), use_container_width=True, hide_index=True)

    with adm_col2:
        st.subheader("📜 Live Core Audit Logs")
        df_audits = get_audit_logs()
        if not df_audits.empty:
            st.dataframe(df_audits, use_container_width=True, hide_index=True)
        else:
            st.info("System vault is clean. No logged operations yet.")