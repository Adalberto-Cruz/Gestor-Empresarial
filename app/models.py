from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    cnpj = Column(String, unique=True, index=True, nullable=False)
    razao_social = Column(String, nullable=False)
    setor = Column(String)
    data_cadastro = Column(DateTime, default=datetime.datetime.utcnow)

    processos = relationship("ProcessoOnboarding", back_populates="empresa")

class ProcessoOnboarding(Base):
    __tablename__ = "processos_onboarding"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    status = Column(String, default="PENDENTE") # PENDENTE, ANALISE_IA, APROVADO, REPROVADO
    score_credito = Column(Float, nullable=True)
    limite_aprovado = Column(Float, nullable=True)
    parecer_ia = Column(String, nullable=True)
    
    empresa = relationship("Empresa", back_populates="processos")
