"""
init_db.py — Railway startup script
Runs creating_postgres_database.py safely on every deploy.
Idempotent: uses IF NOT EXISTS so re-runs are safe.
"""
import os
import sys
import time
import psycopg2
from psycopg2 import OperationalError
from dotenv import load_dotenv

load_dotenv()

def get_conn_params():
    """Prefer DATABASE_URL (Railway auto-injects), fall back to individual vars."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return {"dsn": database_url}
    return {
        "dbname":   os.getenv("PG_DB_NAME",   os.getenv("PGDATABASE", "insurance_db")),
        "user":     os.getenv("PG_USER",       os.getenv("PGUSER",     "postgres")),
        "password": os.getenv("PG_PASSWORD",   os.getenv("PGPASSWORD", "")),
        "host":     os.getenv("PG_HOST",       os.getenv("PGHOST",     "localhost")),
        "port":     int(os.getenv("PG_PORT",   os.getenv("PGPORT",     "5432"))),
    }

def wait_for_db(max_retries=15, delay=4):
    """Wait for Postgres to be ready (Railway provisions it async)."""
    params = get_conn_params()
    for attempt in range(1, max_retries + 1):
        try:
            conn = psycopg2.connect(**params)
            conn.close()
            print(f"✅ Database ready (attempt {attempt})")
            return True
        except OperationalError as e:
            print(f"⏳ Waiting for database... attempt {attempt}/{max_retries}: {e}")
            time.sleep(delay)
    print("❌ Database never became ready.")
    return False

def init_schema():
    """Run the schema setup from creating_postgres_database.py if it exists."""
    if os.path.exists("creating_postgres_database.py"):
        print("🏗️  Running schema initialization...")
        import importlib.util
        spec = importlib.util.spec_from_file_location("creating_postgres_database", "creating_postgres_database.py")
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
            print("✅ Schema initialized.")
        except Exception as e:
            print(f"⚠️  Schema init warning (may already exist): {e}")
    else:
        print("ℹ️  creating_postgres_database.py not found — skipping schema init.")

if __name__ == "__main__":
    print("🚀 Railway startup: initializing database...")
    if not wait_for_db():
        sys.exit(1)
    init_schema()
    print("✅ Init complete.")
