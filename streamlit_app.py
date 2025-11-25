import streamlit as st
import requests
import re
import pandas as pd
import matplotlib.pyplot as plt
from textblob import TextBlob

# ------------------------------
# STREAMLIT LAYOUT
# ------------------------------
st.set_page_config(page_title="YouTube Comment Sentiment Analyzer", layout="wide")
st.title("📊 YouTube Comment Sentiment Dashboard")
st.write("Analyze sentiment, polarity, and extract top positive/negative comments.")

# ------------------------------
# INPUT
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

            response = requests.get(url, params=params)
            data = response.json()

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
    # Display Data Table
    # ------------------------------
    st.subheader("📄 Full Comments Table")
    st.dataframe(df)

    # ------------------------------
    # Visualizations
    # ------------------------------
    st.subheader("📈 Sentiment Distribution")

    # Bar chart
    fig, ax = plt.subplots()
    df["sentiment"].value_counts().plot(kind="bar", ax=ax)
    ax.set_title("Sentiment Count")
    ax.set_xlabel("Sentiment")
    ax.set_ylabel("Count")
    st.pyplot(fig)

    # Polarity histogram
    st.subheader("📊 Polarity Score Distribution")
    fig2, ax2 = plt.subplots()
    ax2.hist(df["polarity"], bins=20)
    ax2.set_title("Polarity Histogram")
    ax2.set_xlabel("Polarity")
    ax2.set_ylabel("Frequency")
    st.pyplot(fig2)

    # ------------------------------
    # Top Positive & Negative
    # ------------------------------
    st.subheader("🏆 Top 10 Most Positive Comments")
    top_positive = df.sort_values("polarity", ascending=False).head(10)
    for idx, row in top_positive.iterrows():
        st.write(f"**Polarity {row['polarity']:.2f}** — {row['comment']}")

    st.subheader("💀 Top 10 Most Negative Comments")
    top_negative = df.sort_values("polarity").head(10)
    for idx, row in top_negative.iterrows():
        st.write(f"**Polarity {row['polarity']:.2f}** — {row['comment']}")

    # ------------------------------
    # Download
    # ------------------------------
    st.subheader("⬇️ Download Results")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="youtube_sentiment_analysis.csv",
        mime="text/csv"
    )
