import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from textblob import TextBlob
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import requests

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="YouTube Caption Sentiment Timeline",
    layout="wide"
)

st.title("🎬 YouTube Caption Sentiment Analyzer")
st.write(
    "Sentiment Analysis.\n\n"
)

# ----------------------------
# HELPERS
# ----------------------------
def get_video_id(url):
    parsed = urlparse(url)
    if parsed.hostname in ["www.youtube.com", "youtube.com"]:
        if "v" in parse_qs(parsed.query):
            return parse_qs(parsed.query)["v"][0]
    if parsed.hostname == "youtu.be":
        return parsed.path[1:]
    raise ValueError("Invalid YouTube URL")

def get_raw_captions(url):
    video_id = get_video_id(url)
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id)
    rows = []
    for entry in transcript:
        rows.append({
            "start": entry.start,
            "duration": entry.duration,
            "text": entry.text
        })
    return pd.DataFrame(rows)

def merge_captions_by_count(df, group_size=2):
    merged = []
    for i in range(0, len(df), group_size):
        chunk = df.iloc[i:i + group_size]
        merged.append({
            "start": chunk.iloc[0]["start"],
            "text": " ".join(chunk["text"].tolist())
        })
    return pd.DataFrame(merged)

def get_video_metadata(video_url, api_key):
    video_id = get_video_id(video_url)
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {"part": "snippet,statistics", "id": video_id, "key": api_key}
    resp = requests.get(url, params=params).json()
    if "items" not in resp or len(resp["items"]) == 0:
        return None
    snippet = resp["items"][0]["snippet"]
    stats = resp["items"][0]["statistics"]
    return {
        "title": snippet.get("title", "Unknown Title"),
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0)),
        "dislikes": int(stats.get("dislikeCount", 0)) if "dislikeCount" in stats else "N/A"
    }

# ----------------------------
# INPUTS
# ----------------------------
col_key, col_url = st.columns([1, 3])
api_key = col_key.text_input("🔑 YouTube API Key", type="password")
video_url = col_url.text_input("🔗 YouTube Video URL")

