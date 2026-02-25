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

# ─── CUSTOM CSS ───
st.markdown("""
<style>
.vps-box {
    padding: 25px; border-radius: 15px; text-align: center;
    margin: 15px 0; border: 3px solid;
}
.pillar-header { font-size: 18px; font-weight: bold; margin-bottom: 10px; }
.score-row { padding: 4px 0; font-size: 14px; }
.video-card {
    padding: 10px; border-radius: 8px; margin: 5px 0;
    border: 1px solid #333; background: #1a1a2e;
}
.video-card a { color: #4da6ff; text-decoration: none; }
.video-card a:hover { text-decoration: underline; }
.gate-pass { color: #2ECC40; font-weight: bold; }
.gate-fail { color: #FF4136; font-weight: bold; }
.gate-cond { color: #FF851B; font-weight: bold; }
.insight-box { padding: 8px 12px; border-left: 3px solid #4da6ff; margin: 5px 0; font-size: 13px; }
.metric-card {
    padding: 15px; border-radius: 10px; text-align: center;
    border: 1px solid #444; margin: 5px 0;
}
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ───
st.sidebar.title("🎯 CaseFinder")
st.sidebar.caption("Viral Crime Case Detection v3.2")

if st.session_state.authenticated:
    user = get_user_by_id(st.session_state.user_id)
    st.sidebar.success(f"👤 **{user['username']}**")
    if user.get('subscriber_count', 0) > 0:
        st.sidebar.caption(f"📺 {user['subscriber_count']:,} subs")
    menu = st.sidebar.radio("", [
        "🏠 Home", "🎯 Score a Case", "📊 Batch Score",
        "🔍 Discover", "👁️ Watchlist", "🏆 Rankings",
        "📈 Results", "⚙️ Settings"
    ])
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"):
        auth.logout_user()
        st.rerun()
else:
    st.sidebar.info("Please log in")
    menu = "🔐 Login / Register"

# ═══════════════════════════════════════
# LOGIN / REGISTER
# ═══════════════════════════════════════
if menu == "🔐 Login / Register":
    st.title("🔐 Login or Register")
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", use_container_width=True):
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
            if st.form_submit_button("Create Account", use_container_width=True):
                if new_email and new_username and new_password:
                    if new_password != confirm: st.error("Passwords don't match.")
                    else:
                        ok, msg = auth.register_user(new_email, new_username, new_password)
                        if ok: st.success(msg)
                        else: st.error(msg)

# ═══════════════════════════════════════
# HOME
# ═══════════════════════════════════════
elif menu == "🏠 Home":
    st.title("🎯 CaseFinder")
    st.markdown("### Viral Crime Case Detection System v3.2")
    st.markdown("""
    Analyzes true crime cases using **YouTube data**, **Wikipedia**, and **comment analysis** 
    to produce a **Viral Potential Score (VPS)** out of 100.
    """)
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("#### 🎯 Score")
        st.write("Full VPS with 16 parameters across 3 pillars")
    with col2:
        st.markdown("#### 📊 Batch")
        st.write("Score multiple cases and auto-rank them")
    with col3:
        st.markdown("#### 🔍 Discover")
        st.write("Find candidates from YouTube + seed list")
    with col4:
        st.markdown("#### 👁️ Track")
        st.write("Watchlist, rankings, results")
    st.markdown("---")
    st.markdown("""
    **VPS Rating Scale:**
    - 🔥 **90-100** — MUST MAKE THIS VIDEO
    - ✅ **75-89** — STRONG CANDIDATE  
    - 👍 **60-74** — WORTH CONSIDERING
    - ⚠️ **40-59** — RISKY
    - ❌ **0-39** — SKIP
    """)

# ═══════════════════════════════════════
# SCORE A CASE
# ═══════════════════════════════════════
elif menu == "🎯 Score a Case":
    st.title("🎯 Score a Case")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    user = get_user_by_id(st.session_state.user_id)
    if not user.get('youtube_api_key'):
        st.error("⚠️ Add your YouTube API key in Settings first!"); st.stop()

    case_name = st.text_input("Enter case name", placeholder="e.g., Alonzo Brooks, Elisa Lam, Maura Murray")
    score_btn = st.button("🎯 Score Case", use_container_width=True)

    if score_btn and case_name:
        progress_bar = st.progress(0)
        status = st.empty()
        phases = {0: 0, 1: 10, 2: 25, 3: 40, 4: 55, 5: 70, 6: 85}

        def update_progress(phase, msg):
            progress_bar.progress(phases.get(phase, 0))
            status.text(f"⏳ {msg}")

        try:
            result = score_case(case_name, user['youtube_api_key'],
                              user.get('subscriber_count', 0), update_progress)
            progress_bar.progress(100)
            status.text("✅ Complete!")
            st.session_state.last_result = result
        except Exception as e:
            st.error(f"Scoring error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

    result = st.session_state.last_result
    if result:
        if result.get("error"):
            st.error(f"Error: {result['error']}")
        else:
            try:
                save_score(st.session_state.user_id, result["case_name"], {
                    "vps": result["vps"], "rating": result["rating"],
                    "demand": result["demand"], "supply": result["supply"],
                    "emotional": result["emotional"],
                    "case_name": result["case_name"],
                    "angle": result.get("angle", ""),
                })
            except: pass

            vps = result['vps']
            if vps >= 90: color = "#FF4500"; bg = "#FF45001A"
            elif vps >= 75: color = "#2ECC40"; bg = "#2ECC401A"
            elif vps >= 60: color = "#0074D9"; bg = "#0074D91A"
            elif vps >= 40: color = "#FF851B"; bg = "#FF851B1A"
            else: color = "#AAAAAA"; bg = "#AAAAAA1A"

            # ─── VPS HEADER ───
            st.markdown(f"""
            <div style="padding:25px; border:3px solid {color}; border-radius:15px; text-align:center; margin:15px 0; background:{bg};">
                <h1 style="margin:0; font-size:60px; color:{color};">{vps}/100</h1>
                <p style="margin:5px 0; font-size:22px; font-weight:bold;">{result['rating']}</p>
                <p style="margin:0; font-size:14px; color:#888;">{result.get('mode','')}</p>
                <p style="margin:5px 0; font-size:16px;">📌 {result.get('angle','')}</p>
            </div>
            """, unsafe_allow_html=True)

            # ─── THREE PILLARS ───
            st.markdown("---")
            tab_demand, tab_supply, tab_emotion = st.tabs(["📊 Demand ("+str(result['demand'])+"/50)", "📉 Supply Gap ("+str(result['supply'])+"/25)", "🔥 Emotional ("+str(result['emotional'])+"/35)"])

            with tab_demand:
                st.markdown(f"### 📊 Demand Signal: {result['demand']}/50")
                d_col1, d_col2 = st.columns(2)
                with d_col1:
                    st.metric("D1 — Peak Views", f"{result['d1']}/15", 
                             f"{result.get('peak_views',0):,} views")
                    st.caption(f"Best on: [{result.get('peak_channel','?')}](https://www.youtube.com/results?search_query={result.get('peak_channel','').replace(' ','+')})")
                    st.metric("D2 — Multi-Creator", f"{result['d2']}/10",
                             f"{result.get('creators_100k',0)} channels with 100K+")
                    st.metric("D3 — Cross-Platform", f"{result['d3']}/10",
                             ', '.join(result.get('d3_sources',[])) or 'none found')
                with d_col2:
                    st.metric("D4 — Search Demand", f"{result['d4']}/5")
                    st.metric("D5 — Pre-YT Buzz", f"{result['d5']}/5",
                             result.get('d5_source','none'))
                    st.metric("D6 — Long-Form Proof", f"{result['d6']}/5")

            with tab_supply:
                st.markdown(f"### 📉 Supply Gap: {result['supply']}/25")
                s_col1, s_col2 = st.columns(2)
                with s_col1:
                    st.metric("S1 — Recency Gap", f"{result['s1']}/15",
                             f"{result.get('s1_months',0)} months since quality video")
                    st.metric("S2 — Quality Gap", f"{result['s2']}/10",
                             f"dur:{result.get('s2_dur',0)} like:{result.get('s2_lr',0)} comp:{result.get('s2_comp',0)}")
                with s_col2:
                    st.metric("S3 — Timing", f"{result['s3']}/5",
                             result.get('s3_reason','none'))
                    s4_val = result['s4']
                    st.metric("S4 — Saturation", f"{s4_val}",
                             f"{result.get('s4_mega',0)} mega-videos (500K+)")
                if result['s1'] >= 12:
                    st.success("🎯 **Big supply gap!** This case hasn't been covered well recently.")
                if s4_val <= -7:
                    st.warning("⚠️ Heavy saturation — many creators already covered this.")

            with tab_emotion:
                st.markdown(f"### 🔥 Emotional Heat: {result['emotional']}/35")
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    st.metric("E1 — Comment/View Ratio", f"{result['e1']}/8",
                             f"{result.get('avg_cvr',0):.2f}%")
                    st.metric("E2 — Emotional Intensity", f"{result['e2']}/8",
                             f"Dominant: {result.get('dominant_emotion','neutral')}")
                    st.metric("E3 — Unresolved Questions", f"{result['e3']}/5")
                with e_col2:
                    st.metric("E4 — Theory Activity", f"{result['e4']}/4")
                    st.metric("E5 — Content Requests", f"{result['e5']}/5")
                    st.metric("R — Rabbit Hole", f"{result['r']}/5",
                             ', '.join(result.get('r_details',[])) or 'none')
                st.caption(f"📊 {result.get('total_comments',0)} comments analyzed")

            # ─── GATES ───
            st.markdown("---")
            st.markdown("### 🔒 Gates")
            g1, g2, g3 = st.columns(3)
            with g1:
                gn = result.get('gate_n','?')
                icon = "✅" if gn == "PASS" else "❌"
                st.markdown(f"**N — Narrative:** {icon} {gn}")
                elems = result.get('gate_n_elements',[])
                if elems: st.caption(f"Found: {', '.join(elems)}")
            with g2:
                gt = result.get('gate_t','?')
                icon = "✅" if gt == "PASS" else "⚠️"
                st.markdown(f"**T — Thumbnail:** {icon} {gt}")
                st.caption(result.get('gate_t_detail',''))
            with g3:
                gc = result.get('gate_c','?')
                st.markdown(f"**C — Competition:** {gc}")
                st.caption(result.get('gate_c_detail',''))

            # ─── TOP VIDEOS (CLICKABLE) ───
            top_vids = result.get('top_videos', [])
            if top_vids:
                st.markdown("---")
                st.markdown("### 🎬 Top Videos Analyzed")
                for v in top_vids:
                    vid_url = f"https://www.youtube.com/watch?v={v['video_id']}"
                    ch_url = f"https://www.youtube.com/channel/{v['channel_id']}"
                    views = v['views']
                    dur = v['duration']
                    st.markdown(f"""
                    <div class="video-card">
                        <a href="{vid_url}" target="_blank">🎥 {v['title']}</a><br>
                        <small>
                            📺 <a href="{ch_url}" target="_blank">{v['channel']}</a> · 
                            👁️ {views:,} views · 
                            ⏱️ {dur:.0f} min · 
                            👍 {v['likes']:,} likes · 
                            💬 {v['comments']:,} comments · 
                            📅 {v['published']}
                        </small>
                    </div>
                    """, unsafe_allow_html=True)

            # ─── ANGLE & TITLES ───
            st.markdown("---")
            st.markdown(f"### 📌 Recommended Angle: {result.get('angle','')}")
            st.info(f"**Why:** {result.get('angle_reason','')}")
            st.markdown("**Suggested Titles:**")
            for i, t in enumerate(result.get('titles', []), 1):
                st.markdown(f"{i}. *{t}*")

            if result.get('contrarian'):
                st.markdown(f"### 🔄 Contrarian Angle: {result['contrarian']['angle']}")
                st.warning(f"**Dominant theory:** {result['contrarian'].get('dominant_theory','')[:120]}")
                for t in result.get('contrarian_titles', []):
                    st.markdown(f"• *{t}*")

            # ─── COMMENT INSIGHTS ───
            st.markdown("---")
            st.markdown("### 💬 Comment Insights")
            ins_tab1, ins_tab2, ins_tab3, ins_tab4 = st.tabs(["❓ Questions", "💭 Theories", "📢 Requests", "⚠️ Complaints"])

            with ins_tab1:
                questions = result.get('top_questions', [])
                if questions:
                    st.markdown(f"**{len(questions)} key audience questions found:**")
                    for q in questions:
                        st.markdown(f'<div class="insight-box">❓ {q}</div>', unsafe_allow_html=True)
                else: st.info("No significant questions found in comments.")

            with ins_tab2:
                theories = result.get('top_theories', [])
                if theories:
                    st.markdown(f"**{len(theories)} theories found:**")
                    for t in theories:
                        st.markdown(f'<div class="insight-box">💭 {t}</div>', unsafe_allow_html=True)
                else: st.info("No significant theories found.")

            with ins_tab3:
                reqs = result.get('top_requests', [])
                if reqs:
                    st.markdown(f"**{len(reqs)} content requests found:**")
                    for r in reqs:
                        st.markdown(f'<div class="insight-box">📢 {r}</div>', unsafe_allow_html=True)
                else: st.info("No content requests found.")

            with ins_tab4:
                comps = result.get('top_complaints', [])
                if comps:
                    st.markdown(f"**{len(comps)} complaints about existing coverage:**")
                    for c in comps:
                        st.markdown(f'<div class="insight-box">⚠️ {c}</div>', unsafe_allow_html=True)
                else: st.info("No complaints found.")

            st.markdown("---")
            st.success("💾 Score saved to rankings!")
            if st.button("🗑️ Clear Results"):
                st.session_state.last_result = None
                st.rerun()

# ═══════════════════════════════════════
# BATCH SCORE
# ═══════════════════════════════════════
elif menu == "📊 Batch Score":
    st.title("📊 Batch Score")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    user = get_user_by_id(st.session_state.user_id)
    if not user.get('youtube_api_key'):
        st.error("Add API key in Settings first!"); st.stop()

    cases_text = st.text_area("Enter case names (one per line)", placeholder="Alonzo Brooks\nElisa Lam\nMaura Murray", height=150)
    if st.button("📊 Score All Cases", use_container_width=True):
        cases = [c.strip() for c in cases_text.strip().split("\n") if c.strip()]
        if cases:
            results = []
            prog = st.progress(0)
            for i, case in enumerate(cases):
                st.write(f"⏳ Scoring: **{case}**...")
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
                    elif r and r.get("error"):
                        st.warning(f"⚠️ {case}: {r['error']}")
                except Exception as e: st.warning(f"❌ {case}: {e}")
                prog.progress((i+1) / len(cases))

            if results:
                results.sort(key=lambda x: x["vps"], reverse=True)
                st.markdown("---")
                st.markdown("### 📊 Final Rankings")
                for i, r in enumerate(results, 1):
                    vps = r['vps']
                    if vps >= 75: emoji = "🟢"
                    elif vps >= 60: emoji = "🔵"
                    elif vps >= 40: emoji = "🟡"
                    else: emoji = "🔴"
                    st.markdown(f"**#{i}** {emoji} **[{vps}/100]** {r['rating']} — **{r['case_name']}**")
                    st.caption(f"D:{r['demand']} S:{r['supply']} E:{r['emotional']} | 📌 {r.get('angle','')}")

# ═══════════════════════════════════════
# DISCOVER
# ═══════════════════════════════════════
elif menu == "🔍 Discover":
    st.title("🔍 Discover New Cases")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    user = get_user_by_id(st.session_state.user_id)
    if not user.get('youtube_api_key'):
        st.error("Add API key in Settings first!"); st.stop()

    st.markdown("Finds candidate cases from YouTube trending and our curated seed list, then quick-scores them.")
    if st.button("🔍 Find Candidates", use_container_width=True):
        status = st.empty()
        with st.spinner("Discovering cases..."):
            candidates = discover(user['youtube_api_key'], count=10,
                                 progress_callback=lambda msg: status.text(f"⏳ {msg}"))
        status.empty()
        if candidates:
            st.markdown("### 📊 Top Candidates (Quick-Scored)")
            for i, c in enumerate(candidates, 1):
                d1 = c["d1"]
                if d1 >= 9: label = "🔥"; desc = "Proven viral"
                elif d1 >= 6: label = "✅"; desc = "Strong interest"
                elif d1 >= 3: label = "👍"; desc = "Some interest"
                else: label = "⬜"; desc = "Low data"
                yt_link = f"https://www.youtube.com/results?search_query={c['name'].replace(' ','+')}"
                st.markdown(f"**#{i}** {label} [{c['name']}]({yt_link}) — D1: **{d1}**/15 | Peak: {c['peak']:,} | {desc} | *{c['source']}*")
            st.info("💡 Full-score the top picks using '🎯 Score a Case'")
        else: st.info("No candidates found.")

# ═══════════════════════════════════════
# WATCHLIST
# ═══════════════════════════════════════
elif menu == "👁️ Watchlist":
    st.title("👁️ Watchlist")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    from db.database import get_watchlist, add_to_watchlist, remove_from_watchlist
    with st.form("add_watch"):
        new_case = st.text_input("Add case to watchlist", placeholder="Case name")
        if st.form_submit_button("➕ Add", use_container_width=True):
            if new_case:
                if add_to_watchlist(st.session_state.user_id, new_case.title()):
                    st.success(f"Added **{new_case.title()}**!"); st.rerun()
                else: st.warning("Already in watchlist.")
    st.markdown("---")
    watchlist = get_watchlist(st.session_state.user_id)
    if watchlist:
        st.markdown(f"### Watching {len(watchlist)} cases")
        for item in watchlist:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                yt_link = f"https://www.youtube.com/results?search_query={item['case_name'].replace(' ','+')}+true+crime"
                st.markdown(f"• [{item['case_name']}]({yt_link})")
            with col2: st.caption(item['added_at'][:10])
            with col3:
                if st.button("🗑️", key=f"r_{item['id']}"):
                    remove_from_watchlist(st.session_state.user_id, item['case_name']); st.rerun()
    else: st.info("Your watchlist is empty. Add cases above!")

# ═══════════════════════════════════════
# RANKINGS
# ═══════════════════════════════════════
elif menu == "🏆 Rankings":
    st.title("🏆 Your Case Rankings")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    scores = get_user_scores(st.session_state.user_id)
    if scores:
        st.markdown(f"**{len(scores)} cases scored** — ranked by VPS")
        for i, s in enumerate(scores, 1):
            vps = s['vps']
            if vps >= 75: emoji = "🟢"
            elif vps >= 60: emoji = "🔵"
            elif vps >= 40: emoji = "🟡"
            else: emoji = "🔴"
            with st.expander(f"#{i} {emoji} [{vps}/100] {s['rating']} — {s['case_name']}"):
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("Demand", f"{s['demand']}/50")
                with c2: st.metric("Supply Gap", f"{s['supply']}/25")
                with c3: st.metric("Emotional", f"{s['emotional']}/35")
                st.caption(f"Scored: {s['scored_at'][:16]}")
                try:
                    data = json.loads(s.get('full_data','{}'))
                    if data.get('angle'): st.write(f"📌 **Angle:** {data['angle']}")
                except: pass
                yt_link = f"https://www.youtube.com/results?search_query={s['case_name'].replace(' ','+')}+true+crime"
                st.markdown(f"[🔍 Search on YouTube]({yt_link})")
    else: st.info("No scores yet. Go to '🎯 Score a Case' to get started!")

# ═══════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════
elif menu == "📈 Results":
    st.title("📈 Video Results")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    from db.database import save_result, get_user_results
    with st.form("add_result"):
        case = st.text_input("Case name")
        views = st.number_input("Views (30 days)", min_value=0, step=1000)
        if st.form_submit_button("💾 Save Result", use_container_width=True):
            if case and views > 0:
                save_result(st.session_state.user_id, case.title(), int(views))
                st.success("Saved!"); st.rerun()
    st.markdown("---")
    results = get_user_results(st.session_state.user_id)
    if results:
        st.markdown(f"### {len(results)} videos tracked")
        for r in results:
            st.write(f"**{r['case_name']}** — {r['views_30d']:,} views ({r['recorded_at'][:10]})")
        if len(results) >= 2:
            avg = sum(r['views_30d'] for r in results) / len(results)
            st.metric("Average Views (30d)", f"{avg:,.0f}")
    else: st.info("No results yet. Record after publishing a video!")

# ═══════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════
elif menu == "⚙️ Settings":
    st.title("⚙️ Settings")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    from db.database import update_user_api_key, update_user_channel
    user = get_user_by_id(st.session_state.user_id)

    st.subheader("👤 Profile")
    st.write(f"**Username:** {user['username']}")
    st.write(f"**Email:** {user['email']}")
    st.write(f"**Member since:** {user['created_at'][:10]}")

    st.markdown("---")
    st.subheader("🔑 YouTube API Key")
    with st.form("api_form"):
        api_key = st.text_input("API Key", value=user.get('youtube_api_key',''), type="password")
        if st.form_submit_button("💾 Save API Key", use_container_width=True):
            if api_key: update_user_api_key(st.session_state.user_id, api_key); st.success("Saved!"); st.rerun()
    if user.get('youtube_api_key'): st.success("✅ API Key configured")
    else: st.warning("⚠️ No API Key — you need one to score cases")

    st.markdown("---")
    st.subheader("📺 Channel Info")
    st.caption("Your subscriber count affects the Supply Gap boost in VPS scoring")
    with st.form("channel_form"):
        handle = st.text_input("Channel Handle", value=user.get('channel_handle',''), placeholder="@YourChannel")
        channel_id = st.text_input("Channel ID", value=user.get('channel_id',''), placeholder="UC...")
        subs = st.number_input("Subscriber Count", value=user.get('subscriber_count',0), min_value=0)
        if st.form_submit_button("💾 Save Channel Info", use_container_width=True):
            update_user_channel(st.session_state.user_id, handle, channel_id, int(subs)); st.success("Saved!"); st.rerun()
    if user.get('subscriber_count', 0) > 0:
        boost = max(1.0, 2.0 - (user['subscriber_count'] / 20000))
        st.info(f"📊 Your supply boost: **{boost:.1f}x** ({user['subscriber_count']:,} subs)")

    st.markdown("---")
    st.markdown("""
    #### How to get a YouTube API Key
    1. Go to [Google Cloud Console](https://console.cloud.google.com/)
    2. Create a new project
    3. Search for **"YouTube Data API v3"** and enable it
    4. Go to **Credentials** → **Create Credentials** → **API Key**
    5. Copy the key and paste it above
    """)
