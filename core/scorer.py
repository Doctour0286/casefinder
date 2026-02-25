"""
CaseFinder v1.0 Web — VPS Scoring Engine
Faithfully ported from case-finder.py v3.2
Only changes: urllib→requests, subprocess→direct calls, print→dict returns
All scoring logic, thresholds, keywords, and formulas are IDENTICAL.
"""

import json, re, time, requests
from datetime import datetime, timedelta

API_BASE = "https://www.googleapis.com/youtube/v3"

# ─── API Helpers ───

def yt_api(endpoint, params, api_key):
    params['key'] = api_key
    url = f"{API_BASE}/{endpoint}"
    try:
        resp = requests.get(url, params=params,
                           headers={'User-Agent': 'CaseFinder/2.0'}, timeout=20)
        return resp.json()
    except Exception as e:
        return {"error": str(e), "items": []}

def search_yt(query, api_key, order="viewCount", n=10, duration="medium", lang="en"):
    params = {
        "part": "snippet", "q": query, "type": "video",
        "order": order, "maxResults": n
    }
    if duration != "any":
        params["videoDuration"] = duration
    else:
        if lang:
            params["relevanceLanguage"] = lang
    data = yt_api("search", params, api_key)
    return data.get("items", [])

def video_stats(ids, api_key):
    if not ids: return []
    data = yt_api("videos", {
        "part": "snippet,statistics,contentDetails",
        "id": ",".join(ids[:50])
    }, api_key)
    return data.get("items", [])

def get_comments(vid_id, api_key, n=100, order="relevance"):
    data = yt_api("commentThreads", {
        "part": "snippet", "videoId": vid_id,
        "maxResults": min(n, 100), "order": order
    }, api_key)
    comments = []
    for item in data.get("items", []):
        cid = item.get("id", "")
        s = item["snippet"]["topLevelComment"]["snippet"]
        comments.append({
            "id": cid,
            "text": s.get("textDisplay", ""),
            "likes": s.get("likeCount", 0),
            "author": s.get("authorDisplayName", "")
        })
    return comments

def get_comments_extended(vid_id, api_key):
    c_rel = get_comments(vid_id, api_key, n=100, order="relevance")
    c_time = get_comments(vid_id, api_key, n=100, order="time")
    seen = set()
    merged = []
    for c in c_rel + c_time:
        if c["id"] and c["id"] not in seen:
            seen.add(c["id"])
            merged.append(c)
        elif not c["id"]:
            key = c["text"][:80].lower().strip()
            if key not in seen:
                seen.add(key)
                merged.append(c)
    return merged

def channel_subs(channel_id, api_key):
    data = yt_api("channels", {"part": "statistics", "id": channel_id}, api_key)
    items = data.get("items", [])
    if items:
        return int(items[0]["statistics"].get("subscriberCount", 0))
    return 0

# ─── Wikipedia ───

def wiki_read(case_name):
    import urllib.parse
    wiki_name = case_name.replace(" ", "_")
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "", wiki_name)
    prefixes = [
        "Murder_of_" + wiki_name, "Disappearance_of_" + wiki_name,
        "Death_of_" + wiki_name, "Killing_of_" + wiki_name,
        wiki_name, wiki_name + "_case",
        "Murder_of_" + safe_name, "Disappearance_of_" + safe_name,
        "Killing_of_" + safe_name, safe_name
    ]
    seen = set()
    unique = [p for p in prefixes if p not in seen and not seen.add(p)]
    for title in unique:
        try:
            encoded = urllib.parse.quote(title)
            url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + encoded
            resp = requests.get(url, headers={"User-Agent": "CaseFinder/2.0"}, timeout=15)
            data = resp.json()
            text = data.get("extract", "")
            if text and len(text.strip()) > 100:
                return text[:5000]
        except: continue
    for title in unique:
        try:
            encoded = urllib.parse.quote(title)
            url = "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=true&exsectionformat=plain&titles=" + encoded + "&format=json"
            resp = requests.get(url, headers={"User-Agent": "CaseFinder/2.0"}, timeout=15)
            data = resp.json()
            for pid, page in data.get("query",{}).get("pages",{}).items():
                if pid != "-1":
                    text = page.get("extract", "")
                    if text and len(text.strip()) > 100:
                        return text[:5000]
        except: continue
    try:
        import urllib.parse
        sq = urllib.parse.quote(case_name)
        url = "https://en.wikipedia.org/w/api.php?action=opensearch&search=" + sq + "&limit=3&format=json"
        resp = requests.get(url, headers={"User-Agent": "CaseFinder/2.0"}, timeout=15)
        data = resp.json()
        if len(data) >= 2 and data[1]:
            found = urllib.parse.quote(data[1][0].replace(" ", "_"))
            url2 = "https://en.wikipedia.org/api/rest_v1/page/summary/" + found
            resp2 = requests.get(url2, headers={"User-Agent": "CaseFinder/2.0"}, timeout=15)
            data2 = resp2.json()
            text = data2.get("extract", "")
            if text and len(text.strip()) > 100:
                return text[:5000]
    except: pass
    return ""

