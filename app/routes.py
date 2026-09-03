from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from . import models, schemas
from .database import get_db

router = APIRouter()

# --- Rotas de Empresa ---
@router.post("/empresas/", response_model=schemas.EmpresaResponse, status_code=status.HTTP_201_CREATED, tags=["Empresas"])
def create_empresa(empresa: schemas.EmpresaCreate, db: Session = Depends(get_db)):
    db_empresa = db.query(models.Empresa).filter(models.Empresa.cnpj == empresa.cnpj).first()
    if db_empresa:
        raise HTTPException(status_code=400, detail="CNPJ já cadastrado.")
    
    nova_empresa = models.Empresa(**empresa.dict())
    db.add(nova_empresa)
    db.commit()
    db.refresh(nova_empresa)
    return nova_empresa

@router.get("/empresas/", response_model=List[schemas.EmpresaResponse], tags=["Empresas"])
def get_empresas(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    empresas = db.query(models.Empresa).offset(skip).limit(limit).all()
    return empresas

@router.get("/empresas/{empresa_id}", response_model=schemas.EmpresaResponse, tags=["Empresas"])
def get_empresa(empresa_id: int, db: Session = Depends(get_db)):
    empresa = db.query(models.Empresa).filter(models.Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada.")
    return empresa

# --- Rotas de Onboarding ---
@router.post("/onboarding/", response_model=schemas.ProcessoResponse, status_code=status.HTTP_201_CREATED, tags=["Onboarding"])
def create_onboarding(processo: schemas.ProcessoCreate, db: Session = Depends(get_db)):
    # Regra de negócio: A empresa existe?
    empresa = db.query(models.Empresa).filter(models.Empresa.id == processo.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada para iniciar o onboarding.")
    
    # Regra de negócio: A empresa já tem um processo pendente?
    processo_existente = db.query(models.ProcessoOnboarding).filter(
        models.ProcessoOnboarding.empresa_id == processo.empresa_id,
        models.ProcessoOnboarding.status == "PENDENTE"
    ).first()
    if processo_existente:
        raise HTTPException(status_code=400, detail="Esta empresa já possui um processo de onboarding em andamento.")

    novo_processo = models.ProcessoOnboarding(empresa_id=processo.empresa_id)
    db.add(novo_processo)
    db.commit()
    db.refresh(novo_processo)
    return novo_processo

@router.put("/onboarding/{processo_id}", response_model=schemas.ProcessoResponse, tags=["Onboarding"])
def update_onboarding(processo_id: int, processo_update: schemas.ProcessoUpdate, db: Session = Depends(get_db)):
    processo = db.query(models.ProcessoOnboarding).filter(models.ProcessoOnboarding.id == processo_id).first()
    if not processo:
        raise HTTPException(status_code=404, detail="Processo de onboarding não encontrado.")
    
    for key, value in processo_update.dict(exclude_unset=True).items():
        setattr(processo, key, value)
        
    db.commit()
    db.refresh(processo)
    return processo

@router.delete("/onboarding/{processo_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Onboarding"])
def delete_onboarding(processo_id: int, db: Session = Depends(get_db)):
    processo = db.query(models.ProcessoOnboarding).filter(models.ProcessoOnboarding.id == processo_id).first()
    if not processo:
        raise HTTPException(status_code=404, detail="Processo não encontrado.")
    
    db.delete(processo)
    db.commit()
    return None
