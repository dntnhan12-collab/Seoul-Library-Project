from html import escape
import json
from os import getenv
from pathlib import Path
from urllib.parse import urlencode

import altair as alt
import folium
from folium.elements import EventHandler
from folium.utilities import JsCode
import streamlit as st
from streamlit_folium import st_folium
from models.library import Library

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
    st.session_state["applied_name"] = name
    st.session_state["applied_district"] = district
    st.session_state["selected_library_id"] = library_id
    st.session_state["suggestion_selected"] = is_suggestion
    st.session_state["map_revision"] += 1
    st.session_state.pop("map_view", None)
def apply_search():
    _set_applied_search(
        st.session_state.get("search_name", "").strip(),
        st.session_state.get("search_district", "All districts"),
    )
    st.session_state["_search_needs_full_rerun"] = True


def clear_suggestion_choice():
    st.session_state["selected_library_id"] = None
    st.session_state["suggestion_selected"] = False

def show_title():
    st.markdown(
        '<h1 style="font-size:clamp(1.7rem, 4vw, 2.35rem); '
        'font-weight:750; line-height:1.15; '
        'margin:0 0 0.65rem;">Seoul Public Library Explorer</h1>',
        unsafe_allow_html=True,
    )
@st.fragment
def show_search_panel(container, districts, libraries):
    with container:
        st.subheader("Find a library")
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
def show_summary(total_libraries, total_districts):
    total_column, district_column = st.columns(2)
    total_column.metric("Total libraries", total_libraries)
    district_column.metric("Districts", total_districts)

def show_map(container, libraries, revision, view=None):
    with container:
        title_column, controls_column = st.columns([3, 1], vertical_alignment="center")
        title_column.subheader("Library map")
        show_subway = controls_column.toggle("Subway", key="show_subway")

        if libraries.empty:
            st.info("No libraries match the search. Try another name or district.")

        zoom = 14 if len(libraries) == 1 else 11
        if view:
            center = [view["center"]["lat"], view["center"]["lng"]]
            zoom = view["zoom"]
        elif not libraries.empty:
            center = [libraries["Latitude"].mean(), libraries["Longitude"].mean()]
        else:
            center = [38, 127]

        voyager_tiles = "https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png"
        carto_key = getenv("CARTO_BASEMAPS_API_KEY", "").strip()
        if carto_key:
            voyager_tiles += "?" + urlencode({"key": carto_key})

        library_map = folium.Map(
            location=center,
            zoom_start=zoom,
            zoom_control="bottomright",
            scroll_wheel_zoom=True,
            double_click_zoom=False,
            touch_zoom=False,
            box_zoom=False,
            keyboard=False,
            inertia=False,
            tiles=folium.TileLayer(
                tiles=voyager_tiles,
                name="CARTO Voyager",
                attr=(
                    '&copy; <a href="https://www.openstreetmap.org/copyright">'
                    'OpenStreetMap</a> contributors &copy; '
                    '<a href="https://carto.com/attributions">CARTO</a>'
                ),
            ),
        )
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
        for _, row in libraries.iterrows():
            folium.Marker(
                location=[row["Latitude"], row["Longitude"]],
                tooltip=escape(row["Library_Name"]),
                icon=folium.Icon(color="darkred"),
                bubbling_mouse_events=False,
            ).add_to(library_map)

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
            height=590,
            use_container_width=True,
            returned_objects=[
                "last_clicked", "last_object_clicked", "last_object_clicked_tooltip",
                "center", "zoom",
            ],
            key=f"library_map_{revision}",
        )

    return result or {}
def show_library_information(row, container):
    library = Library.from_row(row)
    details = library.details()
    destination = urlencode({"api": 1, "destination": f"{library.latitude},{library.longitude}"})
    with container:
        with st.container(border=True):
            st.markdown(f"#### {library.name}")
            st.caption(library.district)
            for label in ("Address", "Operating Hours", "Closed Days", "Phone"):
                value = str(details[label]).strip()
                if value and value.lower() not in {"nan", "none", "<na>"}:
                    st.markdown(f"**{label}**  \n{value}")
            st.link_button("Get directions", f"https://www.google.com/maps/dir/?{destination}", width="stretch")
            website = str(library.website).strip()
            if website.startswith("www."):
                website = f"https://{website}"
            if website.startswith(("https://", "http://")):
                st.link_button("Library website", website, width="stretch")

def show_district_chart(counts):
    st.subheader("Libraries by District")
    chart_data = counts.rename_axis("District").reset_index(name="Libraries")
    largest_count = int(chart_data["Libraries"].max())

    chart = (
        alt.Chart(chart_data)
        .mark_bar(color="#6F1D1B", cornerRadiusEnd=3)
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
        .properties(height=alt.Step(21))
    )

    st.altair_chart(chart, width="stretch")
