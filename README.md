# AI Agentic Chatbot with Persistent Memory & Tool-Oriented Reasoning

A production-style conversational AI system that combines **LLM reasoning, structured state management, tool orchestration, and database-backed persistent memory**.

This project implements a hybrid **LLM + Tool Agent Architecture** capable of natural GPT-like conversations while dynamically invoking external tools (e.g., stock price retrieval, mathematical computation) using intelligent reasoning.

---

## 📌 Project Overview

This chatbot is designed to simulate a real-world AI assistant system with:

* Multi-turn contextual conversations
* Persistent memory across sessions
* Dynamic tool selection and execution
* Structured agent workflow using LangGraph
* Database-backed chat lifecycle management

Unlike basic chatbots, this system separates:

* **LLM reasoning**
* **Tool invocation**
* **State transitions**
* **Memory persistence**
* **Conversation management**

This reflects modern production AI system design.

---

## 🏗 System Architecture

### High-Level Flow

User Input
↓
LLM Intent & Reasoning Layer
↓
Tool Decision (if required)
↓
Tool Execution
↓
Response Synthesis
↓
Persistent Storage (SQLite)

### Core Components

1. **LLM Layer**

   * GPT-like natural response generation
   * Context-aware multi-turn conversation
   * Structured output for tool invocation

2. **Tool Layer**

   * Stock price retrieval
   * Mathematical calculator
   * Tool routing via reasoning graph
   * Automatic decision-making

3. **State Management**

   * Implemented using **LangGraph**
   * Directed graph workflow (START → Agent → Tool → END)
   * Deterministic conversation state transitions

4. **Memory Layer**

   * SQLite-backed persistent storage
   * Session-based UUID tracking
   * Structured message serialization
   * Conversation restoration after restart

5. **Frontend Layer**

   * Streamlit-based interactive UI
   * Scrollable chat interface
   * Real-time updates
   * Chat pin/delete/load system

---

## 🧠 Key Engineering Highlights

* Agentic AI Architecture (LLM + Tools)
* Persistent conversational memory
* Modular and scalable code structure
* Clear separation of concerns
* Database schema design for chat lifecycle
* Tool-augmented reasoning pipeline
* Structured state graph implementation

This mirrors patterns used in modern AI assistants and production AI systems.

---

## 🗄 Database Design

### Tables

* `conversations`
* `messages`

### Features

* UUID-based session tracking
* JSON message storage
* Pinned conversations
* Soft deletion support
* Full chat history restoration

Ensures:

* Durability
* Session continuity
* Clean data modeling

---

## 🛠 Technology Stack

* Python
* LangGraph (State-based Agent Workflow)
* LangChain
* OpenAI / Groq LLM APIs
* SQLite
* Streamlit
* Pydantic
* UUID

---

## ⚙ Design Principles Applied

* Separation of LLM reasoning from tool execution
* Deterministic workflow control via state graph
* Database-first persistence strategy
* Modular agent architecture
* Production-style project structure

---

## 📈 Future Enhancements

* Vector database integration (RAG pipeline)
* Authentication & multi-user isolation
* Deployment on cloud (AWS / GCP / Azure)
* Observability & logging
* Caching layer for tool optimization
* Streaming token responses

---

## 🎯 Why This Project Matters

This project demonstrates applied understanding of:

* Generative AI systems
* Agentic AI workflows
* Tool-augmented LLMs
* Persistent conversational architectures
* Backend engineering for AI systems

It reflects practical experience building **real-world AI infrastructure**, not just prompt-based chatbots.

---

## 👨‍💻 Author

**Danyal Arshad**
BS Computer Science
Focus Areas: Generative AI, NLP, Agentic Systems, LLM Engineering

---
