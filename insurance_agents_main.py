import streamlit as st
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.team.team import Team
from typing import Dict, Any
import os
import time
from dotenv import load_dotenv

load_dotenv()

openai_api_key = os.environ['OPENAI_API_KEY']

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

def initialize_insurance_agents():
    life_insurance_agent = Agent(
        name="Life Insurance Specialist",
        role="Execute research and analysis on life insurance products, underwriting standards, and mortality risk factors",
        description="""Certified life insurance expert specializing in:
        - Policy comparisons (term/whole/universal life)
        - Medical underwriting and risk assessment
        - Premium calculation methodologies
        - Regulatory compliance (SOA, ACLI standards)
        Maintains up-to-date knowledge of IRS tax treatment of life insurance products""",
        model=OpenAIChat(id="gpt-4o-mini", api_key=openai_api_key),
        tools=[DuckDuckGoTools()],
        instructions="""STRICT PROTOCOLS:
        1. Only respond to life insurance queries
        2. Reject with template: "I specialize exclusively in life insurance. For [queried topic], please consult a [relevant expert]."
        3. Always cite sources for premium/benefit comparisons
        4. Flag outdated regulations automatically""",
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
        model=OpenAIChat(id="gpt-4o-mini", api_key=openai_api_key),
        tools=[DuckDuckGoTools()],
        instructions="""STRICT PROTOCOLS:
        1. Domain-limited to residential/commercial property coverage
        2. Rejection template: "As a property insurance specialist, I cannot advise on [queried topic]."
        3. Always disclose coverage exclusions
        4. Cross-reference with NFIP data for flood-related queries""",
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
        model=OpenAIChat(id="gpt-4o-mini", api_key=openai_api_key),
        tools=[DuckDuckGoTools()],
        instructions="""STRICT PROTOCOLS:
        1. Only address motor vehicle insurance topics
        2. Rejection template: "This query about [topic] falls outside my auto insurance specialization."
        3. Always verify state DOI regulations
        4. Disclose claim impact on premiums""",
        markdown=True,
    )

    coordinator = Team(
        name="Insurance Team Coordinator",
        description="""Master routing system for insurance-related queries that:
        - Validates question relevance to insurance domain
        - Maintains audit trails of specialist assignments
        - Enforces FINRA-style suitability standards
        - Implements fallback protocols for cross-domain queries""",
        mode="route",
        members=[life_insurance_agent, home_insurance_agent, auto_insurance_agent],
        model=OpenAIChat(id="gpt-4o-mini", api_key=openai_api_key),
        instructions="""STRICT DOMAIN CONTROL SYSTEM:

        1. CONTENT VALIDATION LAYERS:
        a) First Filter - Insurance Relevance:
            - Reject with template: "Our specialists only handle insurance matters. Your query about [topic] is outside our scope."
            - Exception: Questions mentioning insurance terms but clearly seeking other information

        b) Second Filter - Request Type:
            - Block: "We cannot process [policy numbers/location requests/entertainment content]"
            - Redirect: "For [non-insurance aspect], please consult a [relevant expert]"

        2. SPECIALIST ROUTING LOGIC:
        ┌───────────────────────┬─────────────────────────────┐
        │ Query Type            │ Routing Destination         │
        ├───────────────────────┼─────────────────────────────┤
        │ Mortality risk        → Life Specialist             │
        │ Property valuation    → Home Specialist            │
        │ Vehicle liability     → Auto Specialist            │
        │ Cross-domain          → Multi-specialist review    │
        └───────────────────────┴─────────────────────────────┘

        3. COMPLIANCE ENFORCEMENT:
        a) Absolute Restrictions:
            - No financial advice beyond insurance products
            - No interpretation of medical/legal documents
            - No third-party recommendations

        b) Required Disclosures:
            - "This analysis covers insurance only - consult [professional] for other advice"
            - "Premium estimates may vary based on [factors]"

        FAILSAFE: When uncertain → "Please rephrase your question focusing specifically on insurance coverage details"
        """,
        markdown=True,
    )

    return coordinator

def main():
    set_custom_css()

    st.title("🛡️ Insurance Specialist Assistant")
    st.markdown("""
    Welcome to your AI-powered insurance advisory system! Our certified specialists can help with:
    - 🏠 Homeowners/Property insurance coverage analysis
    - 🚗 Auto insurance policy comparisons
    - 💼 Life insurance underwriting guidance
    - ⚖️ Claims process explanations
    """)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

    if prompt := st.chat_input("Ask your insurance question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        insurance_coordinator = initialize_insurance_agents()

        with st.chat_message("assistant"):
            response_container = st.empty()
            full_response = ""

            try:
                if not is_insurance_related(prompt):
                    full_response = """🚫 <span style="color:red">Insurance Domain Restriction</span>

Our specialists only handle insurance-related inquiries. Your question about:
'<i>{}</i>'
falls outside our scope.
""".format(prompt[:100] + ("..." if len(prompt) > 100 else ""))
                else:
                    response = insurance_coordinator.run(prompt)

                    if hasattr(response, 'content'):
                        response_content = response.content
                    else:
                        response_content = str(response)

                    for i in range(0, len(response_content), 5):
                        chunk = response_content[:i+5]
                        response_container.markdown(chunk + "▌", unsafe_allow_html=True)
                        time.sleep(0.02)

                    full_response = response_content

            except Exception as e:
                full_response = f"""⚠️ <span style="color:orange">Insurance Advisory System Error</span>

Our specialists encountered an issue processing your insurance query:
<code>{str(e)}</code>

Please rephrase your question or try again later."""

            response_container.markdown(full_response, unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

def is_insurance_related(prompt: str) -> bool:
    insurance_keywords = {
        'life': ['life insurance', 'term life', 'whole life', 'death benefit', 'underwriting'],
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
