import html
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

import altair as alt
import folium
from folium.elements import EventHandler
from folium.utilities import JsCode
import streamlit as st
from streamlit_folium import st_folium
from models.library import Library
from services.routing import ROUTE_MODES, RoutingError, coordinates, naver_browser_url, walking_route
from location_control import location_button

SUBWAY_COLORS = {
    "1": "#0052A4", "2": "#00A84D", "3": "#EF7C1C", "4": "#00A5DE",
    "5": "#996CAC", "6": "#CD7C2F", "7": "#747F00", "8": "#E6186C",
    "9": "#BDB092", "airport": "#0090D2", "bundang": "#E3A800",
    "gyeongui": "#69BC9B", "shinbundang": "#D4003B",
}


@st.cache_data
def load_subway_data():
    data_dir = Path(__file__).resolve().parent / "data"
    return (
        json.loads((data_dir / "seoul_subway_lines.geojson").read_text(encoding="utf-8")),
        json.loads((data_dir / "seoul_subway_stations.geojson").read_text(encoding="utf-8")),
    )

def clear_search():
    st.session_state["search_name"] = ""
    st.session_state["search_district"] = "All districts"
    _set_applied_search("", "All districts")
    st.session_state["_search_needs_full_rerun"] = True


def _set_applied_search(name, district, library_id=None, is_suggestion=False):
    clear_route()
    st.session_state["applied_name"] = name
    st.session_state["applied_district"] = district
    st.session_state["selected_library_id"] = library_id
    st.session_state["suggestion_selected"] = is_suggestion
    st.session_state["map_marker_focused"] = False
    st.session_state["map_revision"] += 1
    st.session_state.pop("map_view", None)
def apply_search():
    _set_applied_search(
        st.session_state.get("search_name", "").strip(),
        st.session_state.get("search_district", "All districts"),
    )
    st.session_state["_search_needs_full_rerun"] = True


def clear_suggestion_choice():
    clear_route()
    st.session_state["selected_library_id"] = None
    st.session_state["suggestion_selected"] = False
    st.session_state["map_marker_focused"] = False
    st.session_state["map_revision"] += 1

def show_title():
    st.markdown(
        '<h1 style="text-align:center; color:#6F1D1B; font-size:3.5rem; '
        'font-weight:800; line-height:1.15; letter-spacing:0.02em; '
        'margin:0.25rem 0 1.5rem;">Seoul Public Library Explorer</h1>',
        unsafe_allow_html=True,
    )
@st.fragment
def show_search_panel(container, districts, libraries):
    with container:
        st.subheader("Library Search")
        name = st.text_input(
            "Search by name",
            key="search_name",
            on_change=clear_suggestion_choice,
            placeholder="Type a library name...",
            live=True,
        )
        keyword = name.strip()
        if keyword and not st.session_state.get("suggestion_selected", False):
            suggestions = libraries
            selected_district = st.session_state.get(
                "search_district", "All districts"
            )
            if selected_district != "All districts":
                suggestions = suggestions[
                    suggestions["District_Name"] == selected_district
                ]

            names = suggestions["Library_Name"].fillna("").astype(str)
            suggestions = suggestions[
                names.str.contains(keyword, case=False, regex=False)
            ].sort_values("Library_Name")

            if suggestions.empty:
                st.caption("No matching libraries found.")
            else:
                with st.container(height=150, border=False):
                    for _, row in suggestions.head(5).iterrows():
                        serial = str(row["Library_Serial_Number"])
                        label = f"{row['Library_Name']} — {row['District_Name']}"
                        if st.button(
                            label,
                            key=f"library_suggestion_{serial}",
                            type="tertiary",
                            width="content",
                        ):
                            _set_applied_search(
                                str(row["Library_Name"]),
                                str(row["District_Name"]),
                                serial,
                                is_suggestion=True,
                            )
                            st.rerun()

        st.selectbox(
            "District",
            ["All districts"] + districts,
            key="search_district",
            on_change=clear_suggestion_choice,
        )

        find_column, reset_column = st.columns(2)
        find_column.button(
            "Find",
            type="primary",
            width="stretch",
            on_click=apply_search,
        )
        reset_column.button(
            "Reset",
            on_click=clear_search,
            width="stretch",
        )

    if st.session_state.pop("_search_needs_full_rerun", False):
        st.rerun()
def show_summary(total_libraries, total_districts, found_count):
    total_column, district_column, found_column = st.columns(3)
    total_column.metric("Total libraries", total_libraries)
    district_column.metric("Districts", total_districts)
    found_column.metric("Libraries found", found_count)

