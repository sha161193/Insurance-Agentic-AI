import streamlit as st
from agno.agent import Agent
# from agno.models.groq import Groq # Removed Groq import
# from agno.tools.duckduckgo import DuckDuckGoTools # Removed DuckDuckGoTools import
from agno.team.team import Team
# from agno.vectordb.milvus import Milvus # Using custom Milvus interaction
from typing import Dict, Any
import os
import time
from dotenv import load_dotenv
import google.generativeai as genai
# from pymilvus import connections, Collection # Removed direct pymilvus import
from openai import OpenAI
from agno.vectordb.milvus import Milvus
from agno.embedder.openai import OpenAIEmbedder

load_dotenv()

# Gemini API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
GEMINI_MODEL_NAME = "gemini-2.0-flash"

# OpenAI API Key for embeddings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSION = 1536
MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
MILVUS_COLLECTION_NAME = "insurance_customers"

# Initialize agno Milvus integration
vector_db = Milvus(
    collection=MILVUS_COLLECTION_NAME,
    uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}",
    embedder=OpenAIEmbedder(api_key=OPENAI_API_KEY, dimensions=EMBEDDING_DIMENSION),
    distance="L2"  # Assuming L2 distance, adjust if needed
)

# Custom Tool implementation since agno.tools.base isn't available
class Tool:
    name: str = ""
    description: str = ""

    def _run(self, *args, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement this method")

class TransferTaskTool(Tool):
    name: str = "transfer_task_to_specialist"
    description: str = "Routes the task to the appropriate insurance specialist based on the query type"

    def _run(self, task_description: str, expected_output: str, additional_information: str = "") -> Dict[str, Any]:
        return {
            "status": "routed",
            "task": task_description,
            "instructions": additional_information
        }

# Placeholder for DuckDuckGoTools (as it's not directly used in the combined logic)
class DuckDuckGoTools(Tool):
    name: str = "duckduckgo_search"
    description: str = "Performs a DuckDuckGo search."

    def _run(self, query: str) -> str:
        return "DuckDuckGo search results (placeholder)"

# Modified Milvus interaction using agno
def search_insurance_data(query: str):
    """Searches the Milvus database for relevant insurance customer data using agno's Milvus integration."""
    try:
        results = vector_db.search(
            query=query,
            limit=3,
            output_fields=["customer_name", "policy_types", "metadata"]
        )

        formatted_results = []
        for hit in results:
            entity = hit.entity
            metadata = entity.get('metadata', {})
            formatted_results.append(f"Customer: {entity.get('customer_name', 'N/A')}, "
                                     f"Policies: {entity.get('policy_types', 'N/A')}, "
                                     f"Email: {metadata.get('email', 'N/A')}, "
                                     f"Phone: {metadata.get('phone', 'N/A')}")
        return "\n".join(formatted_results)

    except Exception as e:
        print(f"Error during agno Milvus search: {e}")
        return ""

def answer_with_context(query: str, context: str):
    """Generates an answer to the query based on the provided context using Gemini."""
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
    prompt = f"""You are a helpful chatbot that answers questions based on the following insurance customer information:

{context}

Answer the following question: {query}
If the information is not present, say "I don't have information about that."
"""
    response = model.generate_content(prompt)
    return response.text

# Set up custom CSS
def set_custom_css():
    st.markdown("""
    <style>
        .main {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        .stTextInput input {
            border-radius: 20px;
            padding: 10px 15px;
        }
        .chat-message {
            padding: 1.5rem;
            border-radius: 15px;
            margin-bottom: 1rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .user-message {
            background: #ffffff;
            border: 1px solid #e0e0e0;
        }
        .bot-message {
            background: #007bff;
            color: white;
        }
        .stMarkdown table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
        }
        .stMarkdown th {
            background-color: #007bff;
            color: white;
        }
        .stMarkdown td, .stMarkdown th {
            padding: 12px;
            border: 1px solid #ddd;
            text-align: left;
        }
    </style>
    """, unsafe_allow_html=True)

# Initialize agents
def initialize_insurance_agents():
    life_insurance_agent = Agent(
        name="Life Insurance Specialist",
        role="Execute research and analysis on life insurance products, underwriting standards, and mortality risk factors",
        description="""Certified life insurance expert specializing in:
        - Policy comparisons (term/whole/universal life)
        - Medical underwriting and risk assessment
        - Premium calculation methodologies
        - Regulatory compliance (SOA, ACLI standards)
        - Maintains up-to-date knowledge of IRS tax treatment of life insurance products""",
        model=GEMINI_MODEL_NAME, # Using Gemini 2.0 Flash
        tools=[DuckDuckGoTools()], # Placeholder tool
        instructions="""STRICT PROTOCOLS:
        1. Only respond to life insurance queries
        2. Reject with template: "I specialize exclusively in life insurance. For [queried topic], please consult a [relevant expert]."
        3. Always cite sources for premium/benefit comparisons
        4. Flag outdated regulations automatically""",
        show_tool_calls=True,
        markdown=True,
    )

    home_insurance_agent = Agent(
        name="Home Insurance Specialist",
        role="Analyze property insurance coverages, claims processes, and regional risk factors",
        description="""Licensed property insurance advisor with expertise in:
        - HO-3 vs HO-5 policy structures
        - Catastrophic loss modeling (flood, earthquake, wildfire)
        - Replacement cost vs actual cash value
        - FAIR Plan eligibility requirements""",
        model=GEMINI_MODEL_NAME, # Using Gemini 2.0 Flash
        tools=[DuckDuckGoTools()], # Placeholder tool
        instructions="""STRICT PROTOCOLS:
        1. Domain-limited to residential/commercial property coverage
        2. Rejection template: "As a property insurance specialist, I cannot advise on [queried topic]."
        3. Always disclose coverage exclusions
        4. Cross-reference with NFIP data for flood-related queries""",
        show_tool_calls=True,
        markdown=True,
    )

    auto_insurance_agent = Agent(
        name="Auto Insurance Specialist",
        role="Process vehicle insurance inquiries with emphasis on state-specific compliance",
        description="""ASE-certified auto insurance analyst covering:
        - Comparative fault state regulations
        - Telematics and usage-based insurance
        - Total loss threshold calculations
        - Rideshare endorsement requirements""",
        model=GEMINI_MODEL_NAME, # Using Gemini 2.0 Flash
        tools=[DuckDuckGoTools()], # Placeholder tool
        instructions="""STRICT PROTOCOLS:
        1. Only address motor vehicle insurance topics
        2. Rejection template: "This query about [topic] falls outside my auto insurance specialization."
        3. Always verify state DOI regulations
        4. Disclose claim impact on premiums""",
        show_tool_calls=True,
        markdown=True,
    )

    # Create coordinator with routing tool
    coordinator = Team(
        name="Insurance Team Coordinator",
        description="""Master routing system for insurance-related queries that:
        - Validates question relevance to insurance domain
        - Maintains audit trails of specialist assignments
        - Enforces suitability standards
        - Implements fallback protocols for cross-domain queries
        - Facilitates retrieval of customer insurance data""", # Modified description
        mode="route",
        members=[life_insurance_agent, home_insurance_agent, auto_insurance_agent],
        model=GEMINI_MODEL_NAME, # Using Gemini 2.0 Flash
        instructions="""STRICT DOMAIN CONTROL AND DATA ACCESS SYSTEM:

        1. CONTENT VALIDATION LAYERS:
        a) First Filter - Insurance Relevance:
            - Reject with template: "Our specialists only handle insurance matters. Your query about [topic] is outside our scope."
            - Exception: Questions mentioning insurance terms but clearly seeking other information (creative writing, dining, etc.)

        b) Second Filter - Request Type: (Further Modified)
            - Allow: Queries seeking insurance-related information about specific customers, such as their policies, coverage details, and contact information.
            - Block: Requests for non-insurance related information, location data unrelated to policies, and entertainment content. Policy numbers should only be provided if explicitly found within the retrieved customer data and deemed appropriate based on context and security protocols.
            - Redirect: "For [non-insurance aspect], please consult a [relevant expert]"

        2. QUERY PROCESSING PROTOCOLS:
        a) For Valid Insurance Queries (including customer data requests):
            - If the query asks for information about a specific customer's insurance (including policy details):
                - The coordinator will attempt to retrieve relevant information using internal tools (like the `search_insurance_data` function).
                - If found, the coordinator will use the `answer_with_context` function to provide the information. The response should include policy numbers only if they are part of the retrieved customer data.
                - If not found, the coordinator will respond: "I don't have specific information about that customer."
            - For other insurance-related queries:
                - Use transfer_task_to_specialist tool with parameters:
                    * task_description: The exact insurance question
                    * expected_output: Required response format
                    * additional_information: "STRICTLY ADHERE TO: [specialist domain]"

        b) For Mixed Queries:
            - Process ONLY the insurance portion
            - Response prefix: "Regarding the insurance aspect: [answer]. Other questions require different experts."

        3. SPECIALIST ROUTING LOGIC:
        ┌───────────────────────┬─────────────────────────────┐
        │ Query Type                │ Routing Destination             │
        ├───────────────────────┼─────────────────────────────┤
        │ Mortality risk            → Life Specialist             │
        │ Property valuation        → Home Specialist             │
        │ Vehicle liability         → Auto Specialist             │
        │ Customer Data Inquiry     → Internal Data Retrieval     │ # Implicitly handled by coordinator
        │ Cross-domain            → Multi-specialist review     │
        └───────────────────────┴─────────────────────────────┘

        4. COMPLIANCE ENFORCEMENT:
        a) Absolute Restrictions:
            - No financial advice beyond insurance products
            - No interpretation of medical/legal documents
            - No third-party recommendations

        b) Required Disclosures:
            - "This analysis covers insurance only - consult [professional] for other advice"
            - "Premium estimates may vary based on [factors]"

        5. SECURITY PROTOCOLS:
        a) Data Handling:
            - Handle customer data queries responsibly and provide relevant information retrieved.
            - Flag queries requesting highly sensitive personal information beyond basic insurance details for review.
            - Policy numbers should be treated with sensitivity and provided only if directly relevant to the user's core insurance inquiry and present in the retrieved data.

        b) Audit Trail:
            - Log all routing decisions and data access.
            - Flag borderline cases for review.

        6. EDGE CASE HANDLING:
        a) Creative Contexts:
            - Template: "We cannot provide [creative writing/historical/entertainment] guidance.
                              While your question mentions [insurance term], please consult a [relevant expert]."
            - NO additional tips or commentary

        b) Hypotheticals:
            - "For hypothetical scenarios, we can only provide general product information"

        c) Historical Questions:
            - "Historical insurance practices may differ significantly from current standards"

        FAILSAFE: When uncertain → "Please rephrase your question focusing specifically on insurance coverage details or customer insurance information."
        """,
        enable_agentic_context=True,
        show_tool_calls=True,
        markdown=True,
        show_members_responses=True,
    )

    return coordinator

# Streamlit app
def main():
    set_custom_css()

    st.title("🛡️ Insurance Specialist Assistant")
    st.markdown("""
    Welcome to your AI-powered insurance advisory system! Our certified specialists can help with:
    - 🏠 Homeowners/Property insurance coverage analysis
    - 🚗 Auto insurance policy comparisons
    - 💾 Information retrieval from customer data
    - ⚖️ Claims process explanations
    """)

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

    # Get user input
    if prompt := st.chat_input("Ask your insurance question..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Initialize insurance agent team
        insurance_coordinator = initialize_insurance_agents()

        # Generate response
        with st.chat_message("assistant"):
            response_container = st.empty()
            full_response = ""

            try:
                context = search_insurance_data(prompt)
                if context:
                    full_response = answer_with_context(prompt, context)
                elif is_insurance_related(prompt):
                    response = insurance_coordinator.run(prompt)
                    print(f"Raw Agent Response: {response}") # Keep this for debugging

                    if hasattr(response, 'content'):
                        response_content = response.content
                    else:
                        response_content = str(response)

                    for i in range(0, len(response_content), 5):
                        chunk = response_content[:i+5]
                        response_container.markdown(chunk + "▌", unsafe_allow_html=True)
                        time.sleep(0.02)
                    full_response = response_content
                else:
                    full_response = """🚫 <span style="color:red">Insurance Domain Restriction</span>

Our specialists only handle insurance-related inquiries. Your question about:
'<i>{}</i>'
falls outside our scope.
""".format(prompt[:100] + ("..." if len(prompt) > 100 else ""))

            except Exception as e:
                full_response = f"""⚠️ <span style="color:orange">Insurance Advisory System Error</span>

Our specialists encountered an issue processing your insurance query:
<code>{str(e)}</code>
Please rephrase your question or try again later."""
                print(f"Main Function Error: {e}") # Log the error in the main function as well

            response_container.markdown(full_response, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

def is_insurance_related(prompt: str) -> bool:
    """Check if the user query is insurance-related"""
    insurance_keywords = {
        'life': ['life insurance', 'term life', 'whole life', 'death benefit', 'underwriting', 'premium'],
        'home': ['home insurance', 'property insurance', 'dwelling coverage', 'HO-3', 'HO-5'],
        'auto': ['auto insurance', 'car insurance', 'liability coverage', 'collision', 'comprehensive']
    }
    prompt_lower = prompt.lower()
    return any(
        keyword in prompt_lower
        for category in insurance_keywords.values()
        for keyword in category
    )

if __name__ == "__main__":
    main()