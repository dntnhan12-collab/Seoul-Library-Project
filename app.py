import altair as alt
import folium
import streamlit as st
from folium.plugins import LocateControl
from streamlit_folium import st_folium
from models.library_manager import LibraryManager
from services.data_manager import get_cleaned_library_data
from services.analyzer import (get_total_libraries,get_total_districts,get_libraries_per_district,)

st.set_page_config(page_title="Seoul Public Library Explorer",page_icon="📚",layout="wide",)

def load_css():
    css_path = "styles/style.css"
    try:
        with open(css_path, encoding="utf-8") as css_file:
            st.markdown(f"<style>{css_file.read()}</style>",unsafe_allow_html=True,)
    except FileNotFoundError:
        st.warning("CSS file not found: styles/style.css")
load_css()

@st.cache_data
def load_library_data():
    df = get_cleaned_library_data()
    manager = LibraryManager.from_dataframe(df)
    libraries = manager.get_all()
    return df, libraries

defaults ={
    "applied_search": "",
    "applied_district": "All Districts",
    "selected_library": None,
    "search_input": "",
    "district_input": "All Districts",}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

def find_libraries():
    st.session_state.applied_search =(st.session_state.search_input.strip())
    st.session_state.applied_district =(st.session_state.district_input)
    st.session_state.selected_library = None

def reset_libraries():
    st.session_state.search_input = ""
    st.session_state.district_input = "All Districts"
    st.session_state.applied_search = ""
    st.session_state.applied_district = "All Districts"
    st.session_state.selected_library = None

def show_title():
    st.markdown("""
        <div class="page-header">
            <h1>Seoul Public Library</h1>
        </div>
        """,
        unsafe_allow_html=True,)

def show_search_area(districts):
    with st.container(border=True):
        st.markdown('<div class="section-heading">🔎 &nbsp; Library Search</div>',unsafe_allow_html=True,)
        st.text_input("Search by name",key="search_input",placeholder="Enter library name...",)
        district_options =["All Districts"] + sorted(districts)
        st.selectbox("District",options=district_options,key="district_input",)
        col_find, col_reset = st.columns(2)
        with col_find:
            st.button("⌕ Find",key="find_button",use_container_width=True,on_click=find_libraries,type="primary",)

        with col_reset:
            st.button("↻ Reset",key="reset_button",use_container_width=True,on_click=reset_libraries,)

def filter_libraries(libraries, name, district):
    name = str(name).strip().lower()
    district = str(district).strip()
    results = []
    for library in libraries:
        library_name = str(getattr(library, "name", "")).strip().lower()
        library_district = str(getattr(library, "district", "")).strip()
        if (district != "All Districts" and library_district != district):
            continue
        if name and name not in library_name:
            continue
        results.append(library)
    return results
def show_library_information(library):
    if library is None:
        return
    with st.container(border=True):
        st.markdown('<div class="section-heading">📖 &nbsp; Library Information</div>',unsafe_allow_html=True,)
        st.markdown(f"Name: {getattr(library, 'name', 'N/A')}")
        st.markdown(f"District: {getattr(library, 'district', 'N/A')}")
        st.markdown(f"Address: {getattr(library, 'address', 'N/A')}")
        st.markdown(f"Phone: {getattr(library, 'phone', 'N/A')}")
        website = getattr(library, "website", None)
        if website:
            st.markdown(f"Website: [{website}]({website})")
        else:
            st.markdown("Website: N/A")
        hours = str(getattr(library, "operating_hours", "N/A")).replace("~", " - ")
        st.markdown(f"Operating Hours: {hours}")
        st.markdown(f"Closed Days: {getattr(library, 'closed_days', 'N/A')}")
        st.markdown(f"Library Type: {getattr(library, 'library_type', 'N/A')}")

def get_clicked_library(libraries, map_data):
    if not map_data:
        return None
    clicked = map_data.get("last_object_clicked")
    if not clicked:
        return None
    lat = clicked.get("lat")
    lng = clicked.get("lng")
    if lat is None or lng is None:
        return None
    try:
        lat = float(lat)
        lng = float(lng)
    except (ValueError, TypeError):
        return None
    for library in libraries:
        latitude = getattr(library, "latitude", None)
        longitude = getattr(library, "longitude", None)
        if latitude is None or longitude is None:
            continue
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (ValueError, TypeError):
            continue

        if (abs(latitude - lat) < 0.0005 and abs(longitude - lng) < 0.0005):
            return library
    return None

