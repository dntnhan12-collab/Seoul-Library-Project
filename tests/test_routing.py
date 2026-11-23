import unittest
from unittest.mock import patch
from urllib.error import URLError

from services.routing import RoutingError, _request_json, coordinates, walking_route


START = (37.5665, 126.978)
END = (37.565, 126.982)
WALKING_RESPONSE = {
    "code": "Ok",
    "routes": [{"distance": 500, "duration": 360,
                "geometry": {"coordinates": [[126.978, 37.5665], [126.98, 37.566], [126.982, 37.565]]}}],
}


class RoutingTests(unittest.TestCase):
    def setUp(self):
        sleep = patch("services.routing.time.sleep")
        sleep.start()
        self.addCleanup(sleep.stop)

    def test_walking_uses_foot_server_and_converts_geojson_order(self):
        with patch("services.routing._request_json", return_value=WALKING_RESPONSE) as request:
            route = walking_route(START, END)
        self.assertIn("routed-foot/route/v1/foot/126.978,37.5665", request.call_args.args[0])
        self.assertEqual(route["segments"][0]["points"][0], START)
        self.assertEqual(route["duration"], 360)
        self.assertEqual(len(route["segments"][0]["points"]), 3)

    def test_invalid_coordinates_never_call_provider(self):
        with patch("services.routing._request_json") as request:
            for point in ((float("nan"), 127), (37.5, float("inf")), (0, 0), (None, 127)):
                with self.assertRaises(RoutingError):
                    walking_route(point, END)
            request.assert_not_called()

    def test_missing_route_and_bad_geometry(self):
        for response in ({"code": "NoRoute"}, {"code": "Ok", "routes": [{}]}):
            with patch("services.routing._request_json", return_value=response):
                with self.assertRaises(RoutingError):
                    walking_route(START, END)

    def test_network_errors_do_not_expose_key_or_coordinates(self):
        with patch("services.routing.urlopen", side_effect=URLError("secret-key 126.978")):
            with self.assertRaises(RoutingError) as error:
                _request_json("https://api.odsay.com/example", {"apiKey": "secret-key"})
        self.assertNotIn("secret-key", str(error.exception))
        self.assertNotIn("126.978", str(error.exception))

    def test_naver_preserves_origin(self):
        from types import SimpleNamespace
        from urllib.parse import urlsplit, parse_qs
        from services.directions import naver_directions_links
        library = SimpleNamespace(latitude=END[0], longitude=END[1], name="Library & test")
        for url in naver_directions_links(library, "public", START):
            query = parse_qs(urlsplit(url).query)
            self.assertEqual(float(query["slat"][0]), START[0])
            self.assertEqual(float(query["slng"][0]), START[1])

if __name__ == "__main__":
    unittest.main()
