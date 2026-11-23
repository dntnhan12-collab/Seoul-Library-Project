import app
import streamlit as st
from models.library_manager import LibraryManager
from models.library import Library
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
    state.setdefault("map_marker_focused", False)
    state.setdefault("map_revision", 0)
    state.setdefault("suggestion_selected", False)

    districts = sorted(libraries["District_Name"].dropna().unique())
    search_column, map_column = st.columns([1, 2])
    with map_column:
        map_area = st.container()
        directions_area = st.container()
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

    app.show_summary(
        get_total_libraries(libraries),
        get_total_districts(libraries),
        len(shown),
    )

    selected_id = state["selected_library_id"]
    selected_rows = (
        shown[shown["Library_Serial_Number"].astype(str) == selected_id]
        if selected_id else shown.iloc[0:0]
    )
    if selected_rows.empty and not shown.empty:
        exact_matches = find_exact_libraries(shown, state["applied_name"])
        if len(exact_matches) == 1:
            selected_rows = exact_matches

    route = None
    if not selected_rows.empty:
        app.show_library_information(selected_rows.iloc[0], search_column)
        with directions_area:
            route = app.show_directions(Library.from_row(selected_rows.iloc[0]))
    else:
        app.clear_route()

    focused = state["map_marker_focused"]
    map_libraries = selected_rows if focused else shown
    map_result = app.show_map(
        map_area, map_libraries, route, revision=state["map_revision"], view=state.get("map_view")
    )
    if focused and map_result.get("last_clicked"):
        state["map_marker_focused"] = False
        state["map_view"] = {"center": map_result["center"], "zoom": map_result["zoom"]}
        state["map_revision"] += 1
        st.rerun()

    clicked_coordinates = map_result.get("last_object_clicked")
    if not focused and clicked_coordinates:
        clicked_name = map_result.get("last_object_clicked_tooltip")
        clicked_rows = shown[
            (shown["Latitude"] - clicked_coordinates["lat"]).abs().lt(0.000001)
            & (shown["Longitude"] - clicked_coordinates["lng"]).abs().lt(0.000001)
            & (shown["Library_Name"].str.strip() == clicked_name)
        ]
        if not clicked_rows.empty:
            clicked_id = str(clicked_rows.iloc[0]["Library_Serial_Number"])
            if clicked_id != selected_id:
                app.clear_route()
            state["selected_library_id"] = clicked_id
            state["map_marker_focused"] = True
            state["map_view"] = {"center": map_result["center"], "zoom": map_result["zoom"]}
            state["map_revision"] += 1
            st.rerun()

    app.show_district_chart(get_libraries_per_district(libraries))


if __name__ == "__main__":
    main()
