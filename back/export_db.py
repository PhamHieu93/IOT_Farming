import psycopg2
import json
from datetime import datetime
from config import config


def connect_db():
    """Connect to the PostgreSQL database server and initialize tables if needed"""
    conn = None
    try:
        # read connection parameters
        params = config()
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        
        # Read and execute table creation SQL
        with open('create_tables.sql', 'r') as f:
            create_tables_sql = f.read()
            cur.execute(create_tables_sql)
            conn.commit()
            
        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error connecting to database: {error}")
        if conn:
            conn.rollback()
        return None
    # Don't close connection here as it's used by the caller
    
def export_database():
    """Export database state to SQL file"""
    conn = None
    try:
        conn = connect_db()
        cur = conn.cursor()
        
        # Open file for writing
        filename = f"db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        with open(filename, 'w') as f:
            # Write table creation
            f.write("-- Database backup created at " + datetime.now().isoformat() + "\n\n")
            f.write("-- Recreate tables\n")
            with open('create_tables.sql', 'r') as schema:
                f.write(schema.read() + "\n\n")
            
            # Export Device_Commands data
            cur.execute("SELECT * FROM Device_Commands ORDER BY Timestamp")
            rows = cur.fetchall()
            
            if rows:
                f.write("-- Device Commands Data\n")
                for row in rows:
                    command_data = json.dumps(row[5]) if row[5] else '{}'
                    f.write(
                        f"INSERT INTO Device_Commands (CommandID, Sector, Device, Status, Type, Command_Data, Timestamp) "
                        f"VALUES ({row[0]}, '{row[1]}', '{row[2]}', {row[3]}, '{row[4]}', "
                        f"'{command_data}'::jsonb, '{row[6]}'::timestamp);\n"
                    )
            
            # Export Device data
            cur.execute("SELECT * FROM Device")
            rows = cur.fetchall()
            
            if rows:
                f.write("\n-- Device Data\n")
                for row in rows:
                    status_json = json.dumps(row[4]) if row[4] else '{}'
                    f.write(
                        f"INSERT INTO Device (DID, Dname, Location, Type, status) "
                        f"VALUES ({row[0]}, '{row[1]}', '{row[2]}', '{row[3]}', '{status_json}'::jsonb);\n"
                    )

        print(f"Database backup created: {filename}")
        return filename

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error exporting database: {error}")
        return None
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    export_database()
