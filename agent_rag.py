import os
import re
from dotenv import load_dotenv
from typing import TypedDict, List
from groq import Groq

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langgraph.graph import StateGraph, START, END
from database import query_enterprise_db

load_dotenv()

def call_groq(messages, temperature=0.2):
    client = Groq(api_key=os.getenv("GROQ_API_KEY", "").strip())
    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        temperature=temperature
    )
    return completion.choices[0].message.content


def calculate_school_fee(grade: int, stream: str = "general", has_sibling: bool = False, bus_zone: str = "none") -> str:
    if 1 <= grade <= 5:
        tuition = 13500
    elif 6 <= grade <= 8:
        tuition = 16500
    elif 9 <= grade <= 10:
        tuition = 18000
    elif 11 <= grade <= 12:
        tuition = 22500 if "science" in stream.lower() else 20400
    else:
        return "Invalid grade (must be 1–12)."

    discount = int(tuition * 0.15) if has_sibling else 0
    bus_fee = {"none": 0, "a": 5400, "b": 7200, "c": 9000}.get(bus_zone.lower().strip(), 0)
    total = (tuition - discount) + bus_fee
    return f"Grade {grade} Quarterly Fee: Base ₹{tuition:,} - Sibling Discount ₹{discount:,} + Bus Zone {bus_zone.upper()} ₹{bus_fee:,} = ₹{total:,}."

def calculate_late_fine(days_late: int, fine_type: str = "fee") -> str:
    if fine_type.lower() == "library":
        return f"Library Overdue Fine ({days_late} days @ ₹5/day) = ₹{max(0, days_late) * 5:,}."
    chargeable = max(0, days_late - 5)
    return f"Late Fee Fine ({days_late} days late, 5-day grace, {chargeable} chargeable days @ ₹50/day) = ₹{chargeable * 50:,}."

class ChatState(TypedDict):
    question: str
    user_role: str
    category_filter: str
    chat_history: List[BaseMessage]
    context_docs: List[Document]
    tool_used: str
    tool_output: str
    answer: str

def build_rag_agent():
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    vector_store = InMemoryVectorStore.load("vector_store.json", embeddings)

    def retrieve_node(state: ChatState):
        if state["category_filter"] != "All Categories":
            docs = vector_store.similarity_search(
                state["question"], k=3,
                filter=lambda doc: doc.metadata.get("category") == state["category_filter"]
            )
        else:
            docs = vector_store.similarity_search(state["question"], k=3)
        return {"context_docs": docs}

    def agent_tool_node(state: ChatState):
        q = state["question"].lower()

        if any(w in q for w in ["profit", "invest", "revenue", "surplus", "expense", "capex", "financial"]):
            return {
                "tool_used": f"SQLite Finance DB ({state['user_role']} View)",
                "tool_output": query_enterprise_db("finance", state["user_role"])
            }

        if any(w in q for w in ["how many student", "student count", "students in", "class teacher", "teachers", "faculty", "director", "principal", "chairman", "strength"]):
            return {
                "tool_used": f"SQLite Academic DB ({state['user_role']} View)",
                "tool_output": query_enterprise_db("academic", state["user_role"])
            }

        if any(w in q for w in ["fine", "overdue", "late"]):
            days_match = re.search(r"(\d+)\s*day", q)
            days = int(days_match.group(1)) if days_match else 0
            if days > 0:
                f_type = "library" if any(w in q for w in ["library", "book"]) else "fee"
                return {
                    "tool_used": "Fine Calculator Tool",
                    "tool_output": calculate_late_fine(days, f_type)
                }

        if any(w in q for w in ["calculate", "quarterly fee", "total fee", "tuition fee"]) and any(w in q for w in ["grade", "class"]):
            grade_match = re.search(r"(?:grade|class)\s*(\d+)", q)
            if grade_match:
                grade = int(grade_match.group(1))
                stream = "science" if "science" in q else "general"
                sibling = "sibling" in q
                zone_match = re.search(r"zone\s*([abc])", q)
                zone = zone_match.group(1) if zone_match else "none"
                return {
                    "tool_used": "Fee Calculator Tool",
                    "tool_output": calculate_school_fee(grade, stream, sibling, zone)
                }

        return {"tool_used": "RAG Vector Search", "tool_output": ""}

    def generate_node(state: ChatState):
        context_text = "\n\n".join(
            f"[Source: {d.metadata.get('title', d.metadata.get('source'))}]\n{d.page_content}"
            for d in state["context_docs"]
        )
        tool_section = f"\n\nAI Agent Tool Result:\n{state['tool_output']}" if state["tool_output"] else ""
        system_prompt = (
            f"You are an Enterprise School Management AI Assistant helping a '{state['user_role']}'. "
            "Answer ONLY using the retrieved policy context and tool output below. "
            "If the tool output says ACCESS DENIED, clearly explain that their role lacks permission.\n\n"
            f"Policy Context:\n{context_text}{tool_section}"
        )

        oai_msgs = [{"role": "system", "content": system_prompt}]
        for m in state["chat_history"]:
            role = "user" if isinstance(m, HumanMessage) else "assistant"
            oai_msgs.append({"role": role, "content": m.content})
        oai_msgs.append({"role": "user", "content": state["question"]})

        return {"answer": call_groq(oai_msgs, temperature=0.2)}

    workflow = StateGraph(ChatState)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("agent_tool", agent_tool_node)
    workflow.add_node("generate", generate_node)
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "agent_tool")
    workflow.add_edge("agent_tool", "generate")
    workflow.add_edge("generate", END)

    return vector_store, workflow.compile()
