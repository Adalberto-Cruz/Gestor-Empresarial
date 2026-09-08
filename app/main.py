import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Carrega as variaveis de ambiente antes de qualquer import que dependa delas
load_dotenv()

from . import models  # noqa: E402
from .database import engine  # noqa: E402
from .routes import router  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AutoCred B2B - API de Onboarding e Analise de Credito",
    description=(
        "Backend para automacao de onboarding e analise de credito corporativo "
        "utilizando Agentes de IA.\n\n"
        "**Fluxo principal:** cadastrar empresa -> abrir processo de onboarding -> "
        "acionar o Agente Decisor (`/onboarding/{id}/analisar`) -> consultar o parecer."
    ),
    version="1.1.0",
    contact={"name": "Equipe AutoCred B2B"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restringir em producao
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def erro_nao_tratado(request: Request, exc: Exception):
    """Rede de seguranca: garante resposta JSON padronizada em qualquer falha."""
    logger.exception("Erro nao tratado em %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno no servidor."},
    )


app.include_router(router, prefix="/api/v1")


@app.get("/", tags=["Geral"], summary="Health check da API")
def read_root():
    """Confirma que a API esta no ar e aponta para a documentacao Swagger."""
    return {
        "status": "online",
        "servico": "AutoCred B2B API",
        "versao": "1.1.0",
        "documentacao": "/docs",
    }
