# B2B AI Onboarding & Credit Analysis 

## Nome do Projeto
AutoCred B2B - Agentes de IA para Onboarding e Crédito

## Descrição
Uma plataforma de automação B2B que utiliza sistemas de IA (Multiagentes) para realizar onboarding de novos clientes empresariais, extraindo dados de documentos, fazendo background check e analisando o risco de crédito em minutos.

## Problema Escolhido
O processo de aprovação de crédito e onboarding B2B é extremamente burocrático, manual e demorado. Analistas humanos perdem dias lendo balanços em PDF e consultando restrições no Serasa/Receita, o que aumenta o Custo de Aquisição de Clientes (CAC) e piora a experiência do usuário.

## Público-Alvo
Fintechs, bancos digitais e empresas de crédito B2B que precisam avaliar rapidamente o risco de novos clientes empresariais antes de liberar linhas de crédito, sem depender de um processo manual e demorado de análise.

## Objetivo Principal
Automatizar e acelerar o processo de onboarding e análise de crédito B2B, reduzindo o tempo de decisão de dias para minutos através de um agente de IA que avalia o perfil da empresa e emite score, limite aprovado e parecer.

## Solução Proposta
Um sistema onde o cliente envia seus documentos e uma esteira de Agentes de IA entra em ação:
1. **Agente Leitor:** Extrai dados do PDF (Contrato Social/Balanço).
2. **Agente Investigador:** Checa reputação e processos em APIs públicas.
3. **Agente Analista Financeiro:** Calcula indicadores (liquidez, endividamento).
4. **Agente Decisor:** Emite o parecer e aprova o limite.

O agente implementado e funcional nesta etapa é o **Agente Decisor**: a partir dos dados cadastrais da empresa, ele consulta a API do Gemini e retorna `score_credito`, `limite_aprovado` e `parecer_ia`, atualizando o processo de onboarding correspondente.

## Principais Funcionalidades
- **Gestão de empresas clientes** — CRUD completo com validação de CNPJ e garantia de unicidade.
- **Processos de onboarding** — abertura, consulta, atualização e remoção de processos de análise de crédito vinculados a uma empresa.
- **Análise automatizada de crédito por IA** — o Agente Decisor avalia a empresa e preenche score de crédito, limite aprovado e parecer justificado.
- **Consulta com filtros** — listagem de processos filtrada por empresa e por status, com paginação.
- **Trilha de auditoria** — registro de data de criação, data da análise e modelo de IA utilizado em cada parecer.
- **Tratamento resiliente de falhas** — indisponibilidade do serviço de IA é tratada de forma controlada, sem quebrar a aplicação nem expor detalhes internos.
- **Documentação interativa** — Swagger/OpenAPI gerado automaticamente e disponível em `/docs`.

## Regras de Negócio
- Uma empresa não pode ser cadastrada com um CNPJ já existente (CNPJ é único no sistema).
- Uma empresa não pode ter mais de um processo de onboarding **em aberto** simultaneamente (status `PENDENTE` ou `ANALISE_IA`).
- O CNPJ deve conter 14 dígitos válidos (aceito com ou sem formatação); CNPJs com todos os dígitos iguais são rejeitados.
- `score_credito` deve estar entre 0 e 100; `limite_aprovado` não pode ser negativo.
- O status de um processo só pode assumir um dos valores válidos: `PENDENTE`, `ANALISE_IA`, `APROVADO`, `REPROVADO`, `ERRO_ANALISE`.
- Uma empresa com processos de onboarding vinculados não pode ser excluída (retorna 409), preservando a trilha de auditoria das análises.
- Um processo já finalizado (`APROVADO` ou `REPROVADO`) não pode ser reanalisado pela IA.
- Todo processo de onboarding está sempre vinculado a uma empresa previamente cadastrada.
- Ao ser analisado pelo Agente de IA, o processo muda de status para `ANALISE_IA` (sucesso) ou `ERRO_ANALISE` (falha na comunicação com a IA ou resposta em formato inválido).

## Entidades Principais
- **Empresa**: dados cadastrais (CNPJ, razão social, setor, data de cadastro).
- **ProcessoOnboarding**: processo de análise de crédito vinculado a uma empresa, com status, score de crédito, limite aprovado, parecer da IA e trilha de auditoria (`data_criacao`, `data_analise`, `modelo_ia`).

## Relacionamento entre as Informações
Uma **Empresa** pode ter **N Processos de Onboarding** ao longo do tempo (relacionamento 1:N), permitindo manter o histórico de análises de uma mesma empresa em vez de sobrescrever os dados a cada nova tentativa.

## Restrições Relevantes
- O endpoint de análise de IA depende de uma chave de API do Gemini válida e configurada; sem ela, o endpoint retorna erro 500 de forma controlada.
- O banco de dados utilizado (SQLite) é adequado para desenvolvimento, mas não para produção com alta concorrência.
- O CORS está liberado para todas as origens (`allow_origins=["*"]`), o que é aceitável em ambiente de desenvolvimento mas deveria ser restrito em produção.

## Tecnologias Utilizadas
- **Linguagem:** Python 3.10+
- **Framework Web:** FastAPI (RESTful, validação automática, assíncrono)
- **Banco de Dados:** SQLite (com SQLAlchemy ORM) para ambiente de desenvolvimento CP1.
- **IA:** Google Gemini API (lib `google-genai`), modelo `gemini-3.6-flash`.
- **Documentação:** Swagger / OpenAPI (nativo do FastAPI)
- **Validação de Dados:** Pydantic v2
- **Testes:** Pytest + FastAPI TestClient

