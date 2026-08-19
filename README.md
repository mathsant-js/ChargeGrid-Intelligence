# ChargeGrid Intelligence

Plataforma acadêmica para simular e gerenciar uma infraestrutura de recarga de veículos elétricos com controle energético, energia solar, billing, analytics e previsão de demanda.

O projeto usa um **monólito modular**: uma API FastAPI, uma aplicação React e PostgreSQL. A especificação técnica é a fonte de verdade da implementação.

## Pré-requisitos

- Docker com Docker Compose (caminho recomendado); ou
- Python 3.12, Node.js 22+ e PostgreSQL 16 para execução local.

## Início rápido com Docker

```bash
cp .env.example .env
docker compose up --build
```

Serviços:

- frontend: <http://localhost:5173>
- API: <http://localhost:8000/api/v1/health>
- OpenAPI: <http://localhost:8000/docs>
- PostgreSQL: `localhost:5432`

Para aplicar migrations manualmente:

```bash
docker compose run --rm backend alembic upgrade head
```

## Desenvolvimento local

Backend:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

## Qualidade

```bash
make install # primeira execução
make check
```

O alvo executa testes, lint e verificação de tipos no backend e no frontend, além do build web. Consulte [CONTRIBUTING.md](docs/CONTRIBUTING.md) para o fluxo detalhado.

## Documentação

- [Briefing](BRIEFING.md)
- [Especificação técnica](SPEC.md)
- [Instruções para agentes](AGENTS.md)
- [Arquitetura](docs/ARCHITECTURE.md)
- [Plano da Fase 1](docs/PHASE_1.md)

## Estado atual

A fundação da Fase 1 inclui estrutura de diretórios, configuração por ambiente, PostgreSQL, Alembic, API com health check, shell React, testes e automação de qualidade. Entidades e regras de domínio começam na Fase 2.
