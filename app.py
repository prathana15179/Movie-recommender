# app.py — Simple Movie Recommender with Posters (OMDb)

import streamlit as st
import pandas as pd
from pathlib import Path
import requests
import re
from urllib.parse import urlparse

# ===============================
# Data loading (path-safe)
# ===============================
@st.cache_data
def load_data():
    base = Path(__file__).parent
    movies = pd.read_csv(base / "movies.csv")
    ratings = pd.read_csv(base / "ratings.csv")

    movie_stats = ratings.groupby("movieId")["rating"].agg(["mean", "count"]).reset_index()
    movie_stats.rename(columns={"mean": "avg_rating", "count": "num_ratings"}, inplace=True)

    movies_full = movies.merge(movie_stats, on="movieId", how="left")
    movies_full["num_ratings"] = movies_full["num_ratings"].fillna(0)
    movies_full["avg_rating"] = movies_full["avg_rating"].fillna(0)
    return movies_full

movies_full = load_data()

# ===============================
# Recommender (genre overlap + popularity)
# ===============================
def recommend_popular_similar(movie_name, n=10, min_ratings=10):
    row = movies_full.loc[movies_full["title"] == movie_name]
    if row.empty:
        return None

    target = set(str(row["genres"].values[0]).split("|"))

    def jaccard(a, b):
        if not a or not b:
            return 0.0
        inter, uni = len(a & b), len(a | b)
        return inter / uni if uni else 0.0

    df = movies_full.copy()
    df = df[df["title"] != movie_name]
    df["overlap"] = df["genres"].apply(lambda g: jaccard(set(str(g).split("|")), target))

    cand = df[df["overlap"] > 0]
    if cand.empty:
        cand = df

    filtered = cand[cand["num_ratings"] >= min_ratings]
    if filtered.empty:
        filtered = cand

    denom = (filtered["num_ratings"].max() or 1)
    filtered["score"] = (
        0.6 * filtered["overlap"] +
        0.3 * (filtered["avg_rating"] / 5.0) +
        0.1 * (filtered["num_ratings"] / denom)
    )

    out = filtered.sort_values(["score", "avg_rating", "num_ratings"], ascending=False)
    return out[["title", "genres", "avg_rating", "num_ratings"]].head(n)

# ===============================
# Poster helpers (OMDb)
# ===============================
def _clean_title_for_search(title):
    # remove trailing year in parentheses & surrounding quotes
    t = re.sub(r"\(\d{4}\)$", "", str(title)).strip()
    return t.strip(" '\"")

def _year_from_title(title):
    m = re.search(r"\((\d{4})\)$", str(title))
    return int(m.group(1)) if m else None

def _is_valid_url(u):
    if not isinstance(u, str):
        return False
    p = urlparse(u)
    return p.scheme in ("http", "https") and bool(p.netloc)

@st.cache_data(ttl=60 * 60 * 24)
def fetch_poster_url_omdb(title):
    """Return a poster URL for a movie title using OMDb; None if not found."""
    api_key = st.secrets.get("OMDB_API_KEY")
    if not api_key:
        return None

    cleaned = _clean_title_for_search(title)
    year = _year_from_title(title)

    try:
        # 1) exact lookup
        params = {"t": cleaned, "apikey": api_key}
        if year:
            params["y"] = year
        r = requests.get("https://www.omdbapi.com/", params=params, timeout=10)
        data = r.json() if r.ok else {}
        poster = data.get("Poster")
        if _is_valid_url(poster):
            return poster

        # 2) search fallback (prefer type=movie; first valid poster)
        sr = requests.get("https://www.omdbapi.com/", params={"s": cleaned, "apikey": api_key}, timeout=10)
        sdata = sr.json() if sr.ok else {}
        items = sdata.get("Search") or []
        items.sort(key=lambda it: 0 if it.get("Type") == "movie" else 1)
        for it in items:
            p = it.get("Poster")
            if _is_valid_url(p):
                return p
    except Exception:
        return None
    return None

def _placeholder_box():
    st.markdown(
        """
        <div style="width:100%;aspect-ratio:2/3;border-radius:12px;border:1px solid #444;
                    display:flex;align-items:center;justify-content:center;background:#222;">
            <span style="opacity:.7">No poster</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_cards(df):
    """Render a grid of posters with titles; safe even if poster URL is bad."""
    if df is None or df.empty:
        st.warning("No recommendations found. Try lowering the minimum ratings.")
        return

    cols = st.columns(5)  # 5 cards per row
    for i, (_, row) in enumerate(df.iterrows()):
        title = str(row["title"])
        poster = fetch_poster_url_omdb(title)
        with cols[i % 5]:
            try:
                if _is_valid_url(poster):
                    st.image(poster, use_container_width=True)
                else:
                    _placeholder_box()
            except Exception:
                _placeholder_box()
            st.caption(f"**{title}**  \n{row['genres']}")

# ===============================
# UI
# ===============================
st.title("🍿 Simple Movie Recommender")
st.write("Find **popular movies** that are similar to the one you like!")

movie_name = st.selectbox("🎥 Choose a movie:", sorted(movies_full["title"].dropna().unique()))
num = st.slider("How many recommendations?", 5, 20, 10)
min_r = st.slider("Minimum number of ratings", 0, 100, 10)

if st.button("Show Recommendations"):
    recs = recommend_popular_similar(movie_name, n=num, min_ratings=min_r)
    if recs is not None and not recs.empty:
        st.subheader(f"Because you liked **{movie_name}**, you might also enjoy:")
        render_cards(recs)     # poster grid
        st.dataframe(recs)     # optional table
    else:
        st.warning("Sorry, no similar movies found. Try different settings.")