def wiki_has_image(case_name):
    import urllib.parse
    wiki_name = case_name.replace(" ", "_")
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "", wiki_name)
    titles = []
    for prefix in ["Murder_of_", "Disappearance_of_", "Death_of_", "Killing_of_", ""]:
        for name in [wiki_name, safe_name]:
            t = prefix + name
            if t not in titles:
                titles.append(t)
    for title in titles:
        try:
            encoded = urllib.parse.quote(title)
            url = f"https://en.wikipedia.org/w/api.php?action=query&titles={encoded}&prop=pageimages&format=json&pithumbsize=300&redirects=true"
            resp = requests.get(url, headers={"User-Agent": "CaseFinder/2.0"}, timeout=15)
            data = resp.json()
            for pid, page in data.get("query",{}).get("pages",{}).items():
                if pid != "-1" and page.get("thumbnail"):
                    return True, "Wikipedia image (free license)"
        except: continue
    for title in titles:
        try:
            encoded = urllib.parse.quote(title)
            url = f"https://en.wikipedia.org/w/api.php?action=parse&page={encoded}&prop=images&format=json&redirects=true"
            resp = requests.get(url, headers={"User-Agent": "CaseFinder/2.0"}, timeout=15)
            data = resp.json()
            if "parse" in data:
                images = data["parse"].get("images", [])
                skip = ["icon","logo","flag","map_marker","edit","lock",
                        "question","ambox","wiki","commons","stub",
                        "crystal","nuvola","gnome","tango","ooui",
                        "symbol","pictogram","padlock","emblem"]
                real = [img for img in images if not any(s in img.lower() for s in skip)]
                if real:
                    return True, f"Wikipedia images ({len(real)} found)"
        except: continue
    return False, ""

# ─── Duration / Filtering ───

def parse_duration(iso):
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso or "")
    if not m: return 0
    return int(m.group(1) or 0)*60 + int(m.group(2) or 0) + int(m.group(3) or 0)/60

def is_short(video):
    dur = parse_duration(video.get("contentDetails",{}).get("duration",""))
    if dur < 1.5: return True
    title = video.get("snippet",{}).get("title","").lower()
    if "#shorts" in title or "#short" in title: return True
    return False

def filter_shorts(videos):
    return [v for v in videos if not is_short(v)]

def is_english(text):
    t = " " + text.lower() + " "
    en_words = [" the ", " is ", " was ", " are ", " and ", " but ", " not ",
        " this ", " that ", " have ", " has ", " with ", " for ", " they ",
        " been ", " what ", " when ", " who ", " how ", " why ", " would ",
        " could ", " should ", " she ", " her ", " his ", " don't ", " didn't ",
        " can't ", " won't ", " you ", " were ", " just ", " about ",
        " think ", " know ", " really ", " never ", " still ", " because "]
    hits = sum(1 for w in en_words if w in t)
    if hits >= 2: return True
    if len(text.strip()) < 20:
        if hits >= 1: return True
        alpha = sum(1 for c in text if c.isalpha())
        if alpha < 3: return True
        return False
    if hits == 1: return True
    ascii_alpha = sum(1 for c in text if c.isascii() and c.isalpha())
    total_alpha = sum(1 for c in text if c.isalpha())
    if total_alpha == 0: return True
    if (ascii_alpha / total_alpha) < 0.5: return False
    return False

def is_english_video(video):
    snippet = video.get("snippet", {})
    lang = (snippet.get("defaultLanguage") or "").lower()
    audio = (snippet.get("defaultAudioLanguage") or "").lower()
    if lang.startswith("en") or audio.startswith("en"): return True
    if (lang and not lang.startswith("en")) or (audio and not audio.startswith("en")): return False
    title = " " + snippet.get("title", "").lower() + " "
    en_words = [" the ", " of ", " and ", " is ", " was ", " what ", " who ",
        " how ", " why ", " this ", " that ", " true crime ", " murder ",
        " killed ", " death ", " case ", " mystery ", " story ", " full ",
        " disappearance ", " missing ", " unsolved ", " investigation ",
        " documentary ", " explained ", " evidence ", " suspect ",
        " victim ", " trial ", " part ", " untold ", " solved "]
    if sum(1 for w in en_words if w in title) >= 1: return True
    ch = " " + snippet.get("channelTitle", "").lower() + " "
    ch_words = [" true crime ", " crime ", " mystery ", " case ",
        " stories ", " explained ", " news ", " documentary "]
    if sum(1 for w in ch_words if w in ch) >= 1: return True
    return False

# ─── Keyword Lists (IDENTICAL to v3.2) ───

ANGER = ["angry","furious","disgusting","outrage","justice","monster",
    "evil","rot in","death penalty","sick","how dare","blood boil",
    "infuriating","scum","lock them up","deserves","failed","corrupt"]
SADNESS = ["cry","crying","tears","heartbreaking","devastating","tragic",
    "broke my heart","sobbing","so sad","poor","rest in peace","rip",
    "innocent","didn't deserve","gut-wrenching","gone too soon"]
FEAR = ["terrifying","chilling","haunting","nightmare","shocked",
    "unbelievable","can't believe","insane","scary","disturbing",
    "horrifying","creepy","gave me chills","goosebumps","couldn't sleep"]
OBSESSION = ["can't stop thinking","obsessed","came back to watch",
    "watched this 3 times","still thinking about","keeps me up at night",
    "never forget","binge","rabbit hole","went down a","hours researching",
    "need to know","consumed by"]
QUESTIONS_STRONG = ["why didn't","how come","what about","what happened to",
    "nobody talks about","does anyone know","has anyone",
    "still don't understand","don't get","nobody mentions",
    "everyone ignores","makes no sense","doesn't add up",
    "how is it possible","explain","how did","where was",
    "where were","what was","who was","who is","why was",
    "why would","why did"]
QUESTIONS_MARK_SKIP = ["anyone else","who else","who's watching",
    "who is watching","am i the only","can you imagine",
    "is it just me","right?","no?","yes?","isn't it",
    "hiding in the comments","comment section",
    "like if you","who came here","anyone here",
    "subscribe","notification","bell","3am","2am","1am",
    "at night","who's here","whos here"]
