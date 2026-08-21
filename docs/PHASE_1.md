# Fase 1 — Fundação (concluída)

**Status:** concluída em 21/08/2026.

## Objetivo

Entregar uma base reproduzível para que as primeiras fatias verticais de domínio sejam implementadas sem reestruturar o projeto.

## Entregue

- estrutura modular do repositório;
- documentos de requisitos versionados;
- FastAPI com OpenAPI, CORS, logging e `GET /api/v1/health`;
- SQLAlchemy e Alembic configurados com migration baseline;
- PostgreSQL 16 no Docker Compose;
- React, TypeScript, Vite, React Router, Tailwind e Recharts configurados;
- shell visual que verifica a saúde da API;
- testes backend e frontend;
- lint, type-check, build e workflow de integração contínua;
- `.env.example` sem segredos.

## Continuidade

A fundação passou a sustentar partes das fases seguintes: usuários, veículos,
estações, carregadores, sessões, tarifas, invoices, alertas, leituras energéticas e
configuração de previsão já possuem persistência e API. O ciclo de sessão concentra
suas regras em `backend/app/services/charging_sessions.py`; as demais operações CRUD
ainda usam a sessão SQLAlchemy diretamente nas rotas.

A próxima fatia deve seguir o roadmap do `BRIEFING.md` e o fluxo principal do
`SPEC.md`, priorizando:

1. relógio e produção de leituras pela simulação;
2. cálculo de energia por intervalo;
3. alocação determinística de potência respeitando o limite da rede e os limites de
   carregador e veículo;
4. prioridade solar e separação entre energia solar e energia da rede;
5. integração dessas regras com sessões, alertas e testes de regressão.

Serviços devem ser extraídos quando houver regra de negócio ou coordenação de uma
transação. Repositórios devem ser introduzidos apenas quando consultas repetidas ou
complexas justificarem a abstração; o pacote existente não significa que essa camada
já esteja implementada.

## Critérios de saída

- [x] O health check retorna `{"status":"ok"}`. Evidência:
  `backend/tests/test_health.py::test_health_returns_ok`.
- [x] O OpenAPI lista o health check sob `/api/v1`. Evidência:
  `backend/tests/test_openapi.py::test_openapi_is_available` valida
  `/api/v1/health` no schema gerado.
- [x] O PostgreSQL inicia e recebe `alembic upgrade head`. Evidência:
  `docker-compose.yml` aguarda o health check do banco e executa a migration antes
  do Uvicorn; a validação de 21/08/2026 aplicou a revisão final
  `20260820_0005` em PostgreSQL 16.
- [x] O frontend compila, testa e representa os estados online/offline da API.
  Evidência: `frontend/src/pages/FoundationPage.test.tsx` cobre ambos os estados e
  `npm run build` gera o bundle de produção.
- [x] Arquivos `.env` locais, artefatos e caches permanecem fora do Git. Evidência:
  regras em `.gitignore`; entre esses padrões, somente `.env.example` é
  explicitamente versionado.

## Validação de conclusão

Executada em 21/08/2026:

```text
make check
  ruff: aprovado
  mypy: aprovado (49 arquivos)
  pytest: 16 aprovados, cobertura total de 97%
  eslint: aprovado
  TypeScript: aprovado
  Vitest: 2 aprovados
  Vite build: aprovado

docker compose up -d db
docker compose run --rm backend alembic upgrade head
  PostgreSQL: saudável
  revisão aplicada: 20260820_0005
```
