import streamlit as st
from chatbot_backend_fixed import workflow
from langchain_core.messages import HumanMessage, messages_from_dict
import uuid
import sqlite3
import json
import time
import os
from datetime import datetime

# Constants
DB_PATH = "chatbot.db"
MAX_TITLE_LENGTH = 30

# -----------------------------
# Database Helpers
# -----------------------------

def get_current_timestamp():
    """Get current timestamp as float"""
    return time.time()

def generate_title(text, max_len=MAX_TITLE_LENGTH):
    """Generate a title from text"""
    if not text or not isinstance(text, str):
        return "New Chat"
    
    # Clean the text
    text = str(text).strip().split("\n")[0]
    text = text.replace("#", "").replace("*", "").replace("`", "").strip()
    
    if len(text) > max_len:
        return text[:max_len].strip() + "..."
    return text if text else "New Chat"

def load_threads_from_db():
    """Load all threads from database"""
    threads = {}
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if checkpoints table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]
        
        if 'checkpoints' not in tables:
            conn.close()
            return threads
        
        # Check columns in checkpoints table
        cursor.execute("PRAGMA table_info(checkpoints)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Get thread_ids
        thread_ids = []
        
        if 'thread_id' in column_names:
            cursor.execute("SELECT DISTINCT thread_id FROM checkpoints")
            thread_ids = [row[0] for row in cursor.fetchall()]
        
        for thread_id in thread_ids:
            try:
                # Get the earliest checkpoint for this thread
                cursor.execute(
                    "SELECT checkpoint FROM checkpoints WHERE thread_id = ? ORDER BY rowid ASC LIMIT 1",
                    (thread_id,)
                )
                result = cursor.fetchone()
                
                title = "New Chat"
                
                if result:
                    raw_data = result[0]
                    
                    # Handle byte data
                    if isinstance(raw_data, bytes):
                        try:
                            raw_data = raw_data.decode('utf-8')
                        except UnicodeDecodeError:
                            raw_data = raw_data.decode('utf-8', errors='ignore')
                    
                    # Try to parse JSON and extract first human message
                    try:
                        data = json.loads(raw_data)
                        
                        # Look for messages in different possible locations
                        messages_data = None
                        if 'values' in data and 'messages' in data['values']:
                            messages_data = data['values']['messages']
                        elif 'channel_values' in data and 'messages' in data['channel_values']:
                            messages_data = data['channel_values']['messages']
                        elif 'messages' in data:
                            messages_data = data['messages']
                        
                        if messages_data:
                            # Convert to messages
                            messages = messages_from_dict(messages_data)
                            for msg in messages:
                                if msg.type == "human" and msg.content:
                                    title = generate_title(msg.content)
                                    break
                    except json.JSONDecodeError:
                        # Try to extract title from raw string
                        if isinstance(raw_data, str):
                            if 'human' in raw_data.lower() or 'user' in raw_data.lower():
                                lines = raw_data.split('\n')
                                for line in lines:
                                    if 'content' in line.lower() and len(line) > 20:
                                        parts = line.split(':')
                                        if len(parts) > 1:
                                            potential_content = parts[-1].strip()
                                            if len(potential_content) > 5:
                                                title = generate_title(potential_content)
                                                break
                    except Exception as e:
                        print(f"Error parsing checkpoint: {e}")
                
                # Get last activity timestamp
                last_active = get_current_timestamp()
                
                # Try to get timestamp from rowid
                cursor.execute(
                    "SELECT MAX(rowid) FROM checkpoints WHERE thread_id = ?",
                    (thread_id,)
                )
                max_rowid = cursor.fetchone()[0]
                if max_rowid:
                    last_active = float(max_rowid)
                
                threads[thread_id] = {
                    "title": title,
                    "last": last_active,
                    "pinned": False
                }
                
            except Exception as e:
                print(f"Error loading thread {thread_id}: {e}")
                continue
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Unexpected error loading threads: {e}")
    
    return threads

def delete_thread_from_db(thread_id):
    """Delete a thread from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error deleting thread: {e}")
        return False

def save_thread_title(thread_id, title):
    """Save thread title persistently"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create titles table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_titles (
                thread_id TEXT PRIMARY KEY,
                title TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert or update title
        cursor.execute("""
            INSERT OR REPLACE INTO chat_titles (thread_id, title) 
            VALUES (?, ?)
        """, (thread_id, title))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error saving title: {e}")
        return False

def save_thread_pin(thread_id, pinned):
    """Save pinned state persistently"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_pins (
                thread_id TEXT PRIMARY KEY,
                pinned INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            INSERT OR REPLACE INTO chat_pins (thread_id, pinned)
            VALUES (?, ?)
        """, (thread_id, int(pinned)))

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Error saving pin state: {e}")
        return False

