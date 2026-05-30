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

selected_connection = st.query_params.get("connection")
connection_names = connections["name"].tolist()

if selected_connection not in connection_names:
    selected_connection = connection_names[0] if connection_names else None

add_sidebar = st.sidebar.selectbox(
    "Connections",
    connection_names,
    index=connection_names.index(selected_connection) if selected_connection else None,
)

connections_filt = connections[connections["name"] == add_sidebar]
#connections.columns = ["ID", "Name", "Driver Name"]
#connections = connetions.sort_values(by="ID")[["Name", "Driver Name"]]

connections_display = connections_filt.copy()
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