THEORIES = ["i think","my theory","theory:","what if","could it be",
    "maybe the","i suspect","i believe","hear me out",
    "unpopular opinion","nobody considered","consider this",
    "evidence points to","connecting the dots"]
REQUESTS = ["please cover","please do","follow up","follow-up",
    "part 2","part two","update","more about","deeper dive",
    "full story","can someone make","need more","want to know more",
    "someone needs to cover","why hasn't anyone"]
COMPLAINTS = ["wrong","incorrect","actually,","missed","didn't mention",
    "left out","inaccurate","not true","forgot","skipped",
    "disappointing","clickbait","misleading","surface level",
    "shallow","rushed","too short","oversimplified"]
NARRATIVE = {
    "mystery": ["unsolved","unknown","unidentified","mystery","mysterious",
        "cold case","no suspect","who killed","disappeared","never found",
        "baffling","puzzling","unexplained","enigma","unanswered",
        "what happened","remains unclear","strange","bizarre","perplexing"],
    "twist": ["twist","surprise","unexpected","shocking discovery",
        "turned out","revealed that","nobody expected",
        "however","but then","actually","in fact","revelation",
        "plot twist","discovered that","it emerged","contradiction",
        "bombshell","stunned","shocked to learn","contrary to",
        "recanted","overturned","confession"],
    "complex_cast": ["suspects","witnesses disagreed","conflicting",
        "accomplice","conspiracy","cover-up","web of lies",
        "multiple persons","several suspects","key witness",
        "conflicting testimony","inconsistent","disputed",
        "contradictory","unreliable","changed story",
        "multiple theories","persons of interest"],
    "injustice": ["wrongful","exonerated","failure","misconduct",
        "corruption","got away","escaped justice","acquitted","mishandled",
        "botched","negligence","incompetent","obstruction",
        "tampered","lost evidence","destroyed evidence","contaminated"],
    "human_depth": ["beloved","promising","community mourned","family",
        "mother of","father of","dreams of","just days before",
        "young","student","children","pregnant","engaged",
        "volunteer","loved by","bright future","aspiring","talented"]
}

# ─── Scoring Functions (IDENTICAL thresholds) ───

def sc_d1(v):
    if v>=5000000: return 15
    if v>=3000000: return 12
    if v>=1000000: return 9
    if v>=500000: return 6
    if v>=100000: return 3
    return 0

def sc_d2(c): return min(c*2, 10)

def sc_d3(name, web_platforms="", web_recency=""):
    score, found = 0, []
    wiki = wiki_read(name)
    if wiki and len(wiki) > 200:
        score += 3; found.append("Wiki")
        wl = wiki.lower()
        if any(w in wl for w in ["reddit","subreddit","r/"]): score += 2; found.append("Reddit")
        if any(w in wl for w in ["podcast","crime junkie","serial","casefile","generation why"]): score += 2; found.append("Podcast")
        if any(w in wl for w in ["documentary","netflix","hulu","hbo","dateline","48 hours","20/20","docuseries","film"]): score += 2; found.append("Doc")
        if any(w in wl for w in ["cnn","nbc","bbc","abc","fox news","associated press","fbi","police","sheriff","investigation"]): score += 1; found.append("News")
    wp = web_platforms.lower() if web_platforms else ""
    if score < 10 and wp:
        if "Reddit" not in found and "reddit" in wp: score += 2; found.append("Reddit")
        if "Podcast" not in found and any(w in wp for w in ["podcast","episode","spotify","casefile","crime junkie"]): score += 2; found.append("Podcast")
        if "Doc" not in found and any(w in wp for w in ["documentary","netflix","hulu","dateline","48 hours","20/20"]): score += 2; found.append("Doc")
        if "News" not in found and any(w in wp for w in ["cnn","nbc","bbc","abc","fox","fbi","police","news"]): score += 1; found.append("News")
    return min(score, 10), found

def sc_d4(n_results, recent):
    if n_results >= 10 and recent: return 5
    if n_results >= 10 or recent: return 3
    if n_results >= 5: return 2
    return 0

def sc_d5(name, web_recency=""):
    best, src = 0, "none"
    rl = web_recency.lower() if web_recency else ""
    if "tiktok" in rl and any(w in rl for w in ["viral","million"]): best,src = 5,"TikTok"
    elif any(w in rl for w in ["released","unsealed","reopened"]): best,src = 5,"Court docs"
    elif "reddit.com" in rl and best < 3: best,src = 3,"Reddit"
    elif "websleuths" in rl and best < 2: best,src = 2,"Websleuths"
    return best, src

def sc_s1(months):
    if months>=18: return 15
    if months>=12: return 12
    if months>=9: return 9
    if months>=6: return 6
    if months>=3: return 3
    return 0

def sc_s3(name, web_recency=""):
    best, reason = 0, "none"
    rl = web_recency.lower() if web_recency else ""
    if any(w in rl for w in ["arrest","new evidence","ruling","reopened","identified"]): best,reason=5,"New development"
    elif any(w in rl for w in ["anniversary"]): best,reason=4,"Anniversary"
    elif any(w in rl for w in ["documentary","series","movie"]) and "2026" in rl: best,reason=3,"Related media"
    elif any(w in rl for w in ["similar","reminiscent"]): best,reason=2,"Similar case in news"
    return best, reason

def sc_s4(mega, s3):
    if mega>=15: p=-10
    elif mega>=10: p=-7
    elif mega>=5: p=-4
    elif mega>=3: p=-2
    else: p=0
    if s3==5: p=p//2
    return p

