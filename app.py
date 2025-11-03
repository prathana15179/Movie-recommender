import re, requests, math

def _clean_title_for_search(title: str) -> str:
    # remove year and surrounding quotes, trim subtitles in parentheses
    t = re.sub(r"\(\d{4}\)$", "", str(title)).strip()
    t = t.strip(" '\"")
    return t

def _year_from_title(title: str):
    m = re.search(r"\((\d{4})\)$", str(title))
    return int(m.group(1)) if m else None

@st.cache_data(ttl=60*60*24)
def fetch_poster_url_omdb(title: str) -> str | None:
    api_key = st.secrets.get("OMDB_API_KEY")
    if not api_key:
        return None

    cleaned = _clean_title_for_search(title)
    year = _year_from_title(title)

    try:
        # 1) exact title + year if we have it
        p = {"t": cleaned, "apikey": api_key}
        if year: p["y"] = year
        r = requests.get("https://www.omdbapi.com/", params=p, timeout=10).json()
        poster = r.get("Poster")
        if poster and poster != "N/A":
            return poster

        # 2) search + choose best match by year closeness and type=movie
        sr = requests.get("https://www.omdbapi.com/", params={"s": cleaned, "apikey": api_key}, timeout=10).json()
        best = None
        if isinstance(sr.get("Search"), list):
            def score(item):
                y = item.get("Year")
                y = int(y[:4]) if y and y[:4].isdigit() else None
                # prefer movie type and closest year
                type_bonus = 1 if item.get("Type") == "movie" else 0
                year_pen = 0 if (year is None or y is None) else abs(y - year)
                return (type_bonus, -year_pen)
            best = max(sr["Search"], key=score, default=None)

        if best:
            poster = best.get("Poster")
            if poster and poster != "N/A":
                return poster
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
        poster = fetch_poster_url_omdb(title)
        with cols[i % 5]:
            if poster:
                st.image(poster, use_container_width=True)
            else:
                # pretty placeholder
                st.markdown(
                    f"""
                    <div style="width:100%;aspect-ratio:2/3;border-radius:12px;border:1px solid #444;
                                display:flex;align-items:center;justify-content:center;background:#222;">
                        <span style="opacity:.7">No poster</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            st.caption(f"**{title}**  \n{row['genres']}")
