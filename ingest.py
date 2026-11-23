import os
import glob
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

def load_docs_with_metadata(folder_path="data"):
    documents = []
    for file_path in sorted(glob.glob(os.path.join(folder_path, "*.txt"))):
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        metadata = {"source": os.path.basename(file_path)}
        content = raw_text

        if raw_text.startswith("---"):
            parts = raw_text.split("---", 2)
            if len(parts) == 3:
                for line in parts[1].strip().splitlines():
                    if ":" in line:
                        key, val = line.split(":", 1)
                        metadata[key.strip()] = val.strip()
                content = parts[2].strip()

        documents.append(Document(page_content=content, metadata=metadata))
    return documents

if __name__ == "__main__":
    print("1. Loading school documents and parsing metadata...")
    docs = load_docs_with_metadata("data")

    print("2. Splitting documents into chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
    chunks = splitter.split_documents(docs)

    print("3. Generating Gemini embeddings and saving vector store...")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    vector_store = InMemoryVectorStore.from_documents(chunks, embeddings)
    vector_store.dump("vector_store.json")

    print(f"Done! Saved {len(chunks)} chunks with metadata to vector_store.json")
