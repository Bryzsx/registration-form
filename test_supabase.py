from dotenv import load_dotenv
import os

load_dotenv()

print("Testing Supabase connection...")
print("URL (masked): postgresql://postgres:***@" + os.environ.get('DATABASE_URL', '').split('@')[-1])

from sqlalchemy import create_engine

url = os.environ.get('DATABASE_URL')
engine = create_engine(url)

try:
    with engine.connect() as conn:
        print("SUCCESS! Connected to Supabase!")
        result = conn.execute("SELECT version()")
        version = result.fetchone()[0]
        print("PostgreSQL version:", version[:50])
        engine.dispose()
except Exception as e:
    print("FAILED:", str(e))
    print("\nTroubleshooting:")
    print("1. Check if Supabase project is RUNNING (not paused)")
    print("2. Verify password is correct")
    print("3. Check if 'sslmode=require' is in URL")
