# B2B AI Onboarding & Credit Analysis 

## Nome do Projeto
AutoCred B2B - Agentes de IA para Onboarding e Crédito

## Descrição
Uma plataforma de automação B2B que utiliza sistemas de IA (Multiagentes) para realizar onboarding de novos clientes empresariais, extraindo dados de documentos, fazendo background check e analisando o risco de crédito em minutos.

## Problema Escolhido
O processo de aprovação de crédito e onboarding B2B é extremamente burocrático, manual e demorado. Analistas humanos perdem dias lendo balanços em PDF e consultando restrições no Serasa/Receita, o que aumenta o Custo de Aquisição de Clientes (CAC) e piora a experiência do usuário.

## Solução Proposta
Um sistema onde o cliente envia seus documentos e uma esteira de Agentes de IA entra em ação:
1. **Agente Leitor:** Extrai dados do PDF (Contrato Social/Balanço).
2. **Agente Investigador:** Checa reputação e processos em APIs públicas.
3. **Agente Analista Financeiro:** Calcula indicadores (liquidez, endividamento).
4. **Agente Decisor:** Emite o parecer e aprova o limite.

## Integrantes
- Adalberto Alves Cruz             | RM: 574115
- Bruno Henrique Ferreira Ambrosio | RM: 571218
- Gustavo da Silva Nascimento      | RM: 570821
- Lucas Maximo dos Santos          | RM: 569714
- Tiago Thomaz Cesaro              | RM: 569374

## Tecnologias Utilizadas
- **Linguagem:** Python 3.10+
- **Framework Web:** FastAPI (RESTful, validação automática, assíncrono)
- **Banco de Dados:** SQLite (com SQLAlchemy ORM) para ambiente de desenvolvimento CP1.
- **Documentação:** Swagger / OpenAPI (nativo do FastAPI)
- **Validação de Dados:** Pydantic

## Arquitetura Inicial
O projeto segue o padrão MVC (Model, View, Controller) adaptado para APIs REST, dividido em:
- `models.py`: Entidades do banco de dados (SQLAlchemy).
- `schemas.py`: Contratos de requisição/resposta e validações (Pydantic).
- `routes.py`: Controladores e endpoints (Endpoints REST).
- `database.py`: Configuração do banco (SQLite).

## Instruções de Instalação
1. Clone este repositório.
2. Crie um ambiente virtual: `python -m venv venv`
3. Ative o ambiente virtual:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Instale as dependências: `pip install -r requirements.txt`

## Configuração das Variáveis de Ambiente
Para este Checkpoint 1, o banco de dados utilizado é o SQLite, portanto, nenhuma variável complexa de ambiente é obrigatória. O banco `onboarding.db` será criado automaticamente na raiz do projeto ao rodar a API.

## Instruções para Execução
Execute o servidor uvicorn:
```bash
uvicorn app.main:app --reload
```
A API estará rodando em `http://127.0.0.1:8000`

## Banco de Dados Utilizado
- **SQLite3** (Para o Checkpoint 1, focado em prototipagem e validação da arquitetura).

## Principais Endpoints
- `POST /api/v1/empresas/` - Cadastra uma nova empresa no sistema.
- `GET /api/v1/empresas/` - Lista as empresas cadastradas.
- `POST /api/v1/onboarding/` - Inicia um novo processo de onboarding/análise de crédito.
- `PUT /api/v1/onboarding/{id}` - Atualiza o status/score do processo (será usado pela IA futuramente).

## Link para Documentação Swagger
Com a API rodando, acesse: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Organização do Projeto
- **Link do Trello:** [(https://trello.com/b/vJLowf7X/gestor-empresarial)]
