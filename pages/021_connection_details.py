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
platform["Name"] = platform.pop("name")
platform["Driver Name"] = platform.pop("driver_name")
platform["ID"] = platform.pop("id")
#platform = dict(sorted(platform.items()))

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
sidebar_navigation()

st.header(connection_name or "Connection Details")

st.subheader("Platform")
st.table(data=platform,
         border="horizontal",
         width="content"
         )

if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

platform_edited = {}
for key, value in platform.items():
    platform_edited[key] = st.text_input(label=key, value=value, disabled=not st.session_state.edit_mode)

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
 
st.subheader("Platform edited")
st.table(data=platform_edited,
         border="horizontal",
         width="content"
         )   

st.subheader("Connectiion details")
st.table(data=connection_details_col_names,
         border="horizontal",
         width="content"
         )