# Fase 7 — Dataset temporal e baseline

Esta primeira fatia implementa a geração reproduzível do dataset temporal e a
avaliação do baseline. Treinamento e persistência do modelo, inferência e
classificação de risco permanecem para as próximas fatias da Fase 7.

## Decisões

- 90 dias em UTC, com intervalos de 5 minutos e 25.920 linhas rotuladas;
- target `demand_kw_next_60_minutes` igual à demanda observada exatamente 12
  intervalos à frente;
- `historical_avg_demand_kw` usa apenas observações anteriores do mesmo par
  hora/dia da semana;
- split cronológico de 80% para treino e 20% para teste, sem embaralhamento;
- baseline pela média do target no treino para hora + dia da semana;
- gerador sintético isolado do alocador de produção;
- implementação somente com a biblioteca padrão do Python. NumPy, Pandas e
  scikit-learn não estavam declarados nem instalados, e não foram necessários
  nesta fatia.

## Execução

A partir da raiz do repositório:

```bash
cd backend
.venv/bin/python -m app.ml.pipeline --seed 42
```

Os parâmetros `--days`, `--seed`, `--test-fraction`, `--dataset` e `--metadata`
podem ser configurados. Os CSVs e JSONs gerados sob `data/` são ignorados pelo
Git; apenas `.gitkeep` é versionado.

## Resultado reproduzido

Execução realizada em 23/09/2026 com seed 42 e split 80/20:

| Item | Resultado |
|---|---:|
| Linhas | 25.920 |
| Período do dataset | 2026-01-01 00:00 UTC a 2026-03-31 23:55 UTC |
| Treino | 20.736 linhas; até 2026-03-13 23:55 UTC |
| Teste | 5.184 linhas; desde 2026-03-14 00:00 UTC |
| MAE | 11,096690 kW |
| RMSE | 14,122756 kW |
| R² | 0,825907 |

Comando de validação focada executado:

```bash
backend/.venv/bin/pytest -q backend/tests/test_ml_dataset.py
```

Resultado: `9 passed`.

Validação completa executada:

```bash
backend/.venv/bin/ruff check backend/app backend/tests
backend/.venv/bin/mypy backend/app
backend/.venv/bin/pytest -q backend/tests
```

Resultados: Ruff sem erros, mypy sem erros em 72 arquivos e `194 passed`.
