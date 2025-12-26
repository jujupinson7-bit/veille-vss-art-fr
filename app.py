import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil import parser
import requests

st.set_page_config(page_title="Veille VSS - Art (France)", layout="wide")

st.title("📌 Veille presse — Violences sexuelles et sexistes (domaine artistique, France)")
st.caption("Tri : du plus récent au plus ancien — date affichée au format dd/mm/yyyy")

# --------- Réglages ---------
DEFAULT_QUERY = st.sidebar.text_input(
    "Mots-clés (requête)",
    value="(violences sexuelles OR violences sexistes OR agression sexuelle OR harcèlement) (cinéma OR théâtre OR musique OR art OR artiste OR exposition OR festival) France",
)

days = st.sidebar.slider("Fenêtre (jours)", min_value=1, max_value=365, value=30)

st.sidebar.markdown("---")
st.sidebar.write("Sources :")
use_gdelt = st.sidebar.checkbox("GDELT (gratuit, sans clé)", value=True)

# --------- Fonctions ---------
def ddmmyyyy(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y")

@st.cache_data(ttl=60 * 30)
def fetch_gdelt(query: str, days: int) -> pd.DataFrame:
    """
    GDELT 2.1 DOC : https://blog.gdeltproject.org/gdelt-2-1-api-debuts/
    On utilise une requête texte et on récupère des articles récents.
    """
    # GDELT attend des dates en YYYYMMDDhhmmss ; on peut juste limiter via mode=ArtList & maxrecords
    # Pour "days", on passe via "format" et "mode" + "query" et un "startdatetime" approximatif.
    start = (datetime.utcnow() - pd.Timedelta(days=days)).strftime("%Y%m%d%H%M%S")
    url = (
        "https://api.gdeltproject.org/api/v2/doc/doc"
        f"?query={requests.utils.quote(query)}"
        f"&mode=ArtList"
        f"&format=json"
        f"&maxrecords=250"
        f"&startdatetime={start}"
        f"&sourcelang=French"
    )

    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()

    arts = data.get("articles", [])
    rows = []
    for a in arts:
        # GDELT donne souvent "seendate" ou "datetime" selon endpoint
        raw_date = a.get("seendate") or a.get("datetime") or a.get("date")
        if not raw_date:
            continue
        try:
            dt = parser.parse(raw_date)
        except Exception:
            continue

        rows.append(
            {
                "date": dt,
                "date_ddmmyyyy": ddmmyyyy(dt),
                "title": a.get("title", ""),
                "source": a.get("sourceCountry") or a.get("source") or "",
                "domain": a.get("domain", ""),
                "url": a.get("url", ""),
                "snippet": a.get("summary") or a.get("snippet") or "",
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Tri du plus récent au plus ancien
    df = df.sort_values("date", ascending=False).reset_index(drop=True)
    return df

# --------- UI ---------
dfs = []

if use_gdelt:
    try:
        df_gdelt = fetch_gdelt(DEFAULT_QUERY, days)
        df_gdelt["provider"] = "GDELT"
        dfs.append(df_gdelt)
    except Exception as e:
        st.error(f"Erreur GDELT: {e}")

if not dfs:
    st.info("Aucune source activée (coche GDELT à gauche).")
    st.stop()

df = pd.concat(dfs, ignore_index=True) if len(dfs) > 1 else dfs[0]

# Filtres
st.sidebar.markdown("---")
keyword_filter = st.sidebar.text_input("Filtrer par mot dans le titre", value="")
domain_filter = st.sidebar.text_input("Filtrer par domaine (ex: lemonde.fr)", value="")

if keyword_filter.strip():
    df = df[df["title"].str.contains(keyword_filter, case=False, na=False)]
if domain_filter.strip():
    df = df[df["domain"].str.contains(domain_filter, case=False, na=False)]

# Affichage
st.subheader(f"Résultats ({len(df)})")

# Table cliquable
show_cols = ["date_ddmmyyyy", "title", "domain", "url", "provider"]
st.dataframe(
    df[show_cols],
    use_container_width=True,
    hide_index=True,
)

st.markdown("---")
st.caption("Conseil : ajoute une liste de médias cibles via RSS ou une API presse si tu veux plus de couverture.")