def show_map(libraries):
    with st.container(border=True):
        st.markdown('<div class="section-heading">♧ &nbsp; Library Map</div>',unsafe_allow_html=True,)
        st.caption("Click a marker to view library information.")
        map_object = folium.Map(location=[37.5665, 126.9780],zoom_start=11,tiles="OpenStreetMap",control_scale=True,zoom_control=True,)
        LocateControl(
            auto_start=False,
            strings={"title": "Show my location","popup": "You are here",},).add_to(map_object)
        for library in libraries:
            latitude = getattr(library, "latitude", None)
            longitude = getattr(library, "longitude", None)
            if latitude is None or longitude is None:
                continue
            try:
                latitude = float(latitude)
                longitude = float(longitude)
            except (ValueError, TypeError):
                continue
            name = str(getattr(library, "name", "Library"))
            district = str(getattr(library, "district", "N/A"))
            folium.Marker(
                location=[latitude, longitude],
                tooltip=name,
                popup=folium.Popup(f"<b>{name}</b><br>{district}",max_width=250,),
                icon=folium.Icon(color="darkred",icon="book",prefix="fa",),
            ).add_to(map_object)
        map_data = st_folium(map_object,width=None,height=390,key="library_map",returned_objects=["last_object_clicked"],)
    return map_data

def show_metrics(df, found):
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Libraries",get_total_libraries(df),)
    col2.metric("Total Districts",get_total_districts(df),)
    col3.metric("Libraries Found",found,)

def show_chart(df):
    with st.container(border=True):
        st.markdown('<div class="section-heading">Libraries by District</div>',unsafe_allow_html=True,)
        district_counts = get_libraries_per_district(df)
        if district_counts is None:
            st.info("No district data available.")
            return
        chart_data =(district_counts.rename("Number of Libraries").reset_index())
        chart =(
            alt.Chart(chart_data)
            .mark_bar(color="#8C7655")
            .encode(
                x=alt.X("Number of Libraries:Q",title="Number of Libraries",),
                y=alt.Y("District_Name:N",sort="-x",title="District",),
                tooltip=["District_Name","Number of Libraries",],
            ).properties(height=380))
        st.altair_chart(chart,use_container_width=True,)

def main():
    df, libraries = load_library_data()
    show_title()
    districts ={
        str(getattr(library, "district", "")).strip()
        for library in libraries
        if getattr(library, "district", None)}
    filtered = filter_libraries(libraries,st.session_state.applied_search,st.session_state.applied_district,)

    search_applied =(bool(st.session_state.applied_search) or st.session_state.applied_district != "All Districts")
    found = len(filtered) if search_applied else 0

    if st.session_state.applied_search:
        st.session_state.selected_library =(filtered[0] if filtered else None)

    elif st.session_state.applied_district != "All Districts":
        if filtered:
            current = st.session_state.selected_library
            if current not in filtered:
                st.session_state.selected_library = filtered[0]
        else:
            st.session_state.selected_library = None

    left, right = st.columns([1, 2], gap="small")
    with left:
        show_search_area(districts)
        if st.session_state.applied_search:
            if filtered:
                st.success(f"Found: {filtered[0].name}")
            else:
                st.warning("No library found with this name.")
        elif st.session_state.applied_district != "All Districts":
            st.info(
                f"Found {len(filtered)} libraries in "
                f"{st.session_state.applied_district}.")
        if st.session_state.selected_library is not None:
            show_library_information(st.session_state.selected_library)
    with right:
        map_libraries = filtered if search_applied else libraries
        map_data = show_map(map_libraries)
    clicked_library = get_clicked_library(map_libraries,map_data,)
    if clicked_library is not None:
        if clicked_library != st.session_state.selected_library:
            st.session_state.selected_library = clicked_library
            st.rerun()
    st.divider()
    show_metrics(df, found)
    st.divider()
    show_chart(df)

if __name__ == "__main__":
    main()