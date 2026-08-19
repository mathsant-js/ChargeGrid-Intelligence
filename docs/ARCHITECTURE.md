# Arquitetura

O ChargeGrid Intelligence é um monólito modular composto por três processos em desenvolvimento:

```text
Browser → React/Vite → FastAPI → PostgreSQL
```

O backend separa transporte HTTP (`api`), configuração transversal (`core`), persistência (`db`, `models`, `repositories`) e regras (`services`, `simulation`, `analytics`, `ml`). Os módulos compartilham um único processo e um único banco.

## Fronteiras

- Rotas validam HTTP e delegam comportamento.
- Serviços concentram regras de negócio e invariantes.
- Repositórios isolam consultas e persistência.
- Modelos representam persistência; schemas representam contratos da API.
- O simulador será uma fonte de dados substituível, não o proprietário do domínio.
- ML será consultivo e nunca substituirá restrições energéticas determinísticas.

## Decisões da fundação

- Todo endpoint público usa `/api/v1`.
- Configuração e segredos chegam por variáveis de ambiente.
- Alterações de schema são versionadas por Alembic.
- PostgreSQL 16 é o banco de desenvolvimento e produção do MVP.
- O frontend consome a URL configurável `VITE_API_URL`.
- Datas futuras serão armazenadas em UTC, IDs serão UUID e dinheiro usará tipos decimais.

Consulte `SPEC.md` para regras funcionais e precedência de requisitos.