def sc_e1(cvr):
    if cvr>=1.0: return 8
    if cvr>=0.7: return 6
    if cvr>=0.5: return 4
    if cvr>=0.3: return 2
    return 0

def sc_e2(pct):
    if pct>=60: return 8
    if pct>=45: return 6
    if pct>=30: return 4
    if pct>=15: return 2
    return 0

def sc_e3(pct):
    if pct>=30: return 5
    if pct>=20: return 4
    if pct>=15: return 3
    if pct>=10: return 2
    if pct>=5: return 1
    return 0

def sc_e4(pct):
    if pct>=20: return 4
    if pct>=10: return 3
    if pct>=5: return 2
    if pct>=1: return 1
    return 0

def sc_e5(n):
    if n>=8: return 5
    if n>=5: return 4
    if n>=3: return 3
    if n>=1: return 1
    return 0

def sc_d6(videos):
    long_hits = 0
    for v in videos:
        dur = parse_duration(v.get("contentDetails",{}).get("duration",""))
        views = int(v.get("statistics",{}).get("viewCount",0))
        if dur >= 20 and views >= 500000: long_hits += 1
        elif dur >= 15 and views >= 250000: long_hits += 1
    if long_hits >= 3: return 5
    if long_hits >= 2: return 4
    if long_hits >= 1: return 3
    return 0

def sc_r(name, web_platforms="", web_recency=""):
    score, details = 0, []
    wiki = wiki_read(name)
    wl = (wiki.lower() if wiki else "") + " " + web_platforms + " " + web_recency
    if any(w in wl for w in ["serial","multiple victims","killing spree","multiple murders"]): score+=3; details.append("Serial/multiple")
    if any(w in wl for w in ["related case","connected to","linked to","similar case"]): score+=2; details.append("Connected cases")
    if any(w in wl for w in ["ongoing","developing","upcoming trial","awaiting","pending"]): score+=2; details.append("Ongoing")
    return min(score,5), details

# ─── Comment Analysis (IDENTICAL logic) ───

def analyze_comments(comments, case_name=""):
    for c in comments:
        c["text"] = re.sub(r"<[^>]+>", "", c.get("text", ""))
        c["text"] = c["text"].replace("&#39;", "'").replace("&amp;", "&").replace("&quot;", '"')
    comments = [c for c in comments if is_english(c.get("text",""))]
    res = {
        "total": len(comments),
        "anger": {"count":0, "examples":[]},
        "sadness": {"count":0, "examples":[]},
        "fear": {"count":0, "examples":[]},
        "obsession": {"count":0, "examples":[]},
        "questions": {"count":0, "examples":[]},
        "theories": {"count":0, "examples":[]},
        "requests": {"count":0, "examples":[]},
        "complaints": {"count":0, "examples":[]},
        "emotional_hits": 0,
        "dominant_emotion": "neutral"
    }
    if not comments: return res
    for c in comments:
        t = c["text"].lower()
        txt = c["text"][:200]
        for cat, kws, mx in [
            ("anger", ANGER, 5), ("sadness", SADNESS, 5),
            ("fear", FEAR, 5), ("obsession", OBSESSION, 5),
            ("theories", THEORIES, 5),
            ("requests", REQUESTS, 5), ("complaints", COMPLAINTS, 5)
        ]:
            if any(kw in t for kw in kws):
                res[cat]["count"] += 1
                if len(res[cat]["examples"]) < mx:
                    res[cat]["examples"].append(txt)
        is_q = False
        if any(kw in t for kw in QUESTIONS_STRONG): is_q = True
        elif "?" in t:
            if not any(skip in t for skip in QUESTIONS_MARK_SKIP):
                if len(t) > 30: is_q = True
        if is_q:
            res["questions"]["count"] += 1
            if len(res["questions"]["examples"]) < 8:
                res["questions"]["examples"].append(txt)
    hits = (res["anger"]["count"] + res["sadness"]["count"] +
            res["fear"]["count"] + int(res["obsession"]["count"] * 1.5))
    res["emotional_hits"] = hits
    emo = {"anger": res["anger"]["count"], "sadness": res["sadness"]["count"],
           "fear": res["fear"]["count"], "obsession": res["obsession"]["count"]}
    if max(emo.values()) > 0:
        res["dominant_emotion"] = max(emo, key=emo.get)
    return res

# ─── Gates (IDENTICAL logic) ───

def gate_n(wiki_text, case_name="", comments=None):
    t = wiki_text.lower() if wiki_text else ""
    found = set(e for e, kws in NARRATIVE.items() if any(kw in t for kw in kws))
    if len(found) >= 2: return True, list(found)
    if case_name:
        wiki = wiki_read(case_name)
        if wiki:
            wt = wiki.lower()
            for e, kws in NARRATIVE.items():
                if any(kw in wt for kw in kws): found.add(e)
            if len(found) >= 2: return True, list(found)
    if comments:
        ct = " ".join(c.get("text","") for c in comments).lower()
        for e, kws in NARRATIVE.items():
            if any(kw in ct for kw in kws): found.add(e)
    return len(found) >= 2, list(found)

def gate_t(case_name):
    has_img, img_src = wiki_has_image(case_name)
    if has_img: return "PASS", "Wikipedia image found"
    return "CONDITIONAL", "No Wikipedia image — verify manually"