def build_library_map(libraries, route=None, origin=None, view=None):
    center = (
        [libraries["Latitude"].mean(), libraries["Longitude"].mean()]
        if not libraries.empty else [37.5665, 126.9780]
    )
    zoom = 14 if len(libraries) == 1 else 11
    if view:
        center = [view["center"]["lat"], view["center"]["lng"]]
        zoom = view["zoom"]
    library_map = folium.Map(
        location=center, zoom_start=zoom,
        attr=('© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> · '
              '<a href="https://routing.openstreetmap.de/about.html">OSRM / FOSSGIS</a> · '
              '<a href="https://www.openstreetmap.org/fixthemap">Fix the map</a>'),
    )
    library_map.add_child(EventHandler("layeradd", JsCode("""
        function (event) {
            const map = event.target;
            const container = map.getContainer();
            let dragged = false;

            container.addEventListener('pointerdown', () => { dragged = false; }, true);
            map.on('dragstart', () => { dragged = true; });
            container.addEventListener('click', (click) => {
                if (dragged) click.stopPropagation();
            }, true);
        }
    """), once=True))
    library_map.get_root().header.add_child(folium.Element("""
        <style>
            .subway-station-label { visibility: hidden; }
            .subway-labels-visible .subway-station-label,
            .subway-station-label.station-hovered { visibility: visible; }
        </style>
    """))
    library_map.add_child(EventHandler("zoomend layeradd", JsCode("""
        function (event) {
            const map = event.target;
            map.getContainer().classList.toggle('subway-labels-visible', map.getZoom() >= 14);
        }
    """)))
    folium.plugins.LocateControl(position="topleft", auto_start=False).add_to(library_map)
    for _, row in libraries.iterrows():
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            tooltip=html.escape(str(row["Library_Name"])),
            icon=folium.Icon(color="darkred"),
            bubbling_mouse_events=False,
        ).add_to(library_map)
    if origin:
        folium.Marker(origin, tooltip="Starting point", icon=folium.Icon(color="green", icon="user")).add_to(library_map)
    if route:
        bounds = [origin, route["destination"], *route["points"]]
        folium.PolyLine(
            route["points"], color="#2563EB", weight=6, opacity=0.9,
            tooltip="Walking", interactive=False,
        ).add_to(library_map)
        library_map.fit_bounds(bounds, padding=(35, 35), max_zoom=16)
    elif origin and len(libraries) == 1 and not view:
        library_map.fit_bounds([origin, center], padding=(35, 35), max_zoom=16)
    return library_map


def show_map(container, libraries, route=None, *, revision=0, view=None):
    with container:
        title_column, controls_column = st.columns([3, 1], vertical_alignment="center")
        title_column.subheader("Library Map")
        show_subway = controls_column.toggle("Subway", key="show_subway")

        if libraries.empty:
            st.info("No libraries match the search. Try another name or district.")

        library_map = build_library_map(libraries, route, st.session_state.get("route_origin"), view)

        subway = folium.FeatureGroup(name="Subway")
        if show_subway:
            lines, stations = load_subway_data()
            folium.GeoJson(
                lines,
                style_function=lambda feature: {
                    "color": SUBWAY_COLORS[feature["properties"]["lineId"]],
                    "weight": 3,
                    "opacity": 0.85,
                    "interactive": False,
                },
            ).add_to(subway)
            station_layer = folium.GeoJson(
                stations,
                marker=folium.CircleMarker(
                    radius=3, color="#334155", weight=1,
                    fill=True, fill_color="#ffffff", fill_opacity=1,
                ),
            ).add_to(subway)
            station_layer.add_child(EventHandler("add", JsCode("""
                function (event) {
                    event.target.eachLayer((layer) => {
                        const label = document.createElement('span');
                        const station = layer.feature.properties;
                        label.textContent = station.name_en || station.name_ko;
                        layer.bindTooltip(label, {
                            permanent: true,
                            direction: 'right',
                            offset: [5, 0],
                            className: 'subway-station-label'
                        });
                        layer.on('mouseover', () => {
                            layer.getTooltip().getElement()?.classList.add('station-hovered');
                        });
                        layer.on('mouseout', () => {
                            layer.getTooltip().getElement()?.classList.remove('station-hovered');
                        });
                    });
                }
            """), once=True))

        result = st_folium(
            library_map,
            feature_group_to_add=subway,
            height=500,
            use_container_width=True,
            returned_objects=["last_clicked", "last_object_clicked", "last_object_clicked_tooltip", "center", "zoom"],
            key=f"library_map_{revision}",
        )
    return result or {}
