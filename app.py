import streamlit as st
import pandas as pd

# ==========================
# 🎬 Simple Movie Recommender App
# ==========================

# Load the data
from pathlib import Path

BASE_DIR = Path(__file__).parent  # the folder where app.py lives
movies = pd.read_csv(BASE_DIR / "movies.csv")
ratings = pd.read_csv(BASE_DIR / "ratings.csv")


# Combine movie info and average rating
movie_stats = ratings.groupby('movieId')['rating'].agg(['mean','count']).reset_index()
movie_stats.rename(columns={'mean':'avg_rating','count':'num_ratings'}, inplace=True)
movies_full = movies.merge(movie_stats, on='movieId', how='left')

# ensure numeric stats exist even if NaN
movies_full['num_ratings'] = movies_full['num_ratings'].fillna(0)
movies_full['avg_rating']  = movies_full['avg_rating'].fillna(0)

# split genres into sets for overlap scoring
movies_full['genres_set'] = movies_full['genres'].fillna('').str.split('|').apply(set)

# Recommendation function
def recommend_popular_similar(movie_name, n=10, min_ratings=10, loose=True):
    # find target movie row
    row = movies_full.loc[movies_full['title'] == movie_name]
    if row.empty:
        return None

    # turn genre string into a set of words
    target_set = set(str(row['genres'].values[0]).split('|'))

    # compute simple overlap between sets
    def jaccard(a, b):
        if not a or not b:
            return 0.0
        inter = len(a & b)
        union = len(a | b)
        return inter / union if union else 0.0

    df = movies_full.copy()
    df = df[df['title'] != movie_name]  # skip same movie

    # strict: exact match
    strict = df[df['genres'] == row['genres'].values[0]]

    # loose: overlap > 0
    if loose:
        df['overlap'] = df['genres'].apply(lambda g: jaccard(set(str(g).split('|')), target_set))
        loose_matches = df[df['overlap'] > 0]
    else:
        loose_matches = pd.DataFrame(columns=df.columns.tolist() + ['overlap'])

    # prefer strict if found; else loose
    cand = strict if not strict.empty else loose_matches

    # relax popularity threshold if nothing passes
    if cand.empty:
        cand = df

    # apply min_ratings filter
    filtered = cand[cand['num_ratings'] >= min_ratings]
    if filtered.empty:
        filtered = cand

    # assign a simple score
    if 'overlap' not in filtered.columns:
        filtered['overlap'] = 0
    filtered['score'] = (
        0.6 * filtered['overlap'] +
        0.3 * (filtered['avg_rating'] / 5.0) +
        0.1 * (filtered['num_ratings'] / (filtered['num_ratings'].max() or 1))
    )

    out = filtered.sort_values(['score','avg_rating','num_ratings'], ascending=False)
    return out[['title','genres','avg_rating','num_ratings']].head(n)


# Streamlit interface
st.title("🍿 Simple Movie Recommender")
st.write("Find **popular movies** that are similar to the one you like!")

# Dropdown menu for movie selection
movie_name = st.selectbox("🎥 Choose a movie:", sorted(movies_full['title'].dropna().unique()))

# Slider for number of results
num = st.slider("How many recommendations?", 5, 20, 10)

# Button to show recommendations
if st.button("Show Recommendations"):
    recs = recommend_popular_similar(movie_name, n=num)
    if recs is not None and not recs.empty:
        st.subheader(f"Because you liked **{movie_name}**, you might also enjoy:")
        st.dataframe(recs)
    else:
        st.warning(" Sorry, no similar movies found for that one.")
