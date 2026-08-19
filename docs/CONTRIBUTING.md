# Contribuindo

Antes de alterar uma funcionalidade, leia `SPEC.md`, inspecione a implementação e os testes existentes e faça a menor mudança coerente.

## Backend

```bash
cd backend
ruff check .
mypy app
pytest
```

Crie migrations com nomes descritivos:

```bash
alembic revision --autogenerate -m "create users"
alembic upgrade head
```

Revise migrations autogeradas antes de executá-las.

## Frontend

```bash
cd frontend
npm run lint
npm run typecheck
npm test -- --run
npm run build
```

## Convenções essenciais

- rotas públicas em `/api/v1`;
- regras de negócio em serviços, não em handlers ou componentes;
- TypeScript sem `any` sem justificativa;
- schema alterado somente via Alembic;
- nenhum segredo ou `.env` no repositório;
- correções de bugs devem incluir teste de regressão quando viável.
