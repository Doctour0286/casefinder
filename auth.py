import streamlit as st
import hashlib
import os
import secrets
import time
from db.database import (
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    create_user,
    update_last_login,
)

# ─────────────────────────────────────
# Password Hashing
# ─────────────────────────────────────

def hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + key.hex()

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        stored_key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return new_key == stored_key
    except:
        return False

# ─────────────────────────────────────
# Session Init
# ─────────────────────────────────────

def init_auth_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "username" not in st.session_state:
        st.session_state.username = None

# ─────────────────────────────────────
# Cookie Helpers
# ─────────────────────────────────────

def set_cookie(name, value):
    st.markdown(
        f"""
        <script>
        document.cookie = "{name}={value}; path=/; max-age=2592000";
        </script>
        """,
        unsafe_allow_html=True,
    )

def get_cookie(name):
    cookie_js = f"""
    <script>
    const name = "{name}=";
    const decodedCookie = decodeURIComponent(document.cookie);
    const ca = decodedCookie.split(';');
    for(let i = 0; i <ca.length; i++) {{
        let c = ca[i];
        while (c.charAt(0) == ' ') {{
            c = c.substring(1);
        }}
        if (c.indexOf(name) == 0) {{
            document.write(c.substring(name.length, c.length));
        }}
    }}
    </script>
    """
    return st.markdown(cookie_js, unsafe_allow_html=True)

# ─────────────────────────────────────
# Token Logic
# ─────────────────────────────────────

def generate_login_token():
    return secrets.token_hex(32)

def login_user(email, password):
    user = get_user_by_email(email)
    if not user:
        return False, "User not found"

    if not verify_password(password, user["password_hash"]):
        return False, "Incorrect password"

    token = generate_login_token()

    # Save token to DB
    from db.database import get_db
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET login_token=? WHERE id=?",
            (token, user["id"]),
        )

    set_cookie("cf_token", token)

    st.session_state.authenticated = True
    st.session_state.user_id = user["id"]
    st.session_state.username = user["username"]

    update_last_login(user["id"])
    return True, "Success"

def check_existing_login():
    # Read token from DB and match
    from db.database import get_db

    token = None

    # Extract cookie manually
    if "cf_token" in st.session_state:
        token = st.session_state.cf_token

    # Hack: allow manual cookie fallback
    if not token:
        return False

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, username FROM users WHERE login_token=?",
            (token,),
        ).fetchone()

    if row:
        st.session_state.authenticated = True
        st.session_state.user_id = row["id"]
        st.session_state.username = row["username"]
        return True

    return False

def logout_user():
    from db.database import get_db

    if st.session_state.user_id:
        with get_db() as conn:
            conn.execute(
                "UPDATE users SET login_token=NULL WHERE id=?",
                (st.session_state.user_id,),
            )

    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = None

    set_cookie("cf_token", "")
