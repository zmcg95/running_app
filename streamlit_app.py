import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from textblob import TextBlob
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="YouTube Caption Sentiment Timeline",
    layout="wide"
)

st.title("🎬 YouTube Caption Sentiment Analyzer")
st.write(
    "Sentiment analysis using **ONLY YouTube captions**.\n\n"
    "• Captions merged for better context (2× original size)\n"
    "• Color-coded sentiment visuals\n"
    "• No comments, no API keys"
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

# ----------------------------
# INPUT
# ----------------------------
video_url = st.text_input("🔗 Enter YouTube Video URL")

if st.button("Analyze Captions"):

    if not video_url:
        st.error("Please enter a YouTube video URL.")
        st.stop()

    # Fetch and merge captions
    try:
        raw_df = get_raw_captions(video_url)
        df = merge_captions_by_count(raw_df, group_size=2)  # 2× context
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

    def label_sentiment(p):
        if p > 0.05:
            return "Positive"
        elif p < -0.05:
            return "Negative"
        else:
            return "Neutral"

    df["sentiment"] = df["polarity"].apply(label_sentiment)
    df["rolling_polarity"] = df["polarity"].rolling(window=5, min_periods=1).mean()

    # Color for plots
    def sentiment_color(p):
        if p > 0.05:
            return "green"
        elif p < -0.05:
            return "red"
        else:
            return "gray"

    df["color"] = df["polarity"].apply(sentiment_color)

    # ----------------------------
    # KPI CALCULATIONS
    # ----------------------------
    # 1. Sentiment Volatility (mean absolute difference between consecutive polarities)
    df["polarity_diff"] = df["polarity"].diff().abs()
    volatility = round(df["polarity_diff"].mean(), 3)

    # 2. Positive vs Negative Ratio
    pos_count = (df["sentiment"] == "Positive").sum()
    neg_count = (df["sentiment"] == "Negative").sum()
    pos_neg_ratio = round(pos_count / max(neg_count, 1), 2)

    # ----------------------------
    # DISPLAY KPIs
    # ----------------------------
    kpi1, kpi2 = st.columns(2)
    kpi1.metric("⚡ Sentiment Volatility", volatility)
    kpi2.metric("📊 Positive/Negative Ratio", pos_neg_ratio)

    # ----------------------------
    # PREVIEW TABLE
    # ----------------------------
    st.subheader("📝 Caption Preview (Merged for Context)")
    st.dataframe(df[["time_min", "polarity", "sentiment", "text"]], use_container_width=True)

    # ----------------------------
    # SIDE-BY-SIDE CHARTS
    # ----------------------------
    st.subheader("📈 Sentiment Analysis Overview")
    col1, col2 = st.columns(2)

    # Sentiment timeline
    with col1:
        fig1, ax1 = plt.subplots(figsize=(6, 4))
        ax1.scatter(df["time_min"], df["polarity"], c=df["color"], alpha=0.6)
        ax1.plot(df["time_min"], df["rolling_polarity"], color="black", linewidth=2, label="Smoothed Sentiment")
        ax1.axhline(0, linestyle="--", color="black", alpha=0.5)
        ax1.set_title("Sentiment Over Video Timeline")
        ax1.set_xlabel("Time (minutes)")
        ax1.set_ylabel("Polarity (-1 to 1)")
        ax1.legend()
        st.pyplot(fig1)

    # Sentiment distribution
    with col2:
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        df["sentiment"].value_counts().reindex(["Positive", "Neutral", "Negative"]).plot(
            kind="bar", ax=ax2, color=["green", "gray", "red"]
        )
        ax2.set_ylabel("Count")
        ax2.set_title("Sentiment Distribution")
        st.pyplot(fig2)

    # ----------------------------
    # STRONGEST MOMENTS
    # ----------------------------
    st.subheader("🔥 Strongest Emotional Moments")
    colA, colB = st.columns(2)

    with colA:
        st.write("### 🌟 Most Positive Moments")
        st.table(df.sort_values("polarity", ascending=False).head(8)[["time_min", "polarity", "text"]].reset_index(drop=True))

    with colB:
        st.write("### 💀 Most Negative Moments")
        st.table(df.sort_values("polarity").head(8)[["time_min", "polarity", "text"]].reset_index(drop=True))

    # ----------------------------
    # DOWNLOAD
    # ----------------------------
    st.subheader("⬇️ Download Results")
    st.download_button(
        "Download Caption Sentiment CSV",
        data=df.to_csv(index=False).encode(),
        file_name="caption_sentiment_contextual.csv",
        mime="text/csv"
    )
