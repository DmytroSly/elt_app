
# dataclasses
# https://stackoverflow.com/questions/47955263/what-are-data-classes-and-how-are-they-different-from-common-classes
# https://peps.python.org/pep-0557/
from dataclasses import dataclass, field

from typing import Optional, Dict, Any
# https://docs.python.org/3/library/typing.html

import sqlite3
import json

import encryption

DATABASE_PATH = '../elt_app_metadata.db'

@dataclass
class Platform:
    name: str
    driver_name: str
    id: Optional[int] = field(default=None) # or Union[int, None] or int | None without an import
    
@dataclass
class Connection:
    name: str
    platform: Platform
    connection_details: Dict[str, Any] # or dict[str, any] without an import
    credentials: Dict[str, Any] = field(repr=False) # or dict[str, any] without an import # repr=False not include into the print output
    id: Optional[int] = field(default=None)
    
@dataclass
class Pipeline:
    name: str
    source: Connection
    destination: Connection
    description: str
    id:  Optional[int] = field(default=None)
    
@dataclass
class Dataset:
    name: str
    pipeline: Pipeline
    source_table: Optional[str] = field(default=None)
    source_database: Optional[str] = field(default=None)
    source_schema: Optional[str] = field(default=None)
    destination_database: Optional[str] = field(default=None)
    destination_table: Optional[str] = field(default=None)
    incremental_column: Optional[str] = field(default=None)
    id: Optional[int] = field(default=None)
    
    def __post_init__(self):
        if self.source_table is None:
            self.source_table = self.name
        if self.destination_table is None:
            self.destination_table = self.name
            
