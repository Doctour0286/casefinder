import streamlit as st
import auth
from db.database import get_user_by_id

# Page configuration
st.set_page_config(
    page_title="CaseFinder",
    page_icon="🎯",
    layout="wide"
)

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


# ═══════════════════════════════════════════════════════════
# SIDEBAR - Navigation & Auth
# ═══════════════════════════════════════════════════════════

st.sidebar.title("🎯 CaseFinder")

# Show login/logout in sidebar
if st.session_state.authenticated:
    user = get_user_by_id(st.session_state.user_id)
    st.sidebar.success(f"Logged in as: **{user['username']}**")
    
    # Navigation menu
    menu = st.sidebar.radio("Menu", [
        "🏠 Home",
        "🎯 Score a Case",
        "📊 Batch Score",
        "🔍 Discover",
        "👁️ Watchlist",
        "🏆 Rankings",
        "📈 Results",
        "⚙️ Settings"
    ])
    
    if st.sidebar.button("Logout"):
        auth.logout_user()
        st.rerun()
else:
    st.sidebar.info("Please log in to continue")
    menu = "🔐 Login / Register"


# ═══════════════════════════════════════════════════════════
# PAGE: LOGIN / REGISTER
# ═══════════════════════════════════════════════════════════

if menu == "🔐 Login / Register":
    st.title("🔐 Login or Register")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if email and password:
                    success, message = auth.login_user(email, password)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Please fill in all fields.")
    
    with tab2:
        st.subheader("Register")
        with st.form("register_form"):
            new_email = st.text_input("Email", key="reg_email")
            new_username = st.text_input("Username", key="reg_username")
            new_password = st.text_input("Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit = st.form_submit_button("Create Account")
            
            if submit:
                if new_email and new_username and new_password:
                    if new_password != confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        success, message = auth.register_user(new_email, new_username, new_password)
                        if success:
                            st.success(message + " Please login.")
                        else:
                            st.error(message)
                else:
                    st.error("Please fill in all fields.")


# ═══════════════════════════════════════════════════════════
# PAGE: HOME
# ═══════════════════════════════════════════════════════════

elif menu == "🏠 Home":
    st.title("🎯 Welcome to CaseFinder")
    
    st.markdown("""
    **CaseFinder** analyzes true crime cases using YouTube data, Wikipedia, and comment analysis 
    to produce a **Viral Potential Score (VPS)** — predicting which cases are most likely to go viral on YouTube.
    """)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🎯 Score Cases")
        st.write("Enter any true crime case and get a full VPS breakdown with demand, supply, and emotional heat scores.")
    
    with col2:
        st.markdown("### 🔍 Discover")
        st.write("Find new case candidates from Reddit, Wikipedia, YouTube trending, and our curated seed list.")
    
    with col3:
        st.markdown("### 👁️ Watchlist")
        st.write("Monitor cases for competitor uploads and track video performance over time.")
    
    st.markdown("---")
    
    if st.session_state.authenticated:
        st.success("You're logged in! Use the menu on the left to navigate.")
    else:
        st.info("Please login or register to start scoring cases.")


# ═══════════════════════════════════════════════════════════
# PAGE: SCORE A CASE (Coming Soon)
# ═══════════════════════════════════════════════════════════

elif menu == "🎯 Score a Case":
    st.title("🎯 Score a Case")
    
    if not st.session_state.authenticated:
        st.warning("Please login to score cases.")
        st.stop()
    
    st.info("🚧 Scoring engine coming soon! This feature is being built.")
    
    with st.form("score_form"):
        case_name = st.text_input("Enter case name", placeholder="e.g., Alonzo Brooks")
        submit = st.form_submit_button("Score Case")
        
        if submit and case_name:
            st.success(f"Would score: {case_name}")


# ═══════════════════════════════════════════════════════════
# PAGE: BATCH SCORE (Coming Soon)
# ═══════════════════════════════════════════════════════════

elif menu == "📊 Batch Score":
    st.title("📊 Batch Score")
    
    if not st.session_state.authenticated:
        st.warning("Please login to use batch scoring.")
        st.stop()
    
    st.info("🚧 Batch scoring coming soon!")


# ═══════════════════════════════════════════════════════════
# PAGE: DISCOVER (Coming Soon)
# ═══════════════════════════════════════════════════════════

elif menu == "🔍 Discover":
    st.title("🔍 Discover New Cases")
    
    if not st.session_state.authenticated:
        st.warning("Please login to discover cases.")
        st.stop()
    
    st.info("🚧 Discovery mode coming soon!")


# ═══════════════════════════════════════════════════════════
# PAGE: WATCHLIST
# ═══════════════════════════════════════════════════════════

elif menu == "👁️ Watchlist":
    st.title("👁️ Your Watchlist")
    
    if not st.session_state.authenticated:
        st.warning("Please login to view your watchlist.")
        st.stop()
    
    from db.database import get_watchlist, add_to_watchlist, remove_from_watchlist
    
    # Add new case
    with st.form("add_watchlist"):
        col1, col2 = st.columns([3, 1])
        with col1:
            new_case = st.text_input("Add case to watchlist", placeholder="Case name")
        with col2:
            st.write("")  # spacing
            add_btn = st.form_submit_button("Add")
        
        if add_btn and new_case:
            if add_to_watchlist(st.session_state.user_id, new_case):
                st.success(f"Added '{new_case}' to watchlist!")
                st.rerun()
            else:
                st.warning(f"'{new_case}' is already in your watchlist.")
    
    st.markdown("---")
    
    # Show watchlist
    watchlist = get_watchlist(st.session_state.user_id)
    
    if watchlist:
        st.subheader(f"Your Watchlist ({len(watchlist)} cases)")
        for item in watchlist:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"• **{item['case_name']}**")
            with col2:
                if st.button(f"Remove", key=f"rem_{item['id']}"):
                    remove_from_watchlist(st.session_state.user_id, item['case_name'])
                    st.rerun()
    else:
        st.info("Your watchlist is empty. Add some cases above!")


