from textblob import TextBlob
import matplotlib.pyplot as plt
import re
from youtube_transcript_api import YouTubeTranscriptApi

# ----------------------------
# ---------------------------------------------------------
# PAGE SETTINGS
# ----------------------------
st.set_page_config(page_title="YouTube Sentiment Dashboard", layout="wide")
# ---------------------------------------------------------
st.set_page_config(page_title="YouTube Comment Sentiment Analyzer", layout="wide")
st.title("📊 YouTube Comment Sentiment Analyzer")

# ----------------------------
# USER INPUTS
# ----------------------------
# ---------------------------------------------------------
# INPUTS
# ---------------------------------------------------------
api_key = st.text_input("🔑 Enter Your YouTube API Key", type="password")
video_url = st.text_input("🎥 Enter YouTube Video URL")

if st.button("Fetch & Analyze"):
if st.button("Fetch & Analyze Video"):
if not api_key or not video_url:
        st.error("Please enter BOTH the API key and video URL.")
        st.error("Please provide BOTH an API key and a YouTube video URL.")
st.stop()

# Extract video ID
match = re.search(r"v=([a-zA-Z0-9_-]+)", video_url)
if not match:
st.error("Invalid YouTube URL format.")
st.stop()

video_id = match.group(1)

    # ----------------------------
    # ---------------------------------------------------------
# FETCH VIDEO METADATA
    # ----------------------------
    # ---------------------------------------------------------
video_meta_url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
    video_meta_params = {
"part": "snippet,statistics",
"id": video_id,
"key": api_key
}
    meta_resp = requests.get(video_meta_url, params=params).json()

    if "items" not in meta_resp or len(meta_resp["items"]) == 0:
    video_meta_response = requests.get(video_meta_url, params=video_meta_params)
    video_meta = video_meta_response.json()

    if "items" not in video_meta or len(video_meta["items"]) == 0:
st.error("Could not fetch video metadata.")
st.stop()

    snippet = meta_resp["items"][0]["snippet"]
    stats = meta_resp["items"][0]["statistics"]
    snippet = video_meta["items"][0]["snippet"]
    stats = video_meta["items"][0]["statistics"]

title = snippet.get("title", "Unknown Title")
    channel_id = snippet.get("channelId")
views = int(stats.get("viewCount", 0))
likes = int(stats.get("likeCount", 0))
    comment_count = int(stats.get("commentCount", 0))
    engagement = ((likes + comment_count) / max(views, 1)) * 100
    comments_count = int(stats.get("commentCount", 0))
    channel_id = snippet.get("channelId")

    # ----------------------------
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

    # ---------------------------------------------------------
# FETCH CHANNEL SUBSCRIBERS
    # ----------------------------
    # ---------------------------------------------------------
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
    channel_data = requests.get(channel_url, params=channel_params).json()
    subs = int(channel_data["items"][0]["statistics"].get("subscriberCount", 0))

    # ---------------------------------------------------------
    # KPI CARDS
    # ---------------------------------------------------------
    st.subheader("📌 Video KPIs")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Views", f"{views:,}")
    k2.metric("Likes", f"{likes:,}")
    k3.metric("Comments", f"{comments_count:,}")
    k4.metric("Subscribers", f"{subs:,}")

    # Engagement Rate (simple)
    er = (likes + comments_count) / max(views, 1)
    k5.metric("Engagement Rate", f"{er:.2%}")

    # Display video info
    st.subheader("🎬 Video Information")
    st.image(thumbnail_url, width=450)
    st.write(f"**📌 Title:** {title}")

    # ---------------------------------------------------------
    # FETCH 10 MOST RECENT VIDEOS FROM CHANNEL
    # ---------------------------------------------------------
    search_url = "https://www.googleapis.com/youtube/v3/search"
    search_params = {
        "part": "snippet",
        "channelId": channel_id,
        "maxResults": 10,
        "order": "date",
        "key": api_key
    }

    recent = requests.get(search_url, params=search_params).json()
    video_ids_recent = [i["id"].get("videoId") for i in recent["items"] if i["id"].get("videoId")]

    # Fetch stats for these videos
    stats_url = "https://www.googleapis.com/youtube/v3/videos"
    stats_params = {
        "part": "statistics,snippet",
        "id": ",".join(video_ids_recent),
        "key": api_key
    }

    recent_stats = requests.get(stats_url, params=stats_params).json()

    thumbnail = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    recent_titles = []
    recent_views = []

    # ----------------------------
    # DISPLAY VIDEO & METRICS
    # ----------------------------
    st.subheader("🎬 Video Overview")
    col_vid, col_meta = st.columns([1, 2])
    for v in recent_stats["items"]:
        recent_titles.append(v["snippet"]["title"])
        recent_views.append(int(v["statistics"].get("viewCount", 0)))

    with col_vid:
        st.image(thumbnail, width=420)
    # ---------------------------------------------------------
    # RECENT VIDEOS VIEW COMPARISON CHART
    # ---------------------------------------------------------
    st.subheader("📈 Recent Video Performance (View Comparison)")

    with col_meta:
        st.write(f"### {title}")
    fig_cmp, ax_cmp = plt.subplots(figsize=(10, 4))
    ax_cmp.plot(recent_titles, recent_views, marker='o')
    ax_cmp.axhline(views, linestyle="--", linewidth=2)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("👁️ Views", f"{views:,}")
        m2.metric("👍 Likes", f"{likes:,}")
        m3.metric("💬 Comments", f"{comment_count:,}")
        m4.metric("👥 Subscribers", f"{subs:,}")
    ax_cmp.set_title("View Counts of Last 10 Videos")
    ax_cmp.set_ylabel("Views")
    ax_cmp.set_xticklabels(recent_titles, rotation=45, ha="right")

        m5, m6 = st.columns(2)
        m5.metric("📈 Engagement Rate", f"{engagement:.2f}%")
        m6.metric("🔥 Custom Score", custom_score)
    st.pyplot(fig_cmp)

    # ----------------------------
    # ---------------------------------------------------------
