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

# ─── HELPERS ───
def yt_video_link(vid_id, text=None):
    url = f"https://www.youtube.com/watch?v={vid_id}"
    label = text or vid_id
    return f'<a href="{url}" target="_blank">{label}</a>'

def yt_channel_link(ch_id, ch_name=None):
    url = f"https://www.youtube.com/channel/{ch_id}"
    label = ch_name or ch_id
    return f'<a href="{url}" target="_blank">{label}</a>'

def yt_search_link(query, text=None):
    import urllib.parse
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
    label = text or query
    return f'<a href="{url}" target="_blank">{label}</a>'

def wiki_link(name, text=None):
    import urllib.parse
    url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(name.replace(' ','_'))}"
    label = text or name
    return f'<a href="{url}" target="_blank">{label}</a>'

def reddit_search_link(name, text=None):
    import urllib.parse
    url = f"https://www.reddit.com/search/?q={urllib.parse.quote(name)}"
    label = text or "Reddit"
    return f'<a href="{url}" target="_blank">{label}</a>'

def render_comment(item, all_videos_map=None):
    """Render a comment with link to source video"""
    if isinstance(item, dict):
        text = item.get("text", "")
        vid = item.get("vid", "")
        src = item.get("src", "")
    else:
        text = str(item)
        vid = ""
        src = ""
    
    source_html = ""
    if vid and all_videos_map and vid in all_videos_map:
        v = all_videos_map[vid]
        source_html = f' — <small>[📺 {yt_video_link(vid, v.get("title","video")[:40])} by {yt_channel_link(v.get("channel_id",""), v.get("channel",""))}]</small>'
    elif vid:
        source_html = f' — <small>[{yt_video_link(vid, "🔗 source video")}]</small>'
    elif src:
        source_html = f' — <small>from {src}</small>'
    
    return f'<div style="padding:8px 12px; border-left:3px solid #4da6ff; margin:5px 0; font-size:13px;">{text}{source_html}</div>'

