import streamlit as st
import auth
from db.database import get_user_by_id, save_score, get_user_scores
from core.scorer import score_case

# Page configuration
st.set_page_config(
    page_title="CaseFinder",
    page_icon="🎯",
    layout="wide"
)

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


# SIDEBAR
st.sidebar.title("🎯 CaseFinder")

if st.session_state.authenticated:
    user = get_user_by_id(st.session_state.user_id)
    st.sidebar.success(f"Logged in as: **{user['username']}**")
    
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


# LOGIN / REGISTER
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


# HOME
elif menu == "🏠 Home":
    st.title("🎯 Welcome to CaseFinder")
    
    st.markdown("""
    **CaseFinder** analyzes true crime cases using YouTube data and comment analysis 
    to produce a **Viral Potential Score (VPS)** — predicting which cases are most likely to go viral.
    """)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🎯 Score Cases")
        st.write("Enter any true crime case and get a full VPS breakdown.")
    
    with col2:
        st.markdown("### 🔍 Discover")
        st.write("Find new case candidates from multiple sources.")
    
    with col3:
        st.markdown("### 👁️ Watchlist")
        st.write("Monitor cases for competitor uploads.")
    
    if st.session_state.authenticated:
        st.success("You're logged in! Use the menu on the left.")
    else:
        st.info("Please login or register to start scoring cases.")


