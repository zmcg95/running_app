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
    "• Color-coded sentiment\n"
    "• Context-aware caption grouping\n"
    "• No comments, no API keys"
)

# ----------------------------
# HELPERS (YOUR WORKING LOGIC)
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

# ----------------------------
# CONTEXT MERGING
# ----------------------------
def merge_captions(df, window_seconds=10):
    merged = []
    buffer_text = []
    buffer_start = None
    elapsed = 0

    for _, row in df.iterrows():
        if buffer_start is None:
            buffer_start = row["start"]

        buffer_text.append(row["text"])
        elapsed += row["duration"]

        if elapsed >= window_seconds:
            merged.append({
                "start": buffer_start,
                "text": " ".join(buffer_text)
            })
            buffer_text = []
            buffer_start = None
            elapsed = 0

    if buffer_text:
        merged.append({
            "start": buffer_start,
            "text": " ".join(buffer_text)
        })

    return pd.DataFrame(merged)

# ----------------------------
# INPUT
# ----------------------------
video_url = st.text_input("🔗 Enter YouTube Video URL")

context_window = st.slider(
    "🧠 Context window (seconds per sentiment block)",
    min_value=5,
    max_value=20,
    value=10,
    step=1
)

if st.button("Analyze Captions"):

    if not video_url:
        st.error("Please enter a YouTube video URL.")
        st.stop()

    # ----------------------------
    # FETCH + MERGE CAPTIONS
    # ----------------------------
    try:
        raw_df = get_raw_captions(video_url)
        df = merge_captions(raw_df, window_seconds=context_window)
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
    df["polarity"] = df["text"].apply(
        lambda x: TextBlob(x).sentiment.polarity
    )

    def label_sentiment(p):
        if p > 0.05:
            return "Positive"
        elif p < -0.05:
            return "Negative"
        else:
            return "Neutral"

    df["sentiment"] = df["polarity"].apply(label_sentiment)

    # Smoothed polarity
    df["rolling_polarity"] = (
        df["polarity"]
        .rolling(window=5, min_periods=1)
        .mean()
    )

    # ----------------------------
    # COLOR MAP
    # ----------------------------
    def sentiment_color(p):
        if p > 0.05:
            return "green"
        elif p < -0.05:
            return "red"
        else:
            return "gray"

    df["color"] = df["polarity"].apply(sentiment_color)

    # ----------------------------
    # PREVIEW TABLE (COLOR)
    # ----------------------------
    st.subheader("📝 Caption Blocks (Context-Aware)")

    def color_rows(row):
        return [f"color: {row.color}"] * len(row)

    st.dataframe(
        df[["time_min", "polarity", "sentiment", "text"]]
        .style.apply(color_rows, axis=1),
        use_container_width=True
    )

    # ----------------------------
    # SENTIMENT TIMELINE (COLORED)
    # ----------------------------
    st.subheader("📈 Sentiment Over Video Timeline")

    fig1, ax1 = plt.subplots(figsize=(12, 4))

    ax1.scatter(
        df["time_min"],
        df["polarity"],
        c=df["color"],
        alpha=0.6
    )

    ax1.plot(
        df["time_min"],
        df["rolling_polarity"],
        linewidth=2,
        color="black",
        label="Smoothed Sentiment"
    )

    ax1.axhline(0, linestyle="--", color="black", alpha=0.5)

    ax1.set_title("Caption Sentiment Timeline (Green=Positive, Red=Negative)")
    ax1.set_xlabel("Time (minutes)")
    ax1.set_ylabel("Polarity (-1 to 1)")
    ax1.legend()

    st.pyplot(fig1)

    # ----------------------------
    # DISTRIBUTION
    # ----------------------------
    st.subheader("📊 Sentiment Distribution")

    fig2, ax2 = plt.subplots(figsize=(6, 4))
    df["sentiment"].value_counts().reindex(
        ["Positive", "Neutral", "Negative"]
    ).plot(
        kind="bar",
        ax=ax2,
        color=["green", "gray", "red"]
    )

    ax2.set_ylabel("Count")
    ax2.set_title("Caption Sentiment Breakdown")
    st.pyplot(fig2)

    # ----------------------------
    # STRONGEST MOMENTS
    # ----------------------------
    st.subheader("🔥 Strongest Emotional Moments")

    colA, colB = st.columns(2)

    with colA:
        st.write("### 🌟 Most Positive Moments")
        st.table(
            df.sort_values("polarity", ascending=False)
              .head(8)[["time_min", "polarity", "text"]]
              .reset_index(drop=True)
        )

    with colB:
        st.write("### 💀 Most Negative Moments")
        st.table(
            df.sort_values("polarity")
              .head(8)[["time_min", "polarity", "text"]]
              .reset_index(drop=True)
        )

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