# ─── CSS ───
st.markdown("""
<style>
.video-card { padding:12px; border-radius:8px; margin:8px 0; border:1px solid #444; }
.video-card a { color: #4da6ff; text-decoration: none; }
.video-card a:hover { text-decoration: underline; color: #6dc0ff; }
a { color: #4da6ff; }
a:hover { color: #6dc0ff; }
.d3-source { display:inline-block; padding:3px 8px; margin:2px; border-radius:4px; background:#2a2a3e; font-size:12px; }
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ───
st.sidebar.title("🎯 CaseFinder")
st.sidebar.caption("Viral Crime Case Detection v3.2")

if st.session_state.authenticated:
    user = get_user_by_id(st.session_state.user_id)
    st.sidebar.success(f"👤 **{user['username']}**")
    if user.get('subscriber_count', 0) > 0:
        boost = max(1.0, 2.0 - (user['subscriber_count'] / 20000))
        st.sidebar.caption(f"📺 {user['subscriber_count']:,} subs | Boost: {boost:.1f}x")
    menu = st.sidebar.radio("", [
        "🏠 Home", "🎯 Score a Case", "📊 Batch Score",
        "🔍 Discover", "👁️ Watchlist", "🏆 Rankings",
        "📈 Results", "⚙️ Settings"
    ])
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout"): auth.logout_user(); st.rerun()
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
    st.markdown("Analyzes true crime cases using **YouTube data**, **Wikipedia**, and **comment analysis** to produce a **Viral Potential Score (VPS)** out of 100.")
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown("#### 🎯 Score"); st.write("16 parameters, 3 pillars, 3 gates")
    with col2: st.markdown("#### 📊 Batch"); st.write("Score multiple, auto-rank")
    with col3: st.markdown("#### 🔍 Discover"); st.write("YouTube + seed list")
    with col4: st.markdown("#### 👁️ Track"); st.write("Watchlist + results")
    st.markdown("---")
    st.markdown("🔥 90-100 MUST MAKE · ✅ 75-89 STRONG · 👍 60-74 WORTH IT · ⚠️ 40-59 RISKY · ❌ 0-39 SKIP")

# ═══════════════════════════════════════
# SCORE A CASE
# ═══════════════════════════════════════
elif menu == "🎯 Score a Case":
    st.title("🎯 Score a Case")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    user = get_user_by_id(st.session_state.user_id)
    if not user.get('youtube_api_key'): st.error("⚠️ Add YouTube API key in Settings!"); st.stop()

    case_name = st.text_input("Enter case name", placeholder="e.g., Alonzo Brooks, Elisa Lam")
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
            st.error(f"Error: {str(e)}")
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
                    "emotional": result["emotional"], "case_name": result["case_name"],
                    "angle": result.get("angle", ""),
                })
            except: pass

            vps = result['vps']
            avm = result.get('all_videos_map', {})
            case = result['case_name']

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
                <p style="margin:0; font-size:12px;">{wiki_link(case, '📖 Wikipedia')} · {yt_search_link(case+' true crime', '🔍 YouTube')} · {reddit_search_link(case, '💬 Reddit')}</p>
            </div>
            """, unsafe_allow_html=True)

            # ─── THREE PILLARS ───
            st.markdown("---")
            tab_d, tab_s, tab_e = st.tabs([f"📊 Demand ({result['demand']}/50)", f"📉 Supply ({result['supply']}/25)", f"🔥 Emotional ({result['emotional']}/35)"])

            with tab_d:
                st.markdown(f"### 📊 Demand Signal: {result['demand']}/50")
                d1, d2 = st.columns(2)
                with d1:
                    st.metric("D1 — Peak Views", f"{result['d1']}/15", f"{result.get('peak_views',0):,} views")
                    peak_ch = result.get('peak_channel','?')
                    # Find channel_id for peak channel
                    peak_ch_id = ""
                    for vid_data in result.get('top_videos', []):
                        if vid_data.get('channel') == peak_ch:
                            peak_ch_id = vid_data.get('channel_id', '')
                            break
                    if peak_ch_id:
                        st.markdown(f"Best on: {yt_channel_link(peak_ch_id, peak_ch)}", unsafe_allow_html=True)
                    else:
                        st.caption(f"Best on: {peak_ch}")

                    st.metric("D2 — Multi-Creator", f"{result['d2']}/10", f"{result.get('creators_100k',0)} channels with 100K+")

                    # D3 with clickable sources
                    st.metric("D3 — Cross-Platform", f"{result['d3']}/10")
                    d3s = result.get('d3_sources', [])
                    if d3s:
                        links = []
                        for src in d3s:
                            if src == "Wiki": links.append(wiki_link(case, "📖 Wiki"))
                            elif src == "Reddit": links.append(reddit_search_link(case, "💬 Reddit"))
                            elif src == "Podcast": links.append(f'<a href="https://www.google.com/search?q={case.replace(" ","+")}+podcast" target="_blank">🎙️ Podcast</a>')
                            elif src == "Doc": links.append(f'<a href="https://www.google.com/search?q={case.replace(" ","+")}+documentary" target="_blank">🎬 Doc</a>')
                            elif src == "News": links.append(f'<a href="https://news.google.com/search?q={case.replace(" ","+")}">📰 News</a>')
                            else: links.append(f'<span class="d3-source">{src}</span>')
                        st.markdown(" · ".join(links), unsafe_allow_html=True)
                    else:
                        st.caption("No cross-platform presence found")

                with d2:
                    st.metric("D4 — Search Demand", f"{result['d4']}/5")
                    d5s = result.get('d5_source', 'none')
                    st.metric("D5 — Pre-YT Buzz", f"{result['d5']}/5")
                    if d5s == "TikTok":
                        st.markdown(f'<a href="https://www.tiktok.com/search?q={case.replace(" ","+")}" target="_blank">📱 TikTok results</a>', unsafe_allow_html=True)
                    elif d5s == "Reddit":
                        st.markdown(reddit_search_link(case, "💬 Reddit threads"), unsafe_allow_html=True)
                    elif d5s == "Websleuths":
                        st.markdown(f'<a href="https://www.google.com/search?q=site:websleuths.com+{case.replace(" ","+")}">🔍 Websleuths</a>', unsafe_allow_html=True)
                    elif d5s != "none":
                        st.caption(d5s)
                    st.metric("D6 — Long-Form Proof", f"{result['d6']}/5")

            with tab_s:
                st.markdown(f"### 📉 Supply Gap: {result['supply']}/25")
                s1, s2 = st.columns(2)
                with s1:
                    st.metric("S1 — Recency Gap", f"{result['s1']}/15", f"{result.get('s1_months',0)} months")
                    st.metric("S2 — Quality Gap", f"{result['s2']}/10", f"dur:{result.get('s2_dur',0)} like:{result.get('s2_lr',0)} comp:{result.get('s2_comp',0)}")
                with s2:
                    st.metric("S3 — Timing", f"{result['s3']}/5", result.get('s3_reason','none'))
                    st.metric("S4 — Saturation", f"{result['s4']}", f"{result.get('s4_mega',0)} mega-videos")
                if result['s1'] >= 12:
                    st.success("🎯 Big supply gap — great opportunity!")
                if result['s4'] <= -7:
                    st.warning("⚠️ Heavy saturation")

            with tab_e:
                st.markdown(f"### 🔥 Emotional Heat: {result['emotional']}/35")
                e1, e2 = st.columns(2)
                with e1:
                    st.metric("E1 — CVR", f"{result['e1']}/8", f"{result.get('avg_cvr',0):.2f}%")
                    st.metric("E2 — Intensity", f"{result['e2']}/8", f"Dominant: {result.get('dominant_emotion','neutral')}")
                    st.metric("E3 — Questions", f"{result['e3']}/5")
                with e2:
                    st.metric("E4 — Theories", f"{result['e4']}/4")
                    st.metric("E5 — Requests", f"{result['e5']}/5")
                    st.metric("R — Rabbit Hole", f"{result['r']}/5", ', '.join(result.get('r_details',[])) or 'none')
                st.caption(f"📊 {result.get('total_comments',0)} comments analyzed from multiple videos")

            # ─── GATES ───
            st.markdown("---")
            st.markdown("### 🔒 Gates")
            g1, g2, g3 = st.columns(3)
            with g1:
                gn = result.get('gate_n','?')
                st.markdown(f"**N — Narrative:** {'✅ PASS' if gn == 'PASS' else '❌ FAIL'}")
                elems = result.get('gate_n_elements',[])
                if elems: st.caption(f"Found: {', '.join(elems)}")
            with g2:
                gt = result.get('gate_t','?')
                st.markdown(f"**T — Thumbnail:** {'✅' if gt == 'PASS' else '⚠️'} {gt}")
                td = result.get('gate_t_detail','')
                if "Wikipedia image" in td:
                    st.markdown(f"{wiki_link(case, '🖼️ View on Wikipedia')}", unsafe_allow_html=True)
                else:
                    st.caption(td)
            with g3:
                gc = result.get('gate_c','?')
                st.markdown(f"**C — Competition:** {gc}")
                gcd = result.get('gate_c_detail','')
                st.caption(gcd)

            # ─── TOP VIDEOS (CLICKABLE) ───
            top_vids = result.get('top_videos', [])
            if top_vids:
                st.markdown("---")
                st.markdown(f"### 🎬 Top {len(top_vids)} Videos Analyzed")
                for v in top_vids:
                    vid_url = f"https://www.youtube.com/watch?v={v['video_id']}"
                    ch_url = f"https://www.youtube.com/channel/{v['channel_id']}"
                    st.markdown(f"""
                    <div class="video-card">
                        <a href="{vid_url}" target="_blank" style="font-size:15px; font-weight:bold;">🎥 {v['title']}</a><br>
                        <small>
                            📺 <a href="{ch_url}" target="_blank">{v['channel']}</a> · 
                            👁️ {v['views']:,} views · 
                            ⏱️ {v['duration']:.0f} min · 
                            👍 {v['likes']:,} · 
                            💬 {v['comments']:,} · 
                            📅 {v['published']}
                        </small>
                    </div>
                    """, unsafe_allow_html=True)

            # ─── ANGLE & TITLES ───
            st.markdown("---")
            st.markdown(f"### 📌 Recommended Angle: {result.get('angle','')}")
            st.info(f"**Why:** {result.get('angle_reason','')}")
            for i, t in enumerate(result.get('titles', []), 1):
                st.markdown(f"**{i}.** *{t}*")

            if result.get('contrarian'):
                st.markdown("---")
                st.markdown(f"### 🔄 Contrarian Angle: {result['contrarian']['angle']}")
                dom_theory = result['contrarian'].get('dominant_theory','')
                if isinstance(dom_theory, dict):
                    dom_theory = dom_theory.get('text', str(dom_theory))
                st.warning(f"**Dominant theory:** {dom_theory[:150]}")
                for t in result.get('contrarian_titles', []):
                    st.markdown(f"• *{t}*")

            # ─── COMMENT INSIGHTS (FULL + LINKED) ───
            st.markdown("---")
            st.markdown("### 💬 Comment Insights")
            ins1, ins2, ins3, ins4 = st.tabs(["❓ Questions", "💭 Theories", "📢 Requests", "⚠️ Complaints"])

            with ins1:
                questions = result.get('top_questions', [])
                if questions:
                    st.markdown(f"**{len(questions)} key questions from the audience:**")
                    for q in questions:
                        st.markdown(render_comment(q, avm), unsafe_allow_html=True)
                else: st.info("No significant questions found.")

            with ins2:
                theories = result.get('top_theories', [])
                if theories:
                    st.markdown(f"**{len(theories)} theories found:**")
                    for t in theories:
                        st.markdown(render_comment(t, avm), unsafe_allow_html=True)
                else: st.info("No theories found.")

            with ins3:
                reqs = result.get('top_requests', [])
                if reqs:
                    st.markdown(f"**{len(reqs)} content requests:**")
                    for r in reqs:
                        st.markdown(render_comment(r, avm), unsafe_allow_html=True)
                else: st.info("No requests found.")

            with ins4:
                comps = result.get('top_complaints', [])
                if comps:
                    st.markdown(f"**{len(comps)} complaints about existing coverage:**")
                    for c in comps:
                        st.markdown(render_comment(c, avm), unsafe_allow_html=True)
                else: st.info("No complaints found.")

            st.markdown("---")
            st.success("💾 Score saved to rankings!")
            if st.button("🗑️ Clear Results"):
                st.session_state.last_result = None; st.rerun()

