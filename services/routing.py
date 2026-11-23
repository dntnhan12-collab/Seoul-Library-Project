"""Walking geometry and optional Korean bus/subway routes, in WGS84."""

import json
import math
import threading
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROUTE_MODES = {"Walking": "walk", "Bus": "bus", "Subway": "subway", "Bus + subway": "transit"}
_walking_lock = threading.Lock()
_last_walking_request = 0.0


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


def walking_route(start, end):
    global _last_walking_request
    start, end = coordinates(*start), coordinates(*end)
    coordinate_path = f"{start[1]},{start[0]};{end[1]},{end[0]}"
    # Respect FOSSGIS's maximum of one request per second, across sessions.
    with _walking_lock:
        time.sleep(max(0, 1.05 - (time.monotonic() - _last_walking_request)))
        _last_walking_request = time.monotonic()
        data = _request_json(
            "https://routing.openstreetmap.de/routed-foot/route/v1/foot/" + coordinate_path,
            {"overview": "full", "geometries": "geojson", "steps": "false", "radiuses": "200;200"},
        )
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
        "segments": [{"points": points, "mode": "walk", "label": "Walking"}],
        "distance": distance,
        "duration": duration,
        "steps": [f"Walk to the library ({distance / 1000:.2f} km)."],
        "warnings": [],
    }


def _odsay(endpoint, parameters, api_key):
    data = _request_json(
        "https://api.odsay.com/v1/api/" + endpoint,
        {**parameters, "apiKey": api_key, "lang": 1, "output": "json"},
    )
    if data.get("error"):
        raise RoutingError(
            "ODsay could not return a route. Check the Server API key, registered server IP, "
            "quota, and whether this journey has transit service."
        )
    if not isinstance(data.get("result"), dict):
        raise RoutingError("ODsay returned incomplete route data.")
    return data["result"]


def transit_route(start, end, mode, api_key):
    if not api_key:
        raise RoutingError("Bus and subway routing has not been enabled yet. Walking is available.")
    path_types = {"transit": 0, "subway": 1, "bus": 2}
    if mode not in path_types:
        raise RoutingError("Unsupported travel mode.")
    start, end = coordinates(*start), coordinates(*end)
    result = _odsay("searchPubTransPathT", {
        "SX": start[1], "SY": start[0], "EX": end[1], "EY": end[0],
        "SearchType": 0, "SearchPathType": path_types[mode], "OPT": 0,
    }, api_key)
    paths = [path for path in result.get("path", []) if path.get("pathType") in (1, 2, 3)]
    if mode != "transit":
        paths = [path for path in paths if path.get("pathType") == path_types[mode]]
    if not paths:
        raise RoutingError("No route was found for this travel mode. Try another mode or starting point.")
    try:
        path = paths[0]  # ODsay's recommended route.
        info, subpaths = path["info"], path["subPath"]
        # Zero base ensures loadLane returns absolute longitude/latitude.
        geometry = _odsay("loadLane", {"mapObject": "0:0@" + info["mapObj"]}, api_key)
        segments = []
        for lane in geometry["lane"]:
            lane_mode = {1: "bus", 2: "subway"}[int(lane["class"])]
            for section in lane["section"]:
                points = [coordinates(point["y"], point["x"]) for point in section["graphPos"]]
                if len(points) >= 2:
                    segments.append({"points": points, "mode": lane_mode, "label": lane_mode.title()})
        if not segments:
            raise ValueError("No geometry")
        steps, warnings, stops = [], [], []
        for index, subpath in enumerate(subpaths):
            traffic_type = int(subpath["trafficType"])
            if traffic_type == 3:
                distance = float(subpath.get("distance", 0))
                steps.append(f"Walk {distance:.0f} m.")
                if distance <= 0:
                    continue
                previous = next((p for p in reversed(subpaths[:index]) if p["trafficType"] != 3), None)
                following = next((p for p in subpaths[index + 1:] if p["trafficType"] != 3), None)
                walk_start = coordinates(previous["endY"], previous["endX"]) if previous else start
                walk_end = coordinates(following["startY"], following["startX"]) if following else end
                try:
                    segments.extend(walking_route(walk_start, walk_end)["segments"])
                except RoutingError:
                    warnings.append("A walking connection could not be drawn; follow the stops in the itinerary.")
            else:
                lane = subpath["lane"][0]
                name = str(lane.get("busNo") or lane.get("name") or "Subway")
                boarding, arrival = str(subpath["startName"]), str(subpath["endName"])
                steps.append(f"{name}: {boarding} → {arrival} ({subpath['sectionTime']} min).")
                stops.extend([
                    {"point": coordinates(subpath["startY"], subpath["startX"]), "name": boarding},
                    {"point": coordinates(subpath["endY"], subpath["endX"]), "name": arrival},
                ])
        distance, duration = float(info["totalDistance"]), float(info["totalTime"]) * 60
        if not all(math.isfinite(v) and v >= 0 for v in (distance, duration)):
            raise ValueError("Invalid summary")
        return {"segments": segments, "distance": distance, "duration": duration,
                "steps": steps, "warnings": list(dict.fromkeys(warnings)), "stops": stops}
    except RoutingError:
        raise
    except (KeyError, IndexError, TypeError, ValueError):
        raise RoutingError("ODsay returned incomplete route geometry. Please try another route.") from None
