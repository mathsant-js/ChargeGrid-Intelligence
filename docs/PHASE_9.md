# Fase 9 — Auditoria final do MVP

**Data da auditoria:** 25/09/2026

**Conclusão:** MVP funcional e demonstrável, com requisitos obrigatórios atendidos e débitos técnicos não bloqueantes explicitados abaixo.

Esta auditoria confrontou integralmente o `SPEC.md`, as seções de conceito,
objetivos, escopo, Golden Path, dashboards e critérios de sucesso do
`BRIEFING.md`, a implementação, as 12 migrations, testes, scripts, Docker,
workflows de CI e documentação. O `SPEC.md` foi tratado como fonte de verdade.
Funcionalidades secundárias ou futuras não foram contabilizadas como lacunas.

## Matriz requisito → implementação → teste → estado

| Requisito do MVP | Implementação principal | Evidência verificada | Estado |
| --- | --- | --- | --- |
| Monólito modular, REST `/api/v1` e OpenAPI | `app/api`, `app/services`, `app/simulation`, `app/ml`, `app/main.py` | `test_openapi.py`; API real usada pelo smoke | Atendido |
| Entidades, UUID, UTC e persistência | `app/models`, `app/db` | testes de domínio/API; PostgreSQL 16 limpo | Atendido |
| Evolução de schema por migrations | `migrations/versions/20260818_0001` a `20260924_0012` | `alembic current --check-heads` e `alembic check` | Atendido |
| Auth, hash de senha e papéis ADMIN/USER | `core/security.py`, dependencies e rotas de auth/users | `test_auth_authorization.py`, `test_users.py` | Atendido |
| Isolamento de veículos, sessões, energia, invoices, analytics e dashboard por usuário | filtros nas rotas e serviços | `test_auth_authorization.py`, `test_vehicles.py`, `test_energy.py`, `test_invoice_history.py`, `test_user_dashboard.py` | Atendido |
| Administração de usuários, veículos, estações, carregadores, tarifas e parâmetros | APIs CRUD aplicáveis e `AdminOperationsPage` | testes de users, vehicles, infrastructure, billing/configuration e React | Atendido |
| Regras de início, transições e encerramento de sessão | `services/charging_sessions.py` | `test_charging_session_domain.py`, `test_phase_6_flow.py` | Atendido |
| Concorrência: uma sessão ativa por carregador e veículo | índices parciais únicos e tradução de conflitos | migration `0008`; testes de concorrência/domínio | Atendido |
| Potência solicitada e limites individuais | serviço de sessão e `EqualSharePowerResolver` | `test_charging_session_domain.py`, `test_energy_allocation.py` | Atendido |
| Equal Share com redistribuição de sobras | `services/energy_allocation.py` | `test_energy_allocation.py`; smoke 4 × 15 kW | Atendido |
| Invariantes energéticas e limite de rede | alocador, validações do tick, cálculos e constraints | testes de allocation/readings/tick/runner; smoke 60 kW de rede | Atendido |
| Prioridade e rateio solar | alocador e tick | testes de allocation/tick; smoke 20 kW solar + 60 kW rede | Atendido |
| Cálculo e conservação de energia | `services/energy_readings.py` | `test_energy_reading_domain.py`, testes de simulação e Golden Path | Atendido |
| Relógio acelerado e simulação automática | `simulation/clock.py`, `control.py`, lifecycle FastAPI | `test_simulation_clock.py`, `test_simulation_runner.py`, `test_simulation_api.py` | Atendido |
| Curva solar determinística | `simulation/energy_data.py` | `test_simulation_energy_data.py`; cenário ao meio-dia UTC | Atendido |
| Billing decimal PAY_PER_USE e invoice fechada | `Numeric`, `Decimal`, `ROUND_HALF_UP`, serviço de encerramento | `test_billing_alerts.py`, `test_invoice_history.py`; invoice real de R$ 0,47 | Atendido |
| ESG: percentual solar, CO₂ evitado, fator exposto e economia estimada | `services/analytics.py`, schema e dashboard | `test_analytics.py`, `test_phase_6_flow.py`; smoke ESG | Atendido |
| Alertas HIGH_DEMAND, PEAK_RISK, HIGH_SOLAR_AVAILABILITY e SESSION_FINISHED | tick, inferência e encerramento | testes de tick/inferência/billing; três tipos exercitados no smoke | Atendido |
| Dataset de 90 dias e alvo +60 minutos | `ml/dataset.py`, pipeline e artefatos gerados | `test_ml_dataset.py`; smoke com 25.920 linhas | Atendido |
| Prevenção de leakage temporal | features causais e separação cronológica com gap do horizonte | testes de alteração futura e split sem sobreposição | Atendido |
| Baseline, modelos simples, métricas e seleção | `ml/baseline.py`, `ml/training.py` | `test_ml_training.py`; treino Docker com MAE/RMSE/R² | Atendido |
| Inferência +60 min, risco configurável e recomendação | `services/demand_predictions.py` e `/predictions/demand/run` | testes de inferência/configuração; previsão real HIGH | Atendido |
| ML estritamente consultivo | módulo de previsão não chama nem grava o alocador | inspeção do serviço e testes de inferência | Atendido |
| Dashboard administrativo mínimo | `AdminDashboardPage.tsx` | 14 testes React; dados reais consultados no smoke | Atendido |
| Dashboard do usuário e fluxo básico de sessão | `UserDashboardPage.tsx` | 4 testes React; antes/depois do encerramento no smoke | Atendido |
| Seed reproduzível do cenário oficial | `app/demo_seed.py` | `test_demo_seed.py`; execução Docker em banco limpo | Atendido |
| Tratamento semântico de erros e 500 sem stack trace | handlers, erros de domínio e contratos das rotas | `test_error_handling.py` e testes de autorização/conflito | Atendido |
| Logs de lifecycle, sessão, simulador, treino e falhas | `core/logging.py` e chamadas nos serviços/controladores | inspeção; testes de recuperação/log de falha do runner | Atendido |
| Variáveis de ambiente e proteção de secrets | `Settings`, `.env.example`, `.gitignore` | `.env` não rastreado; varredura não encontrou chaves privadas/tokens | Atendido |
| Docker, Compose, CI e documentação de execução | Dockerfiles, dois Compose, workflows, README e docs | build/stack Docker e workflows inspecionados | Atendido |
| Pagamentos reais, hardware/OCPP/Modbus, mobile nativo, microsserviços e escopo secundário | deliberadamente não implementados | exclusões explícitas em `SPEC.md`/`BRIEFING.md` | Fora do escopo |

