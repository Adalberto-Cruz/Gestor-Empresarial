from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Schemas para Empresa
class EmpresaBase(BaseModel):
    cnpj: str = Field(..., example="12.345.678/0001-90")
    razao_social: str = Field(..., example="Tech Solutions LTDA")
    setor: str = Field(..., example="Tecnologia")

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaResponse(EmpresaBase):
    id: int
    data_cadastro: datetime

    class Config:
        orm_mode = True
        from_attributes = True

# Schemas para Processo de Onboarding
class ProcessoBase(BaseModel):
    empresa_id: int

class ProcessoCreate(ProcessoBase):
    pass

class ProcessoUpdate(BaseModel):
    status: Optional[str]
    score_credito: Optional[float]
    limite_aprovado: Optional[float]
    parecer_ia: Optional[str]

class ProcessoResponse(ProcessoBase):
    id: int
    status: str
    score_credito: Optional[float]
    limite_aprovado: Optional[float]
    parecer_ia: Optional[str]

    class Config:
        orm_mode = True
        from_attributes = True
