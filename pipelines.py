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

def get_destnation_connection_info(dest_connection_name: str, conn: sqlite3.Connection = None):
    dest_conn_info_json = get_connection_info(dest_connection_name, conn)    
    dest_creds_json =  get_credentials(dest_connection_name, conn)
    dest_conn_full_info = dict(**json.loads(dest_conn_info_json), **json.loads(dest_creds_json))
    return dest_conn_full_info

def get_source_connection_string(source_connection_name: str, conn: sqlite3.Connection = None):
    src_conn_info_json = get_connection_info(source_connection_name, conn)    
    src_creds_json =  get_credentials(source_connection_name, conn)
    src_conn_full_info = dict(**json.loads(src_conn_info_json), **json.loads(src_creds_json))    
    src_conn_string = f"postgresql+psycopg2://{src_conn_full_info['username']}:{src_conn_full_info['password']}"
    src_conn_string +=f"@{src_conn_full_info['host']}:{src_conn_full_info['port']}/{src_conn_full_info['database']}"    
    return src_conn_string

def load_standalone_table(pipeline_name: str, table_name: str, full_refresh: bool = False, conn: sqlite3.Connection = None):
    src_conn, dest_conn = get_pipeline_connections(pipeline_name, conn)    
    dest_conn_full_info = get_destnation_connection_info(dest_conn, conn)    
    src_conn_string = get_source_connection_string(src_conn, conn)
    
    pipeline = dlt.pipeline(
        pipeline_name=pipeline_name,
        destination=snowflake(credentials=dest_conn_full_info),
        dataset_name=pipeline_name,
        dev_mode=False,
    )  
    
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
    
def load_set_of_tables(pipeline_name: str, table_list: list, full_refresh: bool = False, conn: sqlite3.Connection = None):
    src_conn, dest_conn = get_pipeline_connections(pipeline_name, conn)    
    dest_conn_full_info = get_destnation_connection_info(dest_conn, conn)    
    src_conn_string = get_source_connection_string(src_conn, conn)
    
    pipeline = dlt.pipeline(
        pipeline_name=pipeline_name,
        destination=snowflake(credentials=dest_conn_full_info),
        dataset_name=pipeline_name,
        dev_mode=False,
    )
    
    source_tables = sql_database(
        credentials=src_conn_string,
        reflection_level="full_with_precision" #?
    ).with_resources(*table_list)
    
    if full_refresh:
        for table in table_list:
            incremental_column = get_incremental_column(pipeline_name=pipeline_name, table_name=table)
            incremental_info = dlt.sources.incremental(cursor_path=incremental_column)
            getattr(source_tables, table).apply_hints(incremental=incremental_info)
        
    info = pipeline.run(source_tables, write_disposition="merge")
    print(info)
    
if __name__ == "__main__":    
    print(get_pipeline_connections(pipeline_name="test_pipeline"))
    print(get_incremental_column(pipeline_name="test_pipeline", table_name="customers"))
    #load_standalone_table(pipeline_name="test_pipeline", table_name="employees", full_refresh=False)
    #load_standalone_table(pipeline_name="test_pipeline", table_name="customers", full_refresh=False)
    load_set_of_tables(pipeline_name="test_pipeline", table_list=["customers", "employees"], full_refresh=False)