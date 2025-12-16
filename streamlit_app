import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from textblob import TextBlob
from youtube_transcript_api import YouTubeTranscriptApi
import re

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="YouTube Caption Sentiment Analyzer",
    layout="wide"
)

st.title("🎬 YouTube Caption Sentiment Timeline")
st.write("**Sentiment analysis using ONLY video captions (no comments).**")

# ----------------------------
# INPUT
# ----------------------------
video_url = st.text_input("🔗 Enter YouTube Video URL")

if st.button("Analyze Captions"):

    if not video_url:
        st.error("Please enter a YouTube video URL.")
        st.stop()

    # Extract video ID
    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", video_url)
    if not match:
        st.error("Invalid YouTube URL.")
        st.stop()

    video_id = match.group(1)

    # ----------------------------
    # FETCH CAPTIONS
    # ----------------------------
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
    except Exception as e:
        st.error("Captions not available for this video.")
        st.stop()

    df = pd.DataFrame(transcript)
    df = df[["start", "duration", "text"]]
    df["time_min"] = df["start"] / 60

    # ----------------------------
    # SENTIMENT ANALYSIS
    # ----------------------------
    df["polarity"] = df["text"].apply(lambda x: TextBlob(x).sentiment.polarity)

    def label_sentiment(p):
        if p > 0.05:
            return "Positive"
        elif p < -0.05:
            return "Negative"
        else:
            return "Neutral"

    df["sentiment"] = df["polarity"].apply(label_sentiment)

    # Rolling sentiment (smooth timeline)
    df["rolling_polarity"] = df["polarity"].rolling(window=10, min_periods=1).mean()

    # ----------------------------
    # DATA PREVIEW
    # ----------------------------
    st.subheader("📝 Caption Data Preview")
    st.dataframe(df.head(30), use_container_width=True)

    # ----------------------------
    # VISUALS
    # ----------------------------
    st.subheader("📈 Sentiment Visualizations")

    col1, col2 = st.columns(2)

    # --- Polarity over time ---
    with col1:
        fig1, ax1 = plt.subplots(figsize=(8, 4))
        ax1.plot(df["time_min"], df["polarity"], alpha=0.5)
        ax1.plot(df["time_min"], df["rolling_polarity"], linewidth=2)
        ax1.axhline(0, linestyle="--")

        ax1.set_title("Sentiment Polarity Over Video Timeline")
        ax1.set_xlabel("Time (minutes)")
        ax1.set_ylabel("Polarity (-1 to 1)")
        st.pyplot(fig1)

    # --- Sentiment distribution ---
    with col2:
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        df["sentiment"].value_counts().plot(
            kind="bar",
            ax=ax2
        )
        ax2.set_title("Sentiment Distribution (Captions)")
        ax2.set_ylabel("Count")
        st.pyplot(fig2)

    # ----------------------------
    # POLARITY HISTOGRAM
    # ----------------------------
    st.subheader("📊 Polarity Distribution")

    fig3, ax3 = plt.subplots(figsize=(10, 4))
    ax3.hist(df["polarity"], bins=30)
    ax3.set_title("Histogram of Caption Sentiment Polarity")
    ax3.set_xlabel("Polarity")
    ax3.set_ylabel("Frequency")
    st.pyplot(fig3)

    # ----------------------------
    # STRONGEST MOMENTS
    # ----------------------------
    st.subheader("🔥 Strongest Emotional Moments")

    colA, colB = st.columns(2)

    with colA:
        st.write("### 🌟 Most Positive Captions")
        st.table(
            df.sort_values("polarity", ascending=False)
              .head(10)[["time_min", "polarity", "text"]]
              .reset_index(drop=True)
        )

    with colB:
        st.write("### 💀 Most Negative Captions")
        st.table(
            df.sort_values("polarity")
              .head(10)[["time_min", "polarity", "text"]]
              .reset_index(drop=True)
        )

    # ----------------------------
    # DOWNLOAD
    # ----------------------------
    st.subheader("⬇️ Download Caption Sentiment Data")

    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False).encode(),
        file_name="caption_sentiment_timeline.csv",
        mime="text/csv"
    )
