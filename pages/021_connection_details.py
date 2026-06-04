#The below 3 lines are just to run the file directly in Python (not with steamlit)
import sys
import os
# adds folder elt_app/elt_app to the search path to that modules from the parent folder can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd
from metadata import MetadataDB, Connection
from st_navigation import sidebar_navigation

# TODO: add Back button to the upper left corner
# TODO: test changes to connection details
# TODO: delete/add fields to connetion details 

connection_name = st.query_params.get("connection_name")

db = MetadataDB()
connection = db.get_connection(name=connection_name)

platform = connection.platform.__dict__

connection_details = connection.connection_details

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

def enable_edit_mode():
    st.session_state.edit_mode = True

def cancel_edit_mode():
    st.session_state.edit_mode = False
    st.session_state["connection_name"] = connection.name
    
    for key, value in connection_details.items():
        st.session_state[f"connection_details_value_{key}"] = value
        st.session_state[f"connection_details_key_{key}"] = key

sidebar_navigation()

st.header(connection_name or "Connection Details")
# Connection name and id
connection_edited = {}
for key in ["id", "name"]:
    label_col, input_col = st.columns([1, 3])
    
    with label_col:
        #st.write(key) # with st.write the text is a bit higher than the text in the text box
        st.markdown(
            f"<div style='padding-top: 8px'>{key.title()}</div>",
            unsafe_allow_html=True
        )
    
    disabled = True if key == 'id' else not st.session_state.edit_mode
    with input_col:
        connection_edited[key] = st.text_input(
            label=key,
            value=getattr(connection, key),
            key=f"connection_{key}",
            disabled=disabled,
            label_visibility="collapsed"
        )  

st.subheader("Platform")
for key, value in platform.items():
    label_col, input_col = st.columns([1, 3])
    with label_col:
        #st.write(key) # with st.write the text is a bit higher than the text in the text box
        st.markdown(
            f"<div style='padding-top: 8px'>{key.title().replace('_', ' ')}</div>",
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

connection_details_edited = {}
keys_to_del = []
for key, value in connection_details.items():
    label_col, input_col = st.columns([1, 3])
    with label_col:
        #st.write(key) # with st.write the text is a bit higher than the text in the text box
        # st.markdown(
        #     f"<div style='padding-top: 8px'>{key.title().replace('_', ' ')}</div>",
        #     unsafe_allow_html=True
        # )
        edited_key = st.text_input(
            label=key,
            value=key,
            key=f"connection_details_key_{key}",
            disabled=not st.session_state.edit_mode,
            label_visibility="collapsed"
        )
        connection_details_edited[edited_key] = connection_details[key]
        if edited_key != key:
            keys_to_del.append(key)
        
        with input_col:
            connection_details_edited[key] = st.text_input(
                label=key,
                value=value,
                key=f"connection_details_value_{key}",
                disabled=not st.session_state.edit_mode,
                label_visibility="collapsed"
            )
        
for key in keys_to_del:
    del connection_details_edited[key]

left, middle, right, _ = st.columns([1, 1, 1, 4], vertical_alignment="bottom")
edit_button = left.button(
    "Edit",
    use_container_width=True,
    disabled=st.session_state.edit_mode,
    on_click=enable_edit_mode
)
cancel_button = middle.button(
    "Cancel",
    use_container_width=True,
    disabled=not st.session_state.edit_mode,
    on_click=cancel_edit_mode
)
save_button = right.button("Save", use_container_width=True, disabled=not st.session_state.edit_mode)

if save_button:
    st.session_state.edit_mode = False
    connection_edited = Connection(
        name=connection_edited['name'],
        platform=platform,
        connection_details=connection_details_edited,
        credentials=connection.credentials,
        id=connection_edited['id']
    )
    db.update_connection(connection_edited)
    st.query_params["connection_name"] = connection_edited.name
    st.rerun()