# SCORE A CASE
elif menu == "🎯 Score a Case":
    st.title("🎯 Score a Case")
    
    if not st.session_state.authenticated:
        st.warning("Please login to score cases.")
        st.stop()
    
    user = get_user_by_id(st.session_state.user_id)
    
    if not user.get('youtube_api_key'):
        st.error("⚠️ You need to add your YouTube API key first!")
        st.info("Go to **Settings** to add your API key.")
        st.stop()
    
    with st.form("score_form"):
        case_name = st.text_input("Enter case name", placeholder="e.g., Alonzo Brooks")
        submit = st.form_submit_button("🎯 Score Case")
        
        if submit and case_name:
            with st.spinner("Scoring case... This may take 30-60 seconds."):
                try:
                    result = score_case(case_name, user['youtube_api_key'], 
                                      user.get('subscriber_count', 0))
                    
                    if result.get("error"):
                        st.error(f"Error: {result['error']}")
                    else:
                        save_score(st.session_state.user_id, case_name, result)
                        
                        vps = result['vps']
                        rating = result['rating']
                        
                        if vps >= 75:
                            color = "green"
                        elif vps >= 60:
                            color = "blue"
                        else:
                            color = "orange"
                        
                        st.markdown(f"""
                        <div style="padding: 20px; background-color: #{color}1A; border-radius: 10px; text-align: center;">
                            <h1 style="margin: 0; font-size: 48px; color: #{color};">{vps}/100</h1>
                            <p style="margin: 0; font-size: 18px;">{rating}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown("---")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Demand", f"{result['demand']}/50")
                            st.write(f"D1 (Peak Views): {result['d1']}/15")
                            st.write(f"D2 (Multi-Creator): {result['d2']}/10")
                            st.write(f"D3 (Cross-Platform): {result['d3']}/10")
                            st.write(f"D4 (Search): {result['d4']}/5")
                            st.write(f"D6 (Long-Form): {result['d6']}/5")
                        
                        with col2:
                            st.metric("Supply Gap", f"{result['supply']}/25")
                            st.write(f"S1 (Recency): {result['s1']}/15")
                            st.write(f"S2 (Quality): {result['s2']}/10")
                            st.write(f"S4 (Saturation): {result['s4']}")
                        
                        with col3:
                            st.metric("Emotional", f"{result['emotional']}/35")
                            st.write(f"E1 (CVR): {result['e1']}/8")
                            st.write(f"E2 (Intensity): {result['e2']}/8")
                            st.write(f"E3 (Questions): {result['e3']}/5")
                            st.write(f"E4 (Theories): {result['e4']}/4")
                        
                        st.markdown("---")
                        
                        st.subheader(f"📌 Angle: {result['angle']}")
                        st.write("**Titles:**")
                        for title in result.get('titles', []):
                            st.write(f"• {title}")
                        
                        st.info("💾 Score saved!")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")


# BATCH SCORE
elif menu == "📊 Batch Score":
    st.title("📊 Batch Score")
    if not st.session_state.authenticated:
        st.warning("Please login.")
        st.stop()
    st.info("Coming soon!")


# DISCOVER
elif menu == "🔍 Discover":
    st.title("🔍 Discover")
    if not st.session_state.authenticated:
        st.warning("Please login.")
        st.stop()
    st.info("Coming soon!")


# WATCHLIST
elif menu == "👁️ Watchlist":
    st.title("👁️ Watchlist")
    
    if not st.session_state.authenticated:
        st.warning("Please login.")
        st.stop()
    
    from db.database import get_watchlist, add_to_watchlist, remove_from_watchlist
    
    with st.form("add_watchlist"):
        col1, col2 = st.columns([3, 1])
        with col1:
            new_case = st.text_input("Add case", placeholder="Case name")
        with col2:
            st.write("")
            add_btn = st.form_submit_button("Add")
        
        if add_btn and new_case:
            if add_to_watchlist(st.session_state.user_id, new_case.title()):
                st.success("Added!")
                st.rerun()
            else:
                st.warning("Already exists.")
    
    st.markdown("---")
    
    watchlist = get_watchlist(st.session_state.user_id)
    
    if watchlist:
        st.subheader(f"Watchlist ({len(watchlist)} cases)")
        for item in watchlist:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"• **{item['case_name']}**")
            with col2:
                if st.button(f"Remove", key=f"rem_{item['id']}"):
                    remove_from_watchlist(st.session_state.user_id, item['case_name'])
                    st.rerun()
    else:
        st.info("Empty watchlist.")


# RANKINGS
elif menu == "🏆 Rankings":
    st.title("🏆 Rankings")
    
    if not st.session_state.authenticated:
        st.warning("Please login.")
        st.stop()
    
    scores = get_user_scores(st.session_state.user_id)
    
    if scores:
        st.subheader(f"{len(scores)} scored cases")
        
        for i, score in enumerate(scores, 1):
            with st.expander(f"#{i} {score['case_name']} — VPS: {score['vps']}"):
                st.write(f"**Rating:** {score['rating']}")
                st.write(f"Demand: {score['demand']}/50 | Supply: {score['supply']}/25 | Emotional: {score['emotional']}/35")
    else:
        st.info("No scores yet. Go to 'Score a Case'!")


# RESULTS
elif menu == "📈 Results":
    st.title("📈 Results")
    if not st.session_state.authenticated:
        st.warning("Please login.")
        st.stop()
    st.info("Coming soon!")


# SETTINGS
elif menu == "⚙️ Settings":
    st.title("⚙️ Settings")
    
    if not st.session_state.authenticated:
        st.warning("Please login.")
        st.stop()
    
    from db.database import get_user_by_id, update_user_api_key
    
    user = get_user_by_id(st.session_state.user_id)
    
    st.subheader("Profile")
    st.write(f"**Username:** {user['username']}")
    st.write(f"**Email:** {user['email']}")
    st.write(f"**Member since:** {user['created_at']}")
    
    st.markdown("---")
    
    st.subheader("YouTube API Key")
    
    with st.form("api_key_form"):
        api_key = st.text_input("YouTube API Key", 
                                 value=user.get('youtube_api_key', ''),
                                 type="password",
                                 help="Get from Google Cloud Console")
        save_btn = st.form_submit_button("Save")
        
        if save_btn and api_key:
            update_user_api_key(st.session_state.user_id, api_key)
            st.success("Saved!")
            st.rerun()
    
    if user.get('youtube_api_key'):
        st.success("✅ API Key configured")
    else:
        st.warning("⚠️ No API Key. Add one to score cases.")
    
    st.markdown("---")
    st.markdown("""
    **How to get API key:**
    1. Go to [Google Cloud Console](https://console.cloud.google.com/)
    2. Create project → Enable "YouTube Data API v3"
    3. Credentials → Create API Key
    """)
