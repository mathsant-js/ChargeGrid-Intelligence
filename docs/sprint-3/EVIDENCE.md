# Evidência do ensaio da Sprint 3

Ensaio executado em 18/09/2026 com banco PostgreSQL isolado, migrations Alembic, seed executado duas vezes e API temporária usando relógio inicial `2026-09-18T11:58:00Z`. Todos os números abaixo são **simulados**. O arquivo bruto do roteiro foi gerado fora do Git em `/tmp/chargegrid-sprint3-evidence.txt`.

| Tick UTC | Sessões | Alocação | Solar | Rede | Energia do intervalo |
| --- | ---: | ---: | ---: | ---: | ---: |
| 11:58 | 3 | 3 × 20 = 60 kW | 0 kW | 60 kW | 1 kWh |
| 11:59 | 4 | 4 × 15 = 60 kW | 0 kW | 60 kW | 1 kWh |
| 12:00 | 4 | 4 × 20 = 80 kW | 20 kW | 60 kW | 1,3333 kWh |

O roteiro retornou alerta `HIGH_DEMAND`. A quarta sessão foi encerrada e recebeu invoice `CLOSED` de **R$ 0,47** com tarifa seed de **R$ 0,8000/kWh**. A API de sustentabilidade retornou **0,1333 kg de CO₂ evitado**, usando **0,4 kg/kWh** configurado em `GRID_EMISSION_FACTOR_KG_PER_KWH`. O dashboard administrativo passou a mostrar faturamento de R$ 0,47, e o dashboard do usuário passou a listar a invoice da sessão concluída. Esses valores resultam da precisão e do arredondamento implementados pela API.

`make check` passou: 179 testes backend, 14 testes frontend, Ruff, mypy, ESLint, TypeScript e build Vite. Capturas visuais da API e dos dashboards ainda devem ser feitas no ambiente de apresentação; não são atribuídas a este ensaio automatizado.
