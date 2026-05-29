import streamlit as st
import pandas as pd
from metadata import MetadataDB



db = MetadataDB()
platforms = pd.DataFrame(db.get_platforms())
platforms.columns = ["ID", "Name", "Driver Name"]
platforms = platforms.sort_values(by="ID")[["Name", "Driver Name"]]

st.set_page_config(
    page_title="Platforms",
    page_icon="👋",
    # menu_items={
    #     'Get Help': 'https://www.extremelycoolapp.com/help',
    #     'Report a bug': "https://www.extremelycoolapp.com/bug",
    #     'About': "# This is a header. This is an *extremely* cool app!"
    # }
)

st.header('Platforms')
st.table(platforms)