Não foi identificado requisito obrigatório ausente. A classificação “Atendido”
significa que há implementação e evidência compatível com o MVP; não significa
prontidão para operação distribuída ou produção comercial.

## Evidências executadas nesta auditoria

### `make check`

Executado com sucesso em 25/09/2026:

```text
Ruff: aprovado
mypy: aprovado em 75 arquivos
pytest: 224 aprovados em 56,40 s; cobertura total 95%
ESLint: aprovado sem warnings
TypeScript: aprovado
Vitest: 34 aprovados em 6 arquivos
Vite build: aprovado; 639 módulos transformados
```

O maior chunk produzido foi `AdminDashboardPage`, com 415,92 kB (120,40 kB
gzip). O build não emitiu aviso de limite de chunk.

### PostgreSQL 16 limpo e Golden Path

`make mvp-smoke` foi executado com Docker Engine 29.7.2 e Compose 5.4.0. O
script criou um projeto Compose isolado, executou os testes abaixo e removeu
containers, rede e volumes ao final:

```text
PostgreSQL: postgres:16-alpine saudável
Migrations: 0001 → 0012 aplicadas
alembic current --check-heads: 20260924_0012 (head)
alembic check: No new upgrade operations detected
Seed: 1 admin, 4 users, 4 veículos, 1 estação, 4 carregadores,
      1 tarifa e configuração ESG
Backend e frontend: saudáveis
Golden Path público: aprovado
```

Resultados observados no Golden Path:

- três sessões receberam 20 kW cada, totalizando 60 kW de rede;
- com a quarta sessão, as quatro receberam 15 kW, ainda com 60 kW de rede;
- com pico solar de 20 kW, foram alocados 80 kW: 20 kW solar e 60 kW rede;
- a previsão para +60 minutos foi 76,5336 kW sobre capacidade efetiva de
  80 kW, classificada como `HIGH`, com recomendação consultiva;
- foram observados no smoke os alertas `HIGH_DEMAND`,
  `HIGH_SOLAR_AVAILABILITY` e `PEAK_RISK`; `SESSION_FINISHED` foi coberto pela
  suíte automatizada de billing/alertas;
