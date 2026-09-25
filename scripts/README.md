## Golden Path de ML da Fase 7

Execute a partir de `backend/`:

```bash
.venv/bin/python -m app.ml.demo_prepare \
  --demo-start 2026-09-18T11:58:00+00:00
```

O comando gera localmente `data/processed/demand_90d.csv` e
`data/processed/training_metrics.json`, persiste o modelo e prepara o histórico
causal da estação já criada por `app.demo_seed`. Esses artefatos são ignorados pelo Git;
somente os arquivos `.gitkeep` permanecem versionados.

Parâmetros úteis:

```bash
.venv/bin/python -m app.ml.pipeline --seed 7 --days 90 --test-fraction 0.2
```
