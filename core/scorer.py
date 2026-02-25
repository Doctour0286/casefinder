"""
CaseFinder v1.0 — VPS Scoring Engine
Complete viral potential scoring system.
"""

import re
from core.youtube_api import (
    search_videos, get_video_stats, get_comments,
    parse_duration, months_since
)
from core.wikipedia_api import search_wikipedia, get_page_extract


# ═══════════════════════════════════════════════════════════
# CONSTANTS (Simplified from original)
# ═══════════════════════════════════════════════════════════

D1_PEAKS = [(5_000_000, 15), (3_000_000, 12), (1_000_000, 9),
            (500_000, 6), (100_000, 3), (0, 0)]

D2_CREATORS = [(5, 10), (4, 8), (3, 6), (2, 4), (1, 2), (0, 0)]

S1_MONTHS = [(18, 15), (12, 12), (9, 9), (6, 6), (3, 3), (0, 0)]

E1_CVR = [(1.0, 8), (0.7, 6), (0.5, 4), (0.3, 2), (0.0, 0)]

VPS_RATINGS = {
    90: "🔥 MUST MAKE THIS VIDEO",
    75: "✅ STRONG CANDIDATE",
    60: "👍 WORTH CONSIDERING",
    40: "⚠️ RISKY",
    0: "❌ SKIP"
}


# ═══════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════

def get_score(value: int, thresholds: list[tuple]) -> int:
    """Get score from value based on thresholds."""
    for threshold, score in thresholds:
        if value >= threshold:
            return score
    return thresholds[-1][1]


def is_english_text(text: str) -> bool:
    """Check if text appears to be English."""
    text_lower = text.lower()
    english_words = ["the", "is", "was", "are", "and", "but", "not", "this",
                   "that", "have", "has", "with", "for", "they", "been",
                   "what", "when", "who", "how", "why", "would", "could",
                   "she", "her", "his", "don't", "didn't", "can't", "won't",
                   "you", "were", "just", "about", "think", "know", "really",
                   "never", "still", "because"]

    words_found = sum(1 for word in english_words if word in text_lower)
    return words_found >= 2


def is_english_video(video: dict) -> bool:
    """Check if video is likely English."""
    title = video.get("title", "").lower()

    # Check for English keywords
    english_keywords = ["the", "of", "and", "true crime", "murder", "killed",
                       "death", "case", "mystery", "story", "disappearance",
                       "missing", "unsolved", "investigation", "documentary",
                       "evidence", "suspect", "victim", "trial"]

    if any(kw in title for kw in english_keywords):
        return True

    # Check default language
    if video.get("default_language", "").startswith("en"):
        return True

    return is_english_text(title)


def is_short(video: dict) -> bool:
    """Check if video is a YouTube Short."""
    duration_mins = parse_duration(video.get("duration", "PT0S"))
    title = video.get("title", "").lower()

    if duration_mins < 1.5:  # Less than 90 seconds
        return True
    if "#shorts" in title or "#short" in title:
        return True
    return False


def count_keywords(text: str, keywords: list[str]) -> int:
    """Count how many keywords appear in text."""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw in text_lower)


def extract_case_name(input_name: str) -> str:
    """Clean and format case name."""
    # Remove extra whitespace and title case
    name = " ".join(input_name.strip().split())
    return name.title()


# ═══════════════════════════════════════════════════════════
# MAIN SCORING FUNCTION
# ═══════════════════════════════════════════════════════════