# FETCH COMMENTS
    # ----------------------------
    comment_url = "https://www.googleapis.com/youtube/v3/commentThreads"
    # ---------------------------------------------------------
    comments_url = "https://www.googleapis.com/youtube/v3/commentThreads"
params = {
"part": "snippet",
"videoId": video_id,
@@ -107,132 +151,130 @@
"textFormat": "plainText"
}

    resp = requests.get(comment_url, params=params).json()
    response = requests.get(comments_url, params=params)
    data = response.json()

comments = [
item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
        for item in resp.get("items", [])
        for item in data.get("items", [])
]

    st.success(f"Fetched {len(comments)} comments.")
    if not comments:
        st.warning("No comments found.")
        st.stop()

    # ----------------------------
    # SENTIMENT ANALYSIS
    # ----------------------------
    sentiment = []
    polarities = []
    st.success(f"Fetched {len(comments)} comments!")

    for c in comments:
        p = TextBlob(c).sentiment.polarity
        polarities.append(p)
    # ---------------------------------------------------------
    # SENTIMENT ANALYSIS (COMMENTS)
    # ---------------------------------------------------------
    polarity_scores = []
    sentiment_labels = []

        if p > 0.05:
            sentiment.append("Positive")
        elif p < -0.05:
            sentiment.append("Negative")
    for c in comments:
        polarity = TextBlob(c).sentiment.polarity
        polarity_scores.append(polarity)

        if polarity > 0.05:
            sentiment_labels.append("Positive")
        elif polarity < -0.05:
            sentiment_labels.append("Negative")
            sentiment_labels.append("Negative")
else:
            sentiment.append("Neutral")
            sentiment_labels.append("Neutral")

df = pd.DataFrame({
"comment": comments,
        "polarity": polarities,
        "sentiment": sentiment
        "polarity": polarity_scores,
        "sentiment": sentiment_labels
})

    st.dataframe(df, use_container_width=True)
    st.subheader("🧾 Full Comment Dataset")
    st.dataframe(df)

    # ---------------------------------------------------------
    # VISUALIZATIONS
    # ---------------------------------------------------------
    st.subheader("📊 Comment Sentiment Visualizations")

    # ----------------------------
    # VISUALS
    # ----------------------------
    st.subheader("📈 Visual Insights")
    colA, colB = st.columns(2)
    col1, col2 = st.columns(2)

    with colA:
    # SENTIMENT COUNTS
    with col1:
fig1, ax1 = plt.subplots()
        df["sentiment"].value_counts().plot(kind="bar", color=["green", "gray", "red"], ax=ax1)
        sentiment_counts = df["sentiment"].value_counts()
        colors = {"Positive": "green", "Neutral": "gray", "Negative": "red"}
        sentiment_counts.plot(kind="bar", color=[colors[s] for s in sentiment_counts.index], ax=ax1)
ax1.set_title("Sentiment Distribution")
        ax1.set_ylabel("Count")
        ax1.tick_params(axis='x', rotation=0)
st.pyplot(fig1)

    with colB:
    # POLARITY HISTOGRAM
    with col2:
