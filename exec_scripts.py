import metadata
from metadata import add_metadata_record, get_pipeline_id
from importlib import reload

import dlt
from dlt.destinations import snowflake
from dlt.sources.sql_database import sql_database, sql_table, Table
from dlt.sources.credentials import ConnectionStringCredentials

import sqlite3
import json


reload(metadata)

dataset_record = dict(
    pipeline_id=metadata.get_pipeline_id('test_pipeline'),
    source_database='db_source_for_dlt',
    source_schema='public',
    source_table='employees',
    destination_database='hub_speak_dmytro_base',
    destination_schema='postgres_data',
    destination_table='employees',
    incremental_column='updated'
)

metadata.add_metadata_record(
    table_name='dataset',
    insert_values=dataset_record
)


# TODO next steps:
#   - Add a pipeline filesystem - Snowflake
#   - Loading progress https://dlthub.com/docs/general-usage/pipeline

# - Test schema evolution
# - Test re-runs
# - Start working on CLI to add connections, pipelines, and datasets
#   - Accepting user input with input()  

# Needed skills:
    # - error handling in Python.
        # Read errors from database and return human readable message
    # - Modules
    # - REPL
    
# Run IDLE from a Python virtual environment
# Start the virtual environment
# Run python -m idlelib.idle
# https://stackoverflow.com/questions/4924068/how-to-launch-python-idle-from-a-virtual-environment-virtualenv
