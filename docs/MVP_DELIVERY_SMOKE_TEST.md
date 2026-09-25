# Validação automatizada da entrega do MVP

O smoke test de entrega executa a aplicação real contra PostgreSQL 16 e percorre,
por HTTP público, o Golden Path definido em `SPEC.md`. Ele é propositalmente
separado dos testes unitários e de integração rápidos executados por `make check`.

## Execução local

Pré-requisitos: Docker Engine, Docker Compose v2 e Python 3 disponíveis para o
orquestrador. Nenhum `.env` é necessário.

```bash
make mvp-smoke
```

O comando:

1. cria um projeto Compose com nome exclusivo;
2. gera senhas e segredo JWT aleatórios somente no ambiente do processo;
3. inicia um volume PostgreSQL exclusivo usando `postgres:16-alpine`;
4. executa `alembic upgrade head`, `alembic current --check-heads` e
   `alembic check` separadamente;
5. executa o seed e o preparo determinístico do modelo de demonstração;
6. inicia backend e frontend reais;
7. valida health, autenticação, energia, alertas, previsão, encerramento,
   billing, ESG, dashboards, OpenAPI e frontend;
8. remove containers, rede e volumes que pertencem somente ao projeto do teste.

Nesse ambiente, o intervalo do runner automático é elevado para uma hora para
não competir com os três ticks manuais determinísticos. Isso não altera a
duração simulada de cada tick nem a configuração padrão da aplicação (1 s).

As portas padrão são `18000` (backend) e `15173` (frontend). Para evitar um
conflito local, escolha outras portas sem editar arquivos:

```bash
MVP_SMOKE_BACKEND_PORT=28000 MVP_SMOKE_FRONTEND_PORT=25173 make mvp-smoke
```

O cleanup é instalado antes da primeira criação de recurso. Interrupções e
falhas também executam `docker compose down --volumes` com o nome exato do
projeto isolado; volumes da instalação normal e de outros projetos não são
referenciados.

## Evidência e falhas

Cada operação começa com `[stage]`. Em caso de erro, a última linha
`[failed] Stage: ...` identifica a etapa. O roteiro HTTP inclui o domínio da
asserção em mensagens como `[energy conservation]` e `[billing amount]`.
Não há retry de operações mutáveis. O único polling é o healthcheck limitado
de startup (20 tentativas no Compose e 30 segundos no cliente HTTP).

Para preservar os containers temporariamente durante investigação, execute os
comandos do arquivo `scripts/mvp_smoke.sh` manualmente; o fluxo oficial sempre
faz cleanup. Durante uma falha, os logs aparecem antes do cleanup com:

```bash
docker compose --project-name <nome-mostrado-no-log> \
  --file docker-compose.mvp-smoke.yml logs backend db frontend
```

Problemas comuns:

- `Docker availability`: inicie o daemon Docker e confirme `docker info`;
- `address already in use`: configure as duas portas alternativas acima;
- `Apply migrations` ou `Verify alembic metadata`: revise a migration indicada;
- `Prepare ML artifact`: confirme espaço em disco e examine a saída de métricas;
- `Start real backend and frontend`: examine os healthchecks e logs do serviço;
- `public-API Golden Path`: a mensagem entre colchetes identifica o contrato
  funcional que divergiu.

## CI

O workflow `MVP delivery smoke` é manual (`workflow_dispatch`) e possui timeout
de 20 minutos. Ele não roda em todo push ou pull request: builds Docker, treino
do artefato e inicialização PostgreSQL são mais caros que a suíte rápida. Use-o
como gate explícito de entrega/release, mantendo o workflow `CI` como feedback
rápido de desenvolvimento.

## Resultado verificado

Em 25/09/2026, o comando `make mvp-smoke` foi executado com Docker Engine
29.7.2 e Docker Compose 5.4.0. Resultado real: **aprovado**.

- PostgreSQL `16-alpine` ficou healthy em volume exclusivo;
- migrations chegaram a `20260924_0012 (head)` e `alembic check` informou
  `No new upgrade operations detected`;
- seed criou 1 ADMIN, 4 USERs, 4 veículos, 1 estação, 4 carregadores, tarifa e
  configuração ESG;
- o pipeline treinou e registrou MAE, RMSE e R² para baseline e candidatos;
- o cenário confirmou 3 × 20 kW, depois 4 × 15 kW e, com solar, 80 kW totais
  (20 kW solar + 60 kW rede), com conservação de energia;
- previsão de 60 minutos retornou risco `HIGH`; alertas `HIGH_DEMAND`,
  `HIGH_SOLAR_AVAILABILITY` e `PEAK_RISK` foram encontrados;
- a quarta sessão terminou `COMPLETED`, o carregador voltou a `AVAILABLE`, a
  invoice ficou `CLOSED` em R$ 0,47, e ESG e dashboards foram atualizados;
- health, OpenAPI e frontend responderam; todos os containers e volumes do
  projeto temporário foram removidos ao final.

Também foram executados `ruff`, `mypy` e os 224 testes do backend: todos
passaram, com cobertura total reportada de 95%.
