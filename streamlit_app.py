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
# SIDE-BY-SIDE GRAPHS (UPDATED)
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

    sentiment_counts.plot(
        kind="bar",
        color=[colors.get(s, "gray") for s in sentiment_counts.index],
        ax=ax1
    )
    ax1.set_title("Sentiment Distribution")
    ax1.set_xlabel("")
    ax1.set_ylabel("Count")
    ax1.tick_params(axis='x', rotation=0)
    st.pyplot(fig1)

# ---------- POLARITY HISTOGRAM WITH RED→GREEN BAR COLORS ----------
with col2:
    fig2, ax2 = plt.subplots()

    # compute histogram manually so we can color each bar
    vals = df["polarity"].dropna().values
    bins = 20
    counts, bin_edges = np.histogram(vals, bins=bins, range=(-1, 1))

    # compute bin centers and normalize to 0..1 for colormap
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    norm_centers = (bin_centers + 1) / 2  # map -1..1 -> 0..1

    cmap = plt.get_cmap("RdYlGn")  # red->yellow->green
    bar_colors = [cmap(n) for n in norm_centers]

    ax2.bar(bin_centers, counts, width=(bin_edges[1]-bin_edges[0]) * 0.95, color=bar_colors, edgecolor="black")
    ax2.set_title("Polarity Distribution (Red → Green)")
    ax2.set_xlabel("Polarity (-1 = Negative, +1 = Positive)")
    ax2.set_ylabel("Frequency")
    ax2.set_xlim(-1, 1)
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
