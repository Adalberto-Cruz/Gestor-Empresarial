"""Camada de servico do Agente de IA (Agente Decisor).

Isola toda a comunicacao com o modelo de linguagem. As rotas nao conhecem
detalhes do provedor de IA - apenas chamam `analisar_empresa()` e recebem
um resultado ja validado.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

from google import genai  # type: ignore

logger = logging.getLogger(__name__)

MODELO_PADRAO = "gemini-3.6-flash"


class IAServiceError(Exception):
    """Falha na comunicacao com o servico de IA ou na resposta recebida."""


@dataclass
class ResultadoAnalise:
    """Resultado estruturado devolvido pelo Agente Decisor."""

    score_credito: float
    limite_aprovado: float
    parecer_ia: str
    modelo_ia: str


def _montar_prompt(cnpj: str, razao_social: str, setor: str) -> str:
    return f"""
Atue como um Agente Analista de Credito B2B especializado em onboarding empresarial.

Analise a empresa abaixo e emita um parecer de credito:
- CNPJ: {cnpj}
- Razao Social: {razao_social}
- Setor de atuacao: {setor}

Criterios:
- score_credito: numero de 0 a 100, onde 100 e o menor risco.
- limite_aprovado: valor em reais, coerente com o score e o porte do setor.
- parecer_ia: justificativa objetiva em ate 3 frases.

Responda APENAS com um JSON valido. NAO use markdown, blocos de codigo
ou texto adicional. Use exatamente esta estrutura:
{{
  "score_credito": 85.5,
  "limite_aprovado": 50000.0,
  "parecer_ia": "Justificativa aqui."
}}
""".strip()


def _limpar_resposta(texto: str) -> str:
    """Remove cercas de markdown que o modelo eventualmente adiciona."""
    texto = texto.strip()
    if texto.startswith("```"):
        linhas = texto.split("\n")
        linhas = linhas[1:]  # remove a linha de abertura (``` ou ```json)
        if linhas and linhas[-1].strip().startswith("```"):
            linhas = linhas[:-1]
        texto = "\n".join(linhas).strip()
    return texto


def _validar_payload(dados: dict[str, Any]) -> None:
    for campo in ("score_credito", "limite_aprovado", "parecer_ia"):
        if campo not in dados:
            raise IAServiceError(f"Resposta da IA sem o campo obrigatorio '{campo}'.")

    score = float(dados["score_credito"])
    limite = float(dados["limite_aprovado"])

    if not 0 <= score <= 100:
        raise IAServiceError("score_credito fora do intervalo permitido (0 a 100).")
    if limite < 0:
        raise IAServiceError("limite_aprovado nao pode ser negativo.")


def analisar_empresa(cnpj: str, razao_social: str, setor: str) -> ResultadoAnalise:
    """Envia os dados da empresa ao modelo e devolve o parecer estruturado.

    Levanta IAServiceError em qualquer falha (chave ausente, erro de rede,
    resposta malformada ou valores fora do dominio esperado).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise IAServiceError("GEMINI_API_KEY nao configurada no ambiente.")

    modelo = os.getenv("GEMINI_MODEL", MODELO_PADRAO)

    try:
        client = genai.Client(api_key=api_key)
        resposta = client.models.generate_content(
            model=modelo,
            contents=_montar_prompt(cnpj, razao_social, setor),
        )
        texto = _limpar_resposta(resposta.text or "")
    except IAServiceError:
        raise
    except Exception as exc:
        logger.exception("Falha na chamada ao provedor de IA.")
        raise IAServiceError("Falha na comunicacao com o provedor de IA.") from exc

    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as exc:
        logger.error("IA retornou conteudo nao-JSON: %r", texto[:500])
        raise IAServiceError("A IA nao retornou um JSON valido.") from exc

    if not isinstance(dados, dict):
        raise IAServiceError("A IA nao retornou um objeto JSON.")

    _validar_payload(dados)

    return ResultadoAnalise(
        score_credito=float(dados["score_credito"]),
        limite_aprovado=float(dados["limite_aprovado"]),
        parecer_ia=str(dados["parecer_ia"]),
        modelo_ia=modelo,
    )
