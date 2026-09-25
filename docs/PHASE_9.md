# Fase 9 — Auditoria final do MVP

**Estado:** concluída em 24/09/2026, com limitações explícitas abaixo.

Esta auditoria confrontou `SPEC.md`, `BRIEFING.md`, implementação, testes,
migrations e roteiro de demonstração. O `SPEC.md` foi tratado como fonte de
verdade. Não foram adicionadas funcionalidades de escopo secundário.

## Matriz requisito → implementação → teste → estado

| Requisito | Implementação principal | Evidência automatizada | Estado |
| --- | --- | --- | --- |
| Entidades, UUID, UTC e migrations | `app/models`, `migrations/versions` | testes de domínio e `alembic current/check` | Atendido |
| Auth, papéis e isolamento por usuário | dependencies, rotas de auth, vehicles, sessions, energy, billing e dashboards | `test_auth_authorization.py`, `test_energy.py`, `test_invoice_history.py`, `test_user_dashboard.py` | Atendido |
| Sessões e limites individuais | `services/charging_sessions.py` | `test_charging_session_domain.py` | Atendido |
| Equal Share e limite da rede | `services/energy_allocation.py`, `simulation/tick.py` | `test_energy_allocation.py`, `test_simulation_tick.py`, `test_phase_6_flow.py` | Atendido |
| Prioridade e rateio solar | alocador e tick | testes de alocação, tick e Golden Path | Atendido |
| Leituras e conservação de energia | `services/energy_readings.py` | `test_energy_reading_domain.py`, `test_simulation_api.py` | Atendido |
| Billing decimal e invoice fechada | `services/billing.py`, serviço de sessões | `test_billing_alerts.py`, `test_invoice_history.py`, Golden Path | Atendido |
| Analytics, ESG e dashboards | serviços de analytics e páginas admin/user | `test_analytics.py`, `test_phase_6_flow.py`, testes React | Atendido |
| Dataset, baseline e ausência de vazamento temporal | `app/ml/dataset.py`, `baseline.py` | `test_ml_dataset.py`, `test_ml_training.py` | Atendido |
| Inferência consultiva, risco e fallback sem modelo | `services/demand_predictions.py`, rota `/predictions/demand/run` | `test_demand_inference.py`, `test_predictions_configuration.py` | Atendido |
| Alertas de demanda, pico, solar e encerramento | tick, inferência e encerramento | `test_simulation_tick.py`, `test_demand_inference.py`, `test_billing_alerts.py` | Atendido |
| Health, OpenAPI e erros sem stack trace | `main.py`, health e handlers | `test_health.py`, `test_openapi.py`, `test_error_handling.py` | Atendido |
| Frontend responsivo, vazio, loading, retry e erros | páginas React e breakpoints em `styles.css` | 31 testes Vitest e inspeção visual em 390 px | Atendido |
| Seed e cenário oficial 3→4 carregadores + ML | `app/demo_seed.py`, `app/ml/demo_prepare.py`, `scripts/sprint3_demo.py` | `test_demo_seed.py`, `test_sprint3_demo_script.py`, PostgreSQL real | Atendido |
| Relógio acelerado automático | relógio configurável e ticks administrativos manuais | testes do relógio e simulação | Parcial |

## Lacunas encontradas e decisão

- O roteiro chamava endpoints protegidos de energia e solar sem JWT. Isso fazia
  a demo falhar em uma API real, embora passasse em testes com dependências
  substituídas. O token ADMIN foi incluído e um teste de regressão foi criado.
- O preparo de ML é separado do seed de domínio: gera dataset/artefato e registra
  explicitamente uma observação histórica causal, idempotente e anterior ao cenário.
- A simulação é acionada por ticks administrativos; não existe loop em background.
  Isso é aceito como limitação do MVP demonstrável, não como integração com hardware.
- O modelo Random Forest versionado como artefato local não superou o baseline no
  ensaio documentado da Fase 7. Ele permanece consultivo e não controla potência.
- A cobertura por família de endpoint é completa. Não foi encontrado endpoint
  público do `SPEC.md` sem teste; as linhas não cobertas do relatório são sobretudo
  ramos de erro/defesa, não famílias inteiras de API.

## Validação executada

Em 24/09/2026:

```text
make check
  Ruff: aprovado
  mypy: aprovado (75 arquivos)
  pytest: 220 aprovados; cobertura total 95%
  ESLint: aprovado
  TypeScript: aprovado
  Vitest: 31 aprovados
  Vite build: aprovado; aviso não bloqueante de chunk de 683,05 kB

PostgreSQL 16 em stack Docker isolada
  alembic current: 20260924_0012 (head)
  alembic check: No new upgrade operations detected
  seed: aprovado
  health: HTTP 200, {"status":"ok"}
  OpenAPI: 3.1.0, 36 paths
  frontend: HTTP 200
```

O Golden Path real confirmou 3 × 20 kW, depois 4 × 15 kW sob limite de
60 kW, e em seguida 80 kW totais com 20 kW solares e 60 kW de rede. A quarta
sessão foi encerrada com invoice `CLOSED` de R$ 0,47 e os dashboards refletiram
billing e ESG. A inferência real produziu previsão para +60 minutos, risco
`HIGH` e alerta `PEAK_RISK` usando os limiares documentados 0,70/0,90. Nenhum
threshold foi alterado para produzir esse resultado.

## Limitações assumidas do MVP

- runner automático coordenado apenas em uma instância do backend, sem scheduler
  distribuído e sem hardware/OCPP/Modbus;
- billing simulado, sem pagamento real;
- modelo local consultivo e dependente de artefato e histórico causal;
- inferência depende da etapa documentada `app.ml.demo_prepare`;
- sem MLOps, cloud complexa, app mobile ou recursos do escopo secundário;
- aviso de tamanho do bundle frontend, sem falha funcional observada.

## Roteiro final de demonstração

1. Subir somente PostgreSQL, aplicar migrations e executar o seed com senhas no ambiente.
2. Executar `app.ml.demo_prepare` para treinar, persistir métricas/artefato e
   preparar o histórico causal; depois iniciar backend e frontend.
3. Abrir health, OpenAPI e autenticar gestor e motorista.
4. Iniciar três sessões e executar tick: 3 × 20 kW, 60 kW de rede.
5. Iniciar a quarta e executar tick: 4 × 15 kW, ainda 60 kW de rede.
6. Configurar pico solar em 20 kW e executar tick: 80 kW alocados, 20 solar + 60 rede.
7. Mostrar leituras, `HIGH_DEMAND`/`HIGH_SOLAR_AVAILABILITY` e dashboards.
8. Executar `POST /predictions/demand/run` e mostrar demanda, capacidade, +60 min,
   risco `HIGH`, recomendação e `PEAK_RISK`, sem alterar alocação.
9. Encerrar a quarta sessão e mostrar `COMPLETED`, carregador `AVAILABLE`, invoice
   `CLOSED`, custo, participação solar, CO₂ evitado e dashboards atualizados.
