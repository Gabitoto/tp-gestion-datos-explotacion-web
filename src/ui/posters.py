"""Pósters de películas vía OMDb API (con caché y placeholder de respaldo)."""
import json
import os
import urllib.parse
import urllib.request

import streamlit as st

OMDB_API_KEY_DEFAULT = "f1b72fd7"  # Key configurada para OMDb API (pósters en vivo)

_PLACEHOLDER = (
    "data:image/svg+xml;utf8,"
    + urllib.parse.quote(
        "<svg xmlns='http://www.w3.org/2000/svg' width='300' height='444' viewBox='0 0 300 444'>"
        "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
        "<stop offset='0' stop-color='#1b2130'/><stop offset='1' stop-color='#141926'/></linearGradient></defs>"
        "<rect width='300' height='444' rx='18' fill='url(#g)'/>"
        "<rect x='1' y='1' width='298' height='442' rx='18' fill='none' stroke='#E50914' stroke-opacity='.45'/>"
        "<text x='150' y='215' font-size='80' text-anchor='middle'>🎬</text>"
        "<text x='150' y='275' font-size='18' fill='#9aa3b5' text-anchor='middle' "
        "font-family='sans-serif'>Sin póster</text></svg>"
    )
)


def _api_key() -> str:
    key = os.environ.get("OMDB_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("OMDB_API_KEY", "")
        except Exception:
            key = ""
    return key or OMDB_API_KEY_DEFAULT


@st.cache_data(ttl=86400, show_spinner=False)
def url_poster(imdb_id: str) -> str:
    """URL del póster de `imdb_id`; devuelve un placeholder si no hay key o falla la consulta."""
    key = _api_key()
    if not key or not imdb_id:
        return _PLACEHOLDER
    try:
        url = f"http://www.omdbapi.com/?i={urllib.parse.quote(imdb_id)}&apikey={urllib.parse.quote(key)}"
        with urllib.request.urlopen(url, timeout=4) as resp:
            poster = json.load(resp).get("Poster", "")
        return poster if poster and poster != "N/A" else _PLACEHOLDER
    except Exception:
        return _PLACEHOLDER