# ═══════════════════════════════════════
# BATCH SCORE
# ═══════════════════════════════════════
elif menu == "📊 Batch Score":
    st.title("📊 Batch Score")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    user = get_user_by_id(st.session_state.user_id)
    if not user.get('youtube_api_key'): st.error("Add API key in Settings!"); st.stop()

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
                            "vps": r["vps"], "rating": r["rating"], "demand": r["demand"],
                            "supply": r["supply"], "emotional": r["emotional"],
                            "case_name": r["case_name"], "angle": r.get("angle", ""),
                        })
                    elif r: st.warning(f"⚠️ {case}: {r['error']}")
                except Exception as e: st.warning(f"❌ {case}: {e}")
                prog.progress((i+1) / len(cases))
            if results:
                results.sort(key=lambda x: x["vps"], reverse=True)
                st.markdown("---")
                st.markdown("### 📊 Final Rankings")
                for i, r in enumerate(results, 1):
                    vps = r['vps']
                    emoji = "🟢" if vps >= 75 else "🔵" if vps >= 60 else "🟡" if vps >= 40 else "🔴"
                    yt = yt_search_link(r['case_name']+' true crime', '🔍')
                    wk = wiki_link(r['case_name'], '📖')
                    st.markdown(f"**#{i}** {emoji} **[{vps}/100]** {r['rating']} — **{r['case_name']}** {yt} {wk}", unsafe_allow_html=True)
                    st.caption(f"D:{r['demand']} S:{r['supply']} E:{r['emotional']} | 📌 {r.get('angle','')}")

