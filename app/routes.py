import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from . import models, schemas
from .database import get_db
from .models import agora_utc
from .schemas import STATUS_EM_ABERTO
from .services.ia_service import IAServiceError, analisar_empresa

logger = logging.getLogger(__name__)
router = APIRouter()

ERRO_404 = {"model": schemas.ErroResponse, "description": "Recurso nao encontrado"}
ERRO_409 = {"model": schemas.ErroResponse, "description": "Conflito com o estado atual"}
ERRO_422 = {"model": schemas.ErroResponse, "description": "Dados invalidos"}


# ==========================================
# Helpers
# ==========================================
def _buscar_empresa(empresa_id: int, db: Session) -> models.Empresa:
    empresa = db.query(models.Empresa).filter(models.Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa nao encontrada.")
    return empresa


def _buscar_processo(processo_id: int, db: Session) -> models.ProcessoOnboarding:
    processo = (
        db.query(models.ProcessoOnboarding)
        .filter(models.ProcessoOnboarding.id == processo_id)
        .first()
    )
    if not processo:
        raise HTTPException(status_code=404, detail="Processo nao encontrado.")
    return processo


# ==========================================
# Rotas de Empresa
# ==========================================
@router.post(
    "/empresas/",
    response_model=schemas.EmpresaResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Empresas"],
    summary="Cadastra uma nova empresa",
    description="Cria uma empresa. O CNPJ e validado (14 digitos) e deve ser unico.",
    responses={409: ERRO_409, 422: ERRO_422},
)
def create_empresa(empresa: schemas.EmpresaCreate, db: Session = Depends(get_db)):
    existente = (
        db.query(models.Empresa).filter(models.Empresa.cnpj == empresa.cnpj).first()
    )
    if existente:
        raise HTTPException(status_code=409, detail="CNPJ ja cadastrado.")

    nova_empresa = models.Empresa(**empresa.model_dump())
    db.add(nova_empresa)
    db.commit()
    db.refresh(nova_empresa)
    return nova_empresa


@router.get(
    "/empresas/",
    response_model=List[schemas.EmpresaResponse],
    tags=["Empresas"],
    summary="Lista as empresas cadastradas",
    description="Retorna a lista de empresas com paginacao via `skip` e `limit`.",
)
def get_empresas(
    skip: int = Query(0, ge=0, description="Registros a pular"),
    limit: int = Query(100, ge=1, le=200, description="Maximo de registros"),
    db: Session = Depends(get_db),
):
    return db.query(models.Empresa).offset(skip).limit(limit).all()


@router.get(
    "/empresas/{empresa_id}",
    response_model=schemas.EmpresaResponse,
    tags=["Empresas"],
    summary="Consulta uma empresa por ID",
    responses={404: ERRO_404},
)
def get_empresa(empresa_id: int, db: Session = Depends(get_db)):
    return _buscar_empresa(empresa_id, db)


@router.put(
    "/empresas/{empresa_id}",
    response_model=schemas.EmpresaResponse,
    tags=["Empresas"],
    summary="Atualiza os dados de uma empresa",
    responses={404: ERRO_404, 409: ERRO_409, 422: ERRO_422},
)
def update_empresa(
    empresa_id: int,
    empresa_update: schemas.EmpresaCreate,
    db: Session = Depends(get_db),
):
    empresa = _buscar_empresa(empresa_id, db)

    # O novo CNPJ nao pode pertencer a outra empresa
    conflito = (
        db.query(models.Empresa)
        .filter(
            models.Empresa.cnpj == empresa_update.cnpj,
            models.Empresa.id != empresa_id,
        )
        .first()
    )
    if conflito:
        raise HTTPException(
            status_code=409, detail="CNPJ ja cadastrado para outra empresa."
        )

    for campo, valor in empresa_update.model_dump().items():
        setattr(empresa, campo, valor)

    db.commit()
    db.refresh(empresa)
    return empresa


@router.delete(
    "/empresas/{empresa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Empresas"],
    summary="Remove uma empresa",
    description=(
        "Remove uma empresa. A exclusao e bloqueada (409) caso existam processos "
        "de onboarding vinculados, preservando a trilha de auditoria das analises."
    ),
    responses={404: ERRO_404, 409: ERRO_409},
)
def delete_empresa(empresa_id: int, db: Session = Depends(get_db)):
    empresa = _buscar_empresa(empresa_id, db)

    if empresa.processos:
        raise HTTPException(
            status_code=409,
            detail=(
                "Nao e possivel excluir: a empresa possui "
                f"{len(empresa.processos)} processo(s) de onboarding vinculado(s)."
            ),
        )

    db.delete(empresa)
    db.commit()
    return None


# ==========================================
# Rotas de Onboarding
# ==========================================
@router.post(
    "/onboarding/",
    response_model=schemas.ProcessoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Onboarding"],
    summary="Inicia um processo de onboarding",
    description=(
        "Abre um processo para uma empresa ja cadastrada. Nao e permitido abrir "
        "um novo processo enquanto houver outro em aberto (PENDENTE ou ANALISE_IA)."
    ),
    responses={404: ERRO_404, 409: ERRO_409},
)
def create_onboarding(processo: schemas.ProcessoCreate, db: Session = Depends(get_db)):
    _buscar_empresa(processo.empresa_id, db)

    em_aberto = (
        db.query(models.ProcessoOnboarding)
        .filter(
            models.ProcessoOnboarding.empresa_id == processo.empresa_id,
            models.ProcessoOnboarding.status.in_(STATUS_EM_ABERTO),
        )
        .first()
    )
    if em_aberto:
        raise HTTPException(
            status_code=409,
            detail=(
                "Esta empresa ja possui um processo em aberto "
                f"(id={em_aberto.id}, status={em_aberto.status})."
            ),
        )

    novo_processo = models.ProcessoOnboarding(empresa_id=processo.empresa_id)
    db.add(novo_processo)
    db.commit()
    db.refresh(novo_processo)
    return novo_processo