def gate_c(videos, api_key):
    for v in videos[:5]:
        ch_id = v.get("snippet",{}).get("channelId","")
        if not ch_id: continue
        subs = channel_subs(ch_id, api_key)
        if subs >= 1000000:
            pub = v.get("snippet",{}).get("publishedAt","")
            try: months = (datetime.now() - datetime.strptime(pub[:10],"%Y-%m-%d")).days / 30
            except: months = 99
            ch_name = v["snippet"].get("channelTitle","?")
            views = int(v.get("statistics",{}).get("viewCount",0))
            if months <= 3: return "🔴 HIGH", f"{ch_name} ({subs//1000000}M subs) {int(months)}mo ago ({views:,} views)"
            if months <= 6: return "🟡 MODERATE", f"{ch_name} ({subs//1000000}M subs) {int(months)}mo ago"
    return "🟢 LOW", "No major creator coverage recently"

# ─── Angle Recommendation (IDENTICAL) ───

def detect_contrarian(analysis):
    theories = analysis.get("theories", {}).get("examples", [])
    if len(theories) < 2: return None
    dominant = theories[0]
    return {
        "angle": "The Contrarian Take",
        "reason": "Dominant audience theory can be challenged",
        "titles": [
            "Everyone is wrong about {case} — here's why",
            "{case}: The evidence nobody talks about",
            "Why the popular theory about {case} doesn't hold up"
        ],
        "dominant_theory": dominant,
        "approach": "Present the popular theory, then systematically challenge it with evidence"
    }

def recommend_angle(analysis, scores):
    e3, e4, e5 = scores.get("e3",0), scores.get("e4",0), scores.get("e5",0)
    dom = analysis.get("dominant_emotion","neutral")
    signals = {"questions":e3, "theories":e4, "requests":e5, "emotion":scores.get("e2",0)}
    top = max(signals, key=signals.get)
    angles = {
        "questions": {
            "angle": "The Unanswered Question",
            "reason": f"{analysis['questions']['count']} unanswered questions in comments",
            "titles": ["The one question nobody can answer about {case}",
                       "{case}: What really happened? [Questions nobody asks]",
                       "I investigated {case} — here's what doesn't add up"]
        },
        "theories": {
            "angle": "The Theory Deep Dive",
            "reason": f"Active theorizing ({analysis['theories']['count']} theory comments)",
            "titles": ["Examining every theory about {case}",
                       "{case}: Multiple theories, only one makes sense",
                       "The truth about {case} — analyzing all evidence"]
        },
        "requests": {
            "angle": "The Definitive Deep Dive",
            "reason": f"{analysis['requests']['count']} viewers requesting more content",
            "titles": ["The complete story of {case} — everything we know",
                       "{case}: The full story from beginning to end",
                       "Everything about {case} in one video"]
        }
    }
    emotion_angles = {
        "anger": {"angle": "The Justice Failure", "reason": "Dominant audience emotion is anger/outrage",
                  "titles": ["How they got away with it — {case}", "The failures that let {case} go unsolved", "{case}: The justice system failed"]},
        "sadness": {"angle": "The Untold Human Story", "reason": "Dominant audience emotion is sadness/empathy",
                    "titles": ["The heartbreaking truth about {case}", "The story behind {case} nobody talks about", "{case}: The life behind the headlines"]},
        "obsession": {"angle": "The Case That Won't Let Go", "reason": "Audience deeply obsessed with this case",
                      "titles": ["{case}: The case that haunts the internet", "Why nobody can stop thinking about {case}", "The case that broke true crime — {case}"]},
        "fear": {"angle": "The Chilling Details", "reason": "Dominant audience reaction is fear/shock",
                 "titles": ["The most disturbing details of {case}", "{case}: Details that keep you up at night", "What really happened in {case} is worse than you think"]}
    }
    if top in angles and signals[top] >= 3: return angles[top]
    if dom in emotion_angles: return emotion_angles[dom]
    return {"angle": "The Complete Story", "reason": "Balanced engagement — comprehensive coverage best",
            "titles": ["The complete story of {case}", "{case}: Everything you need to know", "The untold story of {case}"]}

# ─── VPS Calculation (IDENTICAL formula) ───

def calc_vps(demand, supply, emotional, own_subs=0):
    if own_subs > 0 and own_subs < 20000:
        supply_boost = max(1.0, 2.0 - (own_subs / 20000))
    else:
        supply_boost = 1.0
    boosted_supply = min(supply * supply_boost, 50)
    raw = demand + boosted_supply + emotional
    actual_max = 50 + (25 * supply_boost) + 35
    actual_max = min(actual_max, 135)
    vps = round((raw / actual_max) * 100)
    if supply_boost > 1.0:
        mode = f"Supply boosted {supply_boost:.1f}x ({own_subs:,} subs)"
    else:
        mode = "Standard"
    return min(vps, 100), mode

# ─── MAIN SCORING (IDENTICAL flow, returns dict instead of printing) ───

