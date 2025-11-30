import streamlit as st
import pandas as pd
import numpy as np
import requests
from textblob import TextBlob
import matplotlib.pyplot as plt
import re

# ----------------------------
# PAGE SETTINGS
# ----------------------------
st.set_page_config(page_title="YouTube Sentiment Dashboard", layout="wide")
st.title("📊 YouTube Channel Video Sentiment Analyzer")

# ----------------------------
# USER INPUTS
# ----------------------------
api_key = st.text_input("🔑 Enter Your YouTube API Key", type="password")
channel_url = st.text_input("📺 Enter YouTube Channel URL")

# ----------------------------
# Extract channel ID
# ----------------------------
def extract_channel_id(url):
    # Format: youtube.com/channel/UCxxxx
    match = re.search(r"channel/([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)

    # Format: youtube.com/@username
    match = re.search(r"youtube\.com/@([A-Za-z0-9_-]+)", url)
    if match:
        username = match.group(1)
        lookup_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": username,
            "type": "channel",
            "maxResults": 1,
            "key": api_key
        }
        data = requests.get(lookup_url, params=params).json()
        if "items" in data and len(data["items"]) > 0:
            return data["items"][0]["snippet"]["channelId"]
    return None

# ----------------------------
# Load Channel Videos
# ----------------------------
if st.button("Load Channel Videos"):
    if not api_key or not channel_url:
        st.error("Enter both API key and channel URL.")
        st.stop()

    channel_id = extract_channel_id(channel_url)
    if not channel_id:
        st.error("❌ Could not extract channel ID from URL.")
        st.stop()

    st.session_state["channel_id"] = channel_id

    search_url = "https://www.googleapis.com/youtube/v3/search"
    search_params = {
        "part": "snippet",
        "channelId": channel_id,
        "order": "date",
        "type": "video",
        "maxResults": 50,
        "key": api_key
    }

    data = requests.get(search_url, params=search_params).json()
    st.session_state["videos"] = data.get("items", [])

# ----------------------------
# Video Picker UI
# ----------------------------
if "videos" in st.session_state:
    videos = st.session_state["videos"]

    st.subheader("🎬 Select a Video to Analyze")

    # horizontal scroll container
    scroll_css = """
        <style>
        .scroll-row {
            display: flex;
            overflow-x: auto;
            gap: 20px;
            padding: 10px;
        }
        </style>
    """
    st.markdown(scroll_css, unsafe_allow_html=True)

    st.markdown('<div class="scroll-row">', unsafe_allow_html=True)

    # Create dynamic columns inside scroll area
    for i, v in enumerate(videos):
        thumb = v["snippet"]["thumbnails"]["medium"]["url"]
        title = v["snippet"]["title"]
        vid = v["id"]["videoId"]

        with st.container():
            col1, = st.columns(1)
            with col1:
                st.image(thumb, width=250)
                st.write(title[:60] + "...")
                if st.button(f"Analyze Video {i+1}", key=f"vid_btn_{vid}"):
                    st.session_state["selected_video"] = vid

    st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------
# ANALYZE SELECTED VIDEO
# ----------------------------
if "selected_video" in st.session_state:
    video_id = st.session_state["selected_video"]

    st.success(f"Analyzing video: {video_id}")

    # ----------------------------
    # Fetch video metadata
    # ----------------------------
    video_meta_url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": api_key
    }
    meta_resp = requests.get(video_meta_url, params=params).json()

    snippet = meta_resp["items"][0]["snippet"]
    stats = meta_resp["items"][0]["statistics"]

    title = snippet.get("title")
    channel_id = snippet.get("channelId")
    views = int(stats.get("viewCount", 0))
    likes = int(stats.get("likeCount", 0))
    comment_count = int(stats.get("commentCount", 0))
    engagement = ((likes + comment_count) / max(views, 1)) * 100
    thumbnail = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

    # subscriber count
    sub_req = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "statistics", "id": channel_id, "key": api_key}
    ).json()
    subs = int(sub_req["items"][0]["statistics"]["subscriberCount"])

    custom_score = round(engagement * 0.5 + likes * 0.003, 2)

    # Display overview
    st.subheader("🎬 Video Overview")
    colA, colB = st.columns([1, 2])

    with colA:
        st.image(thumbnail, width=420)

    with colB:
        st.write(f"### {title}")
        a, b, c, d = st.columns(4)
        a.metric("Views", f"{views:,}")
        b.metric("Likes", f"{likes:,}")
        c.metric("Comments", f"{comment_count:,}")
        d.metric("Subscribers", f"{subs:,}")
        a2, b2 = st.columns(2)
        a2.metric("Engagement", f"{engagement:.2f}%")
        b2.metric("Custom Score", custom_score)

    # ----------------------------
    # Fetch comments
    # ----------------------------
    comment_url = "https://www.googleapis.com/youtube/v3/commentThreads"
    resp = requests.get(comment_url, params={
        "part": "snippet",
        "videoId": video_id,
        "key": api_key,
        "maxResults": 100,
        "textFormat": "plainText"
    }).json()

    comments = [
        item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
        for item in resp.get("items", [])
    ]

    st.success(f"Fetched {len(comments)} comments")

    # ----------------------------
    # Sentiment
    # ----------------------------
    pol = [TextBlob(c).sentiment.polarity for c in comments]
    sentiment = ["Positive" if p > 0.05 else "Negative" if p < -0.05 else "Neutral" for p in pol]

    df = pd.DataFrame({"comment": comments, "polarity": pol, "sentiment": sentiment})
    st.dataframe(df, use_container_width=True)

    # ----------------------------
    # Charts
    # ----------------------------
    col1, col2 = st.columns(2)

    with col1:
        fig, ax = plt.subplots()
        df["sentiment"].value_counts().plot(kind="bar", ax=ax)
        ax.set_title("Sentiment Distribution")
        st.pyplot(fig)

    with col2:
        fig2, ax2 = plt.subplots()
        ax2.hist(df["polarity"], bins=20)
        ax2.set_title("Polarity Histogram")
        st.pyplot(fig2)

    # ----------------------------
    # Export
    # ----------------------------
    st.download_button(
        "Download CSV",
        df.to_csv(index=False),
        "sentiment_comments.csv",
        "text/csv"
    )
