# Matriz de rastreabilidade — Sprint 4

Esta matriz liga requisito, implementação, teste e evidência. `Baseline`
significa capacidade existente e verificada em 20/10/2026; `Pendente` indica
trabalho previsto pelo plano, sem alegação de entrega.

| ID | Requisito | Implementação | Teste | Evidência / estado |
| --- | --- | --- | --- | --- |
| S4-01 | Runner cria ticks automaticamente enquanto `RUNNING` | `backend/app/simulation/control.py` | `backend/tests/test_simulation_runner.py::test_runner_ticks_while_running_uses_fresh_session_and_stops` | `make check` e smoke aprovados — **Baseline** |
| S4-02 | Start repetido não cria runners duplicados | `backend/app/simulation/control.py` | `backend/tests/test_simulation_runner.py::test_stopped_controller_has_no_ticks_and_repeated_start_has_one_runner` | 231 testes backend aprovados — **Baseline** |
| S4-03 | Falha isolada de tick não encerra o runner | `backend/app/simulation/control.py` | `backend/tests/test_simulation_runner.py::test_runner_recovers_after_isolated_tick_failure` | 231 testes backend aprovados — **Baseline** |
| S4-04 | Ticks concorrentes são impedidos e o relógio persiste | `backend/app/simulation/control.py`, `backend/app/simulation/tick.py`, migration `20261012_0013_persist_simulation_state.py` | testes de lock, checkpoint e reinício em `backend/tests/test_simulation_runner.py` e `backend/tests/test_simulation_tick.py` | Migration head e suíte aprovados — **Baseline** |
| S4-05 | Alocação respeita potência solicitada, limites individuais e limite da rede | `backend/app/services/energy_allocation.py`, validações defensivas em `backend/app/simulation/tick.py` | `backend/tests/test_energy_allocation.py`, teste de invariantes automáticas em `backend/tests/test_simulation_runner.py` | Golden Path: 4 × 15 kW sem solar e rede em 60 kW — **Baseline** |
| S4-06 | Solar tem prioridade sem exceder geração disponível | `backend/app/services/energy_allocation.py`, `backend/app/simulation/tick.py` | `backend/tests/test_energy_allocation.py`, `backend/tests/test_simulation_tick.py` | Golden Path: 80 kW = 20 kW solar + 60 kW rede — **Baseline** |
| S4-07 | Curva solar é determinística, finita, não negativa e limitada ao pico | `backend/app/simulation/energy_data.py::SimulationEnergyDataProvider` | `backend/tests/test_simulation_energy_data.py` | Suíte backend aprovada — **Baseline** |
| S4-08 | Dashboard expõe KPIs, gráficos, sessões, alertas, ML e ESG | `frontend/src/pages/AdminDashboardPage.tsx` | `frontend/src/pages/AdminDashboardPage.test.tsx`, `frontend/src/pages/energyHistory.test.ts` | 35 testes frontend e build aprovados; smoke confirmou dashboards — **Baseline** |
| S4-09 | Dashboard atualiza periodicamente durante execução | `frontend/src/pages/AdminDashboardPage.tsx` | testes com timers falsos em `frontend/src/pages/AdminDashboardPage.test.tsx` | **Concluído (Etapa 2)** |
| S4-10 | Polling é cancelado no unmount e não sobrepõe consultas | `frontend/src/pages/AdminDashboardPage.tsx` | testes de cleanup e atualização em `frontend/src/pages/AdminDashboardPage.test.tsx` | **Concluído (Etapa 2)** |
| S4-11 | Usuário pode solicitar atualização imediata | Botão `Atualizar agora` em `frontend/src/pages/AdminDashboardPage.tsx` | `frontend/src/pages/AdminDashboardPage.test.tsx` | **Concluído (Etapa 2)** |
| S4-12 | Tela mostra estado, instante, último tick, velocidade e origem dos dados | `frontend/src/pages/AdminDashboardPage.tsx` | `backend/tests/test_simulation_api.py` e `frontend/src/pages/AdminDashboardPage.test.tsx` | **Concluído (Etapa 2)** |
| S4-13 | Provider de replay valida timestamp, finitude, não negatividade, pico, ausência e qualidade | `backend/app/simulation/energy_data.py::TelemetryReplayEnergyDataProvider`, `data/raw/sprint4_telemetry.csv` | `backend/tests/test_simulation_energy_data.py` | Replay determinístico com ausência segura e validação na carga — **Concluído (Etapa 3)** |
| S4-14 | Provider é selecionável por configuração e `curve` segue como padrão | `backend/app/core/config.py`, `backend/app/simulation/control.py`, `.env.example`, `docker-compose.yml` | `backend/tests/test_config.py` e testes do controlador | `curve` preservado como padrão; `telemetry_replay` configurável — **Concluído (Etapa 3)** |
| S4-15 | Troca do provider não altera invariantes energéticas | Contrato `EnergyDataSample`, injeção única no controlador e validações em `execute_tick` | `backend/tests/test_simulation_tick.py::test_tick_integrates_replayed_telemetry_without_changing_energy_invariants` | Replay apenas fornece solar; Equal Share permanece responsável pela alocação — **Concluído (Etapa 3)** |
| S4-16 | Cenário automático da Sprint 4 usa somente APIs públicas | `scripts/sprint4_demo.py`; runner observado por polling de `/energy/history`, sem `/simulation/ticks` | `backend/tests/test_sprint4_demo_script.py` e `make mvp-smoke` | **Concluído (Etapa 4)** |
| S4-17 | Cenário registra resultados reais de energia, billing, ESG, risco e métricas | resumo JSON de `scripts/sprint4_demo.py` e pipeline de ML | `make mvp-smoke` | Saída inclui energia, participação solar, CO₂, economia, invoice, risco e recomendação — **Concluído (Etapa 4)** |
| S4-18 | Materiais da Sprint 4 ficam em `docs/sprint4/` | Índice, baseline e esta matriz | Revisão de links e diff | **Concluído (Etapa 1)** |
| S4-19 | Validação completa executa `make check` e `make mvp-smoke` | `Makefile`, `scripts/mvp_smoke.sh` | Execução real em 20/10/2026 | Ambos aprovados — **Concluído (Etapa 1)** |

## Relação com o `SPEC.md`

| Área do `SPEC.md` | Requisitos da Sprint 4 relacionados |
| --- | --- |
| §§ 18–21 — simulador, relógio, tick e solar | S4-01 a S4-07, S4-13 a S4-15 |
| § 37 e §§ 45–51 — API pública | S4-12, S4-16 |
| §§ 52–53 — dashboards | S4-08 a S4-12 |
| §§ 55–63 — demonstração, aceite e testes | S4-05 a S4-08, S4-16, S4-17, S4-19 |
| §§ 64–69 — requisitos não funcionais e Definition of Done | S4-02 a S4-04, S4-18, S4-19 |

