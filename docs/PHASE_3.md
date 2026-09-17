# Fase 3 — Simulação e leituras

## Escopo entregue

O backend possui relógio simulado determinístico, curva solar por estação, serviço de tick transacional e APIs de leitura de energia e solar. O controle administrativo fica em `/api/v1/simulation`: `GET /status`, `POST /start`, `POST /stop`, `POST /reset` e `POST /ticks` (um tick manual). Todos exigem JWT de ADMIN; token ausente ou inválido retorna 401 e USER retorna 403. Os contratos e erros esperados aparecem no OpenAPI.

`status` informa estado, instante UTC atual, duração simulada do tick em segundos, `simulation_speed` e timestamp do último tick concluído. `start` e `stop` são idempotentes e retornam 200 com o mesmo estado quando repetidos. `start` carrega `simulation_speed` da `SystemConfiguration`, quando presente. Sem configuração, o padrão é 60 segundos simulados por segundo real; o tick manual representa um segundo real.

`POST /ticks` exige estado RUNNING, executa uma vez `execute_tick` e retorna 409 se o simulador estiver parado. O serviço de tick abre uma transação para as leituras e acumuladores, confirma antes de avançar o relógio e registra sucesso ou falha. Sem sessões CHARGING, o relógio ainda avança. A resolução de potência provisória da Fase 3 aloca **zero kW** para cada sessão ativa. Isso gera leituras de energia com zero consumo e mantém os limites físicos, enquanto a curva solar gera `SolarReading` para cada estação com sessão ativa. O resolvedor é injetável; os testes do serviço exercitam leituras com potência não nula por um resolvedor de teste.

`reset` exige STOPPED e retorna 409 durante RUNNING. Ele limpa somente o estado do relógio e o marcador do último tick. O novo instante é o maior entre o horário UTC atual e o último timestamp persistido de energia ou solar mais uma duração de tick. Assim a próxima execução não reutiliza timestamps. **Nenhuma `EnergyReading` ou `SolarReading` é apagada**, nem são zerados acumuladores de sessões. Leituras continuam disponíveis nos endpoints `/energy/current`, `/energy/history`, `/solar/current` e `/solar/history`, inclusive com filtros `station_id`, `from` e `to` nos históricos.

## Arquitetura e limites

O controle usa um relógio e lock por processo web. `start` habilita apenas ticks manuais: não cria thread, timer ou loop automático. O serviço transacional permanece em `app.simulation.tick`, isolado do transporte HTTP. Logs registram start, stop, reset, tick concluído e falhas; erros inesperados recebem a resposta genérica 500 do aplicativo.

Este controle em memória é adequado para a demonstração com **um processo web**. Um reinício perde estado RUNNING, relógio e último tick, mas mantém leituras no banco. Vários workers teriam relógios independentes e não são suportados nesta fase. A idempotência de leituras por estação e timestamp é reforçada por constraints existentes.

## Migrations e validação

A Fase 3 usa as migrations existentes de `station_peak_solar_kw` e unicidade de tick (`20260916_0009` e `20260916_0010`). O controle administrativo não altera o schema, portanto não há migration nova. Os testes cobrem relógio, curva solar, transação, rollback, idempotência, autenticação, autorização, ciclo administrativo, leitura e OpenAPI.

Na validação desta entrega, `alembic heads` encontrou somente `20260916_0010 (head)` e `alembic upgrade head --sql` gerou SQL offline para PostgreSQL. O `alembic check` e o upgrade online não puderam ser concluídos: não havia PostgreSQL em `localhost:5432` e o daemon Docker recusou acesso ao socket. Uma tentativa de upgrade sobre SQLite parou na migration `0006`, que usa alteração de constraint não suportada pelo dialect SQLite. Não houve alteração de schema nesta entrega. A validação online das migrations existentes permanece como limitação operacional.

Ruff e mypy passaram; pytest concluiu 144 testes backend. Vitest concluiu 2 testes frontend; ESLint, typecheck TypeScript e build Vite passaram.

## Próxima fase

**Alocação de potência, limite de rede na distribuição e prioridade solar permanecem para a Fase 4.** O serviço de tick já valida os limites de uma resolução injetada; o resolvedor de produção ainda precisa implementar essas regras.

Alertas e analytics derivados por tick previstos no fluxo completo do SPEC ainda dependem das fases posteriores desses módulos.
