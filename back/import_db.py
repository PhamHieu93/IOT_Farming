import psycopg2
from config import config
import sys

def import_database(filename):
    """Import database state from SQL file"""
    conn = None
    try:
        # Connect with autocommit False for transaction
        params = config()
        conn = psycopg2.connect(**params)
        conn.autocommit = False
        cur = conn.cursor()
        
        print(f"Importing database from {filename}...")
        
        # Read and execute SQL file
        with open(filename, 'r') as f:
            # Execute file contents
            cur.execute(f.read())
        
        # Commit transaction
        conn.commit()
        print("Database import completed successfully")
        return True

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error importing database: {error}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python import_db.py <backup_file.sql>")
        sys.exit(1)
        
    import_database(sys.argv[1])
