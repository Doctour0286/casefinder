import streamlit as st

# Page configuration
st.set_page_config(
    page_title="CaseFinder",
    page_icon="🎯",
    layout="wide"
)

# Title
st.title("🎯 CaseFinder")
st.markdown("**Viral Crime Case Detection System**")
st.markdown("---")

# Sidebar - Login status
st.sidebar.title("Account")

if "authenticated" in st.session_state and st.session_state.authenticated:
    st.sidebar.success(f"Logged in as: {st.session_state.get('username', 'User')}")
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
else:
    st.sidebar.info("Please log in to continue")

# Main content
st.header("Welcome to CaseFinder")

st.markdown("""
This tool analyzes true crime cases using YouTube data, Wikipedia, and comment analysis 
to produce a **Viral Potential Score (VPS)** — predicting which cases are most likely to go viral on YouTube.
""")

# Feature overview
st.subheader("Features")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🎯 Score Cases")
    st.write("Enter any true crime case and get a full VPS breakdown")

with col2:
    st.markdown("### 🔍 Discover")
    st.write("Find new case candidates from Reddit, Wikipedia, and trending")

with col3:
    st.markdown("### 📊 Track")
    st.write("Monitor watchlist and track video performance")

# Coming soon notice
st.markdown("---")
st.info("🚀 **Coming Soon:** User accounts, scoring, and discovery mode. Stay tuned!")
