import streamlit as st

def sidebar_navigation():
    st.sidebar.title("Navigation")
    
    if st.sidebar.button("Main"):
        st.switch_page("elt_app.py")

    if st.sidebar.button("Platforms"):
        st.switch_page("pages/010_platforms.py")
        
    if st.sidebar.button("Connections"):
        st.switch_page("pages/020_connections.py")
