import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'registrations.db')

def migrate():
    if not os.path.exists(db_path):
        print("Database not found at:", db_path)
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get current columns
    cursor.execute("PRAGMA table_info(registration)")
    columns = [row[1] for row in cursor.fetchall()]
    
    print(f"Current columns: {columns}")

    migrations = {
        'gender': "ALTER TABLE registration ADD COLUMN gender VARCHAR(10) NOT NULL DEFAULT 'Not Specified'",
        'age': "ALTER TABLE registration ADD COLUMN age INTEGER NOT NULL DEFAULT 0",
        'church_id': "ALTER TABLE registration ADD COLUMN church_id INTEGER",
        'zone_id': "ALTER TABLE registration ADD COLUMN zone_id INTEGER",
        'church_name': "ALTER TABLE registration ADD COLUMN church_name VARCHAR(200) DEFAULT ''"
    }

    applied = False
    for col, sql in migrations.items():
        if col not in columns:
            print(f"Adding column: {col}")
            cursor.execute(sql)
            applied = True
        else:
            print(f"Column {col} already exists.")

    if applied:
        conn.commit()
        print("Migration successful! Your data is safe.")
    else:
        print("No migrations needed.")
        
    conn.close()

if __name__ == '__main__':
    migrate()
