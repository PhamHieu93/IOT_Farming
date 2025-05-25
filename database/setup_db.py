import psycopg2
import logging
import sys
import os
from config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("setup_db.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("IOT_database_setup")

def test_connection():
    """Test connection to the PostgreSQL database"""
    conn = None
    try:
        # Get connection parameters
        params = config()
        logger.info("Testing database connection...")
        
        # Connect to the default database
        conn = psycopg2.connect(**params)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Display PostgreSQL details
        print("\n" + "=" * 60)
        print("DATABASE CONNECTION SUCCESSFUL!".center(60))
        print("=" * 60)
        
        # Print PostgreSQL version
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        print(f"PostgreSQL Version: {version}")
        
        # Get current user and database
        cur.execute("SELECT current_user, current_database()")
        user, db = cur.fetchone()
        print(f"Connected as: {user}")
        print(f"Current database: {db}")
        
        # Close communication with the database
        cur.close()
        return True
        
    except Exception as error:
        print("\n" + "=" * 60)
        print("CONNECTION ERROR!".center(60))
        print("=" * 60)
        print(f"Error: {error}")
        logger.error(f"Connection test failed: {error}")
        return False
    finally:
        if conn is not None:
            conn.close()

def create_database(dbname):
    """Create the database if it doesn't exist"""
    conn = None
    try:
        # Get connection parameters but connect to default database
        params = config()
        orig_dbname = params["dbname"]
        params["dbname"] = "postgres"  # Connect to default postgres database first
        
        logger.info(f"Creating database {dbname} if it doesn't exist...")
        conn = psycopg2.connect(**params)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
        if cur.fetchone() is None:
            # Create database if it doesn't exist
            cur.execute(f"CREATE DATABASE {dbname}")
            print(f"Database '{dbname}' created successfully!")
            logger.info(f"Database '{dbname}' created")
        else:
            print(f"Database '{dbname}' already exists")
            logger.info(f"Database '{dbname}' already exists")
        
        # Close communication with the database
        cur.close()
        return True
        
    except Exception as error:
        print(f"Error creating database: {error}")
        logger.error(f"Error creating database: {error}")
        return False
    finally:
        if conn is not None:
            conn.close()

def create_tables(dbname):
    """Create the necessary tables if they don't exist"""
    conn = None
    try:
        # Get connection parameters
        params = config()
        params["dbname"] = dbname
        
        logger.info("Creating tables if they don't exist...")
        conn = psycopg2.connect(**params)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Create Device table if it doesn't exist
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Device (
            DID SERIAL PRIMARY KEY,
            Dname VARCHAR(100) NOT NULL,
            Location VARCHAR(100),
            Type VARCHAR(50),
            status JSONB
        )
        """)
        
        # Create Data table if it doesn't exist
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Data (
            DataID SERIAL PRIMARY KEY,
            DID INTEGER REFERENCES Device(DID),
            Value FLOAT NOT NULL,
            Unit VARCHAR(10),
            Status VARCHAR(20),
            Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create Device_Activity table if it doesn't exist
        cur.execute("""
        CREATE TABLE IF NOT EXISTS Device_Activity (
            ActivityID SERIAL PRIMARY KEY,
            DID INTEGER REFERENCES Device(DID),
            Action VARCHAR(100) NOT NULL,
            Status VARCHAR(50),
            Timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        print("Tables created successfully!")
        logger.info("Tables created/updated successfully")
        
        # Close communication with the database
        cur.close()
        return True
        
    except Exception as error:
        print(f"Error creating tables: {error}")
        logger.error(f"Error creating tables: {error}")
        return False
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("IOT FARMING DATABASE SETUP".center(60))
    print("=" * 60)
    
    # Test connection first
    if test_connection():
        # Get database name from config
        params = config()
        dbname = params["dbname"]
        
        # Ask if we should create the database and tables
        if input(f"\nCreate/update database '{dbname}'? (y/n): ").lower() == 'y':
            if create_database(dbname):
                if create_tables(dbname):
                    print("\n" + "=" * 60)
                    print("SETUP COMPLETED SUCCESSFULLY!".center(60))
                    print("=" * 60)
                else:
                    print("\nSetup failed when creating tables.")
            else:
                print("\nSetup failed when creating database.")
    else:
        print("\nSetup failed due to connection error.")
        print("Please check your PostgreSQL credentials and try again.")
