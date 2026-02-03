from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
import shutil

# Define path for local vector store
VECTOR_STORE_PATH = "./chroma_db"

# Initialize Embedding Model (Runs on CPU, very fast)
embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def ingest_resume(file_path: str):
    """
    Parses PDF, splits text, and stores embeddings locally.
    """
    # 1. Load PDF
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    
    # 2. Split Text
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    
    # 3. Clear old DB to prevent mixing candidates
    if os.path.exists(VECTOR_STORE_PATH):
        shutil.rmtree(VECTOR_STORE_PATH)
        
    # 4. Create Vector Store
    Chroma.from_documents(
        documents=chunks, 
        embedding=embedding_function,
        persist_directory=VECTOR_STORE_PATH
    )
    return True

def get_resume_context(query: str):
    """
    Retrieves relevant resume context for the current question.
    """
    if not os.path.exists(VECTOR_STORE_PATH):
        return "No resume uploaded."

    vectorstore = Chroma(
        persist_directory=VECTOR_STORE_PATH, 
        embedding_function=embedding_function
    )
    
    results = vectorstore.similarity_search(query, k=3)
    return "\n".join([doc.page_content for doc in results])