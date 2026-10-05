<<<<<<< ours
import streamlit as st
st.set_page_config(page_title="Seoul Public Library Explorer", page_icon="📚", layout="wide")
st.title("Seoul Public Library Explorer")
col1, col2 = st.columns(2)
with col1:
    st.metric("Total Libraries", 0)
with col2:
    st.metric("Districts", 0)
st.divider()
search_col, map_col = st.columns([1, 2])

with search_col:
    st.subheader("Library Search")

    st.text_input("Search by name")

    st.selectbox(
        "District",
        ["All Districts"]
    )

    find_col, reset_col = st.columns(2)

    with find_col:
        st.button("Find")

    with reset_col:
        st.button("Reset")


with map_col:
    st.subheader("Library Map")

    st.info("Library locations will be displayed here.")

st.divider()

st.subheader("Libraries by District")

st.info("The library distribution by district will be displayed here.")
=======
import altair as alt
import folium
import streamlit as st
from folium.plugins import LocateControl
from streamlit_folium import st_folium
from models.library import Library
>>>>>>> theirs
