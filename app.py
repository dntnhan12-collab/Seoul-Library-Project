import altair as alt
import folium
import streamlit as st
from folium.plugins import LocateControl
from streamlit_folium import st_folium
from models.library import Library

#1. reset + search + library selection
def handle_search_and_selection():
    if "search_name" not in st.session_state:
        st.session_state.search_name = ""

    if "selected_district" not in st.session_state:
        st.session_state.selected_district = "All Districts"

    if "find_clicked" not in st.session_state:
        st.session_state.find_clicked = False

    if "reset_clicked" not in st.session_state:
        st.session_state.reset_clicked = False

    return (
        st.session_state.search_name,
        st.session_state.selected_district,
        st.session_state.find_clicked,
        st.session_state.reset_clicked
    )

#2. show project title
def show_title():
    st.title("Seoul Public Library Explorer")

#3. show search area
def show_search_area(districts):
    st.subheader("Library Search")
    search_name = st.text_input("Search by name", key="search_name")
    district_options = ["All Districts"] + list(districts)
    selected_district = st.selectbox("District", district_options, key="selected_district")
    find_col, reset_col = st.columns(2)

    with find_col:
        find_clicked = st.button("Find", use_container_width=True)
    with reset_col:
        reset_clicked = st.button("Reset", use_container_width=True)
    return (search_name, selected_district, find_clicked, reset_clicked)

#4. show overview metrics
def show_overview_metrics(total_libraries, total_districts, total_found_libraries):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Libraries", total_libraries)
    with col2:
        st.metric("Total Districts", total_districts)
    with col3:
        st.metric("Total Found Libraries", total_found_libraries)

#5. show library map + markers
def show_map(libraries):
    st.subheader("Library Map")
    m = folium.Map(location=[37.5665, 126.9780], zoom_start=11)
    LocateControl().add_to(m)
    for library in libraries:
        latitude = getattr(library, "latitude", None)
        longitude = getattr(library, "longitude", None)
        if latitude is None or longitude is None:
            continue
        folium.Marker(location=[latitude, longitude], popup=library.name, tooltip=library.name).add_to(m)
    map_data = st_folium(m, width=700, height=400)
    return map_data

#6. show library information
def show_library_information(library=None):
    st.subheader("Library Information")
    if library is None:
        st.info("Select a library to view its information.")
        return

    st.write(f"Name: {getattr(library, 'name', 'N/A')}")
    st.write(f"District: {getattr(library, 'district', 'N/A')}")
    st.write(f"Address: {getattr(library, 'address', 'N/A')}")
    st.write(f"Phone: {getattr(library, 'phone', 'N/A')}")
    st.write(f"Website: {getattr(library, 'website', 'N/A')}")
    st.write(f"Operating Hours: "f"{getattr(library, 'operating_hours', 'N/A')}")

#7. show horizontal bar chart
def show_libraries_by_district(district_counts):
    st.subheader("Libraries by District")

    if district_counts is None:
        st.info("Library distribution by district will be displayed here.")
        return

    chart_data = district_counts.rename("Number of Libraries").reset_index()
    chart = (alt.Chart(chart_data).mark_bar()
        .encode(
            x=alt.X("Number of Libraries:Q", title="Number of Libraries"),
            y=alt.Y("District_Name:N", sort="-x", title="District"),
            tooltip=["District_Name", "Number of Libraries"]
        )
        .properties(height=500)
    )
    st.altair_chart(chart, use_container_width=True)

#main dashboard
def main():
    show_title()

    #overview metrics
    show_overview_metrics(total_libraries=0, total_districts=0, total_found_libraries=0)
    st.divider()

    #search and map
    search_col, map_col = st.columns([1, 2])
    with search_col:
        search_name, selected_district, find_clicked, reset_clicked = show_search_area([])
    with map_col:
        show_map([])
    st.divider()

    #library information
    show_library_information()
    st.divider()

    #libraries by district
    show_libraries_by_district(None)

if __name__ == "__main__":
    main()