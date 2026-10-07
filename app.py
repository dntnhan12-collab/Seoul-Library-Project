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
    libraries = manager.get_all()
    return df, manager, libraries

if "applied_search" not in st.session_state:
    st.session_state.applied_search = ""
if "applied_district" not in st.session_state:
    st.session_state.applied_district = "All Districts"
if "selected_library" not in st.session_state:
    st.session_state.selected_library = None
if "total_found_libraries" not in st.session_state:
    st.session_state.total_found_libraries = 0

def find_libraries():
    st.session_state.applied_search = (st.session_state.search_input.strip())
    st.session_state.applied_district = (st.session_state.district_input)
    st.session_state.selected_library = None

def reset_libraries():
    st.session_state.applied_search = ""
    st.session_state.applied_district = "All Districts"
    st.session_state.selected_library = None
    st.session_state.total_found_libraries = 0
    st.session_state.search_input = ""
    st.session_state.district_input = "All Districts"

def show_title():
    st.title("Seoul Public Library")

def show_search_area(districts):
    st.subheader("Library Search")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Search by name",key="search_input")
    with col2:
        district_options = (["All Districts"] + sorted(list(districts)))
        st.selectbox("District",district_options,key="district_input")

    find_col, reset_col = st.columns(2)
    with find_col:
        st.button("Find",use_container_width=True,on_click=find_libraries)
    with reset_col:
        st.button("Reset",use_container_width=True,on_click=reset_libraries)

def find_library_by_name(libraries,search_name,selected_district):
    search_name = str(search_name).strip().lower()
    if not search_name:
        return None
    for library in libraries:
        library_name = str(getattr(library, "name", "")).strip().lower()
        library_district = str(getattr(library, "district", "")).strip()
        if selected_district != "All Districts":
            if library_district != str(selected_district).strip():
                continue
        if library_name == search_name:
            return library
    return None

def filter_libraries(libraries,search_name,selected_district):
    search_name = str(search_name).strip()
    if search_name:
        found_library = find_library_by_name(libraries,search_name,selected_district)
        if found_library is not None:
            return [found_library]
        return []
    if selected_district != "All Districts":
        selected_district = str(selected_district).strip()
        return [
            library
            for library in libraries
            if str(getattr(library, "district", "")).strip() == selected_district
        ]
    return libraries

def show_overview_metrics(total_libraries,total_districts,total_found_libraries):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Libraries",total_libraries)
    with col2:
        st.metric("Total Districts",total_districts)
    with col3:
        st.metric("Total Found Libraries",total_found_libraries)

def show_map(libraries):
    st.subheader("Library Map")
    m = folium.Map(location=[37.5665, 126.9780],zoom_start=11,control_scale=True)
    LocateControl(auto_start=False,strings={"title": "Show my location","popup": "You are here"}).add_to(m)

    for library in libraries:
        latitude = getattr(library,"latitude",None)
        longitude = getattr(library,"longitude",None)
        if latitude is None or longitude is None:
            continue
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (ValueError, TypeError):
            continue
        folium.Marker(
            location=[latitude,longitude],
            popup=library.name,
            tooltip=library.name
        ).add_to(m)
    map_data = st_folium(m,width="100%",height=500,key="library_map",returned_objects=["last_object_clicked"])
    return map_data

def find_library_from_map_click(libraries,map_data):
    if not map_data:
        return None
    clicked = map_data.get("last_object_clicked")
    if not clicked:
        return None
    clicked_lat = clicked.get("lat")
    clicked_lng = clicked.get("lng")
    if clicked_lat is None or clicked_lng is None:
        return None
    try:
        clicked_lat = float(clicked_lat)
        clicked_lng = float(clicked_lng)
    except (ValueError, TypeError):
        return None
    for library in libraries:
        latitude = getattr(library,"latitude",None)
        longitude = getattr(library,"longitude",None)
        if latitude is None or longitude is None:
            continue
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (ValueError, TypeError):
            continue
        if (
            abs(latitude - clicked_lat) < 0.0001
            and
            abs(longitude - clicked_lng) < 0.0001
        ):
            return library
    return None

def show_library_information(library):
    if library is None:
        return
    st.subheader("Library Information")
    st.write(f"Name: "f"{getattr(library, 'name', 'N/A')}")
    st.write(f"District: "f"{getattr(library, 'district', 'N/A')}")
    st.write(f"Address: "f"{getattr(library, 'address', 'N/A')}")
    st.write(f"Phone: "f"{getattr(library, 'phone', 'N/A')}")
    st.write(f"Website: "f"{getattr(library, 'website', 'N/A')}")
    operating_hours = str(getattr(library,"operating_hours","N/A")).replace("~", " - ")
    st.write(f"Operating Hours: "f"{operating_hours}")
    st.write(f"Closed Days: "f"{getattr(library, 'closed_days', 'N/A')}")
    st.write(f"Library Type: "f"{getattr(library, 'library_type', 'N/A')}")

def show_libraries_by_district(district_counts):
    st.subheader("Libraries by District")
    if district_counts is None:
        return
    chart_data = (district_counts.rename("Number of Libraries").reset_index())
    chart = (alt.Chart(chart_data).mark_bar().encode(
            x=alt.X("Number of Libraries:Q",title="Number of Libraries"),
            y=alt.Y("District_Name:N",sort="-x",title="District"),
            tooltip=["District_Name","Number of Libraries"]
        )
        .properties(height=500)
    )
    st.altair_chart(chart,use_container_width=True)

def main():
    df, manager, libraries = load_library_data()
    show_title()
    districts = set(
        str(library.district).strip()
        for library in libraries
        if getattr(library,"district",None)
    )
    total_libraries = get_total_libraries(df)
    total_districts = get_total_districts(df)
    applied_search = (st.session_state.applied_search)
    applied_district = (st.session_state.applied_district)
    filtered_libraries = filter_libraries(libraries,applied_search,applied_district)
    if applied_search:
        total_found_libraries = len(filtered_libraries)
    elif applied_district != "All Districts":
        total_found_libraries = len(filtered_libraries)
    else:
        total_found_libraries = 0
    st.session_state.total_found_libraries = (total_found_libraries)
    show_overview_metrics(total_libraries=total_libraries,total_districts=total_districts,total_found_libraries=total_found_libraries)
    st.divider()
    show_search_area(districts)
    if applied_search:
        if len(filtered_libraries) == 0:
            st.warning("No library found with this name.")
        elif len(filtered_libraries) == 1:
            st.success(f"Found: "f"{filtered_libraries[0].name}")
            st.session_state.selected_library = (filtered_libraries[0])
    elif applied_district != "All Districts":
        st.info(f"Found "f"{len(filtered_libraries)} "f"libraries in "f"{applied_district}.")
    map_data = show_map(filtered_libraries)
    clicked_library = (find_library_from_map_click(libraries,map_data))
    if clicked_library is not None:
        st.session_state.selected_library = (clicked_library)
    show_library_information(st.session_state.selected_library)
    st.divider()
    district_counts = (get_libraries_per_district(df))
    show_libraries_by_district(district_counts)

if __name__ == "__main__":
    main()