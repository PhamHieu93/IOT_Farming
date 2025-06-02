from configparser import ConfigParser
import os

def config(filename='database.ini', section='postgresql'):
    # create a parser
    parser = ConfigParser()
    
    # get the directory containing this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # construct full path to database.ini
    db_config_path = os.path.join(current_dir, filename)
    
    # read config file
    if not parser.read(db_config_path):
        raise Exception(f"Config file {db_config_path} not found")
        
    # get section
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception(f'Section {section} not found in the {filename} file')
    
    return db

