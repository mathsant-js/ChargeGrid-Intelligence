# Resultados quantitativos — Sprint 4

Resultados observados em **20/10/2026** na execução aprovada de `make mvp-smoke`,
com PostgreSQL 16 limpo, replay de telemetria sintética e ticks produzidos pelo
runner automático. O roteiro utilizou somente a API pública.

## Golden Path automático

| Indicador | Resultado observado |
| --- | ---: |
| Demanda solicitada com quatro sessões | 80 kW |
| Limite da rede | 60 kW |
| Solar disponível no marco de 12:02 UTC | 20 kW |
| Potência total atendida nesse marco | 80 kW |
| Potência da rede | 60 kW |
| Potência solar | 20 kW |
| Violações das invariantes | 0 |
| Energia total agregada | 12,3667 kWh |
| Participação solar agregada | 19,1375% |
| CO₂ evitado | 0,9467 kg |
| Economia solar teórica | R$ 1,89 |
| Energia da sessão encerrada | 1,175 kWh |
| Invoice da sessão encerrada | R$ 0,94 |
| Demanda prevista a +60 min | 76,8243 kW |
| Risco previsto | `HIGH` |
| Alertas confirmados | `HIGH_DEMAND`, `HIGH_SOLAR_AVAILABILITY`, `PEAK_RISK` |

Os totais ESG agregam o histórico causal preparado para o modelo e as leituras
do cenário. Por isso, não devem ser interpretados como resultado exclusivo dos
três marcos energéticos exibidos durante a demonstração.

## Resultados qualitativos

- o gestor acompanha relógio, fonte de dados, KPIs, previsão, alertas e ESG na
  mesma interface;
- o cenário pode ser repetido sem aguardar a duração real de uma recarga;
- a origem da energia pode ser trocada sem alterar regras críticas;
- falhas e ausência de telemetria têm comportamento explícito e testado;
- os limites de rede, carregador, veículo e pedido permanecem determinísticos,
  mesmo quando existe previsão de ML.

Esses resultados demonstram integração e auditabilidade. Eles não validam
latência de campo, disponibilidade de rede, precisão de sensores, aceitação por
usuários ou retorno financeiro de uma instalação real.

## Avaliação de Machine Learning

| Modelo | MAE | RMSE | R² |
| --- | ---: | ---: | ---: |
| Baseline histórico, fold final | 11,0964 | 14,1227 | 0,8259 |
| `HistGradientBoostingRegressor` selecionado | 10,9178 | 13,8498 | 0,8330 |

A avaliação usa corte temporal e janela expansiva. O modelo vencedor melhora
as três métricas observadas em relação ao baseline, mas permanece consultivo:
somente a alocação determinística controla potência e protege os limites.

## Como reproduzir os números

Na raiz do repositório, com Docker e Docker Compose disponíveis:

```bash
make mvp-smoke
```

O comando cria um ambiente isolado, aplica migrations, prepara seed e modelo,
executa `scripts/sprint4_demo.py`, imprime o resumo JSON e remove o ambiente ao
final. Os números podem variar apenas se dataset, configuração, algoritmo ou
seed forem alterados; o cenário corrente é determinístico.