# ═══════════════════════════════════════
# DISCOVER
# ═══════════════════════════════════════
elif menu == "🔍 Discover":
    st.title("🔍 Discover New Cases")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    user = get_user_by_id(st.session_state.user_id)
    if not user.get('youtube_api_key'): st.error("Add API key in Settings!"); st.stop()
    st.markdown("Finds cases from YouTube trending + curated seed list, then quick-scores them.")
    if st.button("🔍 Find Candidates", use_container_width=True):
        status = st.empty()
        with st.spinner("Discovering..."):
            candidates = discover(user['youtube_api_key'], count=10, progress_callback=lambda msg: status.text(f"⏳ {msg}"))
        status.empty()
        if candidates:
            st.markdown("### 📊 Top Candidates")
            for i, c in enumerate(candidates, 1):
                d1 = c["d1"]
                label = "🔥" if d1 >= 9 else "✅" if d1 >= 6 else "👍" if d1 >= 3 else "⬜"
                name = c['name']
                yt = yt_search_link(name+' true crime', '🔍 YT')
                wk = wiki_link(name, '📖')
                rd = reddit_search_link(name, '💬')
                st.markdown(f"**#{i}** {label} **{name}** — D1: **{d1}**/15 | Peak: {c['peak']:,} | {c['source']} | {yt} {wk} {rd}", unsafe_allow_html=True)
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
        new_case = st.text_input("Add case", placeholder="Case name")
        if st.form_submit_button("➕ Add", use_container_width=True):
            if new_case:
                if add_to_watchlist(st.session_state.user_id, new_case.title()): st.success("Added!"); st.rerun()
                else: st.warning("Already exists.")
    st.markdown("---")
    watchlist = get_watchlist(st.session_state.user_id)
    if watchlist:
        st.markdown(f"### Watching {len(watchlist)} cases")
        for item in watchlist:
            name = item['case_name']
            col1, col2 = st.columns([5, 1])
            with col1:
                yt = yt_search_link(name+' true crime', '🔍')
                wk = wiki_link(name, '📖')
                rd = reddit_search_link(name, '💬')
                st.markdown(f"• **{name}** {yt} {wk} {rd} <small>({item['added_at'][:10]})</small>", unsafe_allow_html=True)
            with col2:
                if st.button("🗑️", key=f"r_{item['id']}"): remove_from_watchlist(st.session_state.user_id, name); st.rerun()
    else: st.info("Empty.")

