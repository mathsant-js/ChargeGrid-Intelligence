# Fase 2 — Domínio

## Estado

**Concluída em 31/08/2026.**

A Fase 2 entrega o domínio de usuários, autenticação, veículos, estações,
carregadores e sessões previsto no `SPEC.md` e no roadmap do `BRIEFING.md`.
A validação descrita abaixo foi atualizada em 01/09/2026 para refletir o estado
atual do repositório.

## Itens entregues

- usuários com UUID, email único normalizado, papéis `ADMIN`/`USER`, ativação,
  timestamps UTC e senha armazenada somente como hash scrypt;
- login JWT HS256 com expiração, `sub` igual ao UUID do usuário e endpoint
  autenticado `GET /api/v1/auth/me`;
- autorização backend por papel e propriedade, com proteção contra IDOR e respostas
  `401`, `403`, `404`, `409` e `422` conforme o caso;
- CRUD especificado de veículos, com vínculo ao usuário autenticado e potência
  máxima positiva;
- CRUD especificado de estações e carregadores, restrito ao administrador para
  escrita, com potências positivas e estados válidos;
- listagem e consulta de sessões, início e encerramento pelo motorista proprietário;
- regras de início centralizadas no serviço de domínio: usuário ativo, veículo do
  usuário, carregador ativo e disponível, ausência de sessão ativa concorrente no
  carregador e no veículo;
- cálculo de `requested_power_kw` como o menor valor entre os limites do carregador
  e do veículo;
- transições válidas de sessão e bloqueio de retorno de estados terminais;
- encerramento em `COMPLETED`, `ended_at` UTC, potência alocada zerada e carregador
  novamente `AVAILABLE`;
- schemas públicos sem `password_hash` e operações públicas sob `/api/v1`.

## Política de acesso

- `ADMIN` lista, cria e altera usuários e cria ou altera estações e carregadores;
- `ADMIN` consulta globalmente usuários, veículos e sessões, mas não executa as
  operações de motorista sobre veículos e sessões;
- `USER` consulta e altera seu próprio usuário, mas não pode alterar `role`;
- `USER` cria, consulta, altera e exclui somente os próprios veículos;
- `USER` consulta estações e carregadores necessários ao início da recarga;
- `USER` inicia, consulta e encerra somente as próprias sessões;
- recursos de outro usuário respondem `404`, sem confirmar sua existência;
- credenciais inválidas e contas inativas respondem igualmente `401`;
- `user_id` de veículos e sessões é derivado do JWT, não do corpo da requisição.

Tokens ausentes, inválidos ou expirados respondem `401` com desafio Bearer. O login
e o health check são os únicos endpoints da Fase 2 sem segurança Bearer declarada
no OpenAPI.

## Migrations

A cadeia Alembic possui uma única head:

- `20260818_0001`: baseline da Fase 1;
- `20260818_0002`: users, vehicles, charging stations e chargers;
- `20260818_0003`: charging sessions (além de tabelas preparatórias já existentes);
- `20260831_0006`: constraints de `UserRole` e `ChargerStatus`;
- `20260831_0007`: constraint de `ChargingSessionStatus`;
- `20260901_0008`: índices únicos parciais que impedem sessões ativas concorrentes
  para o mesmo carregador ou veículo.

As revisions intermediárias `0004` e `0005` já existiam na cadeia antes desta
validação e não foram ampliadas. Em 01/09/2026, `alembic heads` retornou somente
`20260901_0008 (head)` e a geração SQL offline do upgrade completo para PostgreSQL
foi concluída. A aplicação contra um PostgreSQL ativo não foi validada nesta
execução porque o acesso ao daemon Docker foi negado.

## Checklist objetiva de saída

- [x] **Users/Auth:** CRUD previsto, hash de senha, email único, JWT, conta inativa,
  papéis e não exposição do hash — cobertos por `test_users.py` e
  `test_auth_authorization.py`.
- [x] **Vehicles:** CRUD, propriedade, IDOR, owner derivado do token, validação e
  referências — cobertos por `test_vehicles.py` e `test_auth_authorization.py`.
- [x] **Stations/Chargers:** CRUD, autorização administrativa, referências,
  potências e enums — cobertos por `test_infrastructure.py`.
- [x] **Sessions:** início, término, propriedade, concorrência, disponibilidade,
  potência solicitada e estados terminais — cobertos por
  `test_charging_session_domain.py`.
- [x] **Persistência:** UUIDs, timestamps, FKs, checks positivos e constraints dos
  enums da Fase 2, além dos índices únicos parciais da migration `0008` para
  sessões ativas concorrentes — cobertos pela suíte backend atual.
- [x] **API/OpenAPI:** 27 paths gerados em OpenAPI 3.1.0; todos os endpoints exigidos
  de Auth, Users, Vehicles, Stations, Chargers e Sessions estão presentes e têm a
  segurança esperada — coberto por `test_openapi.py` e inspeção do schema gerado.
- [x] **Qualidade backend:** Ruff e mypy strict passaram; pytest passou com 72 testes
  e 97% de cobertura total.
- [x] **Frontend preservado:** ESLint, TypeScript, 2 testes Vitest e build Vite de
  produção passaram.
- [x] **Segurança do repositório:** nenhum `.env`, chave privada, token ou segredo
  foi adicionado; apenas `.env.example` permanece versionado.
- [x] **Higiene:** nenhuma ocorrência real de TODO/FIXME ou stub; regras de ciclo de
  vida, concorrência e potência de sessão estão em
  `app/services/charging_sessions.py`, enquanto checks de autorização permanecem
  nas dependências/rotas. Classes Pydantic e SQLAlchemy vazias são heranças
  declarativas intencionais, não stubs.

## Limites desta fase

Não fazem parte da conclusão da Fase 2: relógio/ticks do simulador, cálculo ou
alocação energética, prioridade/rateio solar, dashboards, indicadores ESG,
treinamento ou inferência de ML. Os pacotes `simulation`, `analytics` e `ml`
continuam sem implementação dessas regras. Estruturas persistentes e endpoints
preparatórios de energia, solar, billing, alertas e previsões que já existiam não
constituem a implementação dos fluxos das fases posteriores e não foram ampliados
nesta validação.
