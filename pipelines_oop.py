from importlib import reload
import metadata_oop
reload(metadata_oop)
from metadata_oop import MetadataDB, Connection, Pipeline, Dataset
import dlt
from dlt.common.pipeline import LoadInfo
from dlt.destinations import snowflake
from dlt.sources.sql_database import sql_database
from dlt.sources.filesystem import FileItemDict, filesystem, readers, read_csv
import json
from sqlalchemy import create_engine, inspect

class DltPipeline():
    def __init__(self, pipeline_name: str, metadata_db: MetadataDB):
        self.metadata_db = metadata_db
        self.pipeline_metadata = metadata_db.get_pipeline(name=pipeline_name)
        
        if not self.pipeline_metadata:
            raise ValueError(f"Pipeline '{pipeline_name}' is not defined")
        dest_conn_name = self.pipeline_metadata.destination.name
        dest_conn = self.metadata_db.get_connection(name=dest_conn_name)
        dest_conn_dict = dest_conn.__dict__
        dest_conn_details = dest_conn_dict['connection_details']
        dest_conn_creds = dest_conn_dict['credentials']        
        
        self.pipeline = dlt.pipeline(
            pipeline_name=pipeline_name,
            destination=snowflake(credentials=dict(**dest_conn_details, **dest_conn_creds)), # It can be other that snowflake. Add support later
            dataset_name=pipeline_name,
            dev_mode=False,
        )
    
    def _get_source_conn_string(self) -> dict:       
        source_conn_name = self.pipeline_metadata.source.name
        source_conn = self.metadata_db.get_connection(name=source_conn_name)
        source_conn_dict = source_conn.__dict__
        
        source_conn_details = source_conn_dict['connection_details']
        source_conn_creds = source_conn_dict['credentials']
    
        drivername = source_conn_details['drivername']
        username = source_conn_details['username']
        password = source_conn_creds['password']
        host = source_conn_details['host']
        port = source_conn_details['port']
        database = source_conn_details['database']
        source_conn_string = f"{drivername}://{username}:{password}"
        source_conn_string +=f"@{host}:{port}/{database}"
        return source_conn_string
    
    def _validate_source_tables(self, table_list: list[Dataset | str] = []) -> tuple[list[Dataset], list[str]]:
        existing = []
        missing = []
        # First check if tables are defined in metadata
        dataset_list = []
        for table in table_list:
            if isinstance(table, Dataset):
                dataset_list.append(table)
            else:
                dataset = self.metadata_db.get_dataset(name=table)
                if dataset:
                    dataset_list.append(dataset)
                else:
                    message = f"Dataset '{table}' is not defined for pipeline '{self.pipeline_metadata.name}'"
                    missing.append({'table': table, 'message': message})
                                 
        # Then check if tables defined in metadata are available in the source        
        platform_name = self.pipeline_metadata.source.platform.name
        if platform_name != 'local filesystem':
            engine = create_engine(self._get_source_conn_string())
            inspector = inspect(engine)
            for dataset in dataset_list:
                if inspector.has_table(table_name=dataset.source_table, schema=dataset.source_schema):
                    existing.append(dataset)
                else:
                    message = f"Source table '{dataset.source_table}' is absent from the source"
                    missing.append({'table': table, 'message': message})
        else:
            existing = dataset_list
                
        return existing, missing
    
    def load_pipeline(self, table_list: list[Dataset | str] = [], full_refresh: bool = False, drop_pipeline: bool = False) -> LoadInfo:
        # Drop pipeline state if requested (useful for debugging/recovery)
        if drop_pipeline:
            print(f"Dropping pipeline '{self.pipeline_metadata.name}' state...")
            self.pipeline.drop() #https://dlthub.com/docs/api_reference/dlt/pipeline/drop
        
        default_schema_label = 'default schema'        

        existing_datasets, missing_tables = self._validate_source_tables(table_list)  
        if missing_tables:
            for table in missing_tables:
                print(f"{table['table']}: {table['message']}")
        
        if existing_datasets: # Here we group tables by source schema
            resource_dict = {}
            print(f"Running pipeline '{self.pipeline_metadata.name}' for datasets:")
            for resource in existing_datasets:
                print(f"\t- {resource.name} ({default_schema_label if not resource.source_schema else resource.source_schema})")
                if resource.source_schema not in resource_dict.keys():
                    resource_dict[resource.source_schema] = []
                resource_dict[resource.source_schema].append(resource.source_table)    
 
        run_results = {}
        # Run pipeline for each source schema separately (if source schema is not defined, we use default label and run without schema)      
        platform_name = self.pipeline_metadata.source.platform.name
        for schema in resource_dict.keys():
            if platform_name == 'local filesystem':
                source_conn_name = self.pipeline_metadata.source.name
                source_conn = self.metadata_db.get_connection(name=source_conn_name)
                bucket_url = source_conn.connection_details['bucket_url']
                file_glob = source_conn.connection_details['file_glob']
                source_tables = filesystem(
                    #local_dir=local_dir, # !!!
                    bucket_url=bucket_url, # !!!
                    file_glob = file_glob # !!!
                ) | read_csv() #readers().read_csv()
                source_tables.apply_hints(merge_key="id")
            else:
                src_conn_string = self._get_source_conn_string()
                source_tables = sql_database(
                    credentials=src_conn_string,
                    reflection_level="full_with_precision", # What does it mean?
                    schema=schema # source tables by source schema and run pipeline for each schema separately
                ).with_resources(*resource_dict[schema])
            
            for dataset in existing_datasets:
                if dataset.source_table in resource_dict[schema]:
                    if dataset.incremental_column and not full_refresh:
                        incremental_info = dlt.sources.incremental(cursor_path=dataset.incremental_column)
                    else:
                        incremental_info = None                
                    hints = { 'table_name': dataset.destination_table, 'incremental': incremental_info }
                    
                    if platform_name == 'local filesystem':
                        source_tables.apply_hints(**hints)
                    else:
                        getattr(source_tables, dataset.source_table).apply_hints(**hints)
                
            print(f"Importing datasets from source schema '{schema if schema else default_schema_label}'")
            info = self.pipeline.run(source_tables, write_disposition="merge")
            if schema:
                run_results[schema] = info
            else:
                run_results[default_schema_label] = info
            print(info)
        return run_results
        
