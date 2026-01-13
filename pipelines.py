from importlib import reload
import sys
from pathlib import Path

import dlt
from dlt.destinations import snowflake
from dlt.sources.sql_database import sql_database, sql_table
import json
import sqlite3

import metadata
from metadata import get_pipeline_connections, get_connection_info, get_credentials, get_incremental_column
reload(metadata)

def load_standalone_table(pipeline_name: str, table_name: str, full_refresh: bool = False, conn: sqlite3.Connection = None):
    src_conn, dest_conn = get_pipeline_connections(pipeline_name, conn)
    
    src_conn_info_json = get_connection_info(src_conn)    
    src_creds_json =  get_credentials(src_conn)
    src_conn_full_info = dict(**json.loads(src_conn_info_json), **json.loads(src_creds_json))
    
    dest_conn_info_json = get_connection_info(dest_conn)    
    dest_creds_json =  get_credentials(dest_conn)
    dest_conn_full_info = dict(**json.loads(dest_conn_info_json), **json.loads(dest_creds_json))
    
    pipeline = dlt.pipeline(
        pipeline_name=pipeline_name,
        destination=snowflake(credentials=dest_conn_full_info),
        dataset_name=table_name,
        dev_mode=False,
    )
    
    src_conn_string = f"postgresql+psycopg2://{src_conn_full_info['username']}:{src_conn_full_info['password']}"
    src_conn_string +=f"@{src_conn_full_info['host']}:{src_conn_full_info['port']}/{src_conn_full_info['database']}"
    
    if full_refresh:
        incremental_info =  None
    else:
        incremental_column = get_incremental_column(pipeline_name="test_pipeline", table_name="customers")
        incremental_info = dlt.sources.incremental(cursor_path=incremental_column)
    
    table = sql_table(
        table=table_name,
        credentials=src_conn_string,
        incremental=incremental_info,
        reflection_level="full_with_precision",
        defer_table_reflect=True,
    )
    
    #print(table.compute_table_schema()) #???
    #print(pipeline.default_schema.to_pretty_yaml())???
    
    info = pipeline.run(table, write_disposition="merge")
    print(info)
    
if __name__ == "__main__":    
    print(get_pipeline_connections(pipeline_name="test_pipeline"))
    print(get_incremental_column(pipeline_name="test_pipeline", table_name="customers"))
    load_standalone_table(pipeline_name="test_pipeline", table_name="employees", full_refresh=False)