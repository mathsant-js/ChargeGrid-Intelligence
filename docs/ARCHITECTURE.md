# Arquitetura

O ChargeGrid Intelligence é um monólito modular composto por três processos em desenvolvimento:

```text
Browser → React/Vite → FastAPI → PostgreSQL
```

O backend separa transporte HTTP (`api`), configuração transversal (`core`), acesso
ao banco (`db`), persistência (`models`), contratos (`schemas`) e regras de domínio
(`services`). Os pacotes `repositories`, `simulation`, `analytics` e `ml` já reservam
as fronteiras previstas no `SPEC.md`, mas ainda não possuem implementação funcional.
Todos os módulos compartilham um único processo e um único banco.

## Fronteiras

- Rotas usam schemas Pydantic para validar HTTP e, no estado atual, executam CRUD e
  consultas simples diretamente pela `Session` do SQLAlchemy.
- O serviço `services/charging_sessions.py` concentra as regras existentes de início
  e encerramento da sessão: usuário ativo, propriedade do veículo, disponibilidade
  do carregador, exclusividade de sessão ativa, potência solicitada, cálculo final,
  invoice e alerta.
- `api/routes/common.py` centraliza a injeção da sessão de banco, busca com resposta
  404 e commit com conversão de conflito de integridade para HTTP 409.
- O pacote `repositories` está vazio. Repositórios serão adicionados quando consultas
  repetidas ou complexas exigirem essa separação; não são uma camada ativa hoje.
- Modelos representam persistência; schemas representam contratos da API.
- `simulation` será uma fonte de dados substituível, não o proprietário do domínio.
- `analytics` e `ml` ainda serão implementados; ML permanecerá consultivo e nunca
  substituirá restrições energéticas determinísticas.

## Fluxo implementado de sessão

```text
HTTP /api/v1/sessions
        ↓
schemas Pydantic + carregamento das entidades
        ↓
serviço de sessões (regras e alterações da transação)
        ↓
commit na rota
        ↓
SQLAlchemy models → PostgreSQL
```

As demais rotas seguem, por enquanto, o fluxo direto
`rota → Session SQLAlchemy → models → PostgreSQL`. Regras novas não devem ser
acrescentadas a esse fluxo: quando houver regra de negócio, ela deve ser movida para
um serviço testável.

## Decisões da fundação

- Todo endpoint público usa `/api/v1`.
- Configuração e segredos chegam por variáveis de ambiente.
- Alterações de schema são versionadas por Alembic.
- PostgreSQL 16 é o banco de desenvolvimento e produção do MVP.
- O frontend consome a URL configurável `VITE_API_URL`.
- Datas são armazenadas em UTC, IDs usam UUID e valores monetários usam tipos
  decimais.

Consulte `SPEC.md` para regras funcionais e precedência de requisitos.