if __name__ == "__main__":
    #db = MetadataDB()
    
    # Add new dataset
    # meta_pipeline = db.get_pipeline(name="test_pipeline")    
    # new_dataset = Dataset(name="other_customers", source_schema="test_schema", pipeline=meta_pipeline)
    # db.add_dataset(new_dataset)
    
    # Run pipeline from Posrtgres to Snowflake
    #dlt_pipeline = DltPipeline('test_pipeline', db)

    ##test_dataset = db.get_dataset(name='test_dataset')
    # table_list = ['employees', 'customers', 'iob', 'test_dataset', 'other_customers'] #, 'other_customers'
    ##table_list = ['other_customers'] #, 'other_customers'
    # run_results = dlt_pipeline.load_pipeline(table_list)
    # print(run_results)
    
    
    # Run pipeline from Filesystem to Snowflake
    print('-- Here we are loading from filesystem to Snowflake')
    with MetadataDB() as db:
        dlt_pipeline = DltPipeline(pipeline_name='file_sys_pipeline',metadata_db=db)
        table_list = ['mock_data']
        run_results = dlt_pipeline.load_pipeline(table_list=table_list)
    
    print('-- Here we are running from file Postgres to Snowflake')
    # Run pipeline from Posrtgres to Snowflake
    with MetadataDB() as db:
        dlt_pipeline = DltPipeline(pipeline_name='test_pipeline',metadata_db=db)
        table_list = ['employees', 'customers', 'iob', 'test_dataset', 'other_customers']
        run_results = dlt_pipeline.load_pipeline(table_list=table_list)