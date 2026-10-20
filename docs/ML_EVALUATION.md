# Avaliação de previsão de demanda

Execução reproduzida em 20/10/2026, com seed 42. Os dados simulados cobrem
01/01/2026 00:00 a 31/03/2026 23:55 UTC (25.920 linhas, intervalos de 5 minutos).
O target continua sendo a demanda exatamente 60 minutos à frente.

Foram usados três folds walk-forward com treino expansivo. Cada fold tem 5.184
linhas (18 dias) de validação e uma lacuna causal de 12 linhas/60 minutos entre
treino e validação. Os treinos terminam em 05/02, 23/02 e 13/03 às 22:55 UTC; as
validações começam uma hora e cinco minutos depois e cobrem, respectivamente,
06/02–23/02, 24/02–13/03 e 14/03–31/03. Não há embaralhamento, sobreposição entre
as validações nem busca de hiperparâmetros; cada candidato usa uma configuração
fixa e `random_state=42`.

As métricas abaixo agregam as 15.552 previsões fora da amostra dos três folds.

| Candidato | MAE (kW) | RMSE (kW) | R² |
|---|---:|---:|---:|
| Baseline: média por hora/dia | 11,011 | 13,989 | 0,8296 |
| RandomForestRegressor | 11,043 | 14,021 | 0,8288 |
| ExtraTreesRegressor | 10,922 | 13,859 | 0,8328 |
| HistGradientBoostingRegressor | **10,918** | **13,850** | **0,8330** |

O vencedor é `HistGradientBoostingRegressor`, escolhido pelo menor RMSE agregado
nas mesmas janelas. A melhoria de RMSE sobre o baseline permanece pequena:
0,139 kW (0,99%).
O Random Forest original não vencia porque o baseline já captura a forte
sazonalidade de hora/dia do gerador, enquanto os sinais instantâneos são ruidosos
para um horizonte de 60 minutos; a floresta também reproduzia parte desse ruído.

O RMSE do vencedor nos folds foi 13,473, 14,095 e 13,973 kW. Essa variação
explicita a sensibilidade temporal que o corte único não mostrava; o Extra Trees
venceu apenas o primeiro fold, e o HistGradientBoosting venceu os dois seguintes
e o agregado.

| Faixa real | Observações | MAE (kW) | RMSE (kW) | R² |
|---|---:|---:|---:|---:|
| Baixa, abaixo de 50 kW | 8.160 | 9,277 | 11,551 | 0,2663 |
| Média, de 50 a abaixo de 100 kW | 5.702 | 11,557 | 14,394 | -0,0611 |
| Alta, a partir de 100 kW | 1.690 | 16,685 | 20,541 | -1,4905 |

O pior horário agregado foi 18:00 (RMSE 17,396 kW), coerente com o pico
sintético do fim do dia. Embora o desempenho global seja estável, o erro cresce
materialmente nas demandas média e alta e o R² negativo nessas faixas mostra que
o modelo não explica bem sua variação interna. Portanto, o resultado não sustenta
afirmações de boa precisão nos cenários de maior risco operacional.

## Limitações e conclusão

O ensaio usa apenas dados sintéticos de uma distribuição conhecida, três janelas
de uma única série e um ganho marginal. Ele reduz a dependência de um corte, mas
não demonstra generalização para uma estação real nem justifica aumentar a
complexidade. O modelo selecionado é adequado para a demonstração; o baseline
permanece candidato em todos os folds e seria persistido automaticamente se
tivesse o menor RMSE agregado. A previsão continua estritamente consultiva e não
participa da alocação de energia.
