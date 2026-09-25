# Fase 7 — Dataset, baseline e treinamento

Esta fase implementa a geração reproduzível do dataset temporal, avaliação do
baseline, treinamento e persistência do artefato, além da inferência consultiva
integrada à aplicação.

## Decisões

- 90 dias em UTC, com intervalos de 5 minutos e 25.920 linhas rotuladas;
- target `demand_kw_next_60_minutes` igual à demanda observada exatamente 12
  intervalos à frente;
- `historical_avg_demand_kw` usa apenas observações anteriores do mesmo par
  hora/dia da semana;
- split cronológico de 80% para treino e 20% para teste, sem embaralhamento,
  com purge gap de 12 linhas/60 minutos para que nenhum target de treino alcance
  a janela de teste;
- baseline pela média do target no treino para hora + dia da semana;
- gerador sintético isolado do alocador de produção;
- baseline, `RandomForestRegressor`, `ExtraTreesRegressor` e
  `HistGradientBoostingRegressor` avaliados na mesma janela cronológica;
- seleção automática pelo menor RMSE, incluindo o baseline como possível vencedor;
- features do modelo restritas às sete features mínimas da SPEC;
- artefato Joblib contém o vencedor, versão de formato e do scikit-learn,
  contrato ordenado de features, target, horizonte, seed, períodos e métricas
  de todos os candidatos;
- carregamento falha explicitamente para artefato ausente, inválido ou com
  features incompatíveis;
- previsões são consultivas e não são conectadas ao alocador energético;
- a inferência usa somente leituras com timestamp menor ou igual ao instante da
  previsão e exige histórico anterior do mesmo par hora/dia da semana;
- a capacidade efetiva é `grid_limit_kw + solar_available_kw`;
- os limites `medium_peak_threshold` e `high_peak_threshold` vêm de
  `SystemConfiguration`, com igualdade pertencendo ao nível superior;
- recomendações são determinísticas para `LOW`, `MEDIUM` e `HIGH`;
- um alerta `PEAK_RISK` crítico é criado apenas na entrada em `HIGH`; novas
  execuções em `HIGH` no mesmo episódio não duplicam o alerta.

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

Para a demonstração oficial, depois das migrations e de `app.demo_seed`, use o
comando idempotente abaixo antes de iniciar a API. Além do pipeline acima, ele
registra quatro leituras históricas válidas de 20 kW exatamente sete dias antes
da previsão. Nenhuma leitura futura é criada.

```bash
cd backend
.venv/bin/python -m app.ml.demo_prepare \
  --demo-start 2026-09-18T11:58:00+00:00
```

## Inferência administrativa

Configure `DEMAND_MODEL_PATH` (padrão
`../data/models/demand_forecast.joblib`) e execute, autenticado como `ADMIN`:

```http
POST /api/v1/predictions/demand/run
Content-Type: application/json

{"station_id": "<uuid-da-estacao>"}
```

A execução produz uma previsão exatamente 60 minutos à frente e persiste
`station_id`, `generated_at`, `prediction_for`, `predicted_demand_kw`,
`capacity_kw`, `risk_level` e `model_version`. O retorno também contém a
recomendação determinística e mantém o contrato consumido pelo dashboard em
`GET /api/v1/predictions/demand?station_id=<uuid>`.

Respostas operacionais relevantes:

- `422`: não há leituras causais suficientes para montar todas as features;
- `503`: o artefato está ausente, inválido ou incompatível;
- `401`/`403`: autenticação ausente ou usuário sem papel administrativo.

A inferência não chama o alocador, não atualiza `allocated_power_kw` e não pode
substituir as invariantes determinísticas de energia.

## Resultado reproduzido

O relatório atualizado, com os quatro candidatos, análise por faixa de demanda
e limitações, está em [ML_EVALUATION.md](ML_EVALUATION.md). O ganho observado é
pequeno e não altera o caráter consultivo da previsão.

Validação executada:

```bash
cd backend
.venv/bin/ruff check .
.venv/bin/mypy app
.venv/bin/pytest -q
```

Resultados atuais: Ruff sem erros, mypy sem erros em 75 arquivos e `220 passed`.
