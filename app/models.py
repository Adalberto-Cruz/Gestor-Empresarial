import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


def agora_utc() -> datetime.datetime:
    """Timestamp em UTC. Substitui datetime.utcnow(), depreciado no Python 3.12+."""
    return datetime.datetime.now(datetime.timezone.utc)


class Empresa(Base):
    """Empresa cliente que passa pelo processo de onboarding e analise de credito."""

    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    cnpj = Column(String(18), unique=True, index=True, nullable=False)
    razao_social = Column(String(150), nullable=False)
    setor = Column(String(80), nullable=False)
    data_cadastro = Column(DateTime, default=agora_utc, nullable=False)

    processos = relationship("ProcessoOnboarding", back_populates="empresa")


class ProcessoOnboarding(Base):
    """Processo de onboarding/analise de credito vinculado a uma Empresa."""

    __tablename__ = "processos_onboarding"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)

    # PENDENTE | ANALISE_IA | APROVADO | REPROVADO | ERRO_ANALISE
    status = Column(String(20), default="PENDENTE", nullable=False, index=True)

    score_credito = Column(Float, nullable=True)
    limite_aprovado = Column(Float, nullable=True)
    parecer_ia = Column(String, nullable=True)

    # Trilha de auditoria: permite medir o tempo de decisao (proposta de valor do produto)
    data_criacao = Column(DateTime, default=agora_utc, nullable=False)
    data_analise = Column(DateTime, nullable=True)

    # Rastreabilidade da analise (requisito de compliance em credito)
    modelo_ia = Column(String(50), nullable=True)

    empresa = relationship("Empresa", back_populates="processos")
