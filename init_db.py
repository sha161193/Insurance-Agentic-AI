"""
init_db.py — Railway startup script
"""
import os
import sys
import time
import psycopg2
from psycopg2 import OperationalError

def get_conn_params():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Railway injects postgres:// but psycopg2 needs postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        print(f"✅ Using DATABASE_URL: {database_url[:40]}...")
        return {"dsn": database_url}

    # Fallback to individual vars
    host = os.environ.get("PGHOST") or os.environ.get("PG_HOST", "localhost")
    port = os.environ.get("PGPORT") or os.environ.get("PG_PORT", "5432")
    dbname = os.environ.get("PGDATABASE") or os.environ.get("PG_DB_NAME", "railway")
    user = os.environ.get("PGUSER") or os.environ.get("PG_USER", "postgres")
    password = os.environ.get("PGPASSWORD") or os.environ.get("PG_PASSWORD", "")

    print(f"✅ Using individual vars: host={host}, port={port}, dbname={dbname}, user={user}")
    return {"host": host, "port": int(port), "dbname": dbname, "user": user, "password": password}

def wait_for_db(max_retries=15, delay=4):
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
    print("🔍 Environment check:")
    print(f"   DATABASE_URL present: {'DATABASE_URL' in os.environ}")
    print(f"   PGHOST present: {'PGHOST' in os.environ}")
    print(f"   PGUSER present: {'PGUSER' in os.environ}")

    if not wait_for_db():
        sys.exit(1)
    init_schema()
    print("✅ Init complete.")
