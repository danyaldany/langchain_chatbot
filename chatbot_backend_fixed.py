from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import TypedDict, Annotated
from langgraph.checkpoint.sqlite import SqliteSaver
# from langchain_core.messages import HumanMessage, BaseMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage, BaseMessage, SystemMessage
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.tools import tool
import sqlite3
import requests
import os

from dotenv import load_dotenv
load_dotenv()

# ------------------- State ---------------------

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    
llm = ChatGoogleGenerativeAI(model="models/gemini-2.5-flash-lite")

search_tools = DuckDuckGoSearchResults(region='us-en')

# --------------------- Tools -------------------------

# Calculator function
@tool
def calculator(first_num: float, second_num: float, operator: str) -> dict:
    """Perform basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div"""
    try:
        if operator == 'add':
            result = first_num + second_num
        elif operator == 'sub':
            result = first_num - second_num
        elif operator == 'mul':
            result = first_num * second_num
        elif operator == 'div':
            if second_num == 0:
                return {"error": "Divide by zero is not possible"}
            result = first_num / second_num
        else:
            return {'error': f'Unsupported operation: {operator}'} 
        
        return {
            'first_num': first_num, 
            'second_num': second_num, 
            'operator': operator, 
            'result': result
        }
    except Exception as e:
        return {'error': str(e)}

# Stock price fetcher
@tool
def stock(symbols: str) -> dict:
    """Fetch latest stock price for a given symbol (e.g. AAPL, TSLA).
    Uses AlphaVantage API."""
    
    # Validate input
    if not symbols or not symbols.replace('.', '').isalnum() or len(symbols) > 10:
        return {"error": "Invalid stock symbol"}
    
    # Get API key from environment
    api_key = os.getenv('ALPHAVANTAGE_API_KEY', 'KSN55W3NLCMWS51O')
    
    url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbols.upper()}&apikey={api_key}'
    
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        # Check for API errors
        if "Error Message" in data:
            return {"error": data["Error Message"]}
        
        return data
    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

# Create tools list
tools_list = [stock, search_tools, calculator]

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools_list)

# -------------------- Node Functions ----------------

def chat_node(state: ChatState):
    """Main chat node that processes messages with LLM"""
    messages = state['messages']
    
    system_prompt = SystemMessage(content="""You are a helpful AI assistant with access to tools.

IMPORTANT RULES:
- Answer general knowledge questions, roadmaps, explanations, advice, and conversational questions DIRECTLY from your own knowledge. Do NOT use tools for these.
- Only use tools when the user explicitly needs:
  - Real-time stock prices → use `stock` tool
  - Live web search for current news/events → use `search` tool
  - Math calculations → use `calculator` tool
- For questions like "give me a roadmap", "explain X", "what is Y", "how does Z work" → answer DIRECTLY without tools.
- Never ask the user "would you like me to search for that?" for questions you can answer yourself.
""")
    
    response = llm_with_tools.invoke([system_prompt] + messages)
    
    return {'messages': [response]}

# ------------------- Tool Node ------------------

tool_node = ToolNode(tools_list)

# ----------------------- Database -----------------------

conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)

# Create checkpointer
checkpointer = SqliteSaver(conn=conn)

# ---------------- Graph ----------------

graph = StateGraph(ChatState)

# ----------------- Nodes ------------------

graph.add_node('chat_node', chat_node)
graph.add_node('tools', tool_node)

# ----------------- Edges -------------------

graph.add_edge(START, 'chat_node')
graph.add_conditional_edges('chat_node', tools_condition)
graph.add_edge('tools', 'chat_node')
# Note: No direct edge to END - tools_condition handles routing to END

# Compile workflow
workflow = graph.compile(checkpointer=checkpointer)

# Test (commented out)
# if __name__ == "__main__":
#     config = {'configurable': {'thread_id': 'thread-1'}}
#     
#     response = workflow.invoke(
#         {'messages': [HumanMessage(content='Hi my name is dani')]},
#         config=config
#     )
#     
#     print(response)
