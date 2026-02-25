import streamlit as st
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def signup(email, password):
    try:
        # Sign up (trigger will create public.users entry)
        res = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        return True, "Account created! Check email if confirmation is enabled."
    except Exception as e:
        return False, str(e)

def login(email, password):
    try:
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if res.session:
            st.session_state.authenticated = True
            st.session_state.user = res.user
            # Ensure session is saved to local storage if possible (Streamlit limit)
            return True, "Logged in"
        return False, "Login failed"
    except Exception as e:
        return False, str(e)

def logout():
    supabase.auth.sign_out()
    st.session_state.authenticated = False
    st.session_state.user = None

def restore_session():
    """Check if existing session is valid"""
    session = supabase.auth.get_session()
    if session:
        st.session_state.authenticated = True
        st.session_state.user = session.user
        return True
    return False
