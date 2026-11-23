import html
import math
import os

import altair as alt
import folium
import streamlit as st
from streamlit_folium import st_folium
from models.library import Library
from services.directions import naver_directions_links
from services.routing import ROUTE_MODES, RoutingError, coordinates, transit_route, walking_route
from location_control import location_button

def clear_search():
    st.session_state["search_name"] = ""
    st.session_state["search_district"] = "All districts"
    _set_applied_search("", "All districts")
    st.session_state["_search_needs_full_rerun"] = True


def _set_applied_search(name, district, library_id=None, is_suggestion=False):
    clear_route()
    st.session_state["pick_route_origin"] = False
    st.session_state["applied_name"] = name
    st.session_state["applied_district"] = district
    st.session_state["selected_library_id"] = library_id
    st.session_state["suggestion_selected"] = is_suggestion
    st.session_state["ignore_map_click_once"] = True
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

def build_library_map(libraries, route=None, origin=None):
    center = (
        [libraries["Latitude"].mean(), libraries["Longitude"].mean()]
        if not libraries.empty else [37.5665, 126.9780]
    )
    library_map = folium.Map(location=center, zoom_start=14 if len(libraries) == 1 else 11)
    folium.plugins.LocateControl(position="topleft", auto_start=False).add_to(library_map)
    for _, row in libraries.iterrows():
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            tooltip=html.escape(str(row["Library_Name"])),
            icon=folium.Icon(color="darkred"),
        ).add_to(library_map)
    if origin:
        folium.Marker(origin, tooltip="Starting point", icon=folium.Icon(color="green", icon="user")).add_to(library_map)
    if route:
        colors = {"walk": "#2563EB", "bus": "#16A34A", "subway": "#9333EA"}
        bounds = [origin, route["destination"]]
        for segment in route["segments"]:
            folium.PolyLine(
                segment["points"], color=colors[segment["mode"]], weight=6, opacity=0.9,
                tooltip=html.escape(segment["label"]), interactive=False,
            ).add_to(library_map)
            bounds.extend(segment["points"])
        for stop in route.get("stops", []):
            folium.CircleMarker(stop["point"], radius=5, color="#432818", fill=True,
                                tooltip=html.escape(stop["name"]), bubbling_mouse_events=False).add_to(library_map)
        library_map.fit_bounds(bounds, padding=(35, 35), max_zoom=16)
    elif origin and len(libraries) == 1:
        library_map.fit_bounds([origin, center], padding=(35, 35), max_zoom=16)
    return library_map


def show_map(container, libraries, route=None):
    with container:
        st.subheader("Library Map")

        if libraries.empty:
            st.info("No libraries match the search. Try another name or district.")

        picking = st.session_state.get("pick_route_origin", False)
        if picking:
            st.info("Click the map to choose your starting point. Turn off the switch to select libraries again.")
        library_map = build_library_map(libraries, route, st.session_state.get("route_origin"))

        result = st_folium(
            library_map,
            height=500,
            use_container_width=True,
            returned_objects=["last_clicked", "last_object_clicked", "last_object_clicked_count"],
            key="origin_picker" if picking else "library_map",
        )
        if route:
            st.caption("Blue: walking · Green: bus · Purple: subway. Times are estimates.")
        st.caption(
            "Walking routes: [OSRM / FOSSGIS](https://routing.openstreetmap.de/about.html) · "
            "Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) · "
            "[Fix the map](https://www.openstreetmap.org/fixthemap)"
        )
        if route and route["mode"] != "walk":
            st.caption("Public transport route data: [ODsay](https://www.odsay.com/)")
    return result or {}
def show_library_information(row, container):
    library = Library.from_row(row)
    with container:
        with st.container(border=True):
            st.subheader("Library Information")
            st.markdown(f"### {library.name}")
            st.table(library.details())
            return show_directions(library)


def clear_route():
    st.session_state.pop("active_route", None)
    st.session_state.pop("route_error", None)


def receive_location():
    position = st.session_state.get("route_location", {}).get("position")
    if position:
        clear_route()
        try:
            st.session_state["route_origin"] = coordinates(position["latitude"], position["longitude"])
            st.session_state["pick_route_origin"] = False
            st.session_state["location_accuracy"] = position.get("accuracy")
        except (KeyError, RoutingError) as error:
            st.session_state["route_error"] = str(error)


def odsay_api_key():
    key = os.environ.get("ODSAY_API_KEY", "")
    if not key:
        try:
            key = st.secrets.get("ODSAY_API_KEY", "")
        except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
            pass
    return str(key).strip()


def show_directions(library):
    st.markdown("#### Directions on this map")
    mode_label = st.selectbox(
        "Travel mode", list(ROUTE_MODES), key="route_mode", on_change=clear_route,
    )
    mode = ROUTE_MODES[mode_label]
    api_key = odsay_api_key() if mode != "walk" else ""
    if mode != "walk" and not api_key:
        st.info("Bus and subway routes are not enabled yet. You can use Walking or open Naver Map below.")
    location_button(receive_location)
    st.toggle("Choose starting point on map", key="pick_route_origin")
    origin = st.session_state.get("route_origin")
    if origin:
        st.caption(f"Starting point: {origin[0]:.5f}, {origin[1]:.5f}")
        accuracy = st.session_state.get("location_accuracy")
        if accuracy and accuracy > 100:
            st.caption("Location accuracy is low. You can choose a more precise point on the map.")
    else:
        st.caption("Use your current location or choose a starting point on the map.")
    st.caption(
        "Show route sends the starting point and destination to "
        + ("OSRM/FOSSGIS." if mode == "walk" else "ODsay and, for walking connections, OSRM/FOSSGIS.")
    )
    request_key = (str(library.serial_number), origin, mode)
    route = st.session_state.get("active_route")
    if route and route["request_key"] != request_key:
        clear_route()
        route = None
    if st.button("Show route", type="primary", width="stretch",
                 disabled=origin is None or (mode != "walk" and not api_key)):
        clear_route()
        route = None
        try:
            destination = coordinates(library.latitude, library.longitude)
            with st.spinner("Finding your route…"):
                route = (walking_route(origin, destination) if mode == "walk"
                         else transit_route(origin, destination, mode, api_key))
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
        for warning in route["warnings"]:
            st.warning(warning)
        with st.expander("Route details"):
            for index, step in enumerate(route["steps"], 1):
                st.text(f"{index}. {step}")
        if st.button("Clear route", width="stretch"):
            clear_route()
            st.rerun()

    with st.expander("Open in Naver Map"):
        show_naver_directions(library, "walk" if mode == "walk" else "public")
    return route


def show_naver_directions(library, mode):
    try:
        app_url, web_url = naver_directions_links(library, mode)
    except (TypeError, ValueError):
        st.info("Directions are unavailable because this library's coordinates are invalid.")
        return

    st.link_button(
        "Open Naver Map app",
        app_url,
        type="primary",
        width="stretch",
    )
    st.caption(
        "On your phone, requires the Naver Map app. Allow location access "
        "in Naver Map to get directions from your current location."
    )
    st.link_button("Directions in browser", web_url, width="stretch")
    st.caption(
        "On a computer or without the app, open the browser link. "
        "Your destination is filled in; choose your starting point and travel mode in Naver Map."
    )

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
