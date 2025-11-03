# 🍿 Simple Movie Recommender

A lightweight **Streamlit web app** that recommends popular movies similar to the one you like — built using the **MovieLens dataset**.

👉 **Live App:** https://movie-recommender-prathanadankhara.streamlit.app/#647fbad

---

## 🎯 Features
- Built in **Python** using **Streamlit** and **Pandas**
- Uses the MovieLens dataset (`movies.csv` and `ratings.csv`)
- Recommends movies based on **genre similarity**
- Filters out movies with few ratings
- Displays top recommendations in a clean, sortable table

---

## 🧠 How It Works
1. Choose a movie from the dropdown.
2. The app finds other movies that share similar genres.
3. It scores movies based on:
   - **Genre overlap**
   - **Average rating**
   - **Number of ratings**
4. The top-scoring movies are shown as recommendations.

---

## 📊 Dataset
This app uses the **MovieLens small dataset** (available at [grouplens.org/datasets/movielens](https://grouplens.org/datasets/movielens/)).

Files used:
- `movies.csv` — movie titles and genres  
- `ratings.csv` — user ratings

---

## 🧰 Run Locally
If you’d like to run the project on your computer:

```bash
pip install -r requirements.txt
streamlit run app.py
