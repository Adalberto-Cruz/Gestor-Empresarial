"""Testes automatizados da API AutoCred B2B.

Executar na raiz do projeto:  pytest -v
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.ia_service import IAServiceError, ResultadoAnalise  # noqa: E402

# Banco em memoria isolado para os testes
engine_teste = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionTeste = sessionmaker(autocommit=False, autoflush=False, bind=engine_teste)


def _get_db_teste():
    db = SessionTeste()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _get_db_teste


@pytest.fixture(autouse=True)
def banco_limpo():
    Base.metadata.create_all(bind=engine_teste)
    yield
    Base.metadata.drop_all(bind=engine_teste)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


EMPRESA_VALIDA = {
    "cnpj": "12.345.678/0001-90",
    "razao_social": "Tech Solutions LTDA",
    "setor": "Tecnologia",
}


def _criar_empresa(client, **overrides):
    payload = {**EMPRESA_VALIDA, **overrides}
    return client.post("/api/v1/empresas/", json=payload)


# --- Health check ---
def test_health_check(client):
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "online"


# --- Empresa ---
def test_criar_empresa_com_sucesso(client):
    resposta = _criar_empresa(client)
    assert resposta.status_code == 201
    corpo = resposta.json()
    # O CNPJ e armazenado na forma canonica (apenas digitos), independentemente
    # da formatacao enviada na requisicao.
    assert corpo["cnpj"] == "12345678000190"
    assert corpo["id"] > 0


def test_cnpj_duplicado_retorna_409(client):
    _criar_empresa(client)
    resposta = _criar_empresa(client, razao_social="Outra Empresa")
    assert resposta.status_code == 409


def test_cnpj_duplicado_com_formatacao_diferente_retorna_409(client):
    """Regressao: o mesmo CNPJ com e sem mascara nao pode ser cadastrado duas vezes.

    Antes da normalizacao, '12.345.678/0001-90' e '12345678000190' eram tratados
    como CNPJs distintos, permitindo empresas duplicadas.
    """
    primeira = _criar_empresa(client, cnpj="12.345.678/0001-90")
    assert primeira.status_code == 201

    segunda = _criar_empresa(client, cnpj="12345678000190", razao_social="Outra")
    assert segunda.status_code == 409


def test_cnpj_invalido_retorna_422(client):
    resposta = _criar_empresa(client, cnpj="BANANA")
    assert resposta.status_code == 422


def test_razao_social_vazia_retorna_422(client):
    resposta = _criar_empresa(client, razao_social="")
    assert resposta.status_code == 422


def test_empresa_inexistente_retorna_404(client):
    assert client.get("/api/v1/empresas/999").status_code == 404


def test_atualizar_empresa(client):
    empresa_id = _criar_empresa(client).json()["id"]
    resposta = client.put(
        f"/api/v1/empresas/{empresa_id}",
        json={**EMPRESA_VALIDA, "razao_social": "Nome Atualizado"},
    )
    assert resposta.status_code == 200
    assert resposta.json()["razao_social"] == "Nome Atualizado"


def test_excluir_empresa_sem_processos(client):
    empresa_id = _criar_empresa(client).json()["id"]
    assert client.delete(f"/api/v1/empresas/{empresa_id}").status_code == 204


def test_excluir_empresa_com_processo_retorna_409(client):
    """Regressao: antes retornava 500 nao tratado."""
    empresa_id = _criar_empresa(client).json()["id"]
    client.post("/api/v1/onboarding/", json={"empresa_id": empresa_id})

    resposta = client.delete(f"/api/v1/empresas/{empresa_id}")
    assert resposta.status_code == 409
    assert "detail" in resposta.json()


# --- Onboarding ---
def test_criar_onboarding(client):
    empresa_id = _criar_empresa(client).json()["id"]
    resposta = client.post("/api/v1/onboarding/", json={"empresa_id": empresa_id})
    assert resposta.status_code == 201
    assert resposta.json()["status"] == "PENDENTE"
    assert resposta.json()["data_criacao"] is not None


def test_onboarding_para_empresa_inexistente_retorna_404(client):
    resposta = client.post("/api/v1/onboarding/", json={"empresa_id": 999})
    assert resposta.status_code == 404


def test_processo_duplicado_em_aberto_retorna_409(client):
    empresa_id = _criar_empresa(client).json()["id"]
    client.post("/api/v1/onboarding/", json={"empresa_id": empresa_id})
    resposta = client.post("/api/v1/onboarding/", json={"empresa_id": empresa_id})
    assert resposta.status_code == 409


def test_nao_permite_segundo_processo_apos_analise_ia(client):
    """Regressao: o status ANALISE_IA tambem bloqueia novo processo."""
    empresa_id = _criar_empresa(client).json()["id"]
    processo_id = client.post(
        "/api/v1/onboarding/", json={"empresa_id": empresa_id}
    ).json()["id"]

    client.put(f"/api/v1/onboarding/{processo_id}", json={"status": "ANALISE_IA"})

    resposta = client.post("/api/v1/onboarding/", json={"empresa_id": empresa_id})
    assert resposta.status_code == 409


def test_status_invalido_retorna_422(client):
    empresa_id = _criar_empresa(client).json()["id"]
    processo_id = client.post(
        "/api/v1/onboarding/", json={"empresa_id": empresa_id}
    ).json()["id"]

    resposta = client.put(
        f"/api/v1/onboarding/{processo_id}", json={"status": "BANANA_FRITA"}
    )
    assert resposta.status_code == 422


def test_valores_negativos_retornam_422(client):
    empresa_id = _criar_empresa(client).json()["id"]
    processo_id = client.post(
        "/api/v1/onboarding/", json={"empresa_id": empresa_id}
    ).json()["id"]

    resposta = client.put(
        f"/api/v1/onboarding/{processo_id}",
        json={"score_credito": -999, "limite_aprovado": -50000},
    )
    assert resposta.status_code == 422


def test_filtrar_processos_por_status(client):
    empresa_id = _criar_empresa(client).json()["id"]
    client.post("/api/v1/onboarding/", json={"empresa_id": empresa_id})

    resposta = client.get("/api/v1/onboarding/?status=PENDENTE")
    assert resposta.status_code == 200
    assert len(resposta.json()) == 1


# --- Agente de IA ---
def test_analise_ia_com_sucesso(client, monkeypatch):
    """A IA e simulada (mock) para o teste nao depender de rede nem de chave."""
    empresa_id = _criar_empresa(client).json()["id"]
    processo_id = client.post(
        "/api/v1/onboarding/", json={"empresa_id": empresa_id}
    ).json()["id"]

    def fake_analisar(cnpj, razao_social, setor):
        return ResultadoAnalise(
            score_credito=85.5,
            limite_aprovado=50000.0,
            parecer_ia="Empresa com bom perfil de risco.",
            modelo_ia="modelo-de-teste",
        )

    monkeypatch.setattr("app.routes.analisar_empresa", fake_analisar)

    resposta = client.post(f"/api/v1/onboarding/{processo_id}/analisar")
    assert resposta.status_code == 200

    corpo = resposta.json()
    assert corpo["status"] == "ANALISE_IA"
    assert corpo["score_credito"] == 85.5
    assert corpo["data_analise"] is not None
    assert corpo["modelo_ia"] == "modelo-de-teste"


def test_falha_da_ia_retorna_502_e_marca_erro(client, monkeypatch):
    empresa_id = _criar_empresa(client).json()["id"]
    processo_id = client.post(
        "/api/v1/onboarding/", json={"empresa_id": empresa_id}
    ).json()["id"]

    def fake_falha(cnpj, razao_social, setor):
        raise IAServiceError("Falha simulada.")

    monkeypatch.setattr("app.routes.analisar_empresa", fake_falha)

    resposta = client.post(f"/api/v1/onboarding/{processo_id}/analisar")
    assert resposta.status_code == 502
    # A mensagem interna nao pode vazar para o cliente
    assert "Falha simulada" not in resposta.json()["detail"]

    processo = client.get(f"/api/v1/onboarding/{processo_id}").json()
    assert processo["status"] == "ERRO_ANALISE"


def test_analisar_processo_inexistente_retorna_404(client):
    assert client.post("/api/v1/onboarding/999/analisar").status_code == 404
