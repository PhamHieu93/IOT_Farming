import psycopg2
from config import config
from tabulate import tabulate
import json
from datetime import datetime

def connect_db():
    """Connect to PostgreSQL database"""
    try:
        params = config()
        conn = psycopg2.connect(**params)
        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error connecting to database: {error}")
        return None

def get_sector_info(sector):
    """Get all information for a specific sector"""
    conn = None
    try:
        conn = connect_db()
        if not conn:
            return None
            
        cur = conn.cursor()
        
        # Get device commands for the sector
        cur.execute("""
            SELECT 
                CommandID,
                Device,
                Status,
                Type,
                Command_Data::text,
                Timestamp
            FROM Device_Commands 
            WHERE Sector = %s
            ORDER BY Timestamp DESC
            LIMIT 10
        """, (sector,))
        
        commands = []
        for row in cur.fetchall():
            command = {
                'command_id': row[0],
                'device': row[1],
                'status': '✅ ON' if row[2] else '❌ OFF',
                'type': row[3],
                'data': json.loads(row[4]) if row[4] != '{}' else {},
                'timestamp': row[5].strftime('%Y-%m-%d %H:%M:%S')
            }
            commands.append(command)

        print(f"\n{'='*80}")
        print(f"🔍 Sector {sector} Information")
        print(f"{'='*80}")
        
        if commands:
            print("\n📝 Last 10 Commands:")
            headers = ['ID', 'Device', 'Status', 'Type', 'Additional Data', 'Timestamp']
            table_data = [
                [
                    cmd['command_id'],
                    cmd['device'],
                    cmd['status'],
                    cmd['type'],
                    json.dumps(cmd['data'], indent=2) if cmd['data'] else '-',
                    cmd['timestamp']
                ] for cmd in commands
            ]
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
        else:
            print("\n❌ No commands found for this sector")
            
        # Get current device states
        cur.execute("""
            SELECT DISTINCT 
                d.Device,
                d.Type,
                d.Status,
                d.Timestamp
            FROM Device_Commands d
            INNER JOIN (
                SELECT Device, MAX(Timestamp) as MaxTime
                FROM Device_Commands
                WHERE Sector = %s
                GROUP BY Device
            ) m ON d.Device = m.Device AND d.Timestamp = m.MaxTime
            WHERE d.Sector = %s
        """, (sector, sector))
        
        current_states = cur.fetchall()
        
        if current_states:
            print("\n📊 Current Device States:")
            headers = ['Device', 'Control Type', 'Status', 'Last Updated']
            table_data = [
                [
                    dev[0],
                    dev[1],
                    '✅ ON' if dev[2] else '❌ OFF',
                    dev[3].strftime('%Y-%m-%d %H:%M:%S')
                ] for dev in current_states
            ]
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
        else:
            print("\n❌ No devices found in this sector")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error getting sector information: {error}")
    finally:
        if conn:
            conn.close()

def main():
    """Main function to query sector information"""
    while True:
        print("\n🌟 IOT Farming Sector Query Tool")
        print("Select a sector (A/B/C/D) or 'Q' to quit:")
        choice = input(">>> ").upper()
        
        if choice == 'Q':
            break
        elif choice in ['A', 'B', 'C', 'D']:
            get_sector_info(choice)
        else:
            print("❌ Invalid choice. Please select A, B, C, D or Q")

if __name__ == "__main__":
    main()
