import sqlite3

class MyDB:
    def __init__(self):
        print('Initialization')
        self.conn = sqlite3.connect('../elt_app_metadata.db')
    def __enter__(self):
        print('Enter')
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        print('Exit')
        if exc_type:
            print('--Printing errors')
            print('Type: ', exc_type)
            print('Value: ', exc_val)
            print('Traceback: ', exc_tb)
        if self.conn:
            self.conn.close()
        return True  # Don't hide errors

# This error will be raised:
with MyDB() as db:
    raise ValueError("Executiion. Something broke!")
    #print('Execution')
# ValueError: Something broke! <- You see this


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
