import streamlit as st
import pandas as pd
import datetime
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_js_eval import streamlit_js_eval

# --------------------------- CONFIG ---------------------------
st.set_page_config(page_title="Spend Tracker", layout="centered")
st.title("💰 Spend Tracker")

# --------------------------- STYLES ---------------------------
st.markdown("""
    <style>
    .stRadio > div {flex-direction: column;}
    .stRadio label {
        padding: 12px 20px;
        margin: 5px 0;
        border-radius: 12px;
        background: #f0f2f6;
        box-shadow: 1px 1px 5px rgba(0,0,0,0.1);
        font-weight: 500;
    }
    .stSelectbox > div {flex-direction: column;}
    </style>
""", unsafe_allow_html=True)

# --------------------------- SESSION INIT ---------------------------
if "step" not in st.session_state:
    st.session_state.step = 1

if "category_list" not in st.session_state:
    try:
        with open("categories.json", "r") as f:
            st.session_state.category_list = json.load(f)
    except:
        st.session_state.category_list = [
            "Vegetables", "Fruits", "Dairy Products", "Egg", "House Grocery",
            "Snacks", "Tea/coffee", "Juice", "Petrol","Other"
        ]

# --------------------------- LOCATION SETUP ---------------------------
if "location" not in st.session_state:
    loc = streamlit_js_eval(
        js_expressions="navigator.geolocation.getCurrentPosition((pos) => [pos.coords.latitude, pos.coords.longitude])",
        key="initial_loc"
    )
    if loc:
        st.session_state.location = f"{loc[0]:.4f}, {loc[1]:.4f}"
    else:
        st.session_state.location = "Not available"

# --------------------------- GOOGLE SHEET ---------------------------
def get_gsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("Daily_Expense_Data").sheet1
    return sheet

# --------------------------- DOWNLOAD SECTION ---------------------------
st.sidebar.markdown("### 📥 Download Data")
if st.sidebar.button("Download Expenses as CSV"):
    try:
        sheet = get_gsheet()
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty:
            csv_data = df.to_csv(index=False)
            st.sidebar.download_button(
                label="⬇️ Download CSV File",
                data=csv_data,
                file_name=f"expense_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.sidebar.warning("No data available to download")
    except Exception as e:
        st.sidebar.error(f"Error downloading data: {str(e)}")

# --------------------------- STEP 1: NAME ---------------------------
if st.session_state.step == 1:
    st.subheader("👤 Who is entering the expense?")
    name = st.radio("Select name:", ["Vikki", "Sneha"], key="name_radio", index=None)
    
    if st.button("Next ➡️", key="name_next"):
        # Access the radio value directly from session state
        selected_name = st.session_state.get("name_radio")
        if selected_name:
            st.session_state.name = selected_name
            st.session_state.step = 2
            st.rerun()
        else:
            st.error("Please select a name first!")

# --------------------------- STEP 2: CATEGORY ---------------------------
elif st.session_state.step == 2:
    st.subheader("🛒 What did you buy?")
    category = st.selectbox("Select or add a category", st.session_state.category_list, key="cat_select")

    if category == "Other":
        new_cat = st.text_input("Enter new category", key="new_category")
        if new_cat:
            if new_cat not in st.session_state.category_list:
                st.session_state.category_list.insert(-1, new_cat)
                with open("categories.json", "w") as f:
                    json.dump(st.session_state.category_list, f)
            st.session_state.category = new_cat
            st.session_state.step = 3
    elif category:
        st.session_state.category = category
        st.session_state.step = 3

# --------------------------- STEP 3: PAYMENT ---------------------------
elif st.session_state.step == 3:
    st.subheader("💳 Mode of Payment")
    payment = st.radio("Choose:", ["BHIM", "Google Pay", "Cash"], key="pay_radio")
    if payment:
        st.session_state.payment = payment
        st.session_state.step = 4

# --------------------------- STEP 4: AMOUNT ---------------------------
elif st.session_state.step == 4:
    st.subheader("💸 Amount Spent")
    amount = st.number_input("Enter amount", min_value=1.0, step=1.0, key="amount_input")

    with st.expander("🔍 Review Your Entry"):
        st.write(f"**Name**: {st.session_state.name}")
        st.write(f"**Category**: {st.session_state.category}")
        st.write(f"**Payment**: {st.session_state.payment}")
        st.write(f"**Amount**: ₹{amount:.2f}")
        st.write(f"**Location**: {st.session_state.location}")

    if st.button("Save Expense ✅"):
        st.session_state.amount = amount
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        location = st.session_state.location

        # Push to Google Sheet
        sheet = get_gsheet()
        sheet.append_row([
            st.session_state.name,
            st.session_state.category,
            st.session_state.payment,
            st.session_state.amount,
            now,
            location
        ])
        st.success("✅ Expense recorded!")
        st.balloons()
        st.session_state.expense_saved = True
        # st.rerun()

    # Show action buttons after saving (outside the save button block)
    if st.session_state.get("expense_saved", False):
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 Download CSV", key="download_after_save"):
                try:
                    sheet = get_gsheet()
                    df = pd.DataFrame(sheet.get_all_records())
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="⬇️ Get CSV File",
                        data=csv_data,
                        file_name=f"expense_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="csv_download_button"
                    )
                except Exception as e:
                    st.error(f"Error downloading: {str(e)}")
        
        with col2:
            if st.button("➕ Record Another Expense"):    
                # Clear the saved state and reset to step 1
                st.session_state.expense_saved = False
                for key in ["name", "category", "payment", "amount"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.session_state.step = 1
                st.rerun()