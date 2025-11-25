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

    sentiment_counts.plot(
        kind="bar",
        color=[colors.get(s, "gray") for s in sentiment_counts.index],
        ax=ax1
    )

    ax1.set_title("Sentiment Distribution")
    ax1.set_xlabel("")
    ax1.set_ylabel("Count")

    st.pyplot(fig1)

# ---------- POLARITY HISTOGRAM WITH RED→GREEN GRADIENT ----------
with col2:
    fig2, ax2 = plt.subplots()

    # Red (-1) → Yellow (0) → Green (+1)
    cmap = plt.get_cmap("RdYlGn")
    norm_vals = (df["polarity"] + 1) / 2  # map -1..1 to 0..1

    ax2.scatter(df["polarity"], np.zeros_like(df["polarity"]),
                c=norm_vals, cmap=cmap)

    ax2.hist(df["polarity"], bins=20, edgecolor="black", color="lightgray")
    ax2.set_title("Polarity Distribution (Red → Green)")
    ax2.set_xlabel("Polarity")
    ax2.set_ylabel("Frequency")

    st.pyplot(fig2)
