import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'instance', 'registrations.db')

def migrate():
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    if not os.path.exists(db_path):
        logging.info("Database file not found. Creating new database...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable WAL mode for better concurrency
    cursor.execute("PRAGMA journal_mode=WAL")

    # Get current tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    logging.info(f"Current tables: {tables}")

    # Create tables if they don't exist
    if 'admin' not in tables:
        logging.info("Creating 'admin' table...")
        cursor.execute("""
            CREATE TABLE admin (
                id INTEGER PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(200) NOT NULL
            )
        """)

    if 'church' not in tables:
        logging.info("Creating 'church' table...")
        cursor.execute("""
            CREATE TABLE church (
                id INTEGER PRIMARY KEY,
                name VARCHAR(200) UNIQUE NOT NULL
            )
        """)

    if 'zone' not in tables:
        logging.info("Creating 'zone' table...")
        cursor.execute("""
            CREATE TABLE zone (
                id INTEGER PRIMARY KEY,
                name VARCHAR(200) UNIQUE NOT NULL
            )
        """)

    if 'registration' not in tables:
        logging.info("Creating 'registration' table...")
        cursor.execute("""
            CREATE TABLE registration (
                id INTEGER PRIMARY KEY,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                gender VARCHAR(10) NOT NULL DEFAULT 'Not Specified',
                age INTEGER NOT NULL DEFAULT 0,
                church_name VARCHAR(200) DEFAULT '',
                church_id INTEGER,
                zone_id INTEGER,
                registration_code VARCHAR(50) UNIQUE NOT NULL,
                registration_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        # Add missing columns to existing registration table
        cursor.execute("PRAGMA table_info(registration)")
        columns = [row[1] for row in cursor.fetchall()]
        
        migrations = {
            'gender': "ALTER TABLE registration ADD COLUMN gender VARCHAR(10) NOT NULL DEFAULT 'Not Specified'",
            'age': "ALTER TABLE registration ADD COLUMN age INTEGER NOT NULL DEFAULT 0",
            'church_id': "ALTER TABLE registration ADD COLUMN church_id INTEGER",
            'zone_id': "ALTER TABLE registration ADD COLUMN zone_id INTEGER",
            'church_name': "ALTER TABLE registration ADD COLUMN church_name VARCHAR(200) DEFAULT ''"
        }

        for col, sql in migrations.items():
            if col not in columns:
                logging.info(f"Adding column: {col}")
                cursor.execute(sql)
            else:
                logging.info(f"Column '{col}' already exists.")

    # Seed default data if tables are empty
    cursor.execute("SELECT COUNT(*) FROM church")
    if cursor.fetchone()[0] == 0:
        logging.info("Seeding default churches...")
        default_churches = [
            'Mother Church - Main Campus',
            'Mother Church - Extension'
        ]
        for name in default_churches:
            cursor.execute("INSERT OR IGNORE INTO church (name) VALUES (?)", (name,))

    cursor.execute("SELECT COUNT(*) FROM zone")
    if cursor.fetchone()[0] == 0:
        logging.info("Seeding default zones...")
        default_zones = ['Central Zone', 'Eastern Zone', 'Western Zone', 'Mother Church']
        for name in default_zones:
            cursor.execute("INSERT OR IGNORE INTO zone (name) VALUES (?)", (name,))

    cursor.execute("SELECT COUNT(*) FROM admin")
    if cursor.fetchone()[0] == 0:
        logging.info("Creating default admin user (username: admin, password: admin123)...")
        from werkzeug.security import generate_password_hash
        cursor.execute(
            "INSERT INTO admin (username, password_hash) VALUES (?, ?)",
            ('admin', generate_password_hash('admin123'))
        )

    conn.commit()
    logging.info("Migration complete! Your data is safe.")
    
    # Print summary
    cursor.execute("SELECT COUNT(*) FROM church")
    logging.info(f"Total churches: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM zone")
    logging.info(f"Total zones: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM registration")
    logging.info(f"Total registrations: {cursor.fetchone()[0]}")
    
    conn.close()

if __name__ == '__main__':
    migrate()
