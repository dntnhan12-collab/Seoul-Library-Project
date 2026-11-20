import app
import streamlit as st
from models.library_manager import LibraryManager
from services.analyzer import (get_libraries_per_district, get_total_districts, get_total_libraries,)
from services.data_manager import get_cleaned_library_data
from services.search import (create_library_filters, filter_libraries, find_exact_libraries,)

def main():
    st.set_page_config(
        page_title="Seoul Public Library Explorer", layout="wide"
    )
    app.show_title()

    try:
        libraries = get_cleaned_library_data()
    except FileNotFoundError:
        st.error("Could not find the library CSV file in the data folder.")
        st.stop()

    library_manager = LibraryManager.from_dataframe(libraries)

    state = st.session_state
    state.setdefault("applied_name", "")
    state.setdefault("applied_district", "All districts")
    state.setdefault("selected_library_id", None)
    state.setdefault("map_revision", 0)
    state.setdefault("suggestion_selected", False)

    districts = sorted(libraries["District_Name"].dropna().unique())
    explore_tab, statistics_tab = st.tabs(["Explore", "District statistics"])
    search_column, map_column = explore_tab.columns([1, 3], gap="large")
    app.show_search_panel(search_column, districts, libraries)

    filters = create_library_filters(
        state["applied_name"], state["applied_district"]
    )
    matching_libraries = filter_libraries(
        library_manager.get_all(), filters
    )

    matching_serial_numbers = {
        str(library.serial_number) for library in matching_libraries
    }
    shown = libraries[
        libraries["Library_Serial_Number"].astype(str).isin(
            matching_serial_numbers
        )
    ]
    if state["suggestion_selected"]:
        shown = shown[
            shown["Library_Serial_Number"].astype(str)
            == state["selected_library_id"]
        ]

    search_column.caption(f"{len(shown)} {'library' if len(shown) == 1 else 'libraries'} found")

    selected_id = state["selected_library_id"]
    selected_rows = (
        shown[shown["Library_Serial_Number"].astype(str) == selected_id]
        if selected_id
        else shown.iloc[0:0]
    )
    map_libraries = shown if selected_rows.empty else selected_rows
    map_event = app.show_map(
        map_column, map_libraries, state["map_revision"], state.get("map_view")
    )
    if not selected_rows.empty and map_event.get("last_clicked"):
        app.clear_suggestion_choice()
        state["map_view"] = {"center": map_event["center"], "zoom": map_event["zoom"]}
        state["map_revision"] += 1
        st.rerun()

    clicked_coordinates = map_event.get("last_object_clicked")
    if clicked_coordinates and selected_rows.empty and not shown.empty:
        candidates = shown[
            (shown["Latitude"] == clicked_coordinates["lat"])
            & (shown["Longitude"] == clicked_coordinates["lng"])
        ]
        clicked_name = map_event.get("last_object_clicked_tooltip")
        if clicked_name:
            candidates = candidates[candidates["Library_Name"].str.strip() == clicked_name]
        if not candidates.empty:
            clicked_row = candidates.iloc[0]
            state["selected_library_id"] = str(clicked_row["Library_Serial_Number"])
            state["map_view"] = {"center": map_event["center"], "zoom": map_event["zoom"]}
            state["map_revision"] += 1
            st.rerun()

    if selected_rows.empty and not shown.empty:
        exact_matches = find_exact_libraries(shown, state["applied_name"])
        if len(exact_matches) == 1:
            selected_rows = exact_matches

    if not selected_rows.empty:
        app.show_library_information(selected_rows.iloc[0], search_column)

    with statistics_tab:
        app.show_summary(get_total_libraries(libraries), get_total_districts(libraries))
        app.show_district_chart(get_libraries_per_district(libraries))


if __name__ == "__main__":
    main()
