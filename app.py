import math
from html import escape
from pathlib import Path
import altair as alt
import folium
import streamlit as st
from folium.plugins import LocateControl
from streamlit_folium import st_folium
from models.library_manager import LibraryManager
from services.data_manager import get_cleaned_library_data
from services.analyzer import (get_total_libraries,get_total_districts,get_libraries_per_district,)

st.set_page_config(page_title="Seoul Public Library Explorer",page_icon="📚",layout="wide",)
ALL = "All Districts"

def heading(text):
    st.markdown(f'<div class="section-heading">{text}</div>',unsafe_allow_html=True,)

def load_css():
    path = Path(__file__).resolve().parent / "styles" / "style.css"
    if path.exists():
        css = path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    else:
        st.warning("CSS file not found: styles/style.css")

@st.cache_data(show_spinner="Loading library data...")
def load_library_data():
    df = get_cleaned_library_data()
    libraries = LibraryManager.from_dataframe(df).get_all()
    return df, libraries

def init_state():
    defaults = {"applied_search": "","applied_district": ALL,"selected_library": None,"search_input": "","district_input": ALL,"filter_version": 0,}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def apply_search(reset=False):
    s = st.session_state
    if reset:
        s.search_input, s.district_input = "", ALL
    s.applied_search = s.search_input.strip()
    s.applied_district = s.district_input
    s.selected_library = None
    s.filter_version += 1

def show_search(districts):
    with st.container(border=True):
        heading("🔎 &nbsp; Library Search")
        st.text_input("Search by name",key="search_input",placeholder="Enter library name...",)
        st.selectbox("District",[ALL] + sorted(districts),key="district_input",)
        col1, col2 = st.columns(2)
        with col1:
            st.button("⌕ Find",key="find_button",use_container_width=True,on_click=apply_search,type="primary",)
        with col2:
            st.button("↻ Reset",key="reset_button",use_container_width=True,on_click=apply_search,kwargs={"reset": True},)


def filter_libraries(libraries, name, district):
    name = str(name).strip().casefold()
    return [
        lib for lib in libraries
        if (district == ALL or str(getattr(lib, "district", "") or "").strip() == district)
        and name in str(getattr(lib, "name", "") or "").strip().casefold()]

def valid_coords(lat, lon):
    try:
        lat, lon = float(lat), float(lon)
        if (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
            return lat, lon
    except (TypeError, ValueError):
        pass
    return None

def show_info(library):
    if library is None:
        return
    with st.container(border=True):
        heading("📖 &nbsp; Library Information")
        fields = (("Name", "name"),("District", "district"),("Address", "address"),("Phone", "phone"),)
        for label, attr in fields:
            value = getattr(library, attr, None) or "N/A"
            st.write(f"{label}: {value}")
        website = getattr(library, "website", None)
        if website and str(website).startswith(("http://", "https://")):
            st.write("Website:")
            st.link_button("Open library website", str(website))
        else:
            st.write("Website: N/A")
        hours = str(getattr(library, "operating_hours", None) or "N/A").replace("~", " - ")
        st.write(f"Operating Hours: {hours}")
        st.write(f"Closed Days: "f"{getattr(library, 'closed_days', None) or 'N/A'}")
        st.write(f"Library Type: "f"{getattr(library, 'library_type', None) or 'N/A'}")

def show_map(libraries, map_key="library_map"):
    with st.container(border=True):
        heading("♧ &nbsp; Library Map")
        st.caption("Click a marker to view library information.")
        m = folium.Map(location=[37.5665, 126.9780],zoom_start=11,tiles="OpenStreetMap",control_scale=True,zoom_control=True,prefer_canvas=True,)
        LocateControl(auto_start=False,strings={"title": "Show my location","popup": "You are here",},).add_to(m)
        markers = folium.FeatureGroup(name="Libraries")
        for lib in libraries:
            coords = valid_coords(getattr(lib, "latitude", None),getattr(lib, "longitude", None),)
            if coords is None:
                continue
            name = str(getattr(lib, "name", None) or "Library")
            district = str(getattr(lib, "district", None) or "N/A")
            folium.Marker(
                location=coords,
                tooltip=name,
                popup=folium.Popup(f"<b>{escape(name)}</b><br>{escape(district)}",max_width=250,),
                icon=folium.Icon(color="darkred",icon="book",prefix="fa",),
            ).add_to(markers)
        return st_folium(m,key=map_key,height=390,width=None,feature_group_to_add=markers,returned_objects=["last_object_clicked"],)

def get_clicked_library(libraries, map_data):
    clicked = (map_data or {}).get("last_object_clicked")
    if not isinstance(clicked, dict):
        return None
    position = valid_coords(clicked.get("lat"),clicked.get("lng"),)
    if position is None:
        return None
    for lib in libraries:
        coords = valid_coords(getattr(lib, "latitude", None),getattr(lib, "longitude", None),)
        if coords and all(abs(a - b) < 0.000005 for a, b in zip(coords, position)):
            return lib
    return None

def show_chart(df):
    with st.container(border=True):
        heading("Libraries by District")
        counts = get_libraries_per_district(df)
        if counts is None or len(counts) == 0:
            st.info("No district data available.")
            return
        chart_data = counts.rename("Number of Libraries").reset_index()
        chart = (
            alt.Chart(chart_data)
            .mark_bar(color="#8C7655")
            .encode(
                x=alt.X("Number of Libraries:Q",title="Number of Libraries",),
                y=alt.Y("District_Name:N",sort="-x",title="District",),
                tooltip=["District_Name", "Number of Libraries"],)
            .properties(height=380))
        st.altair_chart(chart, use_container_width=True)

def main():
    init_state()
    df, libraries = load_library_data()
    st.markdown(
        '<div class="page-header">'
        '<h1>Seoul Public Library</h1>'
        '</div>',
        unsafe_allow_html=True,)
    districts = {
        str(lib.district).strip()
        for lib in libraries
        if getattr(lib, "district", None)}
    s = st.session_state
    filtered = filter_libraries(libraries,s.applied_search,s.applied_district,)
    searching = bool(s.applied_search) or s.applied_district != ALL
    found = len(filtered) if searching else 0
    if searching and s.selected_library not in filtered:
        s.selected_library = filtered[0] if filtered else None
    left, right = st.columns([1, 2], gap="small")
    with left:
        show_search(districts)
        if s.applied_search:
            if filtered:
                st.success(f"Found {len(filtered)} matching libraries.")
            else:
                st.warning("No library found with this name.")
        elif s.applied_district != ALL:
            st.info(f"Found {len(filtered)} libraries "f"in {s.applied_district}.")
        info_slot = st.empty()
    visible = filtered if searching else libraries
    with right:
        map_data = show_map(visible,map_key="library_map",)
    clicked = get_clicked_library(visible, map_data)
    if clicked is not None:
        s.selected_library = clicked
    with info_slot.container():
        show_info(s.selected_library)
    st.divider()
    a, b, c = st.columns(3)
    a.metric("Total Libraries", get_total_libraries(df))
    b.metric("Total Districts", get_total_districts(df))
    c.metric("Libraries Found", found)
    st.divider()
    show_chart(df)

load_css()
if __name__ == "__main__":
    main()