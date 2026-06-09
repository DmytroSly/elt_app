#The below 3 lines are just to run the file directly in Python (not with steamlit)
import sys
import os
# adds folder elt_app/elt_app to the search path to that modules from the parent folder can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd
from metadata import MetadataDB, Connection
from st_navigation import sidebar_navigation

# TODO: Check @st.dialog - prvent clicking Save when new_key and new_value contains some uncommited text
# TODO: Adding new connection
# TODO: add Back button to the upper left corner


connection_name = st.query_params.get("connection_name")

db = MetadataDB()
connection = db.get_connection(name=connection_name)

platform = connection.platform.__dict__

connection_details = connection.connection_details
credentials = connection.credentials

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
    
def delete_dict_key(details_name_edited, key):
    del st.session_state[details_name_edited][key]
    #st.write('Deleted!')
    
def reset_add_text_boxes():           
    st.session_state.connection_details_new_value = ''
    st.session_state.connection_details_new_key = ''
    st.session_state.credentials_new_value = ''
    st.session_state.credentials_new_key = ''
    
def add_dict_key(details_name_edited, details_edited, key, value):
    if key != '' and value != '':
        st.session_state[details_name_edited][key] = value
        details_edited[key] = value
        reset_add_text_boxes()

def enable_edit_mode():
    st.session_state.edit_mode = True

def cancel_edit_mode():
    st.session_state.edit_mode = False
    st.session_state["connection_name"] = connection.name    
    st.session_state.connection_details_edited = connection.connection_details.copy()
    st.session_state.credentials_edited = connection.credentials.copy()
    for key, value in connection_details.items():
        st.session_state[f"connection_details_value_{key}"] = value
        st.session_state[f"connection_details_key_{key}"] = key
    for key, value in credentials.items():
        st.session_state[f"credentials_value_{key}"] = value
        st.session_state[f"credentials_key_{key}"] = key
    reset_add_text_boxes()
    
def add_editable_details(details_name: str, hide_value: bool = False):
    details_name_edited = f"{details_name}_edited"
    if f"{details_name_edited}" not in st.session_state:
        st.session_state[details_name_edited] = getattr(connection, details_name).copy()        
    details_edited = {}
    for key, value in st.session_state[details_name_edited].items():
        label_col, input_col, button_col = st.columns([1, 3, 0.4])
        with label_col:
            edited_key = st.text_input(
                label=key,
                value=key,
                key=f"{details_name}_key_{key}",
                disabled=not st.session_state.edit_mode,
                label_visibility="collapsed"
            )            
        with input_col:
            edited_value = st.text_input(
                label=key,
                value=value,
                key=f"{details_name}_value_{key}",
                type="password" if hide_value else "default",
                disabled=not st.session_state.edit_mode,
                label_visibility="collapsed"
            )                
        details_edited[edited_key] = edited_value        
        with button_col:
            st.button(
                ":material/delete:",
                key=f"button_col_del_{details_name}_{edited_key}",
                disabled=not st.session_state.edit_mode,
                on_click=delete_dict_key,
                args=(details_name_edited, edited_key,)
            )
    # Adding new key-value pairs to connection details
    with label_col:
            new_key = st.text_input(
                label=key,
                #value=key,
                placeholder='<new key>',
                key=f"{details_name}_new_key",
                disabled=not st.session_state.edit_mode,
                label_visibility="collapsed"
            )            
    with input_col:
            new_value = st.text_input(
                label=key,
                #value=key,
                placeholder='<new value>',
                key=f"{details_name}_new_value",
                type="password" if hide_value else "default",
                disabled=not st.session_state.edit_mode,
                label_visibility="collapsed"
            )            
    with button_col:
        st.button(
            ":material/add:",
            key=f"button_col_add_{details_name}",
            disabled=not st.session_state.edit_mode,
            on_click=add_dict_key,
            args=(details_name_edited, details_edited, new_key, new_value)
        )        
    return details_edited, new_key, new_value
    
@st.dialog("Uncommited changes")
def uncommited_changes():
    st.write(f"Add or remove new key and value before saving or click 'Cancel'")
    if st.button("Got it"):
        st.rerun()
    
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
connection_details_edited, conn_det_new_key, conn_det_new_value = add_editable_details("connection_details")

st.subheader("Credentials")
credentials_edited, creds_new_key, creds_new_value = add_editable_details(details_name="credentials", hide_value=True)
        
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
save_button = right.button(
    "Save",
    use_container_width=True,
    disabled=not st.session_state.edit_mode,
    )

if save_button:
    if conn_det_new_key != '' or conn_det_new_value != '' or creds_new_key != '' or creds_new_value != '':
        uncommited_changes()
        st.stop()        
    st.session_state.edit_mode = False
    connection_edited = Connection(
        name=connection_edited['name'],
        platform=platform,
        connection_details=connection_details_edited,
        credentials=credentials_edited,
        id=connection_edited['id']
    )
    if connection != connection_edited:
        db.update_connection(connection_edited)
        st.query_params["connection_name"] = connection_edited.name
    st.rerun()
