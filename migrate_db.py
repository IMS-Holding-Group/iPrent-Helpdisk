import sqlite3
import os
from config import DATABASE_PATH

def migrate_database():
    if not os.path.exists(DATABASE_PATH):
        print("Database does not exist. Will be created when running app.py")
        return
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(tickets)")
        ticket_columns = [column[1] for column in cursor.fetchall()]
        
        print("Existing columns:", ticket_columns)
        
        migrations = []
        
        if 'ticket_type' not in ticket_columns:
            try:
                cursor.execute("ALTER TABLE tickets ADD COLUMN ticket_type TEXT DEFAULT 'printer'")
                migrations.append("[OK] Added ticket_type column")
            except sqlite3.OperationalError as e:
                print(f"Error adding ticket_type: {e}")
        
        if 'device_name' not in ticket_columns:
            try:
                cursor.execute("ALTER TABLE tickets ADD COLUMN device_name TEXT")
                migrations.append("[OK] Added device_name column")
            except sqlite3.OperationalError as e:
                print(f"Error adding device_name: {e}")
        
        if 'affected_users_count' not in ticket_columns:
            try:
                cursor.execute("ALTER TABLE tickets ADD COLUMN affected_users_count INTEGER DEFAULT 1")
                migrations.append("[OK] Added affected_users_count column")
            except sqlite3.OperationalError as e:
                print(f"Error adding affected_users_count: {e}")

        if 'created_by_user_id' not in ticket_columns:
            try:
                cursor.execute("ALTER TABLE tickets ADD COLUMN created_by_user_id INTEGER")
                migrations.append("[OK] Added created_by_user_id column")
            except sqlite3.OperationalError as e:
                print(f"Error adding created_by_user_id: {e}")

        cursor.execute("PRAGMA table_info(users)")
        user_columns = [column[1] for column in cursor.fetchall()]

        if 'role' not in user_columns:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'employee'")
                cursor.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")
                migrations.append("[OK] Added role column")
            except sqlite3.OperationalError as e:
                print(f"Error adding role: {e}")

        if 'email' not in user_columns:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
                cursor.execute("UPDATE users SET email = 'admin@helpdesk.local' WHERE username = 'admin'")
                migrations.append("[OK] Added email column")
            except sqlite3.OperationalError as e:
                print(f"Error adding email: {e}")
        
        conn.commit()
        
        if migrations:
            print("\n" + "=" * 50)
            print("Database updated:")
            for migration in migrations:
                print(migration)
            print("=" * 50)
        else:
            print("\nDatabase is already up to date!")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("Starting database update...")
    migrate_database()
    print("\nUpdate completed!")
