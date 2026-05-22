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
    driver_name: Optional[str] = field(default=None)
    id: Optional[int] = field(default=None) # or Union[int, None] or int | None without an import
    
@dataclass
class Connection:
    name: str
    platform: Platform
    connection_details: Dict[str, Any] # or dict[str, any] without an import
    credentials: Optional[Dict[str, Any]] = field(repr=False, default=None) # or dict[str, any] without an import # repr=False not include into the print output
    id: Optional[int] = field(default=None)
    
@dataclass
class Pipeline:
    name: str
    source: Connection
    destination: Connection
    description: str
    id: Optional[int] = field(default=None)
    
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
        self.conn = None
        self._initialize(replace_existing_meta)
        
    def _initialize(self, replace_existing_meta):
        if self.conn is None:
            self.conn = self._get_db_connection()
        self._create_metadata_tables(replace_existing=replace_existing_meta)
          
    def _get_db_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = 1")
        return conn
    
    def __enter__(self):
        """Context manager entry - ensures connection is open"""
        if self.conn is None:
            self.conn = self._get_db_connection()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes connection and handles errors"""
        if self.conn:
            if exc_type is not None:
                # An error occurred, rollback any pending transaction
                self.conn.rollback()
            else:
                # No error, commit any pending transaction
                self.conn.commit()
            self.conn.close()
            self.conn = None
        return False  # Don't suppress exceptions
    
    def close(self):
        """Explicitly close the connection if needed"""
        if self.conn:
            self.conn.commit()
            self.conn.close()
            self.conn = None
    
    # @staticmethod # if you want to use this method without an instance of the class #
    # What does @staticmethod bring?
    # What does @classmethod bring?
    def _get_table_definition(table_name: str) -> str:
        match table_name:
            case 'platform':
                ddl_create = '''
                CREATE TABLE IF NOT EXISTS platform (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    driver_name TEXT
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
    
    def migrate_connection_drop_credentials_not_null(self):
        """ Written by AI to demonstrate how remove a NOT NULL constraint from an existing column in SQLite, which doesn't support ALTER COLUMN.
        Remove NOT NULL constraint from connection.credentials column.
        
        SQLite doesn't support ALTER COLUMN, so this recreates the table
        while preserving all data and referential integrity.
        """
        conn = self.conn
        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            cursor.execute('''
                CREATE TABLE connection_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    platform_id INTEGER NOT NULL,
                    connection_details NOT NULL,
                    credentials TEXT,
                    FOREIGN KEY (platform_id) REFERENCES platform(id)
                )
            ''')
            cursor.execute('INSERT INTO connection_new SELECT * FROM connection')
            cursor.execute('DROP TABLE connection')
            cursor.execute('ALTER TABLE connection_new RENAME TO connection')
            conn.commit()
            # Verify referential integrity
            violations = cursor.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError(f"Foreign key violations detected: {violations}")
        finally:
            conn.execute("PRAGMA foreign_keys = ON")

    def _create_table(self, table_name: str, conn: sqlite3.Connection, replace_existing: bool = False):
        conn = self.conn
        cursor = conn.cursor()
        ddl = MetadataDB._get_table_definition(table_name)        
        if replace_existing:
            cursor = conn.cursor()
            cursor.execute(f'DROP TABLE {table_name}')            
        cursor.execute(ddl)
    
    def _create_metadata_tables(self, replace_existing):
        conn = self.conn
        list(map(lambda table: self._create_table(table, self.conn, replace_existing),
                ('platform', 'connection', 'pipeline', 'dataset')
            ))
        conn.commit()
    
    def _add_metadata_record(self, table_name: str, insert_values: dict, encrypt_columns: list = []) -> int:
        conn = self.conn
        if len(encrypt_columns) > 0:
            for col in encrypt_columns:
                if  insert_values[col]: # if column contains a value
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
        return cursor.lastrowid
    
    def _get_metadata(self, sql: str, *sql_parameters) -> tuple | None:
        conn = self.conn
        cursor = conn.cursor()
        result = cursor.execute(sql, sql_parameters)
        row = result.fetchone()
        if row is not None:
            return row
    
    def add_platform(self, platform: Platform) -> int:
        insert_values = dict(name=platform.name, driver_name=platform.driver_name)
        platform_id = self._add_metadata_record('platform', insert_values)
        platform.id = platform_id
        return platform        
    
    def add_connection(self, connection: Connection) -> Connection:
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
        connection.id = connection_id
        return connection
    
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
            return Platform(id=platform[0], name=platform[1], driver_name=platform[2]) if platform else None
    
    def get_connection(self, *, id: int | None = None, name: str | None = None) -> Connection:
        column_list = ['id', 'name', 'platform_id', 'connection_details', 'credentials']
        connection = self._get_entity('connection', column_list, id=id, name=name)
        if not connection:
            return None
        platform = self.get_platform(id=connection[2])
        if connection[4]:
            cretentials = json.loads(encryption.cipher.decrypt(connection[4]).decode())
        else:
            cretentials = None
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
        
    def add_pipeline(self, pipeline: Pipeline) -> Pipeline:
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
        pipeline.id = pipeline_id
        return pipeline
    
    def add_dataset(self, dataset: Dataset) -> Dataset:
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
        dataset.id = dataset_id
        return dataset
    
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
    
    file_system_connection = {
        "local_dir": "C:/Users/dpolishchuk_scalefre/Documents/Repos/csv_files",
        "bucket_url": "C:/Users/dpolishchuk_scalefre/Documents/Repos/csv_files",
        "file_glob": "*.csv"
    }
    # with MetadataDB() as db:
    #platform = Platform(name='local filesystem', driver_name='filesystem') #
    #platform = db.add_platform(platform)
        # platform = db.get_platform(name='local filesystem')        
        # connection = Connection(
        #     name='file_system_my_folder',
        #     platform=platform,
        #     connection_details=file_system_connection
        #     # remove NOT NULL constraint from credentials
        # )
        # connection = db.add_connection(connection)
        # print(connection)    
        
    with MetadataDB() as db:
        test_pipeline = Pipeline(
            name='file_sys_pipeline',
            source=db.get_connection(name='file_system_my_folder'),
            destination=db.get_connection(name='test snowflake connection'),
            description='Just load some system files into Snowflake'
        )
        db.add_pipeline(test_pipeline)
        
        # add dataset and run the fiile system pipeline
    
    with MetadataDB() as db:
        test_dataset = Dataset(
            name='mock_data',
            pipeline=db.get_pipeline(name='file_sys_pipeline')
        )
        db.add_dataset(test_dataset)
        # try duckdb as target
        # introduce unit tests
        
    
    # TODO: Add a file system connection, a pipeline, and a dataset
    
    # Alternative: manual management (don't forget to close!)
    # db = MetadataDB()
    # try:
    #     platform = Platform(name='local filesystem', driver_name='filesystem')
    #     platform_id = db.add_platform(platform)
    #     print(platform)
    # finally:
    #     db.close()  # Explicitly close when done
    
    #print(db.get_platform(name='snowflake'))
    #print(db.get_platform(id=2))
    #print(db.get_platform(id=2, name='snowflake'))
    #print(db.get_platform())
    
    # test_conn = db.get_connection(name='test_conn')
    # print(test_conn)
    # print(test_conn.credentials)
    #print(db.get_connection(id=12))
    #print(db.get_connection(id=12, name='test_conn'))
    #print(db.get_connection())
    
    # print(db.get_pipeline(name='test_pipeline'))
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