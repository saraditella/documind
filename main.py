import dotenv
from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from models import DocumentInfo

load_dotenv()

app = FastAPI(title="DocuMind")


@app.get("/test")
async def test():
    return {"status": "ok", "message": "Server attivo"}

#Configurazione RAG
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vectorstore = Chroma(
    persist_directory="chroma_db",
    embedding_function=embeddings
)

retriever = vectorstore.as_retriever(search_kwargs={"k":4})

prompt = ChatPromptTemplate.from_template(
    """Sei un assistente che estrae informazioni da documenti burocratici.
Usa esclusivamente il contesto fornito qui sotto per rispondere.
Se un'informazione non è presente nel contesto, lascia il campo vuoto.

Contesto:
{contesto}

Domanda:
{domanda}
"""
)

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
structured_llm = llm.with_structured_output(DocumentInfo)

def context_formatting(chuncks):
    return "\n\n".join(chunk.page_content for chunk in chuncks)

rag_chain = (
    {"contesto": retriever | context_formatting,
     "domanda": lambda x: x
     }
    | prompt
    | structured_llm
)

@app.get("/extract-data")
async def extract_data(request: str):
    result = rag_chain.invoke(request)
    return result