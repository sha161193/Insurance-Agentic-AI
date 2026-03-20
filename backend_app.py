from typing import Optional, List
from agno.embedder.openai import OpenAIEmbedder
from agno.agent import Agent, RunResponse
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.vectordb.chroma import ChromaDb
from agno.document.chunking.document import DocumentChunking
from agno.document.chunking.agentic import AgenticChunking
from agno.storage.postgres import PostgresStorage
from agno.storage.sqlite import SqliteStorage
from agno.models.google import Gemini
from agno.memory.v2 import Memory
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from flask import Flask, request, jsonify
import traceback
import os
from dotenv import load_dotenv
import google.auth.transport.requests
import google.oauth2.id_token
import json

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PG_DB_URL = os.getenv("PG_DB_URL")
CLIENT_ID = os.getenv("CLIENT_ID")

agent_storage = SqliteStorage(
    table_name="agent_sessions",
    db_file="database_files/agent_storage.db",
    auto_upgrade_schema=True,
)

# Create a SQLite database for memory
memory_db = SqliteMemoryDb(
    table_name="memories",
    db_file="database_files/memory.db",
)

openai_embedder = OpenAIEmbedder(id="text-embedding-3-large", api_key=OPENAI_API_KEY)

knowledge_base = PDFKnowledgeBase(
    path="data",
    vector_db=ChromaDb(
        collection="insurance_customers_details",
        path="database_files/insurance_data",
        persistent_client=True,
        embedder=openai_embedder
    ),
    chunking_strategy=DocumentChunking(),
)

with open("agent_instructions.txt", "r", encoding="utf-8") as f:
    agent_instructions = f.read()

agent = Agent(
    model=Gemini(id="gemini-2.0-flash", api_key=GOOGLE_API_KEY),
    memory=Memory(db=memory_db),  # Explicitly instantiate and pass Memory v2
    storage=agent_storage,
    knowledge=knowledge_base,
    search_knowledge=True,
    add_history_to_messages=True,
    num_history_runs=3,
    num_history_responses=3,
    enable_user_memories=True,
    enable_session_summaries=True,
    read_chat_history=True,
    read_tool_call_history=True,
    enable_agentic_memory=True,
    debug_mode=True,
    instructions=agent_instructions,
    # markdown=True,
)

app = Flask(__name__)

def verify_token(id_token, client_id):
    """Verifies the Google ID token."""
    try:
        request = google.auth.transport.requests.Request()
        claims = google.oauth2.id_token.verify_oauth2_token(
            id_token, request, client_id
        )
        print(f"Claims after verification: {claims}")
        if not claims:
            return None
        return claims
    except ValueError as e:
        print(f"Error verifying token: {e}")
        return None

@app.route('/query', methods=['POST'])
def handle_query():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Unauthorized: Missing or invalid Authorization header"}), 401

    id_token = auth_header.split(' ')[1]

    if not CLIENT_ID:
        return jsonify({"error": "Backend not properly configured: Missing CLIENT_ID environment variable"}), 500

    claims = verify_token(id_token, CLIENT_ID)

    if not claims:
        return jsonify({"error": "Unauthorized: Invalid or expired token"}), 401

    user_id = claims.get('sub') # Google's unique user ID

    data = request.get_json()
    user_input = data.get('user_input')
    if not user_input:
        return jsonify({"error": "Missing user_input"}), 400

    print(f"Received user input from user {user_id}: '{user_input}'")

    try:
        response: RunResponse = agent.run(user_input, user_id=user_id) # Pass user_id for session management

        if response and hasattr(response, 'content'):
            agent_response_text = response.content
        else:
            agent_response_text = "No response content found."
            print(f"Warning: No 'content' attribute found in the RunResponse: {response}")

        return jsonify({"response": agent_response_text})

    except Exception as e:
        error_message = traceback.format_exc()
        print(f"Error in handle_query: {error_message}")
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

if __name__ == "__main__":
    # Comment out after first run if you have loaded the knowledge base
    knowledge_base.load(recreate=False, skip_existing=True)

    app.run(debug=True, port=8000)