def score_case(case_name, api_key, own_subs=0, progress_callback=None):
    """Score a case. Returns full result dict.
    progress_callback(phase, message) is called for UI updates."""
    case_name = " ".join(case_name.strip().split()).title()

    def progress(phase, msg):
        if progress_callback:
            progress_callback(phase, msg)

    progress(0, "Starting web intelligence...")

    # No web search in web version — D5 and S3 will score from Wikipedia only
    web_platforms = ""
    web_recency = ""

    progress(1, "Searching YouTube...")
    results_long = search_yt(f"{case_name} true crime", api_key, order="viewCount", n=10, duration="long")
    results_med = search_yt(f"{case_name} true crime", api_key, order="viewCount", n=5, duration="medium")

    seen_ids = set()
    results = []
    for r in results_long + results_med:
        vid_id = r.get("id",{}).get("videoId","")
        if vid_id and vid_id not in seen_ids:
            seen_ids.add(vid_id)
            results.append(r)

    if not results:
        results_any = search_yt(f"{case_name} true crime", api_key, order="viewCount", n=10, duration="any")
        for r in results_any:
            vid_id = r.get("id",{}).get("videoId","")
            if vid_id and vid_id not in seen_ids:
                seen_ids.add(vid_id)
                results.append(r)

    if not results:
        results_name = search_yt(case_name, api_key, order="viewCount", n=10, duration="any")
        for r in results_name:
            vid_id = r.get("id",{}).get("videoId","")
            if vid_id and vid_id not in seen_ids:
                seen_ids.add(vid_id)
                results.append(r)

    if not results:
        # Debug: try one more search with no filters
        debug_results = search_yt(case_name, api_key, order="viewCount", n=5, duration="any")
        if debug_results:
            results = debug_results
        else:
            # Try raw API call to check for errors
            import urllib.parse
            test_url = f"{API_BASE}/search?part=snippet&q={urllib.parse.quote(case_name)}&type=video&maxResults=1&key={api_key}"
            try:
                test_resp = requests.get(test_url, timeout=20)
                test_data = test_resp.json()
                if "error" in test_data:
                    return {"case_name": case_name, "error": f"YouTube API: {test_data['error']['message']}", "vps": 0}
            except Exception as ex:
                return {"case_name": case_name, "error": f"Connection error: {str(ex)}", "vps": 0}
            return {"case_name": case_name, "error": "No YouTube results found after all fallbacks", "vps": 0}

    vids_ids = [i["id"]["videoId"] for i in results if "videoId" in i.get("id",{})]
    videos = video_stats(vids_ids, api_key)
    if not videos:
        return {"case_name": case_name, "error": "Could not get video stats", "vps": 0}

    videos = filter_shorts(videos)
    if not videos:
        return {"case_name": case_name, "error": "All results were Shorts", "vps": 0}

    videos_eng = [v for v in videos if is_english_video(v)]
    comment_pool = videos_eng if videos_eng else videos

    progress(2, "Analyzing demand signals...")

    # D1
    peak = max(int(v["statistics"].get("viewCount",0)) for v in videos)
    peak_ch = next((v["snippet"]["channelTitle"] for v in videos if int(v["statistics"].get("viewCount",0))==peak), "?")
    d1 = sc_d1(peak)

    # D2
    creators = {}
    for v in videos:
        ch = v["snippet"].get("channelTitle","?")
        vw = int(v["statistics"].get("viewCount",0))
        if vw >= 100000: creators[ch] = max(creators.get(ch,0), vw)
    d2 = sc_d2(len(creators))

    # D3
    d3, d3s = sc_d3(case_name, web_platforms, web_recency)

    # D4
    has_recent = "2025" in web_recency or "2026" in web_recency
    d4 = sc_d4(len(vids_ids), has_recent)

    # D5
    d5, d5s = sc_d5(case_name, web_recency)

    # D6
    d6 = sc_d6(videos)

    demand = d1+d2+d3+d4+d5+d6

    progress(3, "Checking supply gap (S1 best-of-3)...")

    # S1 best-of-3
    def calc_months_fn(vid_list):
        best = 24
        for v in vid_list:
            vw = int(v.get("statistics",{}).get("viewCount",0))
            if vw >= 100000:
                try:
                    pub = datetime.strptime(v["snippet"]["publishedAt"][:10],"%Y-%m-%d")
                    m = (datetime.now()-pub).days/30
                    if m < best: best = m
                except: pass
        return int(best)

    def s1_date_search(query):
        res_l = search_yt(query, api_key, order="date", n=8, duration="long")
        res_m = search_yt(query, api_key, order="date", n=5, duration="medium")
        seen = set()
        combined = []
        for r in res_l + res_m:
            vid_id = r.get("id",{}).get("videoId","")
            if vid_id and vid_id not in seen:
                seen.add(vid_id)
                combined.append(r)
        ids = [i["id"]["videoId"] for i in combined if "videoId" in i.get("id",{})]
        vids = video_stats(ids, api_key) if ids else []
        return [v for v in vids if not is_short(v)]

    def same_band(a, b):
        bands = [(0,3), (3,6), (6,9), (9,12), (12,18), (18,99)]
        for lo, hi in bands:
            if (lo <= a < hi) and (lo <= b < hi): return True
        return False

    m_baseline = calc_months_fn(videos)
    date_vids_1 = s1_date_search(f"{case_name} true crime")
    m_check1 = calc_months_fn(date_vids_1 + videos)

    if same_band(m_baseline, m_check1):
        months_since = min(m_baseline, m_check1)
    else:
        date_vids_2 = s1_date_search(f"{case_name} true crime case")
        m_check2 = calc_months_fn(date_vids_2 + videos)
        values = [m_baseline, m_check1, m_check2]
        if same_band(m_baseline, m_check2): months_since = min(m_baseline, m_check2)
        elif same_band(m_check1, m_check2): months_since = min(m_check1, m_check2)
        else: months_since = min(values)

    s1 = sc_s1(int(months_since))

    # S2
    durs, lrs = [], []
    for v in videos[:5]:
        durs.append(parse_duration(v.get("contentDetails",{}).get("duration","")))
        vw = max(int(v["statistics"].get("viewCount",1)),1)
        lk = int(v["statistics"].get("likeCount",0))
        lrs.append(lk/vw*100)
    avg_dur = sum(durs)/len(durs) if durs else 0
    avg_lr = sum(lrs)/len(lrs) if lrs else 0
    s2_dur = 4 if avg_dur<10 else 3 if avg_dur<20 else 1 if avg_dur<30 else 0
    s2_lr = 3 if avg_lr<2 else 2 if avg_lr<3.5 else 1 if avg_lr<5 else 0

    # S3
    s3, s3r = sc_s3(case_name, web_recency)

    # S4
    mega = sum(1 for v in videos if int(v["statistics"].get("viewCount",0))>=500000)
    s4 = sc_s4(mega, s3)

    progress(4, "Mining comments (extended)...")

    # Comments
    all_comments = []
    case_words = set(w.lower() for w in case_name.split() if len(w) > 2)
    for v in comment_pool[:5]:
        vtitle = v.get("snippet", {}).get("title", "").lower()
        if case_words and not any(w in vtitle for w in case_words): continue
        coms = get_comments_extended(v["id"], api_key)
        ch_name = v['snippet']['channelTitle']
        for c in coms: c["_src"] = ch_name
        all_comments.extend(coms)
        if len(all_comments) >= 250: break

    comment_sources = set(c.get("_src","") for c in all_comments if c.get("_src"))
    if len(comment_sources) < 2:
        for v in comment_pool[:3]:
            vid = v["id"]
            if any(c.get("_vid") == vid for c in all_comments): continue
            coms = get_comments_extended(vid, api_key)
            for c in coms: c["_vid"] = vid
            all_comments.extend(coms)
            if len(all_comments) >= 150: break

    seen_cids = set()
    unique_comments = []
    for c in all_comments:
        cid = c.get("id", c.get("text","")[:80])
        if cid not in seen_cids:
            seen_cids.add(cid)
            unique_comments.append(c)
    all_comments = unique_comments

    analysis = analyze_comments(all_comments, case_name)

    # S2 complaints
    s2_comp = 3 if analysis["complaints"]["count"]>=5 else 2 if analysis["complaints"]["count"]>=3 else 1 if analysis["complaints"]["count"]>=1 else 0
    s2 = s2_dur + s2_lr + s2_comp

    supply = max(0, s1+s2+s3+s4)

    progress(5, "Scoring emotional heat...")

    # E scores
    cvrs = []
    for v in videos[:5]:
        vw = max(int(v["statistics"].get("viewCount",1)),1)
        vw_capped = min(vw, 5000000)
        cc = int(v["statistics"].get("commentCount",0))
        cvrs.append(cc/vw_capped*100)
    avg_cvr = sum(cvrs)/len(cvrs) if cvrs else 0
    e1 = sc_e1(avg_cvr)

    tot = max(analysis["total"],1)
    emo_pct = analysis["emotional_hits"]/tot*100
    e2 = sc_e2(emo_pct)

    q_pct = analysis["questions"]["count"]/tot*100
    e3 = sc_e3(q_pct)

    t_pct = analysis["theories"]["count"]/tot*100
    e4 = sc_e4(t_pct)

    e5 = sc_e5(analysis["requests"]["count"])

    r_score, r_det = sc_r(case_name, web_platforms, web_recency)

    emotional = e1+e2+e3+e4+e5+r_score

    progress(6, "Checking gates...")

    # Gates
    wiki_text = wiki_read(case_name) or ""
    n_pass, n_elem = gate_n(wiki_text, case_name, all_comments)
    t_res, t_det = gate_t(case_name)
    c_lvl, c_det = gate_c(videos, api_key)

    # VPS
    vps, mode = calc_vps(demand, supply, emotional, own_subs)

    if vps>=90: rating="🔥 MUST MAKE THIS VIDEO"
    elif vps>=75: rating="✅ STRONG CANDIDATE"
    elif vps>=60: rating="👍 WORTH CONSIDERING"
    elif vps>=40: rating="⚠️ RISKY"
    else: rating="❌ SKIP"

    # Angle
    sc = {"e2":e2,"e3":e3,"e4":e4,"e5":e5}
    angle = recommend_angle(analysis, sc)
    titles = [t.replace("{case}",case_name) for t in angle["titles"]]
    contrarian = detect_contrarian(analysis)
    contrarian_titles = []
    if contrarian:
        contrarian_titles = [t.replace("{case}",case_name) for t in contrarian["titles"]]

    return {
        "case_name": case_name,
        "vps": vps,
        "rating": rating,
        "mode": mode,
        "demand": demand,
        "supply": supply,
        "emotional": emotional,
        "d1": d1, "d2": d2, "d3": d3, "d4": d4, "d5": d5, "d6": d6,
        "s1": s1, "s2": s2, "s3": s3, "s4": s4,
        "e1": e1, "e2": e2, "e3": e3, "e4": e4, "e5": e5, "r": r_score,
        "s2_dur": s2_dur, "s2_lr": s2_lr, "s2_comp": s2_comp,
        "gate_n": "PASS" if n_pass else "FAIL",
        "gate_n_elements": n_elem,
        "gate_t": t_res,
        "gate_t_detail": t_det,
        "gate_c": c_lvl,
        "gate_c_detail": c_det,
        "angle": angle["angle"],
        "angle_reason": angle["reason"],
        "titles": titles,
        "contrarian": contrarian,
        "contrarian_titles": contrarian_titles,
        "peak_views": peak,
        "peak_channel": peak_ch,
        "creators_100k": len(creators),
        "d3_sources": d3s,
        "d5_source": d5s,
        "s1_months": int(months_since),
        "s3_reason": s3r,
        "s4_mega": mega,
        "avg_cvr": avg_cvr,
        "avg_duration": avg_dur,
        "avg_like_ratio": avg_lr,
        "dominant_emotion": analysis["dominant_emotion"],
        "total_comments": analysis["total"],
        "top_questions": [q[:120] for q in analysis["questions"]["examples"][:8]],
        "top_theories": [t[:120] for t in analysis["theories"]["examples"][:5]],
        "top_requests": [r[:120] for r in analysis["requests"]["examples"][:5]],
        "top_complaints": [c[:120] for c in analysis["complaints"]["examples"][:5]],
        "r_details": r_det,
        "error": None
    }

