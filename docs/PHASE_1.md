# Fase 1 — Fundação

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

## Próxima fatia recomendada

Iniciar a Fase 2 por usuários/autenticação, em um fluxo vertical:

1. model e migration de `User`;
2. schemas e repository;
3. serviço de criação com hash de senha;
4. endpoints mínimos e testes;
5. tela ou integração mínima necessária.

Não criar antecipadamente todas as entidades em uma única migration. Cada fatia deve permanecer testável e demonstrável.

## Critérios de saída

- health check retorna `{"status":"ok"}`;
- OpenAPI lista o health check sob `/api/v1`;
- banco inicia e recebe `alembic upgrade head`;
- frontend compila, testa e representa estados online/offline da API;
- arquivos locais `.env`, artefatos e caches permanecem fora do Git.