# ═══════════════════════════════════════
# RANKINGS
# ═══════════════════════════════════════
elif menu == "🏆 Rankings":
    st.title("🏆 Rankings")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    scores = get_user_scores(st.session_state.user_id)
    if scores:
        st.markdown(f"**{len(scores)} cases scored**")
        for i, s in enumerate(scores, 1):
            vps = s['vps']
            emoji = "🟢" if vps >= 75 else "🔵" if vps >= 60 else "🟡" if vps >= 40 else "🔴"
            name = s['case_name']
            with st.expander(f"#{i} {emoji} [{vps}/100] {s['rating']} — {name}"):
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("Demand", f"{s['demand']}/50")
                with c2: st.metric("Supply", f"{s['supply']}/25")
                with c3: st.metric("Emotional", f"{s['emotional']}/35")
                try:
                    data = json.loads(s.get('full_data','{}'))
                    if data.get('angle'): st.write(f"📌 {data['angle']}")
                except: pass
                yt = yt_search_link(name+' true crime', '🔍 YouTube')
                wk = wiki_link(name, '📖 Wikipedia')
                rd = reddit_search_link(name, '💬 Reddit')
                st.markdown(f"{yt} · {wk} · {rd}", unsafe_allow_html=True)
                st.caption(f"Scored: {s['scored_at'][:16]}")
    else: st.info("No scores yet.")

# ═══════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════
elif menu == "📈 Results":
    st.title("📈 Results")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    from db.database import save_result, get_user_results
    with st.form("add_result"):
        case = st.text_input("Case name")
        views = st.number_input("Views (30d)", min_value=0, step=1000)
        if st.form_submit_button("💾 Save", use_container_width=True):
            if case and views > 0: save_result(st.session_state.user_id, case.title(), int(views)); st.success("Saved!"); st.rerun()
    st.markdown("---")
    results = get_user_results(st.session_state.user_id)
    if results:
        for r in results: st.write(f"**{r['case_name']}** — {r['views_30d']:,} views ({r['recorded_at'][:10]})")
        if len(results) >= 2:
            avg = sum(r['views_30d'] for r in results) / len(results)
            st.metric("Average Views", f"{avg:,.0f}")
    else: st.info("No results yet.")

# ═══════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════
elif menu == "⚙️ Settings":
    st.title("⚙️ Settings")
    if not st.session_state.authenticated: st.warning("Please login."); st.stop()
    from db.database import update_user_api_key, update_user_channel
    user = get_user_by_id(st.session_state.user_id)
    st.write(f"**{user['username']}** · {user['email']} · since {user['created_at'][:10]}")
    st.markdown("---")
    st.subheader("🔑 YouTube API Key")
    with st.form("api_form"):
        api_key = st.text_input("API Key", value=user.get('youtube_api_key',''), type="password")
        if st.form_submit_button("💾 Save", use_container_width=True):
            if api_key: update_user_api_key(st.session_state.user_id, api_key); st.success("Saved!"); st.rerun()
    if user.get('youtube_api_key'): st.success("✅ Set")
    else: st.warning("⚠️ Not set")
    st.markdown("---")
    st.subheader("📺 Channel")
    with st.form("ch_form"):
        handle = st.text_input("Handle", value=user.get('channel_handle',''), placeholder="@YourChannel")
        ch_id = st.text_input("Channel ID", value=user.get('channel_id',''), placeholder="UC...")
        subs = st.number_input("Subscribers", value=user.get('subscriber_count',0), min_value=0)
        if st.form_submit_button("💾 Save", use_container_width=True):
            update_user_channel(st.session_state.user_id, handle, ch_id, int(subs)); st.success("Saved!"); st.rerun()
    if user.get('subscriber_count', 0) > 0:
        boost = max(1.0, 2.0 - (user['subscriber_count'] / 20000))
        st.info(f"Supply boost: **{boost:.1f}x** ({user['subscriber_count']:,} subs)")
    st.markdown("---")
    st.markdown("[Get API key →](https://console.cloud.google.com/) Create project → Enable YouTube Data API v3 → Credentials → API Key")