# ─── Discovery Mode (IDENTICAL logic, no web search) ───

def quick_score(case_name, api_key):
    results = search_yt(f"{case_name} true crime", api_key, order="viewCount", n=5, duration="any")
    if not results: return 0, 0
    ids = [r["id"]["videoId"] for r in results if "videoId" in r.get("id",{})]
    videos = video_stats(ids, api_key) if ids else []
    videos = [v for v in videos if not is_short(v)]
    if not videos: return 0, 0
    peak = max(int(v["statistics"].get("viewCount",0)) for v in videos)
    d1 = sc_d1(peak)
    return d1, peak

def is_likely_person_name(name):
    words = name.strip().split()
    if len(words) < 2 or len(words) > 4: return False
    not_names = {
        "the","this","that","what","when","where","which","about",
        "case","files","crime","true","cold","unsolved","murder",
        "death","killed","missing","found","mystery","serial",
        "killer","popular","culture","edition","these","those",
        "academic","dictionaries","encyclopedia","wikipedia",
        "wikiwand","watch","video","story","part","full","best",
        "worst","most","more","less","every","each","many","some",
        "new","old","last","first","next","list","top","all",
        "one","two","three","here","there","now","then","just",
        "very","also","other","only","still","even","back",
        "over","after","before","between","under","through",
        "during","without","within","along","among","across",
        "is","are","was","were","been","being","have","has",
        "had","does","did","will","would","could","should",
        "may","might","can","shall","must","need","dare",
        "and","but","not","for","with","from","into","upon"
    }
    for w in words:
        if not w[0].isupper(): return False
        if w.lower() in not_names: return False
    return True