if st.button("Analyze Video"):

    if not video_url:
        st.error("Please enter a YouTube video URL.")
        st.stop()
    if not api_key:
        st.error("Please enter your YouTube API key.")
        st.stop()

    # ----------------------------
    # FETCH VIDEO METADATA
    # ----------------------------
    try:
        meta = get_video_metadata(video_url, api_key)
        if not meta:
            st.error("Could not fetch video metadata. Check API key or video URL.")
            st.stop()
    except Exception as e:
        st.error(f"Error fetching metadata: {e}")
        st.stop()

    # Display video info at top
    st.subheader("🎥 Video Overview")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(meta["thumbnail"], use_column_width=True)
    with col2:
        st.markdown(f"### {meta['title']}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("👁️ Views", f"{meta['views']:,}")
        m2.metric("👍 Likes", f"{meta['likes']:,}")
        m3.metric("💬 Comments", f"{meta['comments']:,}")
        m4.metric("👎 Dislikes", meta['dislikes'])

    # ----------------------------
    # FETCH AND MERGE CAPTIONS
    # ----------------------------
    try:
        raw_df = get_raw_captions(video_url)
        df = merge_captions_by_count(raw_df, group_size=2)
    except Exception as e:
        st.error(f"Could not fetch captions: {e}")
        st.stop()

    if df.empty:
        st.error("No captions found.")
        st.stop()

    # ----------------------------
    # SENTIMENT ANALYSIS
    # ----------------------------
    df["time_min"] = df["start"] / 60
    df["polarity"] = df["text"].apply(lambda x: TextBlob(x).sentiment.polarity)
    df["intensity"] = df["polarity"].abs()

    def label_sentiment(p):
        if p > 0.05:
            return "Positive"
        elif p < -0.05:
            return "Negative"
        else:
            return "Neutral"

    df["sentiment"] = df["polarity"].apply(label_sentiment)
    df["rolling_polarity"] = df["polarity"].rolling(window=5, min_periods=1).mean()
    df["color"] = df["polarity"].apply(lambda p: "green" if p > 0.05 else ("red" if p < -0.05 else "gray"))
    df["polarity_diff"] = df["polarity"].diff().abs()

    # ----------------------------
    # KPI CALCULATIONS
    # ----------------------------
    volatility = round(df["polarity_diff"].mean(), 3)
    pos_count = (df["sentiment"] == "Positive").sum()
    neg_count = (df["sentiment"] == "Negative").sum()
    pos_neg_ratio = round(pos_count / max(neg_count, 1), 2)
    avg_polarity = round(df["polarity"].mean(), 3)
    peak_intensity_time = round(df["time_min"].iloc[df["intensity"].idxmax()], 2)

    # ----------------------------
    # DISPLAY KPI CARDS
    # ----------------------------
    st.subheader("⚡ Video Sentiment KPIs")
    kpi_html = f"""
    <div style="display: flex; gap: 20px; margin-bottom: 20px;">
        <div style="flex: 1; border:1px solid #ccc; padding:20px; border-radius:12px; background-color:#e0f7fa; text-align:center;">
            <h3>📊 Volatility</h3>
            <p style="font-size:24px; margin:0;">{volatility}</p>
        </div>
        <div style="flex: 1; border:1px solid #ccc; padding:20px; border-radius:12px; background-color:#f1f8e9; text-align:center;">
            <h3>⚖️ Pos/Neg Ratio</h3>
            <p style="font-size:24px; margin:0;">{pos_neg_ratio}</p>
        </div>
        <div style="flex: 1; border:1px solid #ccc; padding:20px; border-radius:12px; background-color:#fff3e0; text-align:center;">
            <h3>🧠 Avg Polarity</h3>
            <p style="font-size:24px; margin:0;">{avg_polarity}</p>
        </div>
        <div style="flex: 1; border:1px solid #ccc; padding:20px; border-radius:12px; background-color:#fce4ec; text-align:center;">
            <h3>⏱️ Peak Intensity Time (min)</h3>
            <p style="font-size:24px; margin:0;">{peak_intensity_time}</p>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    # ----------------------------
    # TABLE PREVIEW
    # ----------------------------
    st.subheader("📝 Caption Preview")
    st.dataframe(df[["time_min", "polarity", "sentiment", "text"]], use_container_width=True)

    # ----------------------------
    # SIDE-BY-SIDE CHARTS
    # ----------------------------
    st.subheader("📈 Sentiment Overview")
    col1, col2 = st.columns(2)
    with col1:
        fig1, ax1 = plt.subplots(figsize=(6, 4))
        ax1.scatter(df["time_min"], df["polarity"], c=df["color"], alpha=0.6)
        ax1.plot(df["time_min"], df["rolling_polarity"], color="black", linewidth=2, label="Smoothed Sentiment")
        ax1.axhline(0, linestyle="--", color="black", alpha=0.5)
        ax1.set_title("Sentiment Over Video Timeline")
        ax1.set_xlabel("Time (minutes)")
        ax1.set_ylabel("Polarity")
        ax1.legend()
        st.pyplot(fig1)

    with col2:
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        df["sentiment"].value_counts().reindex(["Positive", "Neutral", "Negative"]).plot(
            kind="bar", ax=ax2, color=["green", "gray", "red"]
        )
        ax2.set_title("Sentiment Distribution")
        ax2.set_ylabel("Count")
        st.pyplot(fig2)

    # ----------------------------
    # INTENSITY & HEATMAP
    # ----------------------------
    st.subheader("🔥 Sentiment Intensity & Heatmap")
    colA, colB = st.columns(2)
    with colA:
        fig3, ax3 = plt.subplots(figsize=(6, 4))
        ax3.plot(df["time_min"], df["intensity"], color="purple", linewidth=2)
        ax3.set_title("Sentiment Intensity Over Time")
        ax3.set_xlabel("Time (minutes)")
        ax3.set_ylabel("Intensity (|Polarity|)")
        st.pyplot(fig3)
    with colB:
        fig4, ax4 = plt.subplots(figsize=(6, 4))
        heatmap = df["polarity"].values[np.newaxis, :]
        c = ax4.imshow(heatmap, aspect="auto", cmap="RdYlGn", vmin=-1, vmax=1)
        ax4.set_title("Sentiment Heatmap")
        ax4.set_xlabel("Time Index")
        ax4.set_yticks([])
        fig4.colorbar(c, ax=ax4, orientation='vertical', label="Polarity")
        st.pyplot(fig4)

    # ----------------------------
    # STRONGEST MOMENTS
    # ----------------------------
    st.subheader("🏆 Strongest Emotional Moments")
    colC, colD = st.columns(2)
    with colC:
        st.write("### 🌟 Most Positive Moments")
        st.table(df.sort_values("polarity", ascending=False).head(8)[["time_min", "polarity", "text"]].reset_index(drop=True))
    with colD:
        st.write("### 💀 Most Negative Moments")
        st.table(df.sort_values("polarity").head(8)[["time_min", "polarity", "text"]].reset_index(drop=True))

    # ----------------------------
    # DOWNLOAD CSV
    # ----------------------------
    st.subheader("⬇️ Download Results")
    st.download_button(
        "Download Caption Sentiment CSV",
        data=df.to_csv(index=False).encode(),
        file_name="caption_sentiment_contextual.csv",
        mime="text/csv"
    )