@router.get(
    "/onboarding/",
    response_model=List[schemas.ProcessoResponse],
    tags=["Onboarding"],
    summary="Lista os processos de onboarding",
    description="Permite filtrar por `empresa_id` e por `status`.",
)
def get_onboardings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    empresa_id: int | None = Query(None, gt=0, description="Filtra por empresa"),
    status_filtro: schemas.StatusProcesso | None = Query(
        None, alias="status", description="Filtra por status"
    ),
    db: Session = Depends(get_db),
):
    consulta = db.query(models.ProcessoOnboarding)
    if empresa_id is not None:
        consulta = consulta.filter(models.ProcessoOnboarding.empresa_id == empresa_id)
    if status_filtro is not None:
        consulta = consulta.filter(
            models.ProcessoOnboarding.status == status_filtro.value
        )
    return consulta.offset(skip).limit(limit).all()


@router.get(
    "/onboarding/{processo_id}",
    response_model=schemas.ProcessoResponse,
    tags=["Onboarding"],
    summary="Consulta um processo por ID",
    responses={404: ERRO_404},
)
def get_onboarding(processo_id: int, db: Session = Depends(get_db)):
    return _buscar_processo(processo_id, db)


@router.put(
    "/onboarding/{processo_id}",
    response_model=schemas.ProcessoResponse,
    tags=["Onboarding"],
    summary="Atualiza um processo de onboarding",
    description=(
        "Atualizacao parcial. Apenas status validos sao aceitos e os valores "
        "numericos sao restritos (score entre 0 e 100, limite nao negativo)."
    ),
    responses={404: ERRO_404, 422: ERRO_422},
)
def update_onboarding(
    processo_id: int,
    processo_update: schemas.ProcessoUpdate,
    db: Session = Depends(get_db),
):
    processo = _buscar_processo(processo_id, db)

    dados = processo_update.model_dump(exclude_unset=True)
    if not dados:
        raise HTTPException(
            status_code=422, detail="Nenhum campo informado para atualizacao."
        )

    for campo, valor in dados.items():
        if campo == "status" and valor is not None:
            valor = valor.value if hasattr(valor, "value") else valor
        setattr(processo, campo, valor)

    db.commit()
    db.refresh(processo)
    return processo


@router.delete(
    "/onboarding/{processo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Onboarding"],
    summary="Remove um processo de onboarding",
    responses={404: ERRO_404},
)
def delete_onboarding(processo_id: int, db: Session = Depends(get_db)):
    processo = _buscar_processo(processo_id, db)
    db.delete(processo)
    db.commit()
    return None


# ==========================================
# Endpoint de IA (Agente Decisor)
# ==========================================
@router.post(
    "/onboarding/{processo_id}/analisar",
    response_model=schemas.ProcessoResponse,
    tags=["IA - Agentes"],
    summary="Aciona o Agente Decisor para analisar o credito",
    description=(
        "Envia os dados cadastrais da empresa ao modelo de IA e preenche "
        "`score_credito`, `limite_aprovado` e `parecer_ia` no processo, "
        "alterando o status para `ANALISE_IA` e registrando a data da analise."
    ),
    responses={
        404: ERRO_404,
        409: ERRO_409,
        502: {
            "model": schemas.ErroResponse,
            "description": "Falha na comunicacao com o servico de IA",
        },
    },
)
def analisar_onboarding(processo_id: int, db: Session = Depends(get_db)):
    processo = _buscar_processo(processo_id, db)
    empresa = _buscar_empresa(processo.empresa_id, db)

    if processo.status in (
        schemas.StatusProcesso.APROVADO.value,
        schemas.StatusProcesso.REPROVADO.value,
    ):
        raise HTTPException(
            status_code=409,
            detail="Processo ja finalizado; nao pode ser reanalisado.",
        )

    try:
        resultado = analisar_empresa(
            cnpj=empresa.cnpj,
            razao_social=empresa.razao_social,
            setor=empresa.setor,
        )
    except IAServiceError as exc:
        logger.warning("Analise de IA falhou no processo %s: %s", processo_id, exc)
        processo.status = schemas.StatusProcesso.ERRO_ANALISE.value
        db.commit()
        raise HTTPException(
            status_code=502,
            detail="Falha na comunicacao com o servico de IA. Tente novamente.",
        ) from exc

    processo.score_credito = resultado.score_credito
    processo.limite_aprovado = resultado.limite_aprovado
    processo.parecer_ia = resultado.parecer_ia
    processo.modelo_ia = resultado.modelo_ia
    processo.status = schemas.StatusProcesso.ANALISE_IA.value
    processo.data_analise = agora_utc()

    db.commit()
    db.refresh(processo)
    return processo
