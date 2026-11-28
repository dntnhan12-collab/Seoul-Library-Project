"""Walking routes and browser links for Naver transit directions."""

import json
import math
import threading
import time
from urllib.error import URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


ROUTE_MODES = {"Walking": "walk", "Bus / subway (Naver Map)": "public"}
WALKING_ROUTE_URL = "https://routing.openstreetmap.de/routed-foot/route/v1/foot/"


class RoutingError(ValueError):
    """An actionable error safe to show without exposing request URLs or keys."""


def coordinates(latitude, longitude):
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError):
        raise RoutingError("Choose a valid starting point in South Korea.") from None
    if not (math.isfinite(lat) and math.isfinite(lon) and 33 <= lat <= 39 and 124 <= lon <= 132):
        raise RoutingError("Choose a starting point in South Korea to route to this library.")
    return lat, lon


def _request_json(url, parameters):
    request = Request(
        url + "?" + urlencode(parameters),
        headers={"User-Agent": "SeoulLibraryExplorer/1.0 (https://github.com/dntnhan12-collab/Seoul-Library-Project)"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            result = json.load(response)
        if not isinstance(result, dict):
            raise ValueError("Invalid response")
        return result
    except (URLError, OSError, ValueError):
        # Provider exceptions can contain URLs with API keys and precise locations.
        raise RoutingError("The routing service is unavailable. Please try again shortly.") from None


class WalkingRouter:
    """Gets walking routes from OSRM, waiting so calls stay one per second."""

    MIN_GAP_SECONDS = 1.05

    def __init__(self):
        self._lock = threading.Lock()
        self._last_request = 0.0

    def route(self, start, end):
        start, end = coordinates(*start), coordinates(*end)
        coordinate_path = f"{start[1]},{start[0]};{end[1]},{end[0]}"
        # Respect FOSSGIS's maximum of one request per second, across sessions.
        with self._lock:
            elapsed = time.monotonic() - self._last_request
            time.sleep(max(0, self.MIN_GAP_SECONDS - elapsed))
            self._last_request = time.monotonic()
            data = _request_json(
                WALKING_ROUTE_URL + coordinate_path,
                {"overview": "full", "geometries": "geojson", "steps": "false", "radiuses": "200;200"},
            )
        return self._read_route(data)

    @staticmethod
    def _read_route(data):
        if data.get("code") != "Ok" or not data.get("routes"):
            raise RoutingError("No walking route was found. Try a starting point closer to a public path.")
        try:
            route = data["routes"][0]
            points = [coordinates(point[1], point[0]) for point in route["geometry"]["coordinates"]]
            distance, duration = float(route["distance"]), float(route["duration"])
            if len(points) < 2 or not all(math.isfinite(v) and v >= 0 for v in (distance, duration)):
                raise ValueError("Invalid route")
        except (KeyError, IndexError, TypeError, ValueError):
            raise RoutingError("The service returned an incomplete walking route. Please try again.") from None
        return {
            "points": points,
            "distance": distance,
            "duration": duration,
        }


# One shared router, so the one-request-per-second limit covers every session.
walking_router = WalkingRouter()


def naver_browser_url(library):
    latitude, longitude = coordinates(library.latitude, library.longitude)
    parameters = {
        "elng": longitude, "elat": latitude, "etext": library.name,
        "menu": "route", "pathType": 1,
    }
    return "https://map.naver.com/index.nhn?" + urlencode(parameters, quote_via=quote)