# ═══════════════════════════════════════════════════════════
# PAGE: RANKINGS
# ═══════════════════════════════════════════════════════════

elif menu == "🏆 Rankings":
    st.title("🏆 Your Case Rankings")
    
    if not st.session_state.authenticated:
        st.warning("Please login to view your rankings.")
        st.stop()
    
    from db.database import get_user_scores
    
    scores = get_user_scores(st.session_state.user_id)
    
    if scores:
        st.subheader(f"Ranked Cases ({len(scores)} cases)")
        
        for i, score in enumerate(scores, 1):
            with st.expander(f"#{i} {score['case_name']} — VPS: {score['vps']}"):
                st.write(f"**Rating:** {score['rating']}")
                st.write(f"**Demand:** {score['demand']}/50")
                st.write(f"**Supply Gap:** {score['supply']}/25")
                st.write(f"**Emotional Heat:** {score['emotional']}/35")
                st.write(f"**Scored:** {score['scored_at']}")
    else:
        st.info("No cases scored yet. Go to 'Score a Case' to get started!")


# ═══════════════════════════════════════════════════════════
# PAGE: RESULTS
# ═══════════════════════════════════════════════════════════

elif menu == "📈 Results":
    st.title("📈 Video Results")
    
    if not st.session_state.authenticated:
        st.warning("Please login to track results.")
        st.stop()
    
    st.info("🚧 Results tracking coming soon!")


# ═══════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ═══════════════════════════════════════════════════════════

elif menu == "⚙️ Settings":
    st.title("⚙️ Settings")
    
    if not st.session_state.authenticated:
        st.warning("Please login to access settings.")
        st.stop()
    
    from db.database import get_user_by_id
    
    user = get_user_by_id(st.session_state.user_id)
    
    st.subheader("Profile")
    st.write(f"**Username:** {user['username']}")
    st.write(f"**Email:** {user['email']}")
    st.write(f"**Member since:** {user['created_at']}")
    
    st.markdown("---")
    
    st.subheader("YouTube API Key")
    
    with st.form("api_key_form"):
        api_key = st.text_input("YouTube Data API Key", 
                                 value=user.get('youtube_api_key', ''),
                                 type="password",
                                 help="Get your API key from Google Cloud Console")
        save_btn = st.form_submit_button("Save API Key")
        
        if save_btn and api_key:
            from db.database import update_user_api_key
            update_user_api_key(st.session_state.user_id, api_key)
            st.success("API Key saved!")
            st.rerun()
    
    if user.get('youtube_api_key'):
        st.success("✅ API Key configured")
    else:
        st.warning("⚠️ No API Key set. You'll need one to score cases.")
