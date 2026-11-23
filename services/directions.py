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


def naver_directions_links(library, mode="public"):
    """Leave the origin unset so the Naver app uses the user's location.

    The browser link opens a destination-filled transit form, where users
    choose their starting point and can change the travel mode.
    """
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

    app_query = urlencode(
        {
            "dlat": latitude,
            "dlng": longitude,
            "dname": library.name,
            "appname": APP_URL,
        },
        quote_via=quote,
    )
    web_query = urlencode(
        {
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
