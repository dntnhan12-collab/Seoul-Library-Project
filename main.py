import app
import streamlit as st
from models.library_manager import LibraryManager
from models.library import Library
from services.analyzer import (get_libraries_per_district, get_total_districts, get_total_libraries,)
from services.data_manager import get_cleaned_library_data
from services.contracts import LibraryDataSource
from services.data_sources import CsvLibraryDataSource
from services.search import (create_library_filters, filter_libraries, find_exact_libraries,)

def main(data_source: LibraryDataSource):
    st.set_page_config(
        page_title="Seoul Public Library Explorer", layout="wide"
    )
    app.show_title()

    try:
        libraries = get_cleaned_library_data(data_source)
    except (OSError, ValueError):
        st.error("Could not load the library data.")
        st.stop()

    library_manager = LibraryManager.from_dataframe(libraries)

    state = st.session_state
    state.setdefault("applied_name", "")
    state.setdefault("applied_district", "All districts")
    state.setdefault("selected_library_id", None)
    state.setdefault("last_map_click_count", None)
    state.setdefault("ignore_map_click_once", False)
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

    # Focus the route view on its destination; retain search results for browsing.
    map_libraries = selected_rows if route is not None else shown
    map_result = app.show_map(map_area, map_libraries, route)
    clicked_coordinates = map_result.get("last_object_clicked")
    click_count = map_result.get("last_object_clicked_count")
    ignore_old_map_click = state["ignore_map_click_once"]
    state["ignore_map_click_once"] = False

    if (
        not ignore_old_map_click
        and click_count is not None
        and click_count != state["last_map_click_count"]
    ):
        state["last_map_click_count"] = click_count

        if clicked_coordinates and not shown.empty:
            # The user marker must not select a library.
            clicked_rows = shown[
                (shown["Latitude"] - clicked_coordinates["lat"]).abs().lt(0.000001)
                & (shown["Longitude"] - clicked_coordinates["lng"]).abs().lt(0.000001)
            ]
            if not clicked_rows.empty:
                state["selected_library_id"] = str(clicked_rows.iloc[0]["Library_Serial_Number"])
                app.clear_route()
                st.rerun()

    app.show_district_chart(get_libraries_per_district(libraries))


if __name__ == "__main__":
    # Compose the app here; its processing depends only on LibraryDataSource.
    main(CsvLibraryDataSource())
