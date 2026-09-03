from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import models
from .database import engine
from .routes import router

# Cria as tabelas no banco de dados SQLite
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de Onboarding B2B com IA",
    description="Backend para automação e análise de crédito corporativo utilizando sistemas multiagentes. (CP1)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "API de Onboarding B2B está rodando! Acesse /docs para o Swagger."}
