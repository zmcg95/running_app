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
st.title("📊 YouTube Comment Sentiment Analyzer")

# ----------------------------
# USER INPUTS
# ----------------------------
api_key = st.text_input("🔑 Enter Your YouTube API Key", type="password")
video_url = st.text_input("🎥 Enter YouTube Video URL")

if st.button("Fetch & Analyze"):
    if not api_key or not video_url:
        st.error("Please enter BOTH the API key and video URL.")
        st.stop()

    # Extract video ID
    match = re.search(r"v=([a-zA-Z0-9_-]+)", video_url)
    if not match:
        st.error("Invalid YouTube URL format.")
        st.stop()

    video_id = match.group(1)

    # ----------------------------
    # FETCH VIDEO METADATA
    # ----------------------------
    video_meta_url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": api_key
    }
    meta_resp = requests.get(video_meta_url, params=params).json()

    if "items" not in meta_resp or len(meta_resp["items"]) == 0:
        st.error("Could not fetch video metadata.")
        st.stop()

    snippet = meta_resp["items"][0]["snippet"]
    stats = meta_resp["items"][0]["statistics"]

    title = snippet.get("title", "Unknown Title")
    channel_id = snippet.get("channelId")
    views = int(stats.get("viewCount", 0))
    likes = int(stats.get("likeCount", 0))
    comment_count = int(stats.get("commentCount", 0))
    engagement = ((likes + comment_count) / max(views, 1)) * 100

    # ----------------------------
    # FETCH CHANNEL SUBSCRIBERS
    # ----------------------------
    channel_url = "https://www.googleapis.com/youtube/v3/channels"
    channel_params = {
        "part": "statistics",
        "id": channel_id,
        "key": api_key
    }
    channel_resp = requests.get(channel_url, params=channel_params).json()
    subs = int(channel_resp["items"][0]["statistics"]["subscriberCount"])

    # Custom Score (example formula)
    custom_score = round(engagement * 0.5 + likes * 0.003, 2)

    thumbnail = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

    # ----------------------------
    # DISPLAY VIDEO & METRICS
    # ----------------------------
    st.subheader("🎬 Video Overview")
    col_vid, col_meta = st.columns([1, 2])

    with col_vid:
        st.image(thumbnail, width=420)

    with col_meta:
        st.write(f"### {title}")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("👁️ Views", f"{views:,}")
        m2.metric("👍 Likes", f"{likes:,}")
        m3.metric("💬 Comments", f"{comment_count:,}")
        m4.metric("👥 Subscribers", f"{subs:,}")

        m5, m6 = st.columns(2)
        m5.metric("📈 Engagement Rate", f"{engagement:.2f}%")
        m6.metric("🔥 Custom Score", custom_score)

    # ----------------------------
    # FETCH COMMENTS
    # ----------------------------
    comment_url = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        "part": "snippet",
        "videoId": video_id,
        "key": api_key,
        "maxResults": 100,
        "textFormat": "plainText"
    }

    resp = requests.get(comment_url, params=params).json()
    comments = [
        item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
        for item in resp.get("items", [])
    ]

    st.success(f"Fetched {len(comments)} comments.")

    # ----------------------------
    # SENTIMENT ANALYSIS
    # ----------------------------
    sentiment = []
    polarities = []

    for c in comments:
        p = TextBlob(c).sentiment.polarity
        polarities.append(p)

        if p > 0.05:
            sentiment.append("Positive")
        elif p < -0.05:
            sentiment.append("Negative")
        else:
            sentiment.append("Neutral")

    df = pd.DataFrame({
        "comment": comments,
        "polarity": polarities,
        "sentiment": sentiment
    })

    st.dataframe(df, use_container_width=True)

    # ----------------------------
    # VISUALS
    # ----------------------------
    st.subheader("📈 Visual Insights")
    colA, colB = st.columns(2)

    with colA:
        fig1, ax1 = plt.subplots()
        df["sentiment"].value_counts().plot(kind="bar", color=["green", "gray", "red"], ax=ax1)
        ax1.set_title("Sentiment Distribution")
        ax1.set_ylabel("Count")
        st.pyplot(fig1)

    with colB:
        fig2, ax2 = plt.subplots()
        vals = df["polarity"].values
        bins = 20
        counts, edges = np.histogram(vals, bins=bins, range=(-1, 1))
        centers = (edges[:-1] + edges[1:]) / 2
        cmap = plt.get_cmap("RdYlGn")
        bar_colors = [cmap((c + 1) / 2) for c in centers]

        ax2.bar(centers, counts, width=(edges[1] - edges[0]) * 0.9, color=bar_colors, edgecolor="black")
        ax2.set_title("Polarity Distribution")
        st.pyplot(fig2)

    # ----------------------------
    # TOP 10 POS/NEG (without index)
    # ----------------------------
    top_pos = df.sort_values("polarity", ascending=False).head(10).reset_index(drop=True)
    top_neg = df.sort_values("polarity", ascending=True).head(10).reset_index(drop=True)

    st.subheader("🏆 Top Comments")
    c1, c2 = st.columns(2)

    with c1:
        st.write("### 🌟 Top 10 Positive Comments")
        st.table(top_pos)

    with c2:
        st.write("### 💀 Top 10 Negative Comments")
        st.table(top_neg)

    # ----------------------------
    # LAST 10 CHANNEL VIDEOS
    # ----------------------------
    st.subheader("📺 Channel Recent Performance")

    uploads_url = "https://www.googleapis.com/youtube/v3/search"
    uploads_params = {
        "part": "snippet",
        "channelId": channel_id,
        "order": "date",
        "maxResults": 10,
        "type": "video",
        "key": api_key
    }
    uploads_resp = requests.get(uploads_url, params=uploads_params).json()

    vid_ids = [item["id"]["videoId"] for item in uploads_resp.get("items", [])]

    # Fetch their stats
    stats_url = "https://www.googleapis.com/youtube/v3/videos"
    stats_params = {
        "part": "statistics",
        "id": ",".join(vid_ids),
        "key": api_key
    }
    vid_stats = requests.get(stats_url, params=stats_params).json()

    recent_views = [int(v["statistics"].get("viewCount", 0)) for v in vid_stats["items"]]

    # ----------------------------
    # LINE CHART FOR LAST 10 VIDEOS + comparison line
    # ----------------------------
    fig3, ax3 = plt.subplots(figsize=(10, 5))
    ax3.plot(range(1, len(recent_views) + 1), recent_views, marker="o")
    ax3.axhline(views, color="red", linestyle="--", label="Analyzed Video Views")

    ax3.set_title("Views of Last 10 Channel Videos")
    ax3.set_xlabel("Recent Videos (Newest → Oldest)")
    ax3.set_ylabel("View Count")
    ax3.legend()

    st.pyplot(fig3)

    # ----------------------------
    # DOWNLOAD CSV
    # ----------------------------
    st.subheader("⬇️ Download Comment Data")
    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False).encode(),
        file_name="sentiment_comments.csv",
        mime="text/csv"
    )
