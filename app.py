import streamlit as st
import pandas as pd

# ==========================
# 🎬 Simple Movie Recommender App
# ==========================

# Load the data
movies = pd.read_csv("/content/sample_data/movies.csv")
ratings = pd.read_csv("/content/sample_data/ratings.csv")

# Combine movie info and average rating
movie_stats = ratings.groupby('movieId')['rating'].agg(['mean','count']).reset_index()
movie_stats.rename(columns={'mean':'avg_rating','count':'num_ratings'}, inplace=True)
movies_full = movies.merge(movie_stats, on='movieId', how='left')

# Recommendation function
def recommend_popular_similar(movie_name, n=10, min_ratings=20):
    try:
        genre = movies_full.loc[movies_full['title'] == movie_name, 'genres'].values[0]
    except IndexError:
        return None
    similar = movies_full[movies_full['genres'] == genre]
    popular = similar[similar['num_ratings'] >= min_ratings]
    result = popular.sort_values(['avg_rating','num_ratings'], ascending=False)
    result = result[result['title'] != movie_name]
    return result[['title','genres','avg_rating','num_ratings']].head(n)

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
