import altair as alt
import folium
import streamlit as st
from streamlit_folium import st_folium
from models.library import Library

def clear_search():
    st.session_state["search_name"] = ""
    st.session_state["search_district"] = "All districts"
    _set_applied_search("", "All districts")
    st.session_state["_search_needs_full_rerun"] = True


def _set_applied_search(name, district, library_id=None, is_suggestion=False):
    st.session_state["applied_name"] = name
    st.session_state["applied_district"] = district
    st.session_state["selected_library_id"] = library_id
    st.session_state["suggestion_selected"] = is_suggestion
    st.session_state["ignore_map_click_once"] = True
def apply_search():
    _set_applied_search(
        st.session_state.get("search_name", "").strip(),
        st.session_state.get("search_district", "All districts"),
    )
    st.session_state["_search_needs_full_rerun"] = True


def clear_suggestion_choice():
    st.session_state["selected_library_id"] = None
    st.session_state["suggestion_selected"] = False

def show_title():
    st.markdown(
        '<h1 style="text-align:center; color:#6F1D1B; font-size:3.5rem; '
        'font-weight:800; line-height:1.15; letter-spacing:0.02em; '
        'margin:0.25rem 0 1.5rem;">Seoul Public Library Explorer</h1>',
        unsafe_allow_html=True,
    )
@st.fragment
def show_search_panel(container, districts, libraries):
    with container:
        st.subheader("Library Search")
        name = st.text_input(
            "Search by name",
            key="search_name",
            on_change=clear_suggestion_choice,
            placeholder="Type a library name...",
            live=True,
        )
        keyword = name.strip()
        if keyword and not st.session_state.get("suggestion_selected", False):
            suggestions = libraries
            selected_district = st.session_state.get(
                "search_district", "All districts"
            )
            if selected_district != "All districts":
                suggestions = suggestions[
                    suggestions["District_Name"] == selected_district
                ]

            names = suggestions["Library_Name"].fillna("").astype(str)
            suggestions = suggestions[
                names.str.contains(keyword, case=False, regex=False)
            ].sort_values("Library_Name")

            if suggestions.empty:
                st.caption("No matching libraries found.")
            else:
                with st.container(height=150, border=False):
                    for _, row in suggestions.head(5).iterrows():
                        serial = str(row["Library_Serial_Number"])
                        label = f"{row['Library_Name']} — {row['District_Name']}"
                        if st.button(
                            label,
                            key=f"library_suggestion_{serial}",
                            type="tertiary",
                            width="content",
                        ):
                            _set_applied_search(
                                str(row["Library_Name"]),
                                str(row["District_Name"]),
                                serial,
                                is_suggestion=True,
                            )
                            st.rerun()

        st.selectbox(
            "District",
            ["All districts"] + districts,
            key="search_district",
            on_change=clear_suggestion_choice,
        )

        find_column, reset_column = st.columns(2)
        find_column.button(
            "Find",
            type="primary",
            width="stretch",
            on_click=apply_search,
        )
        reset_column.button(
            "Reset",
            on_click=clear_search,
            width="stretch",
        )

    if st.session_state.pop("_search_needs_full_rerun", False):
        st.rerun()
def show_summary(total_libraries, total_districts, found_count):
    total_column, district_column, found_column = st.columns(3)
    total_column.metric("Total libraries", total_libraries)
    district_column.metric("Districts", total_districts)
    found_column.metric("Libraries found", found_count)

def show_map(container, libraries):
    with container:
        st.subheader("Library Map")

        if libraries.empty:
            st.info("No libraries match the search. Try another name or district.")

        if not libraries.empty:
            center = [libraries["Latitude"].mean(), libraries["Longitude"].mean()]
        else:
            center = [38, 127]

        zoom = 14 if len(libraries) == 1 else 11
        library_map = folium.Map(location=center, zoom_start=zoom)
        folium.plugins.LocateControl(
            position="topleft",
            auto_start=False,
        ).add_to(library_map)

        for _, row in libraries.iterrows():
            folium.Marker(
                location=[row["Latitude"], row["Longitude"]],
                tooltip=row["Library_Name"],
                icon=folium.Icon(color="darkred"),
            ).add_to(library_map)

        result = st_folium(
            library_map,
            height=500,
            use_container_width=True,
            returned_objects=["last_object_clicked", "last_object_clicked_count"],
            key="library_map",
        )

    if result:
        return (
            result.get("last_object_clicked"),
            result.get("last_object_clicked_count"),
        )
    return None, None
def show_library_information(row, container):
    library = Library.from_row(row)
    with container:
        with st.container(border=True):
            st.subheader("Library Information")
            st.markdown(f"### {library.name}")
            st.table(library.details())

def show_district_chart(counts):
    st.subheader("Libraries by District")
    chart_data = counts.rename_axis("District").reset_index(name="Libraries")
    largest_count = int(chart_data["Libraries"].max())

    chart = (
        alt.Chart(chart_data)
        .mark_bar(color="#BB9457")
        .encode(
            x=alt.X(
                "Libraries:Q",
                title="Number of libraries",
                scale=alt.Scale(domain=[0, largest_count + 1], nice=False),
                axis=alt.Axis(format="d", tickMinStep=1),
            ),
            y=alt.Y("District:N", title=None, sort="-x"),
            tooltip=["District:N", "Libraries:Q"],
        )
        .properties(height=700)
    )

    st.altair_chart(chart, width="stretch")