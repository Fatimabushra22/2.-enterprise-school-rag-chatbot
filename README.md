# 🏫 Greenwood International — Enterprise School Management AI System

An AI-powered **Enterprise School Management Chatbot & Analytics Portal** built with **RAG (Retrieval-Augmented Generation)**, **LangChain**, **LangGraph**, **AI Agent Tools**, **Role-Based Access Control (RBAC)**, **SQLite**, and **Streamlit**.

## 🚀 Features
- **RAG Policy Assistant:** Retrieves accurate answers from 5 metadata-structured school policy documents (`data/`) stored as 32 vector embeddings (`vector_store.json`).
- **LangGraph AI Agent Tools:** Routes queries dynamically across RAG semantic search, quarterly fee & late-fine calculators, and live SQLite database queries.
- **Role-Based Access Control (RBAC):** Supports **Director**, **Teacher**, and **Parent / Student** views—protecting confidential school revenue, net profit, and capital investment analytics.
- **Embeddings & Vector Inspector:** Interactive Streamlit sidebar showing chunk metadata and 3,072-dimensional vector representations.

## ⚙️ Quick Start
1. `python -m venv venv` and `.\venv\Scripts\activate`
2. `pip install -r requirements.txt`
3. Add `GOOGLE_API_KEY` and `GROQ_API_KEY` to `.env`
4. `python -m streamlit run app.py`
