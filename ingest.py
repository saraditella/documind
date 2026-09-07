from langchain_community.document_loaders import PyMuPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

#Caricamento del PDF
loader = PyMuPDFLoader("docs/document.pdf")
pages = loader.load()

if len(pages) == 1:
    print(f"Il PDF ha {len(pages)} pagina")
else:
    print(f"Il PDF ha {len(pages)} pagine")

#print(pages[0].page_content[:300])


#Scomposizione in chunk
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150
)
chunks = splitter.split_documents(pages)
print(f"Le pagine del documento sono state divise in {len(chunks)} chunk")

#Creazione degli embeddings (in locale) e salvataggio in ChromaDB
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="chroma_db"
)
print("Salvataggio completato all'interno del database vettoriale chroma_db/")