## Integrantes
- Adalberto Alves Cruz              | RM: 574115
- Bruno Henrique Ferreira Ambrosio | RM: 571218
- Gustavo da Silva Nascimento      | RM: 570821
- Lucas Maximo dos Santos          | RM: 569714
- Tiago Thomaz Cesaro              | RM: 569374

## Arquitetura Inicial
O projeto segue uma arquitetura em camadas, inspirada no padrão MVC e adaptada para uma API REST (sem camada de View tradicional, já que a "visão" da API é o próprio JSON retornado):
- `main.py`: Ponto de entrada da aplicação — instancia o FastAPI, configura CORS, carrega variáveis de ambiente e registra as rotas com o prefixo `/api/v1`.
- `models.py`: Entidades do banco de dados (SQLAlchemy) — camada de Model.
- `schemas.py`: Contratos de requisição/resposta e validações (Pydantic) — camada de serialização/validação.
- `routes.py`: Controladores e endpoints (Endpoints REST) — camada de Controller.
- `database.py`: Configuração e conexão com o banco (SQLite), com chaves estrangeiras habilitadas.
- `services/ia_service.py`: Camada de serviço que isola toda a integração com o modelo de IA. As rotas não conhecem detalhes do provedor — apenas solicitam a análise e recebem um resultado já validado.
- `tests/`: Testes automatizados da API (Pytest).

```
app/
├── main.py          # entrypoint, CORS, handler global de erros
├── database.py      # engine, sessão e dependência get_db
├── models.py        # entidades SQLAlchemy
├── schemas.py       # contratos Pydantic e validações
├── routes.py        # camada HTTP (Controller)
└── services/
    └── ia_service.py  # integração com o Gemini (Agente Decisor)
tests/
└── test_api.py      # 19 testes automatizados
```

## Instruções de Instalação
1. Clone este repositório.
2. Crie um ambiente virtual: `python -m venv venv`
3. Ative o ambiente virtual:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Instale as dependências: `pip install -r requirements.txt`

## Configuração das Variáveis de Ambiente
Este projeto depende de uma variável de ambiente para o funcionamento do endpoint de análise de IA. Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:

```
GEMINI_API_KEY=sua_chave_aqui
GEMINI_MODEL=gemini-3.6-flash
DATABASE_URL=sqlite:///./onboarding.db
```

> Há um arquivo `.env.example` na raiz do projeto. Basta copiá-lo para `.env` e preencher a chave:
> `cp .env.example .env` (Linux/Mac) ou `copy .env.example .env` (Windows).

A chave pode ser gerada em [Google AI Studio](https://aistudio.google.com/). Sem essa variável configurada, o endpoint `POST /onboarding/{id}/analisar` retorna erro 500 informando que a chave não está configurada.

O banco de dados SQLite (`onboarding.db`) não depende de configuração adicional — é criado automaticamente na raiz do projeto ao rodar a API.

## Instruções para Execução
Execute o servidor uvicorn:
```bash
python -m uvicorn app.main:app --reload
```

A API ficará disponível em `http://127.0.0.1:8000`.

## Testes Automatizados
O projeto possui 19 testes cobrindo CRUD, regras de negócio, validações e o Agente de IA (com mock, sem depender de rede ou chave real).

```bash
pip install pytest httpx
pytest -v
```

## Banco de Dados Utilizado
SQLite, acessado via SQLAlchemy ORM. Arquivo `onboarding.db` gerado automaticamente na raiz do projeto.

## Principais Endpoints

### Geral
| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/` | Health check — confirma que a API está no ar e aponta para o Swagger |

### Empresas
| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/v1/empresas/` | Cadastra uma nova empresa |
| GET | `/api/v1/empresas/` | Lista empresas cadastradas |
| GET | `/api/v1/empresas/{empresa_id}` | Consulta uma empresa por id |
| PUT | `/api/v1/empresas/{empresa_id}` | Atualiza uma empresa |
| DELETE | `/api/v1/empresas/{empresa_id}` | Remove uma empresa |

### Onboarding
| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/v1/onboarding/` | Inicia um processo de onboarding para uma empresa |
| GET | `/api/v1/onboarding/` | Lista processos (filtros: `empresa_id`, `status`) |
| GET | `/api/v1/onboarding/{processo_id}` | Consulta um processo por id |
| PUT | `/api/v1/onboarding/{processo_id}` | Atualiza um processo |
| DELETE | `/api/v1/onboarding/{processo_id}` | Remove um processo |

### IA - Agentes
| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/v1/onboarding/{processo_id}/analisar` | Aciona o Agente de IA para analisar o crédito da empresa e preencher score, limite e parecer |

## Documentação Swagger
Disponível automaticamente ao rodar o projeto, em: `http://127.0.0.1:8000/docs`

## Link do Trello/Notion
`https://trello.com/invite/b/6a999f607f1add5c17565f9a/ATTI401df893b37c3e341000041eca0ab340B409E817/gestor-empresarial`

## Link do Repositório
`https://github.com/Adalberto-Cruz/Gestor-Empresarial`