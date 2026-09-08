import re
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StatusProcesso(str, Enum):
    """Status validos de um processo de onboarding."""

    PENDENTE = "PENDENTE"
    ANALISE_IA = "ANALISE_IA"
    APROVADO = "APROVADO"
    REPROVADO = "REPROVADO"
    ERRO_ANALISE = "ERRO_ANALISE"


# Status que impedem a abertura de um novo processo para a mesma empresa
STATUS_EM_ABERTO = [StatusProcesso.PENDENTE.value, StatusProcesso.ANALISE_IA.value]


# --- Schemas para Empresa ---
class EmpresaBase(BaseModel):
    cnpj: str = Field(
        ...,
        description="CNPJ da empresa (14 digitos, com ou sem formatacao)",
        examples=["12.345.678/0001-90"],
    )
    razao_social: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Razao social da empresa",
        examples=["Tech Solutions LTDA"],
    )
    setor: str = Field(
        ...,
        min_length=2,
        max_length=80,
        description="Setor de atuacao",
        examples=["Tecnologia"],
    )

    @field_validator("cnpj")
    @classmethod
    def validar_cnpj(cls, valor: str) -> str:
        digitos = re.sub(r"\D", "", valor)
        if len(digitos) != 14:
            raise ValueError("CNPJ deve conter exatamente 14 digitos.")
        if digitos == digitos[0] * 14:
            raise ValueError("CNPJ invalido: todos os digitos sao iguais.")
        # Armazena apenas os digitos (forma canonica). Garante que a regra de
        # unicidade funcione independentemente da formatacao enviada
        # ("12.345.678/0001-90" e "12345678000190" passam a ser o mesmo CNPJ).
        return digitos

    @field_validator("razao_social", "setor")
    @classmethod
    def nao_pode_ser_espaco(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("Campo nao pode conter apenas espacos.")
        return valor.strip()


class EmpresaCreate(EmpresaBase):
    pass


class EmpresaResponse(EmpresaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    data_cadastro: Optional[datetime] = None


# --- Schemas para Processo de Onboarding ---
class ProcessoBase(BaseModel):
    empresa_id: int = Field(..., gt=0, description="ID da empresa ja cadastrada")


class ProcessoCreate(ProcessoBase):
    pass


class ProcessoUpdate(BaseModel):
    status: Optional[StatusProcesso] = Field(
        None, description="Novo status do processo"
    )
    score_credito: Optional[float] = Field(
        None, ge=0, le=100, description="Score de credito (0 a 100)"
    )
    limite_aprovado: Optional[float] = Field(
        None, ge=0, description="Limite de credito aprovado em reais (nao negativo)"
    )
    parecer_ia: Optional[str] = Field(None, description="Parecer textual da analise")


class ProcessoResponse(ProcessoBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: StatusProcesso
    score_credito: Optional[float] = None
    limite_aprovado: Optional[float] = None
    parecer_ia: Optional[str] = None
    data_criacao: Optional[datetime] = None
    data_analise: Optional[datetime] = None
    modelo_ia: Optional[str] = None


# --- Schema padronizado de erro (para documentacao no Swagger) ---
class ErroResponse(BaseModel):
    detail: str = Field(..., examples=["Empresa nao encontrada."])
