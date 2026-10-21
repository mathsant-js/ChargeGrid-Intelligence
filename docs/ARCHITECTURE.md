# Arquitetura vigente

**Classificação:** documentação atual. Para decisões e limitações existentes em
momentos anteriores, consulte o [mapa de documentos](README.md) e os registros
`PHASE_*`.

O ChargeGrid Intelligence é um monólito modular. O navegador React consome a
API REST FastAPI sob `/api/v1`; os contratos HTTP usam Pydantic, os serviços
persistem por SQLAlchemy e todas as alterações de schema passam por Alembic em
PostgreSQL. Datas são UTC, IDs são UUID e valores monetários usam tipos
decimais.

```text
React / Vite
    │ HTTP + JWT
    ▼
FastAPI /api/v1
    ├── autenticação e cadastros
    ├── charging_sessions ── billing
    ├── simulation/control ── simulation/tick ── energy allocation
    ├── analytics e alertas
    └── demand_predictions (consultivo)
                 │
                 ▼
          SQLAlchemy / PostgreSQL
```

## Fluxo operacional

O serviço `charging_sessions` valida o início e o encerramento, captura a
tarifa e cria a invoice simulada. O controlador de simulação oferece start,
stop, reset e tick manual; enquanto está `RUNNING`, também mantém um runner
assíncrono. O estado do relógio e o último tick são persistidos, e o PostgreSQL
serializa ticks concorrentes pelo checkpoint do simulador.

O checkpoint persistido é a autoridade após reinício ou quando o relógio de um
worker está atrasado. Cada execução bem-sucedida consome exatamente o instante
do checkpoint e o avança por uma duração de tick. Se um instante já concluído
for reapresentado, as leituras únicas por `(station_id, timestamp)` e
`(session_id, timestamp)` impedem nova energia; checkpoint, leituras e
acumuladores são confirmados ou revertidos na mesma transação.

O contrato `EnergyDataProvider` desacopla aquisição de dados e regras de
energia. `SimulationEnergyDataProvider` calcula geração solar simulada por uma
curva UTC; `TelemetryReplayEnergyDataProvider` reproduz um CSV versionado com
potência fotovoltaica e metadados típicos de gateway. A configuração
`ENERGY_DATA_PROVIDER` seleciona a fonte sem alterar API, persistência ou
alocação. `EqualSharePowerResolver` aplica os limites da rede, do carregador,
do veículo e do pedido, redistribui sobras e prioriza a energia solar.
`simulation/tick.py` persiste leituras, acumuladores, checkpoint e alertas na
mesma transação. O frontend apenas apresenta os resultados; não replica as
regras energéticas.

Analytics e dashboards consultam leituras, sessões e invoices persistidas. O
pipeline de ML gera um artefato versionado e a rota administrativa de
inferência produz previsão a +60 minutos, risco e recomendação. Essa saída é
estritamente consultiva e nunca substitui as restrições determinísticas de
energia.

## Limites do MVP

- energia solar, medição e billing são simulados;
- o replay aproxima o formato de aquisição, mas não consulta equipamento,
  gateway ou nuvem externa;
- não há integração física, OCPP/Modbus ou pagamento real;
- ML depende de artefato preparado e histórico causal compatível;
- para uma demo reproduzível, use um banco isolado e o procedimento em
  [`MVP_DELIVERY_SMOKE_TEST.md`](MVP_DELIVERY_SMOKE_TEST.md).

Os diagramas finais e a sequência do fluxo automatizado estão na
[`entrega da Sprint 4`](sprint4/README.md). Os diagramas em
[`sprint-3/`](sprint-3/README.md) são evidências históricas e podem ter legendas
superadas pelo código vigente.
