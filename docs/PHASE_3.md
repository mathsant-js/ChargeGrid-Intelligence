# Fase 3 — Simulação e leituras

## Escopo entregue

O backend possui relógio simulado determinístico, curva solar por estação, serviço de tick transacional e APIs de leitura de energia e solar. O controle administrativo fica em `/api/v1/simulation`: `GET /status`, `POST /start`, `POST /stop`, `POST /reset` e `POST /ticks` (um tick manual). Todos exigem JWT de ADMIN; token ausente ou inválido retorna 401 e USER retorna 403. Os contratos e erros esperados aparecem no OpenAPI.

`status` informa estado, instante UTC atual, duração simulada do tick em segundos, `simulation_speed` e timestamp do último tick concluído. `start` e `stop` são idempotentes e retornam 200 com o mesmo estado quando repetidos. `start` carrega `simulation_speed` da `SystemConfiguration`, quando presente, e garante um único runner automático ativo. Sem configuração, o padrão é 60 segundos simulados por segundo real; cada execução representa o intervalo real configurado no relógio (um segundo por padrão).

Enquanto o estado é RUNNING, o runner aguarda o intervalo real do relógio e executa `execute_tick` com uma nova `Session` SQLAlchemy, fechada ao fim daquela execução. A sessão HTTP nunca é compartilhada com o runner. Falhas isoladas são registradas, causam rollback e não avançam o relógio; o loop continua para tentar novamente no intervalo seguinte. `POST /stop` interrompe a espera e aguarda a tarefa terminar, e o shutdown do FastAPI faz o mesmo de maneira limpa.

`POST /ticks` continua disponível para testes e demonstrações controladas. Ele exige estado RUNNING, executa uma vez `execute_tick` e retorna 409 se o simulador estiver parado. O mesmo lock protege ticks automáticos e manuais, impedindo sobreposição. O serviço de tick abre uma transação para as leituras e acumuladores, confirma antes de avançar o relógio e registra sucesso ou falha. Sem sessões CHARGING, o relógio ainda avança. Na entrega original da Fase 3, a resolução provisória alocava **zero kW**; a Fase 4 a substituiu por Equal Share Allocation V1. Consulte [Fase 4](PHASE_4.md) para o comportamento atual do tick. O resolvedor permanece injetável para testes do serviço.

`reset` exige STOPPED e retorna 409 durante RUNNING. Ele limpa somente o estado do relógio e o marcador do último tick. O novo instante é o maior entre o horário UTC atual e o último timestamp persistido de energia ou solar mais uma duração de tick. Assim a próxima execução não reutiliza timestamps. **Nenhuma `EnergyReading` ou `SolarReading` é apagada**, nem são zerados acumuladores de sessões. Leituras continuam disponíveis nos endpoints `/energy/current`, `/energy/history`, `/solar/current` e `/solar/history`, inclusive com filtros `station_id`, `from` e `to` nos históricos.

## Arquitetura e limites

O controle usa um relógio, uma tarefa assíncrona e um lock por processo web. O lifecycle do FastAPI inicializa o controlador e garante seu encerramento. O serviço transacional permanece em `app.simulation.tick`, isolado do transporte HTTP. Logs registram startup e shutdown do controlador, start, stop, início e término do runner, reset, tick concluído e falhas; erros inesperados recebem a resposta genérica 500 do aplicativo.

Esta coordenação garante no máximo um runner e ausência de ticks sobrepostos **dentro de uma única instância/processo do backend**, o que é suficiente para o MVP e para a demonstração. Um reinício perde estado RUNNING, relógio e último tick, mas mantém leituras no banco. Vários workers teriam relógios e runners independentes e não são suportados nesta fase. A idempotência de leituras por estação e timestamp é reforçada por constraints existentes.

## Migrations e validação

A Fase 3 usa as migrations existentes de `station_peak_solar_kw` e unicidade de tick (`20260916_0009` e `20260916_0010`). O controle administrativo não altera o schema, portanto não há migration nova. Os testes cobrem relógio, curva solar, transação, rollback, idempotência, autenticação, autorização, ciclo administrativo, leitura, OpenAPI, execução automática, estado parado, stop, start repetido, exclusão mútua, recuperação após falha, shutdown, sessão isolada e invariantes energéticas.

Na validação desta entrega, `alembic heads` encontrou somente `20260916_0010 (head)` e `alembic upgrade head --sql` gerou SQL offline para PostgreSQL. Posteriormente, `alembic upgrade head` foi executado em um PostgreSQL 16 temporário e chegou à revisão `20260916_0010`; `alembic check` concluiu sem operações pendentes. As três constraints de enum das migrations `0006` e `0007` passaram a ser declaradas explicitamente nos modelos: o Alembic 1.19 não compara constraints vinculadas ao tipo `Enum`, embora elas estivessem presentes no banco. Não houve alteração do schema nem migration nova. O banco temporário foi removido após a validação.

Para esta evolução, Ruff e mypy passaram e a suíte completa concluiu 216 testes backend. A mudança não altera o frontend.

## Evolução posterior

Alocação de potência, limite de rede na distribuição e prioridade solar foram entregues na Fase 4.

Alertas e analytics derivados por tick previstos no fluxo completo do SPEC ainda dependem das fases posteriores desses módulos.
