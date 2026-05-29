#The below three imports are just to run the file directly in Pathon (not with steamlit)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # adds folder elt_app/elt_app to the search path

import streamlit as st
import pandas as pd
from metadata import MetadataDB



db = MetadataDB()
#print(db.get_connections())

connections = pd.DataFrame(db.get_connections())
add_sidebar = st.sidebar.selectbox('Connections', connections[["name"]])

connections_filt = connections[connections['name'] == add_sidebar]
#connections.columns = ["ID", "Name", "Driver Name"]
#connections = connetions.sort_values(by="ID")[["Name", "Driver Name"]]

st.set_page_config(
    page_title="Connections",
    page_icon="👋",
    # menu_items={
    #     'Get Help': 'https://www.extremelycoolapp.com/help',
    #     'Report a bug': "https://www.extremelycoolapp.com/bug",
    #     'About': "# This is a header. This is an *extremely* cool app!"
    # }
)

st.header('Connections')
st.table(connections_filt)



