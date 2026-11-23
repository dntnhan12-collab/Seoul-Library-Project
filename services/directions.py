"""Build Naver directions links using the library's existing coordinates."""

import math
from urllib.parse import urlencode, quote


TRAVEL_MODES = {
    "Public transit": "public",
    "Walking": "walk",
    "Driving": "car",
    "Cycling": "bicycle",
}
APP_URL = "https://seoul-library-explorer.streamlit.app/"


def naver_directions_links(library, mode="public", origin=None):
    """Include the same origin in app and browser links."""
    if mode not in TRAVEL_MODES.values():
        raise ValueError("Unsupported travel mode.")

    latitude = float(library.latitude)
    longitude = float(library.longitude)
    if not (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and 31.43 <= latitude <= 44.35
        and 122.37 <= longitude <= 132.00
    ):
        raise ValueError("This library has no valid coordinates for Naver Map.")

    app_origin, web_origin = {}, {}
    if origin is not None:
        from services.routing import coordinates
        lat, lon = coordinates(*origin)
        app_origin = {"slat": lat, "slng": lon, "sname": "Starting point"}
        web_origin = {"slat": lat, "slng": lon, "stext": "Starting point"}
    app_query = urlencode(
        {
            **app_origin,
            "dlat": latitude,
            "dlng": longitude,
            "dname": library.name,
            "appname": APP_URL,
        },
        quote_via=quote,
    )
    web_query = urlencode(
        {
            **web_origin,
            "elng": longitude,
            "elat": latitude,
            "etext": library.name,
            "menu": "route",
            "pathType": 1,
        },
        quote_via=quote,
    )
    return (
        f"nmap://route/{mode}?{app_query}",
        f"https://map.naver.com/index.nhn?{web_query}",
    )
