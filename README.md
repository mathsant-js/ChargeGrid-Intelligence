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
- [Fase 1 — Fundação (concluída)](docs/PHASE_1.md)
- [Fase 2 — Autenticação e autorização](docs/PHASE_2.md)

## Estado atual

### Demonstração do vídeo pitch (`primeira_apresentacao_28_08`)

A página inicial oferece uma simulação acelerada e autocontida para apresentar os três
entregáveis da primeira avaliação: distribuição inteligente de potência com proteção do
limite da rede, acompanhamento e fechamento da cobrança pay-per-use e uma interface de
recarga com quatro veículos. Use **Iniciar simulação** e **Finalizar e cobrar** para
percorrer o roteiro da apresentação. Não é necessário login para esta tela demonstrativa.

A Fase 1 está concluída e seus critérios de saída estão documentados com evidências.
Além da fundação técnica, o backend já expõe APIs e persistência para usuários,
veículos, estações, carregadores, sessões, leituras de energia e solar, tarifas,
invoices, alertas, previsões de demanda e configuração do sistema. O início e o
encerramento de sessões já aplicam regras de domínio, incluindo disponibilidade,
potência solicitada, billing e alerta de conclusão.

O backend também possui login JWT e autorização mínima por papel e propriedade. A
Fase 2 ainda não é declarada concluída: esta fatia cobre autenticação e limites de
acesso, e as próximas fatias devem seguir os critérios documentados em
[Fase 2 — Autenticação e autorização](docs/PHASE_2.md).
