import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from database import init_db, get_dashboard_data, log_chat_query
from agent_rag import build_rag_agent

load_dotenv()
init_db()

st.set_page_config(page_title="Enterprise School Management AI", page_icon="🏫", layout="wide")

@st.cache_resource
def load_engine():
    return build_rag_agent()

vector_store, rag_app = load_engine()

# --- SIDEBAR: RBAC & EMBEDDINGS INSPECTOR ---
with st.sidebar:
    st.header("🔐 Role-Based Access (RBAC)")
    user_role = st.radio("Select Active Portal Role:", ["Director", "Teacher", "Parent / Student"])
    if user_role == "Director":
        st.success("Executive Access: Policies + Staff/Classes + Profit & Investments")
    elif user_role == "Teacher":
        st.info("Faculty Access: Policies + Class Strength & Staff (Finances Locked)")
    else:
        st.warning("Public Access: School Policies & Fee Calculators Only")

    st.divider()
    st.header("🧠 RAG & Embeddings Inspector")
    all_records = list(vector_store.store.values())
    categories = sorted({rec["metadata"].get("category", "General") for rec in all_records})

    c1, c2 = st.columns(2)
    c1.metric("Policy Files", "5")
    c2.metric("Vector Chunks", len(all_records))

    selected_category = st.selectbox("Filter Policy Search:", ["All Categories"] + categories)
    chunk_idx = st.slider("Inspect Vector Chunk (1–32):", 1, len(all_records), 1)
    chosen = all_records[chunk_idx - 1]
    st.caption(f"File: `{chosen['metadata'].get('source')}` | ID: `{chosen['metadata'].get('document_id')}`")
    st.text_area("Chunk Text:", chosen["text"], height=100, disabled=True)
    vec = chosen["vector"]
    st.code(f"Dim: {len(vec)} | [{', '.join(f'{x:.4f}' for x in vec[:8])}, ...]", language="python")

    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

# --- MAIN PORTAL TABS ---
st.title("🏫 Greenwood International — Enterprise School Management Portal")
st.caption(f"Logged in as: **{user_role}** | Architecture: `database.py` (SQLite) + `agent_rag.py` (LangGraph & RAG) + `app.py` (UI)")

tab_chat, tab_dashboard = st.tabs(["💬 AI Assistant Chatbot", "📊 Enterprise School Dashboard"])

with tab_chat:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message("user" if isinstance(msg, HumanMessage) else "assistant"):
            st.markdown(msg.content)

    if user_input := st.chat_input("Ask about policies, class student counts, teachers, or school profit & investments..."):
        with st.chat_message("user"):
            st.markdown(user_input)

        result = rag_app.invoke({
            "question": user_input,
            "user_role": user_role,
            "category_filter": selected_category,
            "chat_history": st.session_state.messages,
            "context_docs": [],
            "tool_used": "RAG Vector Search",
            "tool_output": "",
            "answer": ""
        })
        log_chat_query(user_role, user_input, result["tool_used"])

        with st.chat_message("assistant"):
            if result["tool_output"]:
                if "ACCESS DENIED" in result["tool_output"]:
                    st.error(f"🔒 **RBAC Security Block:** {result['tool_output']}")
                else:
                    st.info(f"🛠️ **AI Agent Tool Used ({result['tool_used']}):** {result['tool_output']}")
            st.markdown(result["answer"])
            with st.expander("📄 View Retrieved Policy Sources & Metadata"):
                for doc in result["context_docs"]:
                    st.markdown(f"**{doc.metadata.get('title', doc.metadata.get('source'))}** (`{doc.metadata.get('document_id', '')}`)")
                    st.caption(doc.page_content[:250] + "...")

        st.session_state.messages.append(HumanMessage(content=user_input))
        st.session_state.messages.append(AIMessage(content=result["answer"]))

with tab_dashboard:
    db = get_dashboard_data()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Enrolled Students", int(db["classes"]["Total Students"].sum()))
    m2.metric("Active Class Sections", len(db["classes"]))
    m3.metric("Faculty Members", len(db["teachers"]))
    m4.metric("Board Directors", len(db["directors"]))

    st.divider()
    st.subheader("💰 School Revenue, Net Profit & Capital Investments (Director Access Only)")
    if user_role == "Director":
        df_fin = db["finance"]
        rev = df_fin[df_fin["Category"] == "Revenue"]["Amount (₹)"].sum()
        exp = df_fin[df_fin["Category"] == "Expense"]["Amount (₹)"].sum()
        inv = df_fin[df_fin["Category"] == "Investment"]["Amount (₹)"].sum()
        profit = rev - exp

        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Total Annual Revenue", f"₹{rev:,.0f}")
        f2.metric("Net Operating Profit", f"₹{profit:,.0f}", delta=f"Expenses: ₹{exp:,.0f}")
        f3.metric("Capital Investments", f"₹{inv:,.0f}")
        f4.metric("Net Surplus After CapEx", f"₹{profit - inv:,.0f}")

        c_chart, c_tbl = st.columns([1, 1.5])
        with c_chart:
            st.bar_chart(df_fin[df_fin["Category"] == "Investment"].set_index("Item")[["Amount (₹)"]])
        with c_tbl:
            st.dataframe(df_fin, use_container_width=True, hide_index=True)
    else:
        st.error(f"🔒 Access Restricted: Switch to **Director** in the sidebar to view Revenue, Profit, and Capital Investments.")

    st.divider()
    st.subheader("🎓 Class-Wise Student Strength & Faculty Directory")
    if user_role in ["Director", "Teacher"]:
        c1, c2 = st.columns(2)
        c1.dataframe(db["classes"], use_container_width=True, hide_index=True)
        c2.dataframe(db["teachers"], use_container_width=True, hide_index=True)
    else:
        st.warning("🔒 Internal class headcounts and staff rosters are hidden for Parents / Students.")

    st.subheader("🏛️ School Board of Directors")
    st.dataframe(db["directors"], use_container_width=True, hide_index=True)

    if user_role == "Director":
        st.divider()
        st.subheader("📋 Recent AI Chatbot Audit Logs")
        st.dataframe(db["logs"], use_container_width=True, hide_index=True)
