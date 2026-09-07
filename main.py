import os
import uuid
import shutil
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter

from models import DocumentInfo

load_dotenv()

app = FastAPI(title="DocuMind")

UPLOAD_DIR = "docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Configurazione RAG
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vectorstore = Chroma(
    persist_directory="chroma_db",
    embedding_function=embeddings
)

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


def get_vectorstore():
    return vectorstore


@app.get("/test")
async def test():
    return {"status": "ok", "message": "Server attivo"}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...), db=Depends(get_vectorstore)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Formato non supportato. Caricare esclusivamente file PDF."
        )

    name = f"{uuid.uuid4()}.pdf"
    file_path = os.path.join(UPLOAD_DIR, name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        loader = PyMuPDFLoader(file_path)
        pages = loader.load()

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = splitter.split_documents(pages)

        db.add_documents(chunks)

        return {
            "status": "success",
            "extracted_pages": len(pages),
            "indexed_chunk": len(chunks)
        }

    except Exception as e:
        print(f"Errore durante l'elaborazione del PDF: {e}")
        raise HTTPException(
            status_code=500,
            detail="Errore durante l'elaborazione del documento. Riprova più tardi."
        )


@app.get("/extract-data")
async def extract_data(request: str, db=Depends(get_vectorstore)):
    retrievers = db.as_retriever(search_kwargs={"k": 4})

    rag_chain = (
            {
                "contesto": retrievers | context_formatting,
                "domanda": lambda x: x
            }
            | prompt
            | structured_llm
    )

    try:
        result = rag_chain.invoke(request)
        return result
    except Exception as error:
        print(f"Errore durante l'estrazione: {error}")
        raise HTTPException(
            status_code=503,
            detail="Il servizio per estrarre i dati non è al momento disponibile. Riprova più tardi."
        )