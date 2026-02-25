import streamlit as st
import json
import auth
from db.database import get_user_by_id, save_score, get_user_scores
from core.scorer import score_case, discover

st.set_page_config(page_title="CaseFinder", page_icon="🎯", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "last_result" not in st.session_state:
    st.session_state.last_result = None

# SIDEBAR
st.sidebar.title("🎯 CaseFinder")

if st.session_state.authenticated:
    user = get_user_by_id(st.session_state.user_id)
    st.sidebar.success(f"**{user['username']}**")
    menu = st.sidebar.radio("Menu", [
        "🏠 Home", "🎯 Score a Case", "📊 Batch Score",
        "🔍 Discover", "👁️ Watchlist", "🏆 Rankings",
        "📈 Results", "⚙️ Settings"
    ])
    if st.sidebar.button("Logout"):
        auth.logout_user()
        st.rerun()
else:
    st.sidebar.info("Please log in")
    menu = "🔐 Login / Register"

# LOGIN / REGISTER
if menu == "🔐 Login / Register":
    st.title("🔐 Login or Register")
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if email and password:
                    ok, msg = auth.login_user(email, password)
                    if ok: st.success(msg); st.rerun()
                    else: st.error(msg)
    with tab2:
        with st.form("register_form"):
            new_email = st.text_input("Email", key="re")
            new_username = st.text_input("Username", key="ru")
            new_password = st.text_input("Password", type="password", key="rp")
            confirm = st.text_input("Confirm Password", type="password")
            if st.form_submit_button("Create Account"):
                if new_email and new_username and new_password:
                    if new_password != confirm: st.error("Passwords don't match.")
                    else:
                        ok, msg = auth.register_user(new_email, new_username, new_password)
                        if ok: st.success(msg)
                        else: st.error(msg)

# HOME
elif menu == "🏠 Home":
    st.title("🎯 CaseFinder")
    st.markdown("**Viral Crime Case Detection System v3.2**")
    st.markdown("Analyzes true crime cases using YouTube data, Wikipedia, and comment analysis to produce a **Viral Potential Score (VPS)**.")
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown("### 🎯 Score"); st.write("Full VPS breakdown with demand, supply gap, and emotional heat.")
    with col2: st.markdown("### 🔍 Discover"); st.write("Find candidates from YouTube trending and seed list.")
    with col3: st.markdown("### 👁️ Track"); st.write("Watchlist, rankings, and results tracking.")

# SCORE A CASE
elif menu == "🎯 Score a Case":
    st.title("🎯 Score a Case")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    user = get_user_by_id(st.session_state.user_id)
    if not user.get('youtube_api_key'):
        st.error("Add your YouTube API key in Settings first!")
        st.stop()

    case_name = st.text_input("Case name", placeholder="e.g., Alonzo Brooks")
    score_btn = st.button("🎯 Score Case")

    if score_btn and case_name:
        progress_bar = st.progress(0)
        status = st.empty()
        phases = {0: 0, 1: 15, 2: 30, 3: 45, 4: 60, 5: 75, 6: 90}

        def update_progress(phase, msg):
            progress_bar.progress(phases.get(phase, 0))
            status.text(msg)

        try:
            result = score_case(case_name, user['youtube_api_key'],
                              user.get('subscriber_count', 0), update_progress)
            progress_bar.progress(100)
            status.text("Done!")
            st.session_state.last_result = result
        except Exception as e:
            st.error(f"Scoring error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

    # Display results from session state
    result = st.session_state.last_result
    if result:
        if result.get("error"):
            st.error(f"Error: {result['error']}")
        else:
            # Save to database
            try:
                save_score(st.session_state.user_id, result["case_name"], {
                    "vps": result["vps"], "rating": result["rating"],
                    "demand": result["demand"], "supply": result["supply"],
                    "emotional": result["emotional"],
                    "case_name": result["case_name"],
                    "angle": result.get("angle", ""),
                })
            except: pass

            # VPS Display
            vps = result['vps']
            if vps >= 90: color = "#FF4500"
            elif vps >= 75: color = "#2ECC40"
            elif vps >= 60: color = "#0074D9"
            elif vps >= 40: color = "#FF851B"
            else: color = "#AAAAAA"

            st.markdown(f"""
            <div style="padding:20px; border:3px solid {color}; border-radius:15px; text-align:center; margin:10px 0;">
                <h1 style="margin:0; font-size:56px; color:{color};">{vps}/100</h1>
                <p style="margin:5px 0; font-size:20px;">{result['rating']}</p>
                <p style="margin:0; font-size:14px; color:#888;">{result.get('mode','')}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"### 📊 Demand: {result['demand']}/50")
                st.write(f"D1 Peak Views: **{result['d1']}**/15 — {result.get('peak_views',0):,} ({result.get('peak_channel','?')})")
                st.write(f"D2 Multi-Creator: **{result['d2']}**/10 — {result.get('creators_100k',0)} channels")
                st.write(f"D3 Cross-Platform: **{result['d3']}**/10 — {', '.join(result.get('d3_sources',[])) or 'none'}")
                st.write(f"D4 Search Demand: **{result['d4']}**/5")
                st.write(f"D5 Pre-YT Buzz: **{result['d5']}**/5 — {result.get('d5_source','none')}")
                st.write(f"D6 Long-Form: **{result['d6']}**/5")

            with col2:
                st.markdown(f"### 📉 Supply Gap: {result['supply']}/25")
                st.write(f"S1 Recency: **{result['s1']}**/15 — {result.get('s1_months',0)} months")
                st.write(f"S2 Quality: **{result['s2']}**/10 (dur:{result.get('s2_dur',0)} like:{result.get('s2_lr',0)} comp:{result.get('s2_comp',0)})")
                st.write(f"S3 Timing: **{result['s3']}**/5 — {result.get('s3_reason','none')}")
                st.write(f"S4 Saturation: **{result['s4']}** — {result.get('s4_mega',0)} mega-videos")

            with col3:
                st.markdown(f"### 🔥 Emotional: {result['emotional']}/35")
                st.write(f"E1 CVR: **{result['e1']}**/8 — {result.get('avg_cvr',0):.2f}%")
                st.write(f"E2 Intensity: **{result['e2']}**/8 — {result.get('dominant_emotion','neutral')}")
                st.write(f"E3 Questions: **{result['e3']}**/5")
                st.write(f"E4 Theories: **{result['e4']}**/4")
                st.write(f"E5 Requests: **{result['e5']}**/5")
                st.write(f"R Rabbit Hole: **{result['r']}**/5 — {', '.join(result.get('r_details',[])) or 'none'}")

            st.markdown("---")
            st.markdown("### 🔒 Gates")
            g1, g2, g3 = st.columns(3)
            with g1: st.write(f"**N Narrative:** {result.get('gate_n','?')} ({', '.join(result.get('gate_n_elements',[]))})")
            with g2: st.write(f"**T Thumbnail:** {result.get('gate_t','?')} ({result.get('gate_t_detail','')})")
            with g3: st.write(f"**C Competition:** {result.get('gate_c','?')} — {result.get('gate_c_detail','')}")

            st.markdown("---")
            st.markdown(f"### 📌 Recommended Angle: {result.get('angle','')}")
            st.write(f"**Why:** {result.get('angle_reason','')}")
            st.write("**Suggested Titles:**")
            for t in result.get('titles', []): st.write(f"• {t}")

            if result.get('contrarian'):
                st.markdown(f"### 🔄 Contrarian: {result['contrarian']['angle']}")
                st.write(f"**Dominant theory:** {result['contrarian'].get('dominant_theory','')[:100]}")
                for t in result.get('contrarian_titles', []): st.write(f"• {t}")

            st.markdown("---")
            if result.get('top_questions'):
                st.markdown("### ❓ Key Audience Questions")
                for q in result['top_questions']: st.write(f"• {q}")
            if result.get('top_theories'):
                st.markdown("### 💭 Top Theories")
                for t in result['top_theories']: st.write(f"• {t}")
            if result.get('top_requests'):
                st.markdown("### 📢 Content Requests")
                for r in result['top_requests']: st.write(f"• {r}")
            if result.get('top_complaints'):
                st.markdown("### ⚠️ Complaints About Existing Coverage")
                for c in result['top_complaints']: st.write(f"• {c}")

            st.write(f"📊 Comments analyzed: {result.get('total_comments',0)}")
            st.success("💾 Score saved to rankings!")

            if st.button("Clear Results"):
                st.session_state.last_result = None
                st.rerun()

# BATCH SCORE
elif menu == "📊 Batch Score":
    st.title("📊 Batch Score")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    user = get_user_by_id(st.session_state.user_id)
    if not user.get('youtube_api_key'):
        st.error("Add your YouTube API key in Settings first!"); st.stop()

    cases_text = st.text_area("Enter case names (one per line)", placeholder="Alonzo Brooks\nElisa Lam\nMaura Murray")
    if st.button("📊 Score All"):
        cases = [c.strip() for c in cases_text.strip().split("\n") if c.strip()]
        if cases:
            results = []
            prog = st.progress(0)
            for i, case in enumerate(cases):
                st.write(f"Scoring: **{case}**...")
                try:
                    r = score_case(case, user['youtube_api_key'], user.get('subscriber_count', 0))
                    if r and not r.get("error"):
                        results.append(r)
                        save_score(st.session_state.user_id, r["case_name"], {
                            "vps": r["vps"], "rating": r["rating"],
                            "demand": r["demand"], "supply": r["supply"],
                            "emotional": r["emotional"], "case_name": r["case_name"],
                            "angle": r.get("angle", ""),
                        })
                except Exception as e: st.warning(f"Error: {case}: {e}")
                prog.progress((i+1) / len(cases))
            if results:
                results.sort(key=lambda x: x["vps"], reverse=True)
                st.markdown("### 📊 Final Rankings")
                for i, r in enumerate(results, 1):
                    st.write(f"**#{i}** [{r['vps']}/100] {r['rating']} — **{r['case_name']}** | {r.get('angle','')}")

# DISCOVER
elif menu == "🔍 Discover":
    st.title("🔍 Discover New Cases")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    user = get_user_by_id(st.session_state.user_id)
    if not user.get('youtube_api_key'):
        st.error("Add your YouTube API key in Settings first!"); st.stop()
    if st.button("🔍 Find Candidates"):
        status = st.empty()
        with st.spinner("Discovering..."):
            candidates = discover(user['youtube_api_key'], count=10, progress_callback=lambda msg: status.text(msg))
        if candidates:
            st.markdown("### 📊 Top Candidates")
            for i, c in enumerate(candidates, 1):
                label = "🔥" if c["d1"] >= 9 else "✅" if c["d1"] >= 6 else "👍" if c["d1"] >= 3 else "⬜"
                st.write(f"**#{i}** {label} **{c['name']}** — D1: {c['d1']}/15 | Peak: {c['peak']:,} | {c['source']}")
        else: st.info("No candidates found.")

# WATCHLIST
elif menu == "👁️ Watchlist":
    st.title("👁️ Watchlist")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    from db.database import get_watchlist, add_to_watchlist, remove_from_watchlist
    with st.form("add_watch"):
        new_case = st.text_input("Add case", placeholder="Case name")
        if st.form_submit_button("Add"):
            if new_case:
                if add_to_watchlist(st.session_state.user_id, new_case.title()): st.success("Added!"); st.rerun()
                else: st.warning("Already exists.")
    st.markdown("---")
    watchlist = get_watchlist(st.session_state.user_id)
    if watchlist:
        for item in watchlist:
            col1, col2 = st.columns([4, 1])
            with col1: st.write(f"• **{item['case_name']}**")
            with col2:
                if st.button("Remove", key=f"r_{item['id']}"):
                    remove_from_watchlist(st.session_state.user_id, item['case_name']); st.rerun()
    else: st.info("Empty.")

# RANKINGS
elif menu == "🏆 Rankings":
    st.title("🏆 Rankings")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    scores = get_user_scores(st.session_state.user_id)
    if scores:
        for i, s in enumerate(scores, 1):
            with st.expander(f"#{i} [{s['vps']}/100] {s['rating']} — {s['case_name']}"):
                st.write(f"Demand: {s['demand']}/50 | Supply: {s['supply']}/25 | Emotional: {s['emotional']}/35")
                st.write(f"Scored: {s['scored_at']}")
                try:
                    data = json.loads(s.get('full_data','{}'))
                    if data.get('angle'): st.write(f"Angle: {data['angle']}")
                except: pass
    else: st.info("No scores yet.")

# RESULTS
elif menu == "📈 Results":
    st.title("📈 Results")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    from db.database import save_result, get_user_results
    with st.form("add_result"):
        case = st.text_input("Case name")
        views = st.number_input("Views (30 days)", min_value=0, step=1000)
        if st.form_submit_button("Save Result"):
            if case and views > 0:
                save_result(st.session_state.user_id, case.title(), int(views))
                st.success("Saved!"); st.rerun()
    st.markdown("---")
    results = get_user_results(st.session_state.user_id)
    if results:
        for r in results:
            st.write(f"**{r['case_name']}** — {r['views_30d']:,} views ({r['recorded_at'][:10]})")
    else: st.info("No results yet.")

# SETTINGS
elif menu == "⚙️ Settings":
    st.title("⚙️ Settings")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    from db.database import update_user_api_key, update_user_channel
    user = get_user_by_id(st.session_state.user_id)
    st.subheader("Profile")
    st.write(f"**Username:** {user['username']} | **Email:** {user['email']}")
    st.markdown("---")
    st.subheader("YouTube API Key")
    with st.form("api_form"):
        api_key = st.text_input("API Key", value=user.get('youtube_api_key',''), type="password")
        if st.form_submit_button("Save"):
            if api_key: update_user_api_key(st.session_state.user_id, api_key); st.success("Saved!"); st.rerun()
    if user.get('youtube_api_key'): st.success("✅ API Key set")
    else: st.warning("⚠️ No API Key")
    st.markdown("---")
    st.subheader("Channel Info")
    with st.form("channel_form"):
        handle = st.text_input("Channel Handle", value=user.get('channel_handle',''), placeholder="@YourChannel")
        channel_id = st.text_input("Channel ID", value=user.get('channel_id',''), placeholder="UC...")
        subs = st.number_input("Subscribers", value=user.get('subscriber_count',0), min_value=0)
        if st.form_submit_button("Save Channel"):
            update_user_channel(st.session_state.user_id, handle, channel_id, int(subs)); st.success("Saved!"); st.rerun()
    st.markdown("---")
    st.markdown("**Get API key:** [Google Cloud Console](https://console.cloud.google.com/) → Create project → Enable YouTube Data API v3 → Credentials → Create API Key")