- a quarta sessão terminou `COMPLETED`, o carregador voltou a `AVAILABLE` e a
  invoice ficou `CLOSED` em R$ 0,47;
- o relatório ESG mostrou 10 kWh totais, 2 kWh solares, 8 kWh da rede,
  20% solar, 0,8 kg de CO₂ evitado e R$ 1,60 de economia estimada;
- dashboards administrativo e do usuário refletiram o encerramento e billing.

O treino reproduzível comparou o baseline e três modelos clássicos. O vencedor
foi `HistGradientBoostingRegressor` por RMSE:

| Candidato | MAE | RMSE | R² |
| --- | ---: | ---: | ---: |
| Baseline histórico | 11,0964 | 14,1227 | 0,8259 |
| Random Forest | 11,1679 | 14,2275 | 0,8233 |
| Extra Trees | 11,0239 | 14,0214 | 0,8284 |
| Hist. Gradient Boosting | 10,9871 | 13,9732 | 0,8296 |

## Lacunas e débitos técnicos restantes

- O controlador automático garante exclusão mútua somente dentro de um processo
  backend. Múltiplos workers teriam relógios e runners independentes. Para a
  demonstração deve ser usado um único processo, como documentado.
- O estado do relógio (`RUNNING`, instante atual e `last_tick`) é local ao
  processo e se perde em reinícios; leituras já persistidas permanecem.
- O workflow normal de CI executa testes, lint, tipos e build, mas o smoke real
  em PostgreSQL/Docker está em workflow manual (`workflow_dispatch`).
- `GET /tariffs` e `GET /tariffs/{id}` não exigem autenticação, embora mutações
  sejam restritas a ADMIN. Tarifas não expõem dados pessoais, mas uniformizar a
  política de autenticação reduziria superfície pública e ambiguidade.
- Documentos históricos como `ARCHITECTURE.md`, `PHASE_4.md`, `PHASE_6.md` e
  `SPRINT_3_PLAN.md` ainda registram corretamente o estado de fases anteriores,
  nas quais não havia runner automático. Eles não devem ser usados como retrato
  do estado final sem consultar `README.md`, `PHASE_3.md` e esta auditoria.
- A vantagem do modelo vencedor sobre o baseline é pequena (RMSE cerca de 1,1%
  menor) e a avaliação por faixa mostra R² negativo nas faixas de demanda média
  e alta. Isso não impede o uso acadêmico consultivo, mas limita afirmações de
  superioridade preditiva ampla.

## Riscos para a apresentação

- Executar mais de um worker do backend pode duplicar controladores e tornar o
  relógio da demonstração incoerente.
- A inferência requer artefato compatível e histórico causal anterior; pular
  `app.ml.demo_prepare` produz respostas 422/503 previstas pela API.
- A demo determinística usa `APP_ENV=demo` e instante UTC explícito. Horário ou
  ambiente incorretos alteram a disponibilidade solar esperada.
- A máquina de apresentação precisa ter recursos para PostgreSQL, backend,
  frontend e treinamento; o smoke completo depende do daemon Docker.
- Credenciais padrão do Compose de desenvolvimento não são adequadas para
  staging/produção. O smoke usa secrets aleatórios efêmeros e a configuração
  rejeita o JWT placeholder fora de ambientes locais.

## Recomendações pós-MVP

1. Manter o roteiro `make mvp-smoke` como ensaio obrigatório antes da banca e
   capturar evidências visuais logo após sua execução.
2. Promover o smoke PostgreSQL a uma etapa protegida de CI quando o tempo de
   pipeline permitir.
3. Persistir/eleger o controlador da simulação antes de adotar múltiplos workers
   ou múltiplas réplicas; isso é evolução operacional, não requisito do MVP.
4. Reavaliar o modelo com dados reais e validação temporal por múltiplas janelas,
   dando atenção específica às faixas média e alta de demanda.
5. Uniformizar autenticação nas leituras de tarifa e consolidar documentos
   históricos em uma visão arquitetural final após a apresentação.

## Estado do Git ao iniciar a auditoria

A branch `codex/closing-gaps-mvp` estava alinhada com
`origin/codex/closing-gaps-mvp` e sem alterações rastreadas. A única mudança
produzida por esta auditoria é a atualização comprovada deste documento.
