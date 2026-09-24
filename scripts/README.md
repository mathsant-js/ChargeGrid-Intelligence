## Dataset e baseline da Fase 7

Execute a partir de `backend/`:

```bash
.venv/bin/python -m app.ml.pipeline --seed 42
```

O comando gera localmente `data/processed/demand_90d.csv` e
`data/processed/baseline_metrics.json`. Esses artefatos são ignorados pelo Git;
somente os arquivos `.gitkeep` permanecem versionados.

Parâmetros úteis:

```bash
.venv/bin/python -m app.ml.pipeline --seed 7 --days 90 --test-fraction 0.2
```
