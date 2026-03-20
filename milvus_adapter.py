"""
milvus_adapter.py
Drop-in wrapper that connects to either:
  - Local Milvus (MILVUS_USE_CLOUD=false, default for local dev)
  - Zilliz Cloud (MILVUS_USE_CLOUD=true, used on Railway)

Usage in your code:
    from milvus_adapter import get_milvus_client
    client = get_milvus_client()
"""
import os
from dotenv import load_dotenv

load_dotenv()

def get_milvus_client():
    use_cloud = os.getenv("MILVUS_USE_CLOUD", "false").lower() == "true"

    if use_cloud:
        # Zilliz Cloud — free tier available at https://cloud.zilliz.com
        from pymilvus import MilvusClient
        uri   = os.getenv("MILVUS_HOST")          # e.g. https://xxx.api.gcp-us-west1.zillizcloud.com
        token = os.getenv("MILVUS_TOKEN")         # API key from Zilliz console
        if not uri or not token:
            raise ValueError(
                "MILVUS_HOST and MILVUS_TOKEN must be set when MILVUS_USE_CLOUD=true.\n"
                "Get them from https://cloud.zilliz.com"
            )
        client = MilvusClient(uri=uri, token=token)
        print(f"✅ Connected to Zilliz Cloud: {uri}")
        return client
    else:
        # Local / self-hosted Milvus
        from pymilvus import connections
        host = os.getenv("MILVUS_HOST", "localhost")
        port = os.getenv("MILVUS_PORT", "19530")
        connections.connect(host=host, port=port)
        print(f"✅ Connected to local Milvus at {host}:{port}")
        return None   # legacy connections.connect() style; return None for compat


def get_pg_connection():
    """Returns a psycopg2 connection, preferring DATABASE_URL on Railway."""
    import psycopg2
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    return psycopg2.connect(
        dbname   = os.getenv("PG_DB_NAME",  "insurance_db"),
        user     = os.getenv("PG_USER",     "postgres"),
        password = os.getenv("PG_PASSWORD", ""),
        host     = os.getenv("PG_HOST",     "localhost"),
        port     = int(os.getenv("PG_PORT", "5432")),
    )