def score_case(case_name: str, api_key: str, subscriber_count: int = 0) -> dict:
    """
    Score a case and return full VPS breakdown.
    """
    case_name = extract_case_name(case_name)
    result = {
        "case_name": case_name,
        "vps": 0,
        "rating": "",
        "demand": 0,
        "supply": 0,
        "emotional": 0,
        "d1": 0, "d2": 0, "d3": 0, "d4": 0, "d5": 0, "d6": 0,
        "s1": 0, "s2": 0, "s3": 0, "s4": 0,
        "e1": 0, "e2": 0, "e3": 0, "e4": 0, "e5": 0, "r": 0,
        "gate_n": "PASS",
        "gate_t": "PASS",
        "gate_c": "🟢 LOW",
        "angle": "The Complete Story",
        "titles": [],
        "top_questions": [],
        "top_theories": [],
        "error": None
    }

    try:
        # ═══ PHASE 1: YOUTUBE SEARCH
        search_query = f"{case_name} true crime"

        # Search long-form (20+ min)
        videos_long = search_videos(api_key, search_query, max_results=10,
                                    order="viewCount", duration="long")
        # Search medium (4-20 min)
        videos_medium = search_videos(api_key, search_query, max_results=5,
                                     order="viewCount", duration="medium")

        # Combine and dedupe
        all_videos = {}
        for v in videos_long + videos_medium:
            all_videos[v["video_id"]] = v

        if not all_videos:
            result["error"] = "No YouTube videos found for this case."
            return result

        # Get detailed stats
        video_ids = list(all_videos.keys())
        video_details = get_video_stats(api_key, video_ids)

        # Filter out Shorts and non-English
        english_videos = [v for v in video_details if not is_short(v) and is_english_video(v)]

        if not english_videos:
            english_videos = video_details  # Fallback to all

        # Sort by views
        english_videos.sort(key=lambda x: x["views"], reverse=True)
        top_videos = english_videos[:10]

        # ═══ PHASE 2: D1 — Peak Views
        max_views = max((v["views"] for v in top_videos), default=0)
        result["d1"] = get_score(max_views, D1_PEAKS)

        # ═══ PHASE 3: D2 — Multi-Creator Success
        creators_100k = set()
        for v in top_videos:
            if v["views"] >= 100_000:
                creators_100k.add(v["channel"])
        result["d2"] = get_score(len(creators_100k), D2_CREATORS)

        # ═══ PHASE 4: D3 — Cross-Platform (Wikipedia)
        wiki = search_wikipedia(case_name)
        if wiki:
            result["d3"] = 3  # Wikipedia presence
        else:
            result["d3"] = 0

        # ═══ PHASE 5: D4 — Search Demand
        if len(english_videos) >= 10:
            result["d4"] = 3
        elif len(english_videos) >= 5:
            result["d4"] = 2
        else:
            result["d4"] = 0

        # ═══ PHASE 6: D5 — Pre-YouTube Buzz (Limited in v1)
        result["d5"] = 0  # No web search in v1

        # ═══ PHASE 7: D6 — Long-Form Success
        long_hits = 0
        for v in top_videos:
            duration = parse_duration(v.get("duration", "PT0S"))
            views = v["views"]
            if duration >= 20 and views >= 500_000:
                long_hits += 1
            elif duration >= 15 and views >= 250_000:
                long_hits += 1
        result["d6"] = get_score(long_hits, [(3, 5), (2, 4), (1, 3), (0, 0)])

        # ═══ PHASE 8: S1 — Coverage Recency
        recent_100k = None
        for v in top_videos:
            if v["views"] >= 100_000:
                months = months_since(v.get("published", ""))
                if recent_100k is None or months < recent_100k:
                    recent_100k = months

        if recent_100k is not None:
            result["s1"] = get_score(recent_100k, S1_MONTHS)

        # ═══ PHASE 9: S2 — Quality Gap
        # Duration score
        if len(top_videos) >= 3:
            avg_duration = sum(parse_duration(v.get("duration", "PT0S")) for v in top_videos[:3]) / 3
            if avg_duration < 10:
                s2_dur = 4
            elif avg_duration < 20:
                s2_dur = 3
            elif avg_duration < 30:
                s2_dur = 1
            else:
                s2_dur = 0
        else:
            s2_dur = 0

        # Like ratio score
        total_views = sum(v["views"] for v in top_videos[:3] if v["views"] > 0)
        total_likes = sum(v["likes"] for v in top_videos[:3])
        if total_views > 0:
            like_ratio = (total_likes / total_views) * 100
            if like_ratio < 2:
                s2_likes = 3
            elif like_ratio < 3.5:
                s2_likes = 2
            elif like_ratio < 5:
                s2_likes = 1
            else:
                s2_likes = 0
        else:
            s2_likes = 0

        result["s2"] = s2_dur + s2_likes

        # ═══ PHASE 10: S3 — Timing (Limited in v1)
        result["s3"] = 0

        # ═══ PHASE 11: S4 — Saturation
        mega_videos = sum(1 for v in english_videos if v["views"] >= 500_000)
        if mega_videos >= 15:
            result["s4"] = -10
        elif mega_videos >= 10:
            result["s4"] = -7
        elif mega_videos >= 5:
            result["s4"] = -4
        elif mega_videos >= 3:
            result["s4"] = -2
        else:
            result["s4"] = 0

        # ═══ PHASE 12: COMMENTS — Emotional Heat
        # Get comments from top 3 videos
        all_comments = []
        for v in top_videos[:3]:
            comments = get_comments(api_key, v["video_id"], max_results=50, order="relevance")
            comments += get_comments(api_key, v["video_id"], max_results=50, order="time")
            all_comments.extend(comments)

        # Dedupe
        seen_ids = set()
        unique_comments = []
        for c in all_comments:
            if c["id"] not in seen_ids:
                seen_ids.add(c["id"])
                unique_comments.append(c["text"])

        comments_text = "\n".join(unique_comments[:150])

        # E1: Comment-to-View Ratio
        total_comment_count = sum(v["comments"] for v in top_videos[:3])
        total_view_count = sum(min(v["views"], 5_000_000) for v in top_videos[:3])
        if total_view_count > 0:
            cvr = (total_comment_count / total_view_count) * 100
            result["e1"] = get_score(cvr, E1_CVR)

        # E2: Emotional Intensity
        emotion_keywords = ["angry", "furious", "disgusting", "outrage", "justice",
                          "cry", "crying", "tears", "heartbreaking", "devastating",
                          "terrifying", "chilling", "haunting", "nightmare", "shocked",
                          "obsessed", "can't stop thinking", "rabbit hole"]
        emotion_count = count_keywords(comments_text, emotion_keywords)
        if len(unique_comments) > 0:
            emotion_ratio = (emotion_count / len(unique_comments)) * 100
            if emotion_ratio >= 45:
                result["e2"] = 6
            elif emotion_ratio >= 30:
                result["e2"] = 4
            elif emotion_ratio >= 15:
                result["e2"] = 2

        # E3: Unresolved Questions
        question_keywords = ["why didn't", "how come", "what about", "what happened to",
                           "nobody talks about", "does anyone know", "has anyone",
                           "still don't understand", "makes no sense", "doesn't add up"]
        question_count = count_keywords(comments_text, question_keywords)
        if len(unique_comments) > 0:
            q_ratio = (question_count / len(unique_comments)) * 100
            if q_ratio >= 20:
                result["e3"] = 4
            elif q_ratio >= 10:
                result["e3"] = 2
            elif q_ratio >= 5:
                result["e3"] = 1

        # E4: Theory Activity
        theory_keywords = ["i think", "my theory", "theory:", "what if", "could it be",
                         "maybe the", "i believe", "hear me out"]
        theory_count = count_keywords(comments_text, theory_keywords)
        if len(unique_comments) > 0:
            t_ratio = (theory_count / len(unique_comments)) * 100
            if t_ratio >= 10:
                result["e4"] = 3
            elif t_ratio >= 5:
                result["e4"] = 2
            elif t_ratio >= 1:
                result["e4"] = 1

        # E5: Content Requests
        request_keywords = ["please cover", "please do", "follow up", "part 2",
                          "more about", "deeper dive", "full story"]
        request_count = count_keywords(comments_text, request_keywords)
        if request_count >= 5:
            result["e5"] = 4
        elif request_count >= 3:
            result["e5"] = 2
        elif request_count >= 1:
            result["e5"] = 1

        # R: Rabbit Hole
        if wiki:
            extract = get_page_extract(None, wiki.get("title", ""))
            if extract:
                rabbit_words = ["serial", "connected", "related case", "ongoing", "developing"]
                if any(w in extract.lower() for w in rabbit_words):
                    result["r"] = 3

        # ═══ PHASE 13: CALCULATE VPS
        demand = result["d1"] + result["d2"] + result["d3"] + result["d4"] + result["d5"] + result["d6"]
        supply = max(0, result["s1"] + result["s2"] + result["s3"] + result["s4"])
        emotional = result["e1"] + result["e2"] + result["e3"] + result["e4"] + result["e5"] + result["r"]

        # Channel size adjustment (supply boost)
        supply_boost = 1.0
        if subscriber_count > 0 and subscriber_count < 20000:
            supply_boost = max(1.0, 2.0 - (subscriber_count / 20000))

        boosted_supply = supply * supply_boost

        # Calculate VPS
        raw_total = demand + boosted_supply + emotional
        actual_max = 50 + (25 * supply_boost) + 35
        vps = int((raw_total / actual_max) * 100)

        result["vps"] = vps
        result["demand"] = demand
        result["supply"] = supply
        result["emotional"] = emotional

        # Rating
        for threshold, rating in VPS_RATINGS.items():
            if vps >= threshold:
                result["rating"] = rating
                break

        # Angle recommendation
        if result["e3"] >= 3:
            result["angle"] = "The Unanswered Question"
        elif result["e4"] >= 3:
            result["angle"] = "The Theory Deep Dive"
        elif result["e5"] >= 3:
            result["angle"] = "The Definitive Deep Dive"
        elif result["e2"] >= 4:
            result["angle"] = "The Chilling Details"
        else:
            result["angle"] = "The Complete Story"

        # Generate titles
        titles = [
            f"{result['angle']} — {case_name}",
            f"The complete story of {case_name}",
            f"Everything you need to know about {case_name}"
        ]
        result["titles"] = titles

    except Exception as e:
        result["error"] = str(e)

    return result
