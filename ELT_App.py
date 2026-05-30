import streamlit as st
from st_navigation import sidebar_navigation

st.set_page_config(
    page_title="ELT App",
    page_icon="👋",
    # menu_items={
    #     'Get Help': 'https://www.extremelycoolapp.com/help',
    #     'Report a bug': "https://www.extremelycoolapp.com/bug",
    #     'About': "# This is a header. This is an *extremely* cool app!"
    # }
)

st.title("ELT App") 
st.write('Hello!')

sidebar_navigation()


