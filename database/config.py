import os
from configparser import ConfigParser
import getpass
import logging

logger = logging.getLogger("IOT_database")

def config(filename='database.ini', section='postgresql'):
    """Parse database connection parameters from a config file."""
    db_config = {}
    
    # First check environment variables (highest priority)
    if os.environ.get("DB_HOST"):
        logger.info("Using database credentials from environment variables")
        db_config = {
            "host": os.environ.get("DB_HOST", "localhost"),
            "port": os.environ.get("DB_PORT", "5432"),
            "dbname": os.environ.get("DB_NAME", "postgres"),
            "user": os.environ.get("DB_USER", "postgres"),
            "password": os.environ.get("DB_PASSWORD", "")
        }
        return db_config
        
    # If no environment variables, try to read from config file
    parser = ConfigParser()
    if os.path.isfile(filename):
        try:
            parser.read(filename)
            
            # Check if section exists
            if parser.has_section(section):
                params = parser.items(section)
                for param in params:
                    db_config[param[0]] = param[1]
                
                # If we have a complete config, return it
                if all(key in db_config for key in ["host", "port", "dbname", "user", "password"]):
                    logger.info(f"Using database configuration from {filename}")
                    return db_config
                else:
                    missing = [key for key in ["host", "port", "dbname", "user", "password"] if key not in db_config]
                    logger.warning(f"Incomplete database config in {filename}. Missing: {missing}")
            else:
                logger.warning(f"Section {section} not found in {filename}")
        except Exception as e:
            logger.error(f"Error reading config file: {e}")
    
    # If we get here, we either don't have a config file or it's incomplete
    # Create a default config and ask for missing values
    default_config = {
        "host": "localhost",
        "port": "5432",
        "dbname": "postgres",
        "user": "postgres",
        "password": ""
    }
    
    # Use any values we already have from partial config
    for key in default_config:
        if key not in db_config:
            db_config[key] = default_config[key]
    
    print("\n" + "=" * 50)
    print("PostgreSQL Database Configuration")
    print("=" * 50)
    print("Enter database connection details (press Enter to use default):")
    
    db_config["host"] = input(f"Database host [{db_config['host']}]: ") or db_config["host"]
    db_config["port"] = input(f"Database port [{db_config['port']}]: ") or db_config["port"] 
    db_config["dbname"] = input(f"Database name [{db_config['dbname']}]: ") or db_config["dbname"]
    db_config["user"] = input(f"Database user [{db_config['user']}]: ") or db_config["user"]
    db_config["password"] = getpass.getpass(f"Database password: ") or db_config["password"]
    
    save = input("Save these settings to database.ini? (y/n): ")
    if save.lower() == "y":
        try:
            if not parser.has_section(section):
                parser.add_section(section)
            
            for key, value in db_config.items():
                parser.set(section, key, value)
            
            with open(filename, 'w') as f:
                parser.write(f)
                
            print(f"Settings saved to {filename}")
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    return db_config

