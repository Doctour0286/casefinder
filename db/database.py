from supabase import create_client
import streamlit as st
from datetime import datetime

# ─── Supabase Client ───
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── USERS ───

def create_user(email, username, password_hash):
    data = {
        "email": email,
        "username": username,
        "password_hash": password_hash
    }
    return supabase.table("users").insert(data).execute()

def get_user_by_email(email):
    res = supabase.table("users").select("*").eq("email", email).execute()
    return res.data[0] if res.data else None

def get_user_by_username(username):
    res = supabase.table("users").select("*").eq("username", username).execute()
    return res.data[0] if res.data else None

def get_user_by_id(user_id):
    res = supabase.table("users").select("*").eq("id", user_id).execute()
    return res.data[0] if res.data else None

def update_user_api_key(user_id, api_key):
    supabase.table("users").update({"youtube_api_key": api_key}).eq("id", user_id).execute()

def update_user_channel(user_id, handle, channel_id, subs):
    supabase.table("users").update({
        "channel_handle": handle,
        "channel_id": channel_id,
        "subscriber_count": subs
    }).eq("id", user_id).execute()

def update_last_login(user_id):
    supabase.table("users").update({
        "last_login": datetime.utcnow().isoformat()
    }).eq("id", user_id).execute()

def update_login_token(user_id, token):
    supabase.table("users").update({"login_token": token}).eq("id", user_id).execute()

def get_user_by_token(token):
    res = supabase.table("users").select("*").eq("login_token", token).execute()
    return res.data[0] if res.data else None

# ─── SCORES ───

def save_score(user_id, case_name, score_data):
    # delete existing
    supabase.table("scores").delete().eq("user_id", user_id).eq("case_name", case_name).execute()
    supabase.table("scores").insert({
        "user_id": user_id,
        "case_name": case_name,
        "vps": score_data.get("vps"),
        "rating": score_data.get("rating"),
        "demand": score_data.get("demand"),
        "supply": score_data.get("supply"),
        "emotional": score_data.get("emotional"),
        "full_data": score_data
    }).execute()

def get_user_scores(user_id):
    res = supabase.table("scores").select("*").eq("user_id", user_id).order("vps", desc=True).execute()
    return res.data

def get_score_history(user_id, days=90):
    res = supabase.table("scores").select("*").eq("user_id", user_id).order("scored_at").execute()
    return res.data

# ─── WATCHLIST ───

def add_to_watchlist(user_id, case_name):
    supabase.table("watchlist").insert({
        "user_id": user_id,
        "case_name": case_name
    }).execute()
    return True

def remove_from_watchlist(user_id, case_name):
    supabase.table("watchlist").delete().eq("user_id", user_id).eq("case_name", case_name).execute()
    return True

def get_watchlist(user_id):
    res = supabase.table("watchlist").select("*").eq("user_id", user_id).order("added_at", desc=True).execute()
    return res.data

def update_watchlist_check(user_id, case_name, alert=None):
    supabase.table("watchlist").update({
        "last_checked": datetime.utcnow().isoformat(),
        "last_alert": alert
    }).eq("user_id", user_id).eq("case_name", case_name).execute()

# ─── RESULTS ───

def save_result(user_id, case_name, views, retention=None, ctr=None):
    supabase.table("results").insert({
        "user_id": user_id,
        "case_name": case_name,
        "views_30d": views,
        "avg_retention_pct": retention,
        "ctr_pct": ctr
    }).execute()

def get_user_results(user_id):
    res = supabase.table("results").select("*").eq("user_id", user_id).order("recorded_at", desc=True).execute()
    return res.data