def show_library_information(row, container):
    library = Library.from_row(row)
    with container:
        with st.container(border=True):
            st.subheader("Library Information")
            st.html(f"<h3>{html.escape(str(library.name))}</h3>")
            rows = []
            for label, value in library.details().items():
                text = " ".join(str(value).split())
                content = html.escape(text)
                if label == "Website":
                    url = "https://" + text if text.startswith("www.") else text
                    if urlsplit(url).scheme in ("http", "https"):
                        content = (
                            f'<a href="{html.escape(url, quote=True)}" target="_blank" '
                            f'rel="noopener noreferrer">{content}</a>'
                        )
                rows.append(f"<tr><th scope='row'>{html.escape(label)}</th><td>{content}</td></tr>")
            st.html(
                """<style>
                .library-details {width:100%; border-collapse:collapse; font-size:14px;}
                .library-details th, .library-details td {
                    padding:8px 10px; border:1px solid #E8D8BD;
                    text-align:left; vertical-align:top; line-height:1.6;
                    white-space:normal; word-break:normal; overflow-wrap:anywhere;
                    letter-spacing:normal; word-spacing:normal;
                }
                .library-details th {width:28%; font-weight:400; color:#786A61;}
                </style><table class="library-details"><tbody>"""
                + "".join(rows) + "</tbody></table>"
            )


def clear_route():
    st.session_state.pop("active_route", None)
    st.session_state.pop("route_error", None)
    st.session_state.pop("find_route_requested", None)


def receive_location():
    position = st.session_state.get("route_location", {}).get("position")
    if position:
        clear_route()
        try:
            st.session_state["route_origin"] = coordinates(position["latitude"], position["longitude"])
            st.session_state["find_route_requested"] = True
        except (KeyError, RoutingError) as error:
            st.session_state["route_error"] = str(error)


def show_directions(library):
    st.markdown("#### Directions")
    mode_column, action_column = st.columns([1, 2], vertical_alignment="bottom")
    with mode_column:
        mode_label = st.selectbox(
            "Travel mode", list(ROUTE_MODES), key="route_mode", on_change=clear_route,
        )
    mode = ROUTE_MODES[mode_label]
    browser_url = naver_browser_url(library) if mode == "public" else None
    with action_column:
        location_button(receive_location, browser_url=browser_url)
    origin = st.session_state.get("route_origin")
    find_requested = st.session_state.pop("find_route_requested", False)
    if mode == "public":
        st.session_state.pop("active_route", None)
        if st.session_state.get("route_error"):
            st.warning(st.session_state["route_error"])
        return None
    request_key = (str(library.serial_number), origin, mode)
    route = st.session_state.get("active_route")
    if route and (route["request_key"] != request_key or "points" not in route):
        clear_route()
        route = None
    if find_requested and origin is not None:
        clear_route()
        route = None
        try:
            destination = coordinates(library.latitude, library.longitude)
            with st.spinner("Finding your route…"):
                route = walking_route(origin, destination)
            route.update(request_key=request_key, destination=destination, mode=mode)
            st.session_state["active_route"] = route
        except RoutingError as error:
            st.session_state["route_error"] = str(error)
    if st.session_state.get("route_error"):
        st.warning(st.session_state["route_error"])
    if route:
        distance_column, time_column = st.columns(2)
        distance_column.metric("Route distance", f"{route['distance'] / 1000:.2f} km")
        time_column.metric("Estimated time", f"{max(1, math.ceil(route['duration'] / 60))} min")
        if st.button("Clear route", type="tertiary"):
            clear_route()
            st.rerun()

    return route


def show_district_chart(counts):
    st.subheader("Libraries by District")
    chart_data = counts.rename_axis("District").reset_index(name="Libraries")
    largest_count = int(chart_data["Libraries"].max())

    chart = (
        alt.Chart(chart_data)
        .mark_bar(color="#BB9457")
        .encode(
            x=alt.X(
                "Libraries:Q",
                title="Number of libraries",
                scale=alt.Scale(domain=[0, largest_count + 1], nice=False),
                axis=alt.Axis(format="d", tickMinStep=1),
            ),
            y=alt.Y("District:N", title=None, sort="-x"),
            tooltip=["District:N", "Libraries:Q"],
        )
        .properties(height=700)
    )

    st.altair_chart(chart, width="stretch")
