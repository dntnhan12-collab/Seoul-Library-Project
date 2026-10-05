import altair as alt
import folium
import streamlit as st
from folium.plugins import LocateControl
from streamlit_folium import st_folium
from models.library import Library


# 1. Reset + Search + Library Selection
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


# 2. Show project title
def show_title():
    st.title("Seoul Public Library Explorer")


# 3. Show search area
def show_search_area():
    st.subheader("Library Search")

    search_name = st.text_input(
        "Search by name",
        key="search_name"
    )

    selected_district = st.selectbox(
        "District",
        ["All Districts"],
        key="selected_district"
    )

    find_clicked = st.button("Find")

    reset_clicked = st.button("Reset")

    return search_name, selected_district, find_clicked, reset_clicked


# 4. Show overview metrics
def show_overview_metrics():
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Libraries", 0)

    with col2:
        st.metric("Total Districts", 0)

    with col3:
        st.metric("Total Found Libraries", 0)


# 5. Show library map + markers
def show_map():
    st.subheader("Library Map")

    m = folium.Map(
        location=[37.5665, 126.9780],
        zoom_start=11
    )

    LocateControl().add_to(m)

    map_data = st_folium(
        m,
        width=700,
        height=400
    )

    return map_data


# 6. Show library information
def show_library_information():
    st.subheader("Library Information")

    st.info("Library information will be displayed here.")


# 7. Show horizontal bar chart
def show_libraries_by_district():
    st.subheader("Libraries by District")

    st.info("The library distribution by district will be displayed here.")