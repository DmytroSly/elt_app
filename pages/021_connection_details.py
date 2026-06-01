#The below 3 lines are just to run the file directly in Python (not with steamlit)
import sys
import os
# adds folder elt_app/elt_app to the search path to that modules from the parent folder can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd
from metadata import MetadataDB
from st_navigation import sidebar_navigation

connection_name = st.query_params.get("connection_name", "")

db = MetadataDB()
connection = db.get_connection(name=connection_name)

platform = connection.platform.__dict__
platform_col_names = {}
for key in platform.keys():
    platform_col_names[key.title().replace('_', ' ')] = platform[key]

connection_details = connection.connection_details
connection_details_col_names = {}
for key in connection_details.keys():
    connection_details_col_names[key.title().replace('_', ' ')] = connection_details[key]

st.set_page_config(
    page_title=connection_name or "Connection Details",
    page_icon="👋",
    # menu_items={
    #     'Get Help': 'https://www.extremelycoolapp.com/help',
    #     'Report a bug': "https://www.extremelycoolapp.com/bug",
    #     'About': "# This is a header. This is an *extremely* cool app!"
    # }
)

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False
sidebar_navigation()

st.header(connection_name or "Connection Details")

st.subheader("Platform")
for key, value in platform_col_names.items():
    label_col, input_col = st.columns([1, 3])
    with label_col:
        #st.write(key) # with st.write the text is a bit higher than the text in the text box
        st.markdown(
            f"<div style='padding-top: 8px'>{key}</div>",
            unsafe_allow_html=True
        )
    with input_col:
        platform[key] = st.text_input(
            label=key,
            value=value,
            key=f"platform_{key}",
            disabled=True,
            label_visibility="collapsed"
        )  

st.subheader("Connection details")

connecton_edited = {}
for key, value in connection_details_col_names.items():
    label_col, input_col = st.columns([1, 3])
    with label_col:
        #st.write(key) # with st.write the text is a bit higher than the text in the text box
        st.markdown(
            f"<div style='padding-top: 8px'>{key}</div>",
            unsafe_allow_html=True
        )
        with input_col:
            connecton_edited[key] = st.text_input(
                label=key,
                value=value,
                key=f"platform_{key}",
                disabled=not st.session_state.edit_mode,
                label_visibility="collapsed"
            )

left, middle, right, _ = st.columns([1, 1, 1, 4], vertical_alignment="bottom")
edit_button = left.button("Edit", use_container_width=True)
cancel_button = middle.button("Cancel", use_container_width=True)
save_button = right.button("Save", use_container_width=True)

if edit_button:
    st.session_state.edit_mode = True
    st.rerun()
    
if cancel_button:
    st.session_state.edit_mode = False
    st.rerun()
 
    
if save_button:
    st.session_state.edit_mode = False
    # TODO: write changes to the database
    st.rerun()