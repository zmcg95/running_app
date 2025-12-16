import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from textblob import TextBlob
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

st.subheader("📈 Sentiment Analysis Overview")

col1, col2 = st.columns(2)

# ----------------------------
# SENTIMENT TIMELINE
# ----------------------------
with col1:
    fig1, ax1 = plt.subplots(figsize=(6, 4))

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

    ax1.set_title("Sentiment Over Video Timeline")
    ax1.set_xlabel("Time (minutes)")
    ax1.set_ylabel("Polarity")
    ax1.legend()

    st.pyplot(fig1)

# ----------------------------
# SENTIMENT DISTRIBUTION
# ----------------------------
with col2:
    fig2, ax2 = plt.subplots(figsize=(6, 4))

    df["sentiment"].value_counts().reindex(
        ["Positive", "Neutral", "Negative"]
    ).plot(
        kind="bar",
        ax=ax2,
        color=["green", "gray", "red"]
    )

    ax2.set_title("Sentiment Distribution")
    ax2.set_ylabel("Count")

    st.pyplot(fig2)
