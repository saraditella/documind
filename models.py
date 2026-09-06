from pydantic import BaseModel, Field
from typing import Optional

class DocumentInfo(BaseModel):
    document_title: str = Field(
        description="Il titolo ufficiale del bando o del contratto"
    )

    expiration: str = Field(
        description="La data di scadenza del bando, in formato GG/MM/AAAA"
    )

    allocated_budget: Optional[str] = Field(
        default=None, description="L'importo economico stanziato per il bando, se presente nel testo"
    )

    key_requirements: list[str] = Field(
        description="Elenco dei requisiti principali richiesti per partecipare al bando"
    )