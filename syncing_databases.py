import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from openai import OpenAI
from pymilvus import Collection, connections
import json
import time
from threading import Timer, Event, Thread, Lock
import os
from dotenv import load_dotenv
from milvus_adapter import get_milvus_client, get_pg_connection

load_dotenv()

# Validate environment variables (DATABASE_URL is acceptable too)
if not os.getenv("DATABASE_URL"):
    required_vars = ["PG_DB_NAME", "PG_USER", "PG_PASSWORD", "PG_HOST", "PG_PORT"]
    for var in required_vars:
        if not os.getenv(var):
            raise ValueError(f"Missing required environment variable: {var}")

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("Missing required environment variable: OPENAI_API_KEY")

# Set up OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

try:
    # Connect to PostgreSQL (handles DATABASE_URL or individual vars)
    conn = get_pg_connection()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # Verify table exists
    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'insurance_policies')")
    if not cur.fetchone()[0]:
        raise Exception("Table 'insurance_policies' does not exist")

    # Create trigger function
    cur.execute("""
        CREATE OR REPLACE FUNCTION notify_insurance_policy_change() RETURNS TRIGGER AS $$
        BEGIN
            PERFORM pg_notify('insurance_policy_change', row_to_json(NEW)::text);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger
    cur.execute("""
        CREATE OR REPLACE TRIGGER insurance_policy_change_trigger
        AFTER INSERT OR UPDATE ON insurance_policies
        FOR EACH ROW EXECUTE FUNCTION notify_insurance_policy_change();
    """)

    # Listen for notifications
    cur.execute("LISTEN insurance_policy_change;")

    # Connect to Milvus (handles cloud vs local automatically)
    get_milvus_client()
    collection = Collection("insurance_policy_embeddings")

    # Thread-safe notifications list
    notifications = []
    notifications_lock = Lock()
    stop_event = Event()

    def get_openai_embedding(text):
        try:
            response = openai_client.embeddings.create(
                input=text,
                model="text-embedding-3-large"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return None

    def process_notifications():
        global notifications
        with notifications_lock:
            if notifications:
                current_batch = notifications.copy()
                notifications = []
            else:
                current_batch = []

        if current_batch:
            print(f"Processing {len(current_batch)} notifications")
            processed_ids = set()

            for notify in current_batch:
                try:
                    data = json.loads(notify.payload)
                    record_id = data['id']

                    if record_id in processed_ids:
                        continue

                    processed_ids.add(record_id)

                    text = (
                        f"{data['customer_name']} {data['policy_type']} "
                        f"{data.get('life_insurance_details', '')} "
                        f"{data.get('home_insurance_details', '')} "
                        f"{data.get('auto_insurance_details', '')}"
                    )

                    embedding = get_openai_embedding(text)
                    if embedding:
                        collection.delete(f"id == {record_id}")
                        collection.insert([{"id": record_id, "embedding": embedding}])
                        collection.flush()
                        print(f"✅ Updated embedding for record ID {record_id}")
                except Exception as e:
                    print(f"Error processing notification: {e}")

        if not stop_event.is_set():
            Timer(5, process_notifications).start()

    def listen_for_stop_command():
        while not stop_event.is_set():
            command = input()
            if command.lower() == "stop":
                stop_event.set()
                break

    # Start processing thread
    process_notifications()

    # Start stop command thread
    stop_thread = Thread(target=listen_for_stop_command)
    stop_thread.daemon = True
    stop_thread.start()

    print("Waiting for notifications on channel 'insurance_policy_change'...")

    while not stop_event.is_set():
        conn.poll()
        while conn.notifies:
            notify = conn.notifies.pop(0)
            with notifications_lock:
                notifications.append(notify)

except Exception as e:
    print(f"Error: {e}")
finally:
    stop_event.set()
    if 'cur' in locals():
        cur.close()
    if 'conn' in locals():
        conn.close()
    try:
        connections.disconnect("default")
    except Exception:
        pass  # Already disconnected or cloud connection — safe to ignore
    print("Program stopped")
