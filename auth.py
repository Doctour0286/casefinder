import streamlit as st
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def register_user(email, password, username=None):
    # Username is unused in Auth but stored in metadata or ignored
    try:
        data = {"email": email, "password": password}
        if username:
            data["options"] = {"data": {"username": username}}
            
        res = supabase.auth.sign_up(data)
        
        # Trigger handles public.users creation
        return True, "Account created! You can login now."
    except Exception as e:
        return False, str(e)

def login_user(email, password, cookie_manager=None):
    # cookie_manager unused here but kept for signature compatibility
    try:
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if res.session:
            st.session_state.authenticated = True
            st.session_state.user = res.user
            st.session_state.user_id = res.user.id # For app compatibility
            return True, "Logged in"
        return False, "Login failed"
    except Exception as e:
        return False, str(e)

def logout_user(cookie_manager=None):
    supabase.auth.sign_out()
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.user_id = None

def restore_session():
    """Check if existing session is valid"""
    try:
        session = supabase.auth.get_session()
        if session:
            st.session_state.authenticated = True
            st.session_state.user = session.user
            st.session_state.user_id = session.user.id
            return True
    except: pass
    return False
    
# Initialize state
def init_auth_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None

# Mock cookie manager for compatibility
class MockCookieManager:
    def get(self, name): return None
    def set(self, name, val, **kwargs): pass
    def delete(self, name): pass

def get_cookie_manager():
    return MockCookieManager()
