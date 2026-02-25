import streamlit as st
import hashlib
import os
import secrets
from db.database import (
    get_user_by_email,
    create_user,
    update_last_login,
    update_login_token,
    get_user_by_token
)

def hash_password(password):
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + key.hex()

def verify_password(password, stored_hash):
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        stored_key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return new_key == stored_key
    except:
        return False

def init_auth_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "username" not in st.session_state:
        st.session_state.username = None

def login_user(email, password):
    user = get_user_by_email(email)
    if not user:
        return False, "User not found"
    if not verify_password(password, user["password_hash"]):
        return False, "Incorrect password"

    token = secrets.token_hex(32)
    update_login_token(user["id"], token)

    # Store cookie (30 days)
    st.markdown(f"""
    <script>
    document.cookie = "cf_token={token}; path=/; max-age=2592000";
    </script>
    """, unsafe_allow_html=True)

    st.session_state.authenticated = True
    st.session_state.user_id = user["id"]
    st.session_state.username = user["username"]
    st.session_state.token = token

    update_last_login(user["id"])
    return True, "Success"

def register_user(email, username, password):
    ph = hash_password(password)
    create_user(email, username, ph)
    return True, "Account created"

def logout_user():
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.token = None

def restore_session():
    if "token" in st.session_state and st.session_state.token:
        user = get_user_by_token(st.session_state.token)
        if user:
            st.session_state.authenticated = True
            st.session_state.user_id = user["id"]
            st.session_state.username = user["username"]
            return True
    return False