def extract_case_names(text):
    candidates = []
    patterns = [
        r'(?:murder|disappearance|death|killing|case|story|vanishing)\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s+(?:case|murder|disappearance|death|killing|mystery|homicide)',
        r'(?:what happened to|who killed|the search for|looking for|find)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',
        r'(?:unsolved|missing|cold case|mysterious death).*?([A-Z][a-z]+\s+[A-Z][a-z]+)',
    ]
    text = re.sub(r'\s+', ' ', text)
    for pat in patterns:
        for m in re.finditer(pat, text):
            name = m.group(1).strip()
            name = re.sub(r'\s+', ' ', name).strip()
            if len(name) < 5 or len(name) > 35: continue
            if not is_likely_person_name(name): continue
            if name not in candidates: candidates.append(name)
    return candidates

SEED_CASES = [
    "Jennifer Kesse", "Brandon Lawson", "Brian Shaffer",
    "Springfield Three", "Delphi Murders", "Kyron Horman",
    "Relisha Rudd", "Tamla Horsford", "Kenneka Jenkins",
    "Darlie Routier", "Amy Mihaljevic", "Brittanee Drexel",
    "Lauren Spierer", "Natalee Holloway", "Mollie Tibbetts",
    "Suzanne Morphew", "Summer Wells", "Harmony Montgomery",
    "Laci Peterson", "Kristin Smart", "Rey Rivera"
]

def discover(api_key, count=10, progress_callback=None):
    def progress(msg):
        if progress_callback: progress_callback(msg)

    all_candidates = []
    def add_candidate(name, source):
        name = re.sub(r'\s+', ' ', name).strip().title()
        if len(name) < 5 or len(name) > 35: return
        if not is_likely_person_name(name): return
        skip = ["true crime","cold case","serial killer","crime scene",
                "crime watch","mystery case","police officer","new york",
                "los angeles","united states","last week","this week",
                "first time","full story","real life","breaking news",
                "prime video","netflix","youtube","subscribe","episode",
                "part one","part two","season","chapter","reddit",
                "tiktok","podcast","documentary","wikipedia","update"]
        if any(s in name.lower() for s in skip): return
        if " " not in name: return
        for existing in all_candidates:
            if existing["name"].lower() == name.lower(): return
        all_candidates.append({"name": name, "source": source})

    # Source 1: YouTube trending
    progress("Searching YouTube trending...")
    yt_queries = [
        ("unsolved true crime case", "viewCount"),
        ("true crime cold case", "viewCount"),
        ("unsolved murder documentary", "date"),
    ]
    for query, order in yt_queries:
        results = search_yt(query, api_key, order=order, n=10, duration="long")
        for r in results:
            title = r.get("snippet", {}).get("title", "")
            for n in extract_case_names(title): add_candidate(n, "YouTube")
            desc = r.get("snippet", {}).get("description", "")
            for n in extract_case_names(desc): add_candidate(n, "YouTube")

    # Source 2: Seed list
    progress("Checking seed cases...")
    for name in SEED_CASES:
        add_candidate(name, "Seed")

    if not all_candidates:
        return []

    # Quick-score
    to_score = all_candidates[:count * 2]
    progress(f"Quick-scoring {len(to_score)} candidates...")
    scored = []
    for item in to_score:
        d1, peak = quick_score(item["name"], api_key)
        item["d1"] = d1
        item["peak"] = peak
        scored.append(item)

    scored.sort(key=lambda x: x["d1"], reverse=True)
    top = [c for c in scored[:count] if c["d1"] > 0]
    return top
