# app.py
import uuid
from datetime import datetime, timezone
import streamlit as st
import asyncio
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
#from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

# Load environment variables
load_dotenv()

# import nest_asyncio
# nest_asyncio.apply()

st.set_page_config(page_title="Money Assistant", page_icon="💸")

st.title("💸 Money Assistant")

PROMPT = """
            You are a multilingual personal finance assistant that helps customers understand their finances and recommends suitable products based on their spending patterns. 

            **CORE BEHAVIOR:**
            - ALWAYS use the `get_money_info` tool first when users ask about balances, transactions, or financial status
            - Use the `get_products` tool to access current product catalog when making recommendations
            - Analyze spending patterns from transaction data to suggest relevant products
            - Be conversational and helpful, not pushy about products

            **FRAUD DETECTION APPROACH:**
            •⁠  ⁠If the user's question mentions suspicious transactions, fraud, chargebacks, or abnormal behavior,
                ALWAYS call the FraudAgent (get transaction score, check application fraud).
            If the user says things like "I didn’t make my last transaction", "The last two transactions are not mine",
              or "The YouTube payment is not mine", ALWAYS call the get_money_info tool to retrieve the relevant transaction(s).
              Then, show the suspected transaction(s) with: "Are you referring to this transaction?" 
              → If the user confirms (Yes), respond with: 
                "We have reported this issue to our customer service team. They will be in touch with you as soon as possible today."
              → If the user says "No", show the next most relevant recent transaction(s) using get_money_info and ask again.
              → If the user still says "No", respond with: 
                "Understood. We have reported this issue to our customer service team. They will be in touch with you as soon as possible today."

            **PRODUCT RECOMMENDATION APPROACH:**
            1. First understand the customer's financial situation using money data
            2. Identify spending patterns and potential opportunities
            3. Call `get_products` tool to see what's available
            4. Make personalized recommendations based on actual data
            5. Explain benefits clearly and let customers decide

            **LANGUAGE HANDLING:**
            If the user's message is not in English, always use the `detect_language` and `translate` tools to translate it to English before answering, and then translate your answer back.

            **TOOL USAGE:**
            Call tools proactively. Don't make assumptions about products - always check with the tools first.
        """

# MCP Tool server konfigürasyonu
tool_configs = {
    "MoneyAgent": {
        "url": "http://localhost:8003/mcp",
        "transport": "streamable_http"
    },
    "TranslationAgent": {
        "url": "http://localhost:8002/mcp",
        "transport": "streamable_http"
    },
    "ProductAgent": {
        "url": "http://localhost:8004/mcp",
        "transport": "streamable_http"
    },
    "FraudAgent": {
        "url": "http://localhost:8005/mcp",
        "transport": "streamable_http"
    }

}

# Generate a thread_id if it doesn't exist
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())


# Agent setup
@st.cache_resource
def setup_agent():
    llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
    client = MultiServerMCPClient(tool_configs)
    tools = asyncio.run(client.get_tools())
    checkpointer = InMemorySaver()
    agent = create_react_agent(
        model=llm,
        tools=tools,
        checkpointer=checkpointer,
        prompt=PROMPT)
    return agent

agent = setup_agent()

config = {
        "configurable": {
            "thread_id": st.session_state.thread_id,
        }
    }

# UI
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

user_input = st.chat_input("Ask your assistant something...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)
    with st.chat_message("assistant"):
        async def process_stream():
            all_chunks = []
            async for chunk in agent.astream(
                {"messages": [HumanMessage(content=user_input)]},
                stream_mode="updates", config=config
            ):
                all_chunks.append(chunk)
                print(chunk)
            
            # Find the final response from all chunks
            final_response = ""
            for chunk in reversed(all_chunks):
                if 'agent' in chunk and 'messages' in chunk['agent']:
                    messages = chunk['agent']['messages']
                    for message in messages:
                        if hasattr(message, 'content') and message.content and message.content.strip():
                            final_response = message.content
                            break
                    if final_response:
                        break
            
            if final_response:
                st.session_state.messages.append({"role": "assistant", "content": final_response})
                st.write(final_response)
            else:
                st.write("Your request is being processed...")
        
        asyncio.run(process_stream())