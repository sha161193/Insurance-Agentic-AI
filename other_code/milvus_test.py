from typing import Optional, List
import typer
from agno.embedder.openai import OpenAIEmbedder
from agno.agent import Agent
from agno.knowledge.combined import CombinedKnowledgeBase
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase
from agno.vectordb.milvus import Milvus
from agno.document.chunking.document import DocumentChunking
from agno.storage.postgres import PostgresStorage
from agno.models.google import Gemini
from agno.playground import Playground, serve_playground_app
from rich.prompt import Prompt

import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PG_DB_URL = os.getenv("PG_DB_URL")
storage = PostgresStorage(table_name="agent_sessions", db_url=PG_DB_URL,auto_upgrade_schema=True)

# Initialize Milvus vector database
local_pdf_knowledge_base = PDFKnowledgeBase(
    path="insurance_data_strings.pdf",
    vector_db=Milvus(
        collection="insurance_customers",
        uri="http://localhost:19530",
        embedder=OpenAIEmbedder(id="text-embedding-3-large", api_key=OPENAI_API_KEY)
    ),
    chunking_strategy=DocumentChunking(),
)

url_pdf_knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://www.iii.org/sites/default/files/docs/pdf/Insurance_Handbook_20103.pdf"],
    vector_db=Milvus(
        collection="insurance_details_handbook",
        uri="http://localhost:19530",
        # token="your_token", # Uncomment and replace if your Milvus has authentication
        embedder=OpenAIEmbedder(id="text-embedding-3-large", api_key=OPENAI_API_KEY)
    ),
    chunking_strategy=DocumentChunking(),
)

knowledge_base = CombinedKnowledgeBase(
    sources=[
        local_pdf_knowledge_base,
        url_pdf_knowledge_base,
    ],
    vector_db=Milvus(
        collection="combined_knowledge",
        uri="http://localhost:19530",
        embedder=OpenAIEmbedder(id="text-embedding-3-large", api_key=OPENAI_API_KEY)  
    ),
)

def create_milvus_agent(new: bool = False, user: str = "user"):
    session_id: Optional[str] = None

    try:
        if not new:
            existing_sessions: List[str] = storage.get_all_session_ids(user)
            if len(existing_sessions) > 0:
                session_id = existing_sessions[0]

        agent = Agent(
            model=Gemini(id="gemini-2.0-flash",  api_key=GOOGLE_API_KEY),
            # Fix the session id to continue the same session across execution cycles
            session_id="fixed_id_for_demo",
            storage=storage,
            user_id=user,
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
        )

        if session_id is None:
            session_id = agent.session_id
            print(f"Started Session: {session_id}\n")
        else:
            print(f"Continuing Session: {session_id}\n")

        while True:
            message = Prompt.ask(f"[bold] :sunglasses: {user} [/bold]")
            if message in ("exit", "bye"):
                break
            agent.print_response(message)


    except Exception as e:
        print(f"Error initializing agent: {e}")
        return None

    # Runs the agent as a cli app
    # agent.cli_app(markdown=True)

#app = Playground(agents=[create_milvus_agent()]).get_app()

if __name__ == "__main__":
    # Comment out after first run
    knowledge_base.load(recreate=True)

    typer.run(create_milvus_agent)