import unittest
from unittest.mock import patch
from urllib.error import URLError

from services.routing import RoutingError, _request_json, coordinates, transit_route, walking_route


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

    def test_transit_requires_key_without_network_request(self):
        with patch("services.routing._request_json") as request:
            with self.assertRaises(RoutingError):
                transit_route(START, END, "bus", "")
            request.assert_not_called()

    def test_bus_geometry_and_walking_connections(self):
        search = {"result": {"path": [{"pathType": 2,
            "info": {"mapObj": "123:1:0:3", "totalDistance": 1200, "totalTime": 12},
            "subPath": [
                {"trafficType": 3, "distance": 100},
                {"trafficType": 2, "lane": [{"busNo": "143"}], "sectionTime": 8,
                 "startName": "Stop A", "endName": "Stop B", "startX": 126.979,
                 "startY": 37.566, "endX": 126.981, "endY": 37.5655},
                {"trafficType": 3, "distance": 100},
            ]}]}}
        geometry = {"result": {"lane": [{"class": 1, "section": [{"graphPos": [
            {"x": 126.979, "y": 37.566}, {"x": 126.98, "y": 37.5658},
            {"x": 126.981, "y": 37.5655},
        ]}]}]}}
        with patch("services.routing._request_json", side_effect=[search, geometry]) as request:
            with patch("services.routing.walking_route", return_value={"segments": [
                {"points": [START, END], "mode": "walk", "label": "Walking"}
            ]}) as walk:
                route = transit_route(START, END, "bus", "test-key")
        self.assertEqual(request.call_args_list[0].args[1]["SearchPathType"], 2)
        self.assertEqual(request.call_args_list[1].args[1]["mapObject"], "0:0@123:1:0:3")
        self.assertEqual(route["segments"][0]["mode"], "bus")
        self.assertEqual(len(route["segments"][0]["points"]), 3)
        self.assertEqual(route["duration"], 720)
        self.assertEqual(walk.call_count, 2)
        self.assertIn("143: Stop A", route["steps"][1])

    def test_subway_filter_and_provider_error(self):
        with patch("services.routing._request_json", return_value={"error": [{"code": "500"}]}):
            with self.assertRaises(RoutingError):
                transit_route(START, END, "subway", "test-key")
        with patch("services.routing._request_json", return_value={"result": {"path": [{"pathType": 2}]}}) as request:
            with self.assertRaises(RoutingError):
                transit_route(START, END, "subway", "test-key")
            self.assertEqual(request.call_args.args[1]["SearchPathType"], 1)


if __name__ == "__main__":
    unittest.main()