fig2, ax2 = plt.subplots()
        vals = df["polarity"].values
        bins = 20
        counts, edges = np.histogram(vals, bins=bins, range=(-1, 1))
        centers = (edges[:-1] + edges[1:]) / 2
        vals = df["polarity"].dropna().values
        counts, bin_edges = np.histogram(vals, bins=20, range=(-1, 1))

        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        norm_centers = (bin_centers + 1) / 2
cmap = plt.get_cmap("RdYlGn")
        bar_colors = [cmap((c + 1) / 2) for c in centers]
        bar_colors = [cmap(n) for n in norm_centers]

        ax2.bar(centers, counts, width=(edges[1] - edges[0]) * 0.9, color=bar_colors, edgecolor="black")
        ax2.bar(bin_centers, counts, width=(bin_edges[1] - bin_edges[0]), color=bar_colors, edgecolor="black")
ax2.set_title("Polarity Distribution")
st.pyplot(fig2)

    # ----------------------------
    # TOP 10 POS/NEG (without index)
    # ----------------------------
    top_pos = df.sort_values("polarity", ascending=False).head(10).reset_index(drop=True)
    top_neg = df.sort_values("polarity", ascending=True).head(10).reset_index(drop=True)

    # ---------------------------------------------------------
    # TOP 10 POSITIVE & NEGATIVE
    # ---------------------------------------------------------
st.subheader("🏆 Top Comments")
    c1, c2 = st.columns(2)

    with c1:
        st.write("### 🌟 Top 10 Positive Comments")
        st.table(top_pos)
    col3, col4 = st.columns(2)

    with c2:
        st.write("### 💀 Top 10 Negative Comments")
        st.table(top_neg)
    with col3:
        st.write("### 🌟 Top 10 Most Positive Comments")
        st.table(df.sort_values(by="polarity", ascending=False).head(10)[["comment", "polarity"]])

    # ----------------------------
    # LAST 10 CHANNEL VIDEOS
    # ----------------------------
    st.subheader("📺 Channel Recent Performance")
    with col4:
        st.write("### 💀 Top 10 Most Negative Comments")
        st.table(df.sort_values(by="polarity", ascending=True).head(10)[["comment", "polarity"]])

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
    # ---------------------------------------------------------
    # TRANSCRIPT SENTIMENT TIMELINE
    # ---------------------------------------------------------
    st.subheader("🎬 Sentiment Throughout the Video (Transcript)")

    vid_ids = [item["id"]["videoId"] for item in uploads_resp.get("items", [])]
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

    # Fetch their stats
    stats_url = "https://www.googleapis.com/youtube/v3/videos"
    stats_params = {
        "part": "statistics",
        "id": ",".join(vid_ids),
        "key": api_key
    }
    vid_stats = requests.get(stats_url, params=stats_params).json()
        times = []
        sentiments = []

    recent_views = [int(v["statistics"].get("viewCount", 0)) for v in vid_stats["items"]]
        for t in transcript:
            times.append(t["start"] / 60)
            sentiments.append(TextBlob(t["text"]).sentiment.polarity)

    # ----------------------------
    # LINE CHART FOR LAST 10 VIDEOS + comparison line
    # ----------------------------
    fig3, ax3 = plt.subplots(figsize=(10, 5))
    ax3.plot(range(1, len(recent_views) + 1), recent_views, marker="o")
    ax3.axhline(views, color="red", linestyle="--", label="Analyzed Video Views")
        trans_df = pd.DataFrame({"time_min": times, "polarity": sentiments})

    ax3.set_title("Views of Last 10 Channel Videos")
    ax3.set_xlabel("Recent Videos (Newest → Oldest)")
    ax3.set_ylabel("View Count")
    ax3.legend()
        fig_t, ax_t = plt.subplots(figsize=(10, 4))
        ax_t.plot(trans_df["time_min"], trans_df["polarity"], linewidth=2)
        ax_t.axhline(0, color="black", linestyle="--")
        ax_t.set_title("Sentiment Over Video Timeline")
        ax_t.set_xlabel("Time (minutes)")
        ax_t.set_ylabel("Sentiment Polarity (-1 to 1)")
        st.pyplot(fig_t)

    st.pyplot(fig3)
    except Exception as e:
        st.warning(f"Transcript not available: {e}")

    # ----------------------------
    # ---------------------------------------------------------
# DOWNLOAD CSV
    # ----------------------------
    st.subheader("⬇️ Download Comment Data")
    # ---------------------------------------------------------
    st.subheader("⬇️ Download Results")
    csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
label="Download CSV",
        data=df.to_csv(index=False).encode(),
        file_name="sentiment_comments.csv",
        data=csv,
        file_name="youtube_sentiment_results.csv",
mime="text/csv"
)
