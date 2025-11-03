import streamlit as st
import pandas as pd
import requests
import re
from pathlib import Path

# -------------------------------
# Load data (path-safe for Cloud)
# -------------------------------
BASE_DIR = Path(__file__).parent
movies  = pd.read_csv(BASE_DIR / "movies.csv")
ratings = pd.read_csv(BASE_DIR / "ratings.csv")

movie_stats = ratings.groupby('movieId')['rating'].agg(['mean','count']).reset_index()
movie_stats.rename(columns={'mean':'avg_rating','count':'num_ratings'}, inplace=True)
movies_full = movies.merge(movie_stats, on='movieId', how='left')
movies_full['num_ratings'] = movies_full['num_ratings'].fillna(0)
movies_full['avg_rating']  = movies_full['avg_rating'].fillna(0)

# --------------------------------
# Simple flexible recommendations
# --------------------------------
def recommend_popular_similar(movie_name, n=10, min_ratings=10):
    row = movies_full.loc[movies_full['title'] == movie_name]
    if row.empty:
        return None
    target = set(str(row['genres'].values[0]).split('|'))

    def jaccard(a, b):
        if not a or not b: return 0.0
        inter, uni = len(a & b), len(a | b)
        return inter / uni if uni else 0.0

    df = movies_full.copy()
    df = df[df['title'] != movie_name]
    df['overlap'] = df['genres'].apply(lambda g: jaccard(set(str(g).split('|')), target))
    cand = df[df['overlap'] > 0]
    if cand.empty:
        cand = df

    filtered = cand[cand['num_ratings'] >= min_ratings]
    if filtered.empty: filtered = cand

    filtered['score'] = (
        0.6 * filtered['overlap'] +
        0.3 * (filtered['avg_rating'] / 5.0) +
        0.1 * (filtered['num_ratings'] / (filtered['num_ratings'].max() or 1))
    )
    out = filtered.sort_values(['score','avg_rating','num_ratings'], ascending=False)
    return out[['title','genres','avg_rating','num_ratings']].head(n)

# -------------------------------
# Poster helpers (OMDb)
# -------------------------------
def extract_year_from_title(title: str):
    m = re.search(r'\((\d{4})\)$', str(title))
    return m.group(1) if m else None

@st.cache_data(ttl=60*60*24)
def fetch_poster_url_omdb(title: str, year: str | None = None) -> str | None:
    api_key = st.secrets.get("OMDB_API_KEY")
    if not api_key:
        return None
    params = {"t": title, "apikey": api_key}
    if year: params["y"] = year
    try:
        r = requests.get("https://www.omdbapi.com/", params=params, timeout=10)
        data = r.json()
        poster = data.get("Poster")
        if poster and poster != "N/A":
            return poster
        # fallback: search
        sr = requests.get("https://www.omdbapi.com/", params={"s": title, "apikey": api_key}, timeout=10)
        sdata = sr.json()
        if sdata.get("Search"):
            p = sdata["Search"][0].get("Poster")
            return p if p and p != "N/A" else None
    except Exception:
        return None
    return None

def render_cards(df):
    if df is None or df.empty:
        st.warning("No recommendations found.")
        return
    cols = st.columns(5)
    for i, (_, row) in enumerate(df.iterrows()):
        title = str(row["title"])
        year  = extract_year_from_title(title)
        poster = fetch_poster_url_omdb(title, year)
        with cols[i % 5]:
            if poster:
                st.image(poster, use_container_width=True)
            st.caption(f"**{title}**  \n{row['genres']}")

# -------------------------------
# UI
# -------------------------------
st.title("🍿 Simple Movie Recommender")
st.write("Find **popular movies** that are similar to the one you like!")

movie_name = st.selectbox("🎥 Choose a movie:", sorted(movies_full['title'].dropna().unique()))
num = st.slider("How many recommendations?", 5, 20, 10)
min_r = st.slider("Minimum number of ratings", 0, 100, 10)

if st.button("Show Recommendations"):
    recs = recommend_popular_similar(movie_name, n=num, min_ratings=min_r)
    if recs is not None and not recs.empty:
        st.subheader(f"Because you liked **{movie_name}**, you might also enjoy:")
        render_cards(recs)     # 🖼️ posters grid
        st.dataframe(recs)     # optional table
    else:
        st.warning("Sorry, no similar movies found. Try lowering the minimum ratings.")
