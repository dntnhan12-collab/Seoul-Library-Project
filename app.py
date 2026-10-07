import altair as alt
import folium
import streamlit as st
from folium.plugins import LocateControl
from streamlit_folium import st_folium
from models.library_manager import LibraryManager
from services.data_manager import get_cleaned_library_data
from services.analyzer import (get_total_libraries, get_total_districts, get_libraries_per_district)

@st.cache_data
def load_library_data():
    df = get_cleaned_library_data()
    manager = LibraryManager.from_dataframe(df)
    libraries = manager.get_all()
    return df, libraries

def show_title():
    st.title("Seoul Public Library Explorer")

def show_search_area(districts):
    st.subheader("Library Search")
    search_name = st.text_input("Search by name", key="search_name")
    district_options = ["All Districts"] + sorted(list(districts))
    selected_district = st.selectbox("District", district_options, key="selected_district")
    find_col, reset_col = st.columns(2)
    with find_col:
        find_clicked = st.button("Find", use_container_width=True)
    with reset_col:
        reset_clicked = st.button("Reset", use_container_width=True)
    return (search_name, selected_district, find_clicked, reset_clicked)

def show_overview_metrics(total_libraries, total_districts, total_found_libraries=0):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Libraries", total_libraries)
    with col2:
        st.metric("Total Districts", total_districts)
    with col3:
        st.metric("Total Found Libraries", total_found_libraries)

def show_map(libraries):
    st.subheader("Library Map")
    m = folium.Map(location=[37.5665, 126.9780],zoom_start=11)
    LocateControl().add_to(m)
    for library in libraries:
        latitude = getattr(library, "latitude", None)
        longitude = getattr(library, "longitude", None)
        if latitude is None or longitude is None:
            continue
        folium.Marker(location=[latitude, longitude],popup=library.name,tooltip=library.name).add_to(m)
    map_data = st_folium(m,width=700,height=450,key="library_map")
    return map_data

def find_library_by_name(libraries, search_name, selected_district):
    if not search_name:
        return None
    search_name = search_name.strip().lower()
    for library in libraries:
        library_name = getattr(library, "name", "").strip().lower()
        library_district = getattr(library, "district", "")
        if selected_district != "All Districts":
            if library_district != selected_district:
                continue
        if library_name == search_name:
            return library
    return None

def find_library_from_map_click(libraries, map_data):
    if not map_data:
        return None
    clicked = map_data.get("last_object_clicked")
    if not clicked:
        return None
    clicked_lat = clicked.get("lat")
    clicked_lng = clicked.get("lng")
    if clicked_lat is None or clicked_lng is None:
        return None
    for library in libraries:
        latitude = getattr(library, "latitude", None)
        longitude = getattr(library, "longitude", None)
        if latitude is None or longitude is None:
            continue
        if (
            abs(float(latitude) - clicked_lat) < 0.0001
            and
            abs(float(longitude) - clicked_lng) < 0.0001
        ):
            return library
    return None

def show_library_information(library=None):
    if library is None:
        return
    st.subheader("Library Information")
    st.write(f"Name: {getattr(library, 'name', 'N/A')}")
    st.write(f"District: {getattr(library, 'district', 'N/A')}")
    st.write(f"Address: {getattr(library, 'address', 'N/A')}")
    st.write(f"Phone: {getattr(library, 'phone', 'N/A')}")
    st.write(f"Website: {getattr(library, 'website', 'N/A')}")
    st.write(f"Operating Hours: "f"{str(getattr(library, 'operating_hours', 'N/A')).replace('~', ' - ')}")
    st.write(f"Closed Days: "f"{getattr(library, 'closed_days', 'N/A')}")
    st.write(f"Library Type: "f"{getattr(library, 'library_type', 'N/A')}")

def show_libraries_by_district(district_counts):
    st.subheader("Libraries by District")
    if district_counts is None:
        return
    chart_data = (district_counts.rename("Number of Libraries").reset_index())
    chart = (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X("Number of Libraries:Q", title="Number of Libraries"),
            y=alt.Y("District_Name:N", sort="-x", title="District"),
            tooltip=["District_Name", "Number of Libraries"]
        )
        .properties(height=500)
    )
    st.altair_chart(chart, use_container_width=True)

def main():
    df, libraries = load_library_data()
    show_title()
    districts = set(
        library.district
        for library in libraries
        if library.district)
    if "selected_library" not in st.session_state:
        st.session_state.selected_library = None
    total_libraries = get_total_libraries(df)
    total_districts = get_total_districts(df)
    show_overview_metrics(total_libraries=total_libraries,total_districts=total_districts,total_found_libraries=0)
    st.divider()
    search_col, map_col = st.columns([1, 1])
    with search_col:
        search_name, selected_district, find_clicked, reset_clicked = (show_search_area(districts))
    with map_col:
        map_data = show_map(libraries)
    if reset_clicked:
        st.session_state.selected_library = None
        st.session_state.search_name = ""
        st.session_state.selected_district = "All Districts"
        st.rerun()
    if find_clicked:
        found_library = find_library_by_name(libraries,search_name,selected_district)
        st.session_state.selected_library = found_library
        if found_library is None:
            st.warning("No library found with this name.")
    clicked_library = find_library_from_map_click(libraries,map_data)
    if clicked_library is not None:
        st.session_state.selected_library = clicked_library
    with search_col:
        show_library_information(st.session_state.selected_library)
    st.divider()
    district_counts = get_libraries_per_district(df)
    show_libraries_by_district(district_counts)

if __name__ == "__main__":
    main()