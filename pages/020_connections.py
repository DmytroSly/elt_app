#The below 3 lines are just to run the file directly in Python (not with steamlit)
import sys
import os
# adds folder elt_app/elt_app to the search path to that modules from the parent folder can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd
from html import escape
from urllib.parse import quote
from metadata import MetadataDB
from st_navigation import sidebar_navigation

db = MetadataDB()
connections = pd.DataFrame(db.get_connections())

st.set_page_config(
    page_title="Connections",
    page_icon="👋",
    # menu_items={
    #     'Get Help': 'https://www.extremelycoolapp.com/help',
    #     'Report a bug': "https://www.extremelycoolapp.com/bug",
    #     'About': "# This is a header. This is an *extremely* cool app!"
    # }
)
sidebar_navigation()

# Remove sidebar from here later
# connection_names = connections["name"].sort_values()
# add_sidebar = st.sidebar.selectbox(
#     "Connections",
#     connection_names
# )

#connections_filt = connections[connections["name"] == add_sidebar]
#connections.columns = ["ID", "Name", "Driver Name"]
#connections = connetions.sort_values(by="ID")[["Name", "Driver Name"]]

connections_display = connections.copy()
connections_display["name"] = connections_display["name"].apply(
    lambda name: (
        f'<a href="/connection_details?connection_name={quote(name)}" target="_self">'
        f'{escape(name)}</a>'
    )
)

st.header('Connections')
st.markdown(
    """
    <style>
        .connections-table th:nth-child(5),
        .connections-table td:nth-child(5) {
            max-width: 180px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    connections_display.to_html(
        classes="connections-table",
        escape=False,
        index=False,
    ),
    unsafe_allow_html=True,
)

new_connection = st.button("Add connection")
if new_connection:
    st.session_state.connection_details_edited = {}
    st.session_state.credentials_edited = {}
    st.session_state.connection_name_error = False
    st.session_state.connection_details_error = False
    st.switch_page("pages/021_connection_details.py", query_params={'connection_name': f'{escape("New connection")}'})