class MetadataDB():
    def __init__(self, replace_existing_meta: bool = False, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._create_metadata_tables(replace_existing=replace_existing_meta)
        
    def _get_db_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = 1")
        return conn
    
    def _get_table_definition(table_name: str) -> str:
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
                    credentials TEXT NOT NULL,
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
                    name TEXT NOT NULL,
                    pipeline_id INTEGER NOT NULL,
                    source_database TEXT,
                    source_schema TEXT,
                    source_table TEXT,
                    destination_database TEXT,
                    destination_table TEXT,
                    incremental_column,
                    FOREIGN KEY (pipeline_id) REFERENCES pipeline(id)
                )
                '''
            case _:
                ddl_create = None
        return ddl_create
    
    def _create_table(self, table_name: str, conn: sqlite3.Connection, replace_existing: bool = False):
        conn = self._get_db_connection()
        cursor = conn.cursor()
        ddl = MetadataDB._get_table_definition(table_name)        
        if replace_existing:
            cursor = conn.cursor()
            cursor.execute(f'DROP TABLE {table_name}')            
        cursor.execute(ddl)
    
    def _create_metadata_tables(self, replace_existing):
        # TODO: Check if tables exist
        conn = self._get_db_connection()    
        list(map(lambda table: self._create_table(table, conn, replace_existing),
                ('platform', 'connection', 'pipeline', 'dataset')
            ))
        conn.commit()
        conn.close()
    
    def _add_metadata_record(self, table_name: str, insert_values: dict, encrypt_columns: list = []) -> int:
        # TODO: Close connection in the main method
        conn = self._get_db_connection()
        if len(encrypt_columns) > 0:
            for col in encrypt_columns:
                col_json = json.dumps(insert_values[col]) if type(insert_values[col]) is dict else insert_values[col]
                insert_values[col] = encryption.cipher.encrypt(col_json.encode())
        cursor = conn.cursor()
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
        cursor.execute(insert_sql, (values))
        conn.commit()
        conn.close() # ask Copilot for sugestions on how to close connection with a class
        return cursor.lastrowid
    
    def _get_metadata(self, sql: str, *sql_parameters) -> tuple | None:
        # TODO: Close connection in the main method
        conn = self._get_db_connection()
        cursor = conn.cursor()
        result = cursor.execute(sql, sql_parameters)
        row = result.fetchone()
        conn.close() # ask Copilot for sugestions on how to close connection with a class
        if row is not None:
            return row
    
    def add_platform(self, platform: Platform) -> int:
        insert_values = dict(name=platform.name, driver_name=platform.driver_name)
        platform_id = self._add_metadata_record('platform', insert_values)
        return platform_id        
    
    def add_connection(self, connection: Connection) -> int:
        insert_values = dict(
            name=connection.name,
            platform_id=connection.platform.id,
            connection_details=connection.connection_details,
            credentials=connection.credentials
        )
        connection_id = self._add_metadata_record(
                table_name='connection',
                insert_values=insert_values,
                encrypt_columns=['credentials']
            )
        return connection_id
    
    def _get_entity(self, table, column_list: list, id: int | None = None, name: str | None = None)  -> tuple | None:
        if id is None and name is None:
            raise ValueError("Either 'name' or 'id' must be provded")
        if id is not None and name is not None:
            raise ValueError("Only one of 'name' or 'id' should be provded")
        columns_str = ', '.join(column_list)
        sql = f'SELECT {columns_str} FROM {table} WHERE '
        if id is not None:
            sql += 'id = ?'
            param = id
        else:
            sql += 'name = ?'
            param = name
        entity = self._get_metadata(sql, param)
        if entity is not None:
            return entity
    
    def get_platform(self, *, id: int | None = None, name: str | None = None) -> Platform:
            column_list = ['id', 'name', 'driver_name']  
            platform = self._get_entity('platform', column_list, id=id, name=name)
            return Platform(id=platform[0], name=platform[1], driver_name=platform[2])
    
    def get_connection(self, *, id: int | None = None, name: str | None = None) -> Connection:
        column_list = ['id', 'name', 'platform_id', 'connection_details', 'credentials']
        connection = self._get_entity('connection', column_list, id=id, name=name)
        platform = self.get_platform(id=connection[2])
        cretentials = json.loads(encryption.cipher.decrypt(connection[4]).decode())
        return Connection(
                id=connection[0],
                name=connection[1],
                platform=platform,
                connection_details=json.loads(connection[3]),
                credentials=cretentials
            )
    
    def get_pipeline(self, *, id: int | None = None, name: str | None = None) -> Pipeline:
        column_list = ['id', 'name', 'source_id', 'destination_id', 'description']
        pipeline = self._get_entity('pipeline', column_list, id=id, name=name)
        if not pipeline:
            return None
        source_conn = self.get_connection(id=pipeline[2])
        dest_conn = self.get_connection(id=pipeline[3])
        return Pipeline (
            id=pipeline[0],
            name=pipeline[1],
            source=source_conn,
            destination=dest_conn,
            description=pipeline[4]
        )
        
    def add_pipeline(self, pipeline: Pipeline ) -> int:
        insert_values = dict(
            name=pipeline.name,
            source_id=pipeline.source.id,
            destination_id=pipeline.destination.id,
            description=pipeline.description
        )
        pipeline_id = self._add_metadata_record(
                table_name='pipeline',
                insert_values=insert_values
            )
        return pipeline_id
    
    def add_dataset(self, dataset: Dataset) -> int:
        insert_values = dict(
            name=dataset.name,
            source_table=dataset.source_table,
            pipeline_id=dataset.pipeline.id,
            source_database=dataset.source_database,
            source_schema=dataset.source_schema,            
            destination_database=dataset.destination_database,
            destination_table=dataset.destination_table,
            incremental_column=dataset.incremental_column
        )
        dataset_id = self._add_metadata_record(
                table_name='dataset',
                insert_values=insert_values
            )
        return dataset_id
    
    def get_dataset(self, *, id: int | None = None, name: str | None = None) -> Dataset:
        # Pipeline name or id should be also passed as an argument if dataset name is not unique
        # Consider making dataset name unuque or introduce a pipeline argument
        column_list = [
            'id', 'name', 'pipeline_id', 'source_database', 'source_schema',
            'source_table', 'destination_database', 'destination_table',
            'incremental_column'
        ]
        dataset = self._get_entity('dataset', column_list, id=id, name=name)
        if dataset:
            pipeline = self.get_pipeline(id=dataset[2])
            return Dataset(
                id=dataset[0],
                name=dataset[1],
                pipeline=pipeline,
                source_database=dataset[3],
                source_schema=dataset[4],
                source_table=dataset[5],
                destination_database=dataset[6],
                destination_table=dataset[7],
                incremental_column=dataset[8]
            )
        else:
            return None
    
if __name__ == "__main__":
    db = MetadataDB()
    # test_platform = Platform(id=None, name='test platform', driver_name='test_driver')
    # print(test_platform)
    # platform_id = db.add_platform(test_platform)
    # test_platform.id = platform_id
    # print(test_platform)
    
    #print(db.get_platform(name='snowflake'))
    #print(db.get_platform(id=2))
    #print(db.get_platform(id=2, name='snowflake'))
    #print(db.get_platform())
    
    test_conn = db.get_connection(name='test_conn')
    print(test_conn)
    print(test_conn.credentials)
    #print(db.get_connection(id=12))
    #print(db.get_connection(id=12, name='test_conn'))
    #print(db.get_connection())
    
    print(db.get_pipeline(name='test_pipeline'))
    #print(db.get_pipeline(id=1))

    # test_pipeline = Pipeline(
    #     name='test_pipeline_in_module',
    #     source=db.get_connection(name='test postgres connection'),
    #     destination=db.get_connection(name='test snowflake connection'),
    #     description='Test description'
    # )
    
    # pipeline_id = db.add_pipeline(test_pipeline)
    # print(db.get_pipeline(id=pipeline_id))
    
      
    # test_connetion = Connection(
    #         id=None,
    #         name='test_conn',
    #         platform=db.get_platform('snowflake'),
    #         connection_details={'host': 'localhost', 'port': 5432, 'database': 'mydb'},
    #         credentials={'password': 'secret'}
    #     )
    
    # print(db.add_connection(test_connetion))
    # print(db.get_connection(name='test_conn'))