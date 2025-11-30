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

# Extract channel ID from URL
def extract_channel_id(url):
    # Format: https://www.youtube.com/channel/UCxxxx
    match = re.search(r"channel/([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)

    # For formats like: https://www.youtube.com/@ChannelName
    match = re.search(r"youtube\.com/@([A-Za-z0-9_-]+)", url)
    if match:
        username = match.group(1)
        # Convert @username → channel ID
        lookup_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": username,
            "type": "channel",
            "key": api_key,
            "maxResults": 1
        }
        data = requests.get(lookup_url, params=params).json()
        if "items" in data and len(data["items"]) > 0:
            return data["items"][0]["snippet"]["channelId"]

    return None

# ----------------------------
# FETCH CHANNEL VIDEOS
# ----------------------------
if st.button("Load Channel Videos"):
    if not api_key or not channel_url:
        st.error("Please enter BOTH the API key and channel URL.")
        st.stop()

    channel_id = extract_channel_id(channel_url)
    if not channel_id:
        st.error("❌ Could not extract channel ID from URL.")
        st.stop()

    st.success("Channel ID extracted successfully!")

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
    videos = data.get("items", [])

    if len(videos) == 0:
        st.error("No videos found for this channel.")
        st.stop()

    st.subheader("🎬 Select a Video to Analyze")

    # Horizontal scroll container
    scroll_css = """
        <style>
        .scroll-container {
            display: flex;
            overflow-x: auto;
            padding: 15px;
            gap: 15px;
            white-space: nowrap;
        }
        .video-card {
            border: 1px solid #ddd;
            padding: 10px;
            border-radius: 10px;
            width: 260px;
            text-align: center;
            background: #fafafa;
        }
        .video-card img {
            border-radius: 8px;
        }
        </style>
    """
    st.markdown(scroll_css, unsafe_allow_html=True)

    st.markdown("<div class='scroll-container'>", unsafe_allow_html=True)

    vid_selected = None

    # Display thumbnails
    for v in videos:
        vid = v["id"]["videoId"]
        title = v["snippet"]["title"]
        thumb = v["snippet"]["thumbnails"]["medium"]["url"]

        # Create a button inside each video box
        box = f"""
        <div class='video-card'>
            <img src="{thumb}" width="240">
            <p>{title[:50]}...</p>
            <form action="" method="post">
                <button name="selected_video" value="{vid}" type="submit">Analyze</button>
            </form>
        </div>
        """
        st.markdown(box, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Check if user clicked a video
    vid_selected = st.session_state.get("selected_video", None)

# Workaround because Streamlit cannot read form POSTs natively
selected_video_id = st.query_params.get("selected_video", None)

if selected_video_id:
    video_id = selected_video_id

    st.success(f"Analyzing Video ID: **{video_id}**")

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

    custom_score = round(engagement * 0.5 + likes * 0.003, 2)
    thumbnail = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

    # ----------------------------
    # DISPLAY VIDEO METRICS
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
    # SENTIMENT
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
        st.pyplot(fig1)

    with colB:
        fig2, ax2 = plt.subplots()
        vals = df["polarity"].values
        bins = 20
        counts, edges = np.histogram(vals, bins=bins, range=(-1, 1))
        centers = (edges[:-1] + edges[1:]) / 2
        cmap = plt.get_cmap("RdYlGn")
        bar_colors = [cmap((c + 1) / 2) for c in centers]
        ax2.bar(centers, counts, width=(edges[1] - edges[0]) * 0.9, color=bar_colors)
        ax2.set_title("Polarity Distribution")
        st.pyplot(fig2)

    # ----------------------------
    # TOP COMMENTS
    # ----------------------------
    st.subheader("🏆 Top Comments")
    c1, c2 = st.columns(2)

    top_pos = df.sort_values("polarity", ascending=False).head(10).reset_index(drop=True)
    top_neg = df.sort_values("polarity", ascending=True).head(10).reset_index(drop=True)

    with c1:
        st.write("### 🌟 Top 10 Positive Comments")
        st.table(top_pos)

    with c2:
        st.write("### 💀 Top 10 Negative Comments")
        st.table(top_neg)

    # ----------------------------
    # EXPORT
    # ----------------------------
    st.subheader("⬇️ Download Comment Data")
    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False).encode(),
        file_name="sentiment_comments.csv",
        mime="text/csv"
    )
