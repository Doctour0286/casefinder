"""
CaseFinder v1.0 — Authentication
Handles user registration, login, and session management.
"""

import hashlib
import os
import streamlit as st
from db.database import (
    create_user, get_user_by_email, get_user_by_username,
    update_last_login, get_user_by_id
)


def hash_password(password: str) -> str:
    """Hash password with salt."""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + key.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash."""
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        stored_key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return new_key == stored_key
    except Exception:
        return False


def register_user(email: str, username: str, password: str) -> tuple[bool, str]:
    """Register a new user."""
    email = email.strip().lower()
    username = username.strip()

    if not email or "@" not in email:
        return False, "Invalid email address."

    if not username or len(username) < 3:
        return False, "Username must be at least 3 characters."

    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    if get_user_by_email(email):
        return False, "Email already registered."

    if get_user_by_username(username):
        return False, "Username already taken."

    password_hash = hash_password(password)
    user_id = create_user(email, username, password_hash)

    return True, "Account created! You can now log in."


def login_user(email: str, password: str) -> tuple[bool, str]:
    """Authenticate a user."""
    email = email.strip().lower()

    user = get_user_by_email(email)
    if not user:
        return False, "No account found with this email."

    if not verify_password(password, user["password_hash"]):
        return False, "Incorrect password."

    # Set session state
    update_last_login(user["id"])
    st.session_state["authenticated"] = True
    st.session_state["user_id"] = user["id"]
    st.session_state["username"] = user["username"]
    st.session_state["email"] = user["email"]

    return True, f"Welcome back, {user['username']}!"


def logout_user():
    """Log out current user."""
    for key in ["authenticated", "user_id", "username", "email"]:
        if key in st.session_state:
            del st.session_state[key]


def is_authenticated() -> bool:
    """Check if user is logged in."""
    return st.session_state.get("authenticated", False)


def get_current_user_id() -> int | None:
    """Get current user's ID."""
    return st.session_state.get("user_id")


def get_current_username() -> str:
    """Get current user's username."""
    return st.session_state.get("username", "")


def require_auth():
    """Require authentication to access a page."""
    if not is_authenticated():
        st.warning("⚠️ Please log in to continue.")
        st.stop()
