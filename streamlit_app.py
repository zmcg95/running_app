import streamlit as st
import requests
import re
import pandas as pd
import matplotlib.pyplot as plt
from textblob import TextBlob
import numpy as np

# ------------------------------
# STREAMLIT LAYOUT
# ------------------------------
st.set_page_config(page_title="YouTube Comment Sentiment Analyzer", layout="wide")
st.title("📊 YouTube Comment Sentiment Dashboard")
st.write("Analyze sentiment, polarity, and extract top positive/negative comments.")

# ------------------------------
# INPUTS
# ------------------------------
API_KEY = st.text_input("🔑 Enter YouTube API Key", type="password")
youtube_url = st.text_input("📺 Enter YouTube Video URL", placeholder="https://www.youtube.com/watch?v=xxxxx")

MAX_COMMENTS = st.slider("How many comments to fetch?", 20, 200, 100)

if st.button("Analyze Video"):
    if not API_KEY or not youtube_url:
        st.error("API key and URL are required.")
        st.stop()

    # ------------------------------
    # Extract Video ID
    # ------------------------------
    match = re.search(r"v=([a-zA-Z0-9_-]+)", youtube_url)
    if not match:
        st.error("Invalid YouTube URL.")
        st.stop()

    VIDEO_ID = match.group(1)

    # ------------------------------
    # Fetch Comments
    # ------------------------------
    url = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        "part": "snippet",
        "videoId": VIDEO_ID,
        "key": API_KEY,
        "maxResults": 100,
        "textFormat": "plainText"
    }

    all_comments = []
    next_page = None

    with st.spinner("Fetching comments..."):
        while len(all_comments) < MAX_COMMENTS:
            if next_page:
                params["pageToken"] = next_page

            resp = requests.get(url, params=params)
            data = resp.json()

            for item in data.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                all_comments.append(snippet["textDisplay"])

            next_page = data.get("nextPageToken")
            if not next_page:
                break

    st.success(f"Fetched {len(all_comments)} comments!")

    # ------------------------------
    # Sentiment Analysis
    # ------------------------------
    processed = []
    for text in all_comments:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity

        if polarity > 0.1:
            sentiment = "Positive"
        elif polarity < -0.1:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"

        processed.append({
            "comment": text,
            "polarity": polarity,
            "sentiment": sentiment
        })

    df = pd.DataFrame(processed)

    # ------------------------------
    # Display Table
    # ------------------------------
    st.subheader("📄 Full Comments Table")
    st.dataframe(df)

    # ------------------------------
    # SIDE-BY-SIDE GRAPHS
    # ------------------------------
    st.subheader("📈 Visual Insights")

    col1, col2 = st.columns(2)

    # ---------- SENTIMENT BAR CHART ----------
    with col1:
        fig1, ax1 = plt.subplots()

        sentiment_counts = df["sentiment"].value_counts()

        colors = {
            "Positive": "green",
            "Neutral": "gray",
            "Negative": "red"
        }

        sentiment_counts.plot(kind="bar", color=[colors[s] for s in sentiment_counts.index], ax=ax1)
        ax1.set_title("Sentiment Distribution")
        ax1.set_xlabel("")
        ax1.set_ylabel("Count")

        st.pyplot(fig1)

    # ---------- POLARITY HISTOGRAM (RED→GREEN GRADIENT) ----------
    with col2:
        fig2, ax2 = plt.subplots()

        # Gradient from red (-1) → yellow (0) → green (1)
        cmap = plt.get_cmap("RdYlGn")

        # Normalize values to 0–1 range for colormap
        norm_polarity = (df["polarity"] + 1) / 2

        ax2.scatter(df["polarity"], np.zeros_like(df["polarity"]), c=norm_polarity, cmap=cmap)

        ax2.hist(df["polarity"], bins=20, color="lightgray", edgecolor="black")
        ax2.set_title("Polarity Distribution")
        ax2.set_xlabel("Polarity (-1 = Red, +1 = Green)")
        ax2.set_ylabel("Frequency")

        st.pyplot(fig2)

    # ------------------------------
    # TOP 10 TABLES
    # ------------------------------
    st.subheader("🏆 Top Comments")

    top_positive = df.sort_values("polarity", ascending=False).head(10)
    top_negative = df.sort_values("polarity").head(10)

    col3, col4 = st.columns(2)

    with col3:
        st.write("### 🌟 Top 10 Positive Comments")
        st.table(top_positive[["polarity", "comment"]])

    with col4:
        st.write("### 💀 Top 10 Negative Comments")
        st.table(top_negative[["polarity", "comment"]])

    # ------------------------------
    # DOWNLOAD CSV
    # ------------------------------
    st.subheader("⬇️ Download Results")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="youtube_sentiment_analysis.csv",
        mime="text/csv"
    )