def load_thread_pins():
    """Load pinned states"""
    pins = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='chat_pins'
        """)

        if cursor.fetchone():
            cursor.execute("SELECT thread_id, pinned FROM chat_pins")
            for row in cursor.fetchall():
                pins[row[0]] = bool(row[1])

        conn.close()
    except sqlite3.Error as e:
        print(f"Error loading pins: {e}")

    return pins

def load_thread_titles():
    """Load thread titles from persistent storage"""
    titles = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if titles table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_titles'")
        if cursor.fetchone():
            cursor.execute("SELECT thread_id, title FROM chat_titles")
            for row in cursor.fetchall():
                titles[row[0]] = row[1]
        
        conn.close()
    except sqlite3.Error as e:
        print(f"Error loading titles: {e}")
    
    return titles

# -----------------------------
# Custom CSS for Color Theme
# -----------------------------

def apply_custom_theme():
    custom_css = """
    <style>
    /* ========== APP BACKGROUND ========== */
    .stApp {
        background-color: #FFFFFF;
    }

    /* ========== SIDEBAR ========== */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 3px solid #FB5656 !important;
    }

    /* Sidebar titles */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div {
        color: black !important;
    }

    /* ========== CHAT HISTORY BUTTONS ========== */
    div[data-testid="stButton"] > button {
        background: linear-gradient(135deg, #ff5f6d, #ffc371);
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px;
        padding: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    div[data-testid="stButton"] > button:hover {
        transform: scale(1.03);
        background: linear-gradient(135deg, #ffc371, #ff5f6d);
    }

    /* Active chat */
    div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #00c6ff, #0072ff) !important;
        color: white !important;
    }

    /* Pin & Delete buttons */
    button:has(svg) {
        background-color: #ffffff !important;
        color: #880d1e !important;
        border-radius: 50%;
        border: none !important;
    }

    button:has(svg):hover {
        background-color: #ffccd5 !important;
    }

    /* ========== CHAT MESSAGES ========== */
    [data-testid="stChatMessage"][aria-label="user"] {
        background-color: #f1f5ff;
        color: #000000;
        border-radius: 15px;
        padding: 12px;
    }

    [data-testid="stChatMessage"][aria-label="assistant"] {
        background-color: #f9f9f9;
        color: #000000;
        border-radius: 15px;
        padding: 12px;
    }

    /* ========== CHAT INPUT ========== */
    .stChatInputContainer {
        background-color: #FFF5F5;
        border-radius: 12px;
        border: 1px solid #ddd;
    }

    /* Remove red text everywhere */
    body, p, span, div {
        color: #000000;
    }

    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

# -----------------------------
# Page Configuration
# -----------------------------

st.set_page_config(
    page_title="LangGraph Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom theme
apply_custom_theme()

# -----------------------------
# Session State Initialization
# -----------------------------

if "initialized" not in st.session_state:
    # Initialize session state
    st.session_state.threads = {}
    st.session_state.current_thread = None
    st.session_state.initialized = True
    
    # Load existing threads from database
    db_threads = load_threads_from_db()
    
    # Load saved titles and pins
    saved_titles = load_thread_titles()
    saved_pins = load_thread_pins()
    
    # Merge saved titles with loaded threads
    for thread_id in db_threads:
        if thread_id in saved_titles and saved_titles[thread_id]:
            db_threads[thread_id]["title"] = saved_titles[thread_id]

        if thread_id in saved_pins:
            db_threads[thread_id]["pinned"] = saved_pins[thread_id]
    
    if db_threads:
        st.session_state.threads = db_threads
        # Set current thread to most recent
        most_recent = max(db_threads.keys(), key=lambda k: db_threads[k]["last"])
        st.session_state.current_thread = most_recent
    else:
        # Create first thread
        tid = str(uuid.uuid4())
        st.session_state.threads[tid] = {
            "title": "New Chat",
            "last": get_current_timestamp(),
            "pinned": False
        }
        st.session_state.current_thread = tid

# -----------------------------
# Sidebar
# -----------------------------

with st.sidebar:
    st.title("🤖 Chat Assistant")
    st.caption("Your AI Conversation Partner")
    
    # New Chat button
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        tid = str(uuid.uuid4())
        st.session_state.threads[tid] = {
            "title": "New Chat",
            "last": get_current_timestamp(),
            "pinned": False
        }
        st.session_state.current_thread = tid
        st.rerun()
    
    st.divider()
    
    # Chat History
    st.subheader("📜 Chat History")
    
    if not st.session_state.threads:
        st.info("No chats yet. Start a conversation!")
    else:
        # Sort threads: pinned first, then by last activity
        sorted_threads = sorted(
            st.session_state.threads.items(),
            key=lambda x: (not x[1]["pinned"], -x[1]["last"])
        )
        
        for idx, (thread_id, data) in enumerate(sorted_threads):
            cols = st.columns([5, 1, 1])
            
            with cols[0]:
                # Display thread title with icon
                icon = "📌 " if data["pinned"] else "💬 "
                display_title = f"{icon}{data['title']}"
                
                is_current = st.session_state.current_thread == thread_id
                
                if st.button(
                    display_title,
                    key=f"select_{thread_id}_{idx}",
                    use_container_width=True,
                    type="primary" if is_current else "secondary"
                ):
                    if not is_current:
                        st.session_state.current_thread = thread_id
                        st.rerun()
            
            with cols[1]:
                # Pin/unpin button
                pin_key = f"pin_{thread_id}_{idx}"
                if st.button(
                    "📌" if not data["pinned"] else "✅",
                    key=pin_key,
                    help="Pin/Unpin chat"
                ):
                    new_pin_state = not data["pinned"]
                    data["pinned"] = new_pin_state
                    st.session_state.threads[thread_id] = data
                    save_thread_pin(thread_id, new_pin_state)
                    st.rerun()

            with cols[2]:
                # Delete button
                del_key = f"del_{thread_id}_{idx}"
                if st.button(
                    "🗑️",
                    key=del_key,
                    help="Delete chat"
                ):
                    if len(st.session_state.threads) > 1:
                        # Delete from database
                        if delete_thread_from_db(thread_id):
                            # Remove from session state
                            if thread_id in st.session_state.threads:
                                del st.session_state.threads[thread_id]
                            
                            # Delete from titles table
                            try:
                                conn = sqlite3.connect(DB_PATH)
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM chat_titles WHERE thread_id = ?", (thread_id,))
                                cursor.execute("DELETE FROM chat_pins WHERE thread_id = ?", (thread_id,))
                                conn.commit()
                                conn.close()
                            except sqlite3.Error as e:
                                print(f"Error deleting metadata: {e}")
                            
                            # Set new current thread if needed
                            if st.session_state.current_thread == thread_id:
                                remaining = list(st.session_state.threads.keys())
                                if remaining:
                                    st.session_state.current_thread = remaining[0]
                            
                            st.rerun()
                    else:
                        st.warning("Cannot delete the only chat")

# -----------------------------
# Main Chat Area
# -----------------------------

current_thread_id = st.session_state.current_thread
current_thread_data = st.session_state.threads.get(current_thread_id, {})

# Scrollable container for chat
chat_container = st.container()

with chat_container:
    try:
        # Get the conversation state from LangGraph
        state = workflow.get_state(
            config={"configurable": {"thread_id": current_thread_id}}
        )

        if state and hasattr(state, 'values') and 'messages' in state.values:
            messages = state.values['messages']

            # Display all messages - simplified without tracking
            for msg in messages:
                if msg.type == "human":
                    with st.chat_message("user"):
                        st.write(msg.content)
                elif msg.type == "ai":
                    with st.chat_message("assistant"):
                        st.write(msg.content)

            if not messages:
                st.info("✨ Start a conversation by typing a message below!")

        else:
            st.info("✨ Start a conversation by typing a message below!")

    except Exception as e:
        print(f"Error loading messages: {e}")
        st.info("👋 Welcome! This is a new chat. Start a conversation below.")

# -----------------------------
# Chat Input
# -----------------------------

user_input = st.chat_input("Type your message here...")

if user_input:
    # Update thread timestamp
    if current_thread_id in st.session_state.threads:
        st.session_state.threads[current_thread_id]["last"] = get_current_timestamp()
    
    # Display user message immediately
    with chat_container:
        with st.chat_message("user"):
            st.write(user_input)

    # Display assistant response with streaming
    with chat_container:
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            try:
                # Stream response from LangGraph
                for chunk, _ in workflow.stream(
                    {"messages": [HumanMessage(content=user_input)]},
                    config={"configurable": {"thread_id": current_thread_id}},
                    stream_mode="messages",
                ):
                    if hasattr(chunk, 'content'):
                        full_response += chunk.content
                        response_placeholder.write(full_response)

                # Update thread title if it's still "New Chat"
                if current_thread_data and current_thread_data.get("title") == "New Chat":
                    new_title = generate_title(user_input)
                    current_thread_data["title"] = new_title
                    st.session_state.threads[current_thread_id] = current_thread_data
                    save_thread_title(current_thread_id, new_title)
                    # Note: Removed st.rerun() here to avoid interrupting flow

            except Exception as e:
                print(f"Error generating response: {e}")
                st.error(f"Error generating response: {e}")
                response_placeholder.write("Sorry, I encountered an error. Please try again.")
