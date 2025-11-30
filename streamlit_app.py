import streamlit as st
import requests
import re
import pandas as pd
import matplotlib.pyplot as plt
from textblob import TextBlob
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

st.set_page_config(layout="wide", page_title="YouTube Sentiment Dashboard")

# ------------------------------------------
#               INPUT AREA
# ------------------------------------------
st.title("🎥 YouTube Sentiment Dashboard")
video_url = st.text_input("Enter a YouTube Video URL:")

API_KEY = st.secrets["API_KEY"] if "API_KEY" in st.secrets else "YOUR_API_KEY_HERE"

if video_url:
    # Extract video ID
    match = re.search(r"v=([a-zA-Z0-9_-]+)", video_url)
    if not match:
        st.error("Invalid YouTube URL.")
        st.stop()

    VIDEO_ID = match.group(1)

    # ------------------------------------------
    #          FETCH VIDEO DETAILS
    # ------------------------------------------
    video_api = "https://www.googleapis.com/youtube/v3/videos"
    params_vid = {
        "part": "snippet,statistics",
        "id": VIDEO_ID,
        "key": API_KEY
    }
    data_video = requests.get(video_api, params=params_vid).json()

    if "items" not in data_video or len(data_video["items"]) == 0:
        st.error("Video not found.")
        st.stop()

    vid = data_video["items"][0]
    title = vid["snippet"]["title"]
    thumbnail = vid["snippet"]["thumbnails"]["high"]["url"]
    views = int(vid["statistics"].get("viewCount", 0))
    channel_id = vid["snippet"]["channelId"]
    channel_title = vid["snippet"]["channelTitle"]

    # ------------------------------------------
    #          FETCH CHANNEL DETAILS
    # ------------------------------------------
    channel_api = "https://www.googleapis.com/youtube/v3/channels"
    params_channel = {
        "part": "statistics",
        "id": channel_id,
        "key": API_KEY
    }
    channel_data = requests.get(channel_api, params=params_channel).json()
    subs = int(channel_data["items"][0]["statistics"]["subscriberCount"])

    # ------------------------------------------
    #               DISPLAY KPI
    # ------------------------------------------
    colA, colB, colC, colD = st.columns([1, 1, 1, 1])

    with colA:
        st.metric("Video Title", title)
    with colB:
        st.metric("Channel", channel_title)
    with colC:
        st.metric("Views", f"{views:,}")
    with colD:
        st.metric("Subscribers", f"{subs:,}")

    st.image(thumbnail, width=400)

    # ------------------------------------------
    #          FETCH COMMENTS
    # ------------------------------------------
    comment_api = "https://www.googleapis.com/youtube/v3/commentThreads"
    params_comments = {
        "part": "snippet",
        "videoId": VIDEO_ID,
        "key": API_KEY,
        "maxResults": 100,
        "textFormat": "plainText"
    }

    resp = requests.get(comment_api, params=params_comments).json()
    comments = []

    for item in resp.get("items", []):
        snippet = item["snippet"]["topLevelComment"]["snippet"]
        text = snippet["textDisplay"]

        blob = TextBlob(text).sentiment.polarity

        if blob > 0.1:
            sentiment = "Positive"
        elif blob < -0.1:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"

        comments.append({
            "text": text,
            "sentiment": sentiment,
            "polarity": float(blob)
        })

    st.success(f"Fetched {len(comments)} comments!")

    df = pd.DataFrame(comments)

    # ------------------------------------------
    #       SENTIMENT DISTRIBUTION PLOT
    # ------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Sentiment Distribution")
        fig, ax = plt.subplots()
        sentiment_counts = df["sentiment"].value_counts()
        ax.bar(sentiment_counts.index, sentiment_counts.values,
               color=["green", "grey", "red"])
        ax.set_ylabel("Count")
        st.pyplot(fig)

    with col2:
        st.subheader("Polarity Distribution")
        fig2, ax2 = plt.subplots()
        cmap = plt.get_cmap("RdYlGn")  # red→yellow→green
        colors = [cmap((p + 1) / 2) for p in df["polarity"]]

        ax2.bar(range(len(df["polarity"])), df["polarity"], color=colors)
        ax2.axhline(0, color="black", linestyle="--")
        ax2.set_ylabel("Polarity")
        st.pyplot(fig2)

    # ------------------------------------------
    #       TOP 10 POSITIVE / NEGATIVE
    # ------------------------------------------
    st.subheader("Top 10 Positive Comments")
    st.table(df.sort_values("polarity", ascending=False).head(10)[["text", "polarity"]])

    st.subheader("Top 10 Negative Comments")
    st.table(df.sort_values("polarity", ascending=True).head(10)[["text", "polarity"]])

    # ------------------------------------------
    #         SENTIMENT BY TRANSCRIPT
    # ------------------------------------------
    st.header("Transcript Sentiment Over Time")

    def fetch_transcript(video_id):
        try:
            # Try direct English transcript
            try:
                return YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            except:
                pass

            transcripts = YouTubeTranscriptApi.list_transcripts(video_id)

            for lang in ["en", "en-US", "a.en"]:
                try:
                    return transcripts.find_transcript([lang]).fetch()
                except:
                    continue

            return None

        except (TranscriptsDisabled, NoTranscriptFound):
            return None
        except Exception as e:
            st.error(f"Transcript Error: {e}")
            return None

    transcript = fetch_transcript(VIDEO_ID)

    if transcript:
        times = [t["start"] for t in transcript]
        texts = [t["text"] for t in transcript]
        sentiments = [TextBlob(t).sentiment.polarity for t in texts]

        df_trans = pd.DataFrame({"time": times, "sentiment": sentiments})

        fig3, ax3 = plt.subplots(figsize=(12, 4))
        ax3.plot(df_trans["time"], df_trans["sentiment"])
        ax3.axhline(0, linestyle="--", color="black")
        ax3.set_title("Sentiment Over Video Timeline")
        ax3.set_xlabel("Time (seconds)")
        ax3.set_ylabel("Sentiment")
        st.pyplot(fig3)
    else:
        st.warning("No transcript available for this video.")

    # ------------------------------------------
    #     LAST 10 VIDEOS SENTIMENT COMPARISON
    # ------------------------------------------
    st.header("Last 10 Videos from Channel")

    search_api = "https://www.googleapis.com/youtube/v3/search"
    params_search = {
        "part": "snippet",
        "channelId": channel_id,
        "order": "date",
        "maxResults": 10,
        "key": API_KEY
    }

    recent = requests.get(search_api, params=params_search).json()

    video_ids = [x["id"]["videoId"] for x in recent.get("items", [])
                 if x["id"]["kind"] == "youtube#video"]

    view_counts = []
    titles = []

    for vid in video_ids:
        params_stats = {
            "part": "statistics,snippet",
            "id": vid,
            "key": API_KEY
        }
        stats = requests.get(video_api, params=params_stats).json()
        if "items" in stats and len(stats["items"]) > 0:
            item = stats["items"][0]
            titles.append(item["snippet"]["title"])
            view_counts.append(int(item["statistics"].get("viewCount", 0)))

    fig4, ax4 = plt.subplots(figsize=(10, 5))
    ax4.plot(range(len(view_counts)), view_counts, marker="o")
    ax4.axhline(views, color="red", linestyle="--", label="Current Video Views")
    ax4.set_xticks(range(len(titles)))
    ax4.set_xticklabels([t[:20] + "..." for t in titles], rotation=45, ha='right')
    ax4.set_ylabel("Views")
    ax4.set_title("Last 10 Videos View Comparison")
    ax4.legend()
    st.pyplot(fig4)
