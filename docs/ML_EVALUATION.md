# Avaliação de previsão de demanda

Execução reproduzida em 25/09/2026, com seed 42. Os dados simulados cobrem
01/01/2026 00:00 a 31/03/2026 23:55 UTC (25.920 linhas, intervalos de 5 minutos).
O target continua sendo a demanda exatamente 60 minutos à frente.

O split é cronológico: 20.724 linhas de treino (até 13/03 22:55), lacuna causal
de 12 linhas/60 minutos e 5.184 linhas de teste (14/03 a 31/03). Não há
embaralhamento nem busca de hiperparâmetros; cada candidato usa uma configuração
fixa e `random_state=42`.

| Candidato | MAE (kW) | RMSE (kW) | R² |
|---|---:|---:|---:|
| Baseline: média por hora/dia | 11,096 | 14,123 | 0,8259 |
| RandomForestRegressor | 11,168 | 14,227 | 0,8233 |
| ExtraTreesRegressor | 11,024 | 14,021 | 0,8284 |
| HistGradientBoostingRegressor | **10,987** | **13,973** | **0,8296** |

O vencedor é `HistGradientBoostingRegressor`, escolhido pelo menor RMSE no mesmo
teste temporal. A melhoria de RMSE sobre o baseline é pequena: 0,149 kW (1,06%).
O Random Forest original não vencia porque o baseline já captura a forte
sazonalidade de hora/dia do gerador, enquanto os sinais instantâneos são ruidosos
para um horizonte de 60 minutos; a floresta também reproduzia parte desse ruído.

Por faixa de demanda, o vencedor obteve RMSE de 11,650 kW abaixo de 50 kW,
14,518 kW entre 50 e 100 kW e 20,726 kW a partir de 100 kW. O pior horário foi
18:00 (RMSE 17,273 kW), coerente com o pico sintético do fim do dia.

## Limitações e conclusão

O ensaio usa apenas dados sintéticos de uma distribuição conhecida, um único
corte temporal e um ganho marginal. Ele não demonstra generalização para uma
estação real nem justifica aumentar a complexidade. O modelo selecionado é
adequado para a demonstração, mas o baseline permanece candidato e seria
persistido automaticamente se tivesse o menor RMSE. A previsão continua
estritamente consultiva e não participa da alocação de energia.
