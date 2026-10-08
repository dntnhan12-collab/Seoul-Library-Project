import altair as alt
import folium
import streamlit as st
from folium.plugins import LocateControl
from streamlit_folium import st_folium
from models.library_manager import LibraryManager
from services.data_manager import get_cleaned_library_data
from services.analyzer import (get_total_libraries,get_total_districts,get_libraries_per_district)

st.set_page_config(page_title="Seoul Public Library",page_icon="📚",layout="wide")

@st.cache_data
def load_library_data():
    df = get_cleaned_library_data()
    manager = LibraryManager.from_dataframe(df)
    return df, manager, manager.get_all()

if "applied_search" not in st.session_state:
    st.session_state.applied_search = ""
if "applied_district" not in st.session_state:
    st.session_state.applied_district = "All Districts"
if "selected_library" not in st.session_state:
    st.session_state.selected_library = None
if "map_center" not in st.session_state:
    st.session_state.map_center = [37.5665, 126.9780]
if "map_zoom" not in st.session_state:
    st.session_state.map_zoom = 11

def find_libraries():
    st.session_state.applied_search = st.session_state.search_input.strip()
    st.session_state.applied_district = st.session_state.district_input
    st.session_state.selected_library = None

def reset_libraries():
    st.session_state.applied_search = ""
    st.session_state.applied_district = "All Districts"
    st.session_state.selected_library = None
    st.session_state.search_input = ""
    st.session_state.district_input = "All Districts"

def show_search_area(districts):
    st.subheader("Library Search")
    st.text_input("Search by name", key="search_input")
    st.selectbox("District",["All Districts"] + sorted(districts),key="district_input")
    col1, col2 = st.columns(2)
    with col1:
        st.button("Find",use_container_width=True,on_click=find_libraries)
    with col2:
        st.button("Reset",use_container_width=True,on_click=reset_libraries)

def find_library(libraries, name, district):
    name = name.strip().lower()
    if not name:
        return None
    for library in libraries:
        if library.name.strip().lower() == name:
            if (district == "All Districts" or library.district.strip() == district):
                return library
    return None

def filter_libraries(libraries, name, district):
    if name.strip():
        library = find_library(libraries,name,district)
        return [library] if library else []
    if district != "All Districts":
        return [
            library
            for library in libraries
            if library.district.strip() == district
        ]
    return libraries

def show_metrics(df, found):
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Libraries",get_total_libraries(df))
    col2.metric("Total Districts",get_total_districts(df))
    col3.metric("Total Found Libraries",found)

def show_map(libraries):
    st.markdown(
        "<h3 style='color:#2E8B57;'>Library Map</h3>",
        unsafe_allow_html=True
    )

    m = folium.Map(
        location=[37.5665, 126.9780],
        zoom_start=11,
        tiles="OpenStreetMap",
        control_scale=True,
        zoom_control=True
    )

    LocateControl(
        auto_start=False,
        strings={
            "title": "Show my location",
            "popup": "You are here"
        }
    ).add_to(m)

    for library in libraries:
        try:
            lat = float(library.latitude)
            lng = float(library.longitude)
        except (ValueError, TypeError):
            continue

        folium.Marker(
            location=[lat, lng],
            tooltip=library.name,
            icon=folium.Icon(
                color="red",
                icon="info-sign"
            )
        ).add_to(m)

    map_data = st_folium(
        m,
        width="100%",
        height=400,
        key="library_map",
        returned_objects=["last_object_clicked"]
    )

    return map_data

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
    for library in libraries:
        try:
            library_lat = float(library.latitude)
            library_lng = float(library.longitude)
        except (ValueError, TypeError):
            continue
        if (
            abs(library_lat - float(lat)) < 0.0005
            and
            abs(library_lng - float(lng)) < 0.0005
        ):
            return library
    return None

def show_library_information(library):
    if library is None:
        return
    st.subheader("Library Information")

    st.write(f"Name: {library.name}")
    st.write(f"District: {library.district}")
    st.write(f"Address: {library.address}")
    st.write(f"Phone: {library.phone}")
    st.write(f"Website: {library.website}")
    hours = str(library.operating_hours).replace("~","-")
    st.write(f"**Operating Hours:** {hours}")
    st.write(f"**Closed Days:** {library.closed_days}")
    st.write(f"**Library Type:** {library.library_type}")

def show_chart(df):
    st.subheader("Libraries by District")
    data = (get_libraries_per_district(df).rename("Number of Libraries").reset_index())

    chart = (alt.Chart(data).mark_bar().encode(
            x=alt.X("Number of Libraries:Q",title="Number of Libraries"),
            y=alt.Y("District_Name:N",sort="-x",title="District"),
            tooltip=["District_Name","Number of Libraries"]
        )
        .properties(height=380)
    )
    st.altair_chart(chart, use_container_width=True)

def main():
    df, manager, libraries = load_library_data()
    st.markdown(
        "<h1 style='color:#2E8B57;'>"
        "Seoul Public Library"
        "</h1>",
        unsafe_allow_html=True
    )

    districts = {
        library.district.strip()
        for library in libraries
        if library.district
    }
    filtered = filter_libraries(libraries,st.session_state.applied_search,st.session_state.applied_district)
    found = (len(filtered)
        if (st.session_state.applied_search or st.session_state.applied_district != "All Districts")
        else 0
    )
    show_metrics(df, found)
    st.divider()
    left, right = st.columns([1, 2])
    with left:
        show_search_area(districts)
        if st.session_state.applied_search:
            if filtered:
                st.session_state.selected_library = filtered[0]
                st.success(f"Found: {filtered[0].name}")
            else:
                st.warning("No library found with this name.")
        elif st.session_state.applied_district != "All Districts":
            st.info(f"Found {len(filtered)} libraries "f"in {st.session_state.applied_district}.")
    with right:
        map_data = show_map(filtered)
    clicked = get_clicked_library(libraries,map_data)
    if clicked:
        st.session_state.selected_library = clicked
    if st.session_state.selected_library:
        with left:
            st.divider()
            show_library_information(st.session_state.selected_library)
    st.divider()
    show_chart(df)

if __name__ == "__main__":
    main()