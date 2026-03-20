# 🚀 Railway Deployment Guide — Insurance Specialist AI

## Architecture on Railway

```
Railway Project
├── 🐍 App Service        (Streamlit + AI agents)
├── 🐘 PostgreSQL Plugin  (managed by Railway)
└── ☁️  Zilliz Cloud      (external — free Milvus-compatible service)
```

> **Why Zilliz Cloud instead of self-hosted Milvus?**
> Railway doesn't support Docker-compose sidecars or custom TCP ports needed
> by Milvus. Zilliz Cloud is the official Milvus cloud service — free tier
> gives you 1 cluster with 1GB storage, which is plenty to start.

---

## Step 1 — Get a Zilliz Cloud account (5 min)

1. Go to **https://cloud.zilliz.com** → Sign up free
2. Create a new **Serverless Cluster** (free tier)
3. Copy the **Public Endpoint** (looks like `https://xxx.api.gcp-us-west1.zillizcloud.com`)
4. Go to **API Keys** → Create a key → Copy it

---

## Step 2 — Prepare your GitHub repo

Add these files to your repo root (all provided in this package):

```
your-repo/
├── railway.toml              ← Railway build + start config
├── nixpacks.toml             ← Python build config
├── requirements.txt          ← Python dependencies
├── init_db.py                ← Startup DB initializer
├── milvus_adapter.py         ← Cloud/local Milvus switcher
├── .streamlit/
│   └── config.toml           ← Streamlit server config
├── .env.example              ← Reference (do NOT commit .env)
├── creating_postgres_database.py   ← your existing file
├── first_vector_embedding.py       ← your existing file
├── syncing_databases.py            ← your existing file
└── insurance_agents_main.py        ← your existing Streamlit app
```

**Update your existing files** to use `milvus_adapter.py`:

```python
# In first_vector_embedding.py and syncing_databases.py, replace:
from pymilvus import connections
connections.connect(host=..., port=...)

# With:
from milvus_adapter import get_milvus_client, get_pg_connection
client = get_milvus_client()
conn = get_pg_connection()
```

---

## Step 3 — Deploy on Railway

### Option A — Railway Dashboard (easiest)

1. Go to **https://railway.app** → New Project
2. **Deploy from GitHub repo** → select your repo
3. Railway auto-detects Python → click **Add Plugin → PostgreSQL**
4. Go to **Variables** tab → add these:

| Variable | Value |
|---|---|
| `MILVUS_USE_CLOUD` | `true` |
| `MILVUS_HOST` | your Zilliz endpoint URL |
| `MILVUS_TOKEN` | your Zilliz API key |
| `OPENAI_API_KEY` | your OpenAI key |
| `GROQ_API_KEY` | your Groq key |

> PostgreSQL vars (`PGHOST`, `PGPASSWORD`, etc.) are **auto-injected** by
> Railway when you add the PostgreSQL plugin — you don't need to set them.

5. Click **Deploy** → watch the build logs

### Option B — Railway CLI

```bash
# Install CLI
npm install -g @railway/cli

# Login
railway login

# Create project
railway init

# Add Postgres
railway add --plugin postgresql

# Set environment variables
railway variables set MILVUS_USE_CLOUD=true
railway variables set MILVUS_HOST=https://your-cluster.zillizcloud.com
railway variables set MILVUS_TOKEN=your-token
railway variables set OPENAI_API_KEY=sk-...
railway variables set GROQ_API_KEY=gsk_...

# Deploy
railway up
```

---

## Step 4 — Verify deployment

1. Railway will show a public URL like `https://insurance-ai.up.railway.app`
2. Open it — Streamlit should load within 30 seconds
3. Check **Deploy Logs** if anything fails

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Connection refused` on Postgres | Wait 60s — Railway provisions DB async |
| `MILVUS_HOST not set` | Add env vars in Railway dashboard → Variables |
| App crashes on startup | Check logs for missing env var names |
| Streamlit shows blank page | Ensure `--server.headless true` is in start command |
| `ModuleNotFoundError` | Add missing package to `requirements.txt` |

---

## Cost estimate

| Service | Cost |
|---|---|
| Railway Hobby plan | $5/month + usage |
| Railway PostgreSQL | ~$0–5/month (depends on size) |
| Zilliz Cloud free tier | $0 |
| OpenAI API | Pay per use |
| Groq API | Free tier available |

---

## Local dev (unchanged)

```bash
# Still works exactly as before
docker run milvus ...         # local Milvus
python creating_postgres_database.py
python first_vector_embedding.py
python syncing_databases.py &
streamlit run insurance_agents_main.py
```

Set `MILVUS_USE_CLOUD=false` (or omit it) in your local `.env`.
