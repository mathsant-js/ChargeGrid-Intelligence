# Fase 7 — Dataset, baseline e treinamento

Esta fatia implementa a geração reproduzível do dataset temporal, avaliação do
baseline, treinamento do modelo e persistência do artefato. A classificação de
risco e sua integração com a aplicação permanecem para as próximas fatias.

## Decisões

- 90 dias em UTC, com intervalos de 5 minutos e 25.920 linhas rotuladas;
- target `demand_kw_next_60_minutes` igual à demanda observada exatamente 12
  intervalos à frente;
- `historical_avg_demand_kw` usa apenas observações anteriores do mesmo par
  hora/dia da semana;
- split cronológico de 80% para treino e 20% para teste, sem embaralhamento;
- baseline pela média do target no treino para hora + dia da semana;
- gerador sintético isolado do alocador de produção;
- `RandomForestRegressor` treinado apenas na janela cronológica de treino;
- features do modelo restritas às sete features mínimas da SPEC;
- artefato Joblib contém modelo, versão, contrato ordenado de features, target,
  períodos de treino/teste e métricas;
- carregamento falha explicitamente para artefato ausente, inválido ou com
  features incompatíveis;
- previsões são consultivas e não são conectadas ao alocador energético.

## Execução

A partir da raiz do repositório:

```bash
cd backend
.venv/bin/python -m app.ml.pipeline \
  --seed 42 \
  --dataset ../data/processed/demand_90d.csv \
  --metadata ../data/processed/training_metrics.json \
  --artifact ../data/models/demand_forecast.joblib
```

Os parâmetros `--days`, `--seed`, `--test-fraction`, `--dataset`, `--metadata` e `--artifact`
podem ser configurados. Os CSVs e JSONs gerados sob `data/` são ignorados pelo
Git; apenas `.gitkeep` é versionado.

## Resultado reproduzido

Execução realizada em 23/09/2026 com seed 42 e split 80/20:

| Item | Random Forest | Baseline | Diferença (modelo vs baseline) |
|---|---:|---:|---:|
| MAE | 11,542932 kW | 11,096690 kW | +0,446242 kW |
| RMSE | 14,714592 kW | 14,122756 kW | +0,591836 kW |
| R² | 0,811010 | 0,825907 | -0,014897 |

Foram usadas 25.920 linhas. O treino contém 20.736 linhas entre
2026-01-01 00:00 UTC e 2026-03-13 23:55 UTC; o teste contém 5.184 linhas entre
2026-03-14 00:00 UTC e 2026-03-31 23:55 UTC.

O Random Forest inicial **não superou o baseline** nesta execução. O resultado
é preservado como evidência experimental; o modelo não deve substituir o
baseline nem influenciar diretamente a alocação energética com base nestas
métricas.

Validação executada:

```bash
cd backend
.venv/bin/ruff check .
.venv/bin/mypy app
.venv/bin/pytest -q
```

Resultados: Ruff sem erros, mypy sem erros em 73 arquivos e `200 passed`.
