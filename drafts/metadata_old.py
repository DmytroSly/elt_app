import sqlite3
import json
from importlib import reload
import encryption

#from encryption import cipher

reload(encryption)

DATABASE_NAME = '../elt_app_metadata.db'

# Create metadata tables
def get_table_definition(table_name: str) -> str:
    match table_name:
        case 'platform':
            ddl_create = '''
            CREATE TABLE IF NOT EXISTS platform (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                driver_name TEXT UNIQUE NOT NULL
            )
            '''
        case 'connection':
            ddl_create = '''
            CREATE TABLE IF NOT EXISTS connection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                platform_id INTEGER NOT NULL,
                connection_details NOT NULL,
                credentials TEXT,
                FOREIGN KEY (platform_id) REFERENCES platform(id)
            )
            '''
        case 'pipeline':
            ddl_create = '''
            CREATE TABLE IF NOT EXISTS pipeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                source_id INTEGER NOT NULL,
                destination_id INTEGER NOT NULL,
                description TEXT,
                FOREIGN KEY (source_id) REFERENCES connection(id),
                FOREIGN KEY (destination_id) REFERENCES connection(id)
            )
            '''
        case 'dataset':
            ddl_create = '''
            CREATE TABLE IF NOT EXISTS dataset (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_id INTEGER NOT NULL,
                source_database TEXT NOT NULL,
                source_schema TEXT NOT NULL,
                source_table TEXT NOT NULL,
                destination_database TEXT NOT NULL,
                destination_schema TEXT NOT NULL,
                destination_table TEXT NOT NULL,
                incremental_column TEXT,
                FOREIGN KEY (pipeline_id) REFERENCES pipeline(id)
            )
            '''
        case _:
            ddl_create = None
    return ddl_create

def drop_table(table_name: str, conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute(f'DROP TABLE {table_name}')

def get_db_connection(conn: sqlite3.Connection = None) -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_NAME) if conn is None else conn
    conn.execute("PRAGMA foreign_keys = 1") # enforce foreign key constraints
    return conn    

def create_table(table_name: str, conn: sqlite3.Connection = None, replace_existing: bool = False):
    conn_inn = get_db_connection(conn)
    cursor = conn_inn.cursor()
    ddl = get_table_definition(table_name)
    try:
        if replace_existing:
            drop_table(table_name)   
        cursor.execute(ddl)
        if conn is None:
            conn_inn.commit()
    finally:  
        if conn is None:
            conn_inn.close()
            
def create_metadata_tables(conn: sqlite3.Connection = None):
    conn_inn = get_db_connection(conn)    
    list(map(lambda table: create_table(table, conn_inn),
            ('platform', 'connection', 'pipeline', 'dataset')
        ))
    conn_inn.commit()
    conn_inn.close()

# Add records into metadata tables
def add_metadata_record(table_name: str, insert_values: dict, encrypt_columns: list = [], conn: sqlite3.Connection = None):
    conn_inn = get_db_connection(conn)
    if len(encrypt_columns) > 0:
        for col in encrypt_columns:
            col_json = json.dumps(insert_values[col]) if type(insert_values[col]) is dict else insert_values[col]
            insert_values[col] = encryption.cipher.encrypt(col_json.encode())
    cursor = conn_inn.cursor()
    column_list_str = ','.join(list(insert_values.keys()))
    insert_sql = f'''
        INSERT INTO {table_name} ({column_list_str})
        VALUES ({','.join(list(len(insert_values.keys()) * '?'))})
        '''
    values = tuple(
                map(
                    lambda v: json.dumps(v) if type(v) is dict else v, 
                    insert_values.values()
                )
            )    
    try:
        cursor.execute(insert_sql, (values))
        if conn is None:
            conn_inn.commit()
    finally:
        if conn is None:
            conn_inn.close()
    
# Quering metadata tables
def get_platform_id(name: str, conn: sqlite3.Connection = None) -> int:
    sql = 'SELECT id FROM platform WHERE name = ?'
    result = get_metadata(sql, name, conn=conn)
    return result[0]

def get_platform_name(platform_id: int, conn: sqlite3.Connection = None) -> str:
    sql = 'SELECT name FROM platform WHERE id = ?'
    result = get_metadata(sql, platform_id, conn=conn)
    return result[0]
    
def get_driver_name(platform_name: str, conn: sqlite3.Connection = None) -> str:
    sql = 'SELECT driver_name FROM platform WHERE name = ?'
    result = get_metadata(sql, platform_name, conn=conn)
    return result[0]
            
def get_credentials(connection_name: str, conn: sqlite3.Connection = None) -> str | None:
    sql ='SELECT credentials FROM connection WHERE name = ?'
    result = get_metadata(sql, connection_name, conn=conn)
    if result is not None:
        return encryption.cipher.decrypt(result[0]).decode()

def get_connection_info(connection_name: str, conn: sqlite3.Connection = None) -> str | None:
    sql = 'SELECT connection_details FROM connection WHERE name = ?'
    result = get_metadata(sql, connection_name, conn=conn)
    return result[0]
            
def get_pipeline_connections(pipeline_name: str, conn: sqlite3.Connection = None) -> tuple[str, str] | None:
    sql = '''
            SELECT  c_src.NAME  AS src_connection_name,
                    c_dest.NAME AS dest_connection_name
            FROM   pipeline p
                INNER JOIN connection c_src
                        ON p.source_id = c_src.id
                INNER JOIN connection c_dest
                        ON p.destination_id = c_dest.id
            WHERE  p.NAME = ?                  
        '''
    result = get_metadata(sql, pipeline_name, conn=conn)
    return result[0], result[1]
            
def get_pipeline_id(pipeline_name: str, conn: sqlite3.Connection = None) -> int | None:
    sql = 'SELECT id FROM pipeline WHERE NAME = ?'
    result = get_metadata(sql, pipeline_name, conn=conn)
    return result[0]
            
def get_incremental_column(pipeline_name: str, table_name: str, conn: sqlite3.Connection = None) -> str | None:
    sql = '''
        SELECT d.incremental_column
        FROM   dataset d
            INNER JOIN pipeline p
                    ON d.pipeline_id = p.id
        WHERE   d.destination_table = ?
                AND p.NAME = ?                 
        '''
    result = get_metadata(sql, table_name, pipeline_name, conn=conn)
    return result[0]
    
def get_metadata(sql: str, *sql_parameters, conn: sqlite3.Connection = None) -> tuple | None:
    conn_inn = get_db_connection(conn)
    cursor = conn_inn.cursor()
    try:
        result = cursor.execute(sql, sql_parameters)
        row = result.fetchone()
        if row is not None:
            return row
    finally:
        if conn is None:
            conn_inn.close()
    
if __name__ == "__main__":    
    #create_metadata_tables()
    # print(get_pipeline_connections(pipeline_name="test_pipeline"))    
    #print(get_metadata('select 1 as col1 where 1=? and 1=?', '1', '1'))
    print(get_metadata("select source_database, pipeline_id from dataset where id = ? and source_table = ?", '1', 'customers'))
    print(get_incremental_column(pipeline_name="test_pipeline", table_name="customers"))
    print(get_pipeline_id('test_pipeline'))
    print(get_pipeline_connections('test_pipeline'))
    print(get_connection_info('test postgres connection'))
    print(get_credentials('test postgres connection'))
    print(get_driver_name('postgres'))