import streamlit as st
import app
from services.analyzer import (
    get_total_districts,
    get_total_libraries,
    get_libraries_per_district,
)
from services.data_manager import get_cleaned_library_data
from models.library_manager import LibraryManager
from services.search import (
    filter_by_district,
    find_exact_libraries,
    search_libraries,
)

def main():
    st.set_page_config(page_title="Seoul Public Library Explorer", layout="wide")
    app.show_title()

    try:
        libraries = get_cleaned_library_data()
    except FileNotFoundError:
        st.error("Could not find the library CSV file in the data folder.")
        st.stop()

    library_manager = LibraryManager.from_dataframe(libraries)

    st.session_state.setdefault("applied_name", "")
    st.session_state.setdefault("applied_district", "All districts")
    st.session_state.setdefault("selected_library_id", None)
    st.session_state.setdefault("last_map_click_count", None)
    st.session_state.setdefault("ignore_map_click_once", False)
    st.session_state.setdefault("suggestion_selected", False)

    districts = sorted(libraries["District_Name"].dropna().unique())
    search_column, map_column = st.columns([1, 2])
    app.show_search_panel(search_column, districts, libraries)

    matching_libraries = search_libraries(
        library_manager.get_all(), st.session_state["applied_name"]
    )
    matching_libraries = filter_by_district(
        matching_libraries, st.session_state["applied_district"]
    )

    matching_serial_numbers = {
        str(library.serial_number) for library in matching_libraries
    }
    shown = libraries[
        libraries["Library_Serial_Number"].astype(str).isin(
            matching_serial_numbers
        )
    ]
    if st.session_state["suggestion_selected"]:
        shown = shown[
            shown["Library_Serial_Number"].astype(str)
            == st.session_state["selected_library_id"]
        ]

    app.show_summary(
        get_total_libraries(libraries),
        get_total_districts(libraries),
        len(shown),
    )

    clicked_coordinates, click_count = app.show_map(map_column, shown)
    ignore_old_map_click = st.session_state["ignore_map_click_once"]
    st.session_state["ignore_map_click_once"] = False

    if (
        not ignore_old_map_click
        and click_count is not None
        and click_count != st.session_state["last_map_click_count"]
    ):
        st.session_state["last_map_click_count"] = click_count

        if clicked_coordinates and not shown.empty:
            distances = (
                (shown["Latitude"] - clicked_coordinates["lat"]) ** 2
                + (shown["Longitude"] - clicked_coordinates["lng"]) ** 2
            )
            clicked_row = shown.loc[distances.idxmin()]
            st.session_state["selected_library_id"] = str(
                clicked_row["Library_Serial_Number"]
            )

    selected_id = st.session_state["selected_library_id"]
    selected_rows = (
        shown[shown["Library_Serial_Number"].astype(str) == selected_id]
        if selected_id
        else shown.iloc[0:0]
    )

    if selected_rows.empty and not shown.empty:
        exact_matches = find_exact_libraries(
            shown, st.session_state["applied_name"]
        )
        if len(exact_matches) == 1:
            selected_rows = exact_matches

    if not selected_rows.empty:
        app.show_library_information(selected_rows.iloc[0], search_column)

    app.show_district_chart(get_libraries_per_district(libraries))

if __name__ == "__main__":
    main()