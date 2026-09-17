# Fase 4 — Gestão energética

## Comportamento entregue

O tick manual `POST /api/v1/simulation/ticks`, disponível a ADMIN com o relógio
RUNNING, busca as sessões `CHARGING` e agrupa por estação. Para cada estação com
sessão ativa, consulta a curva solar determinística (06:00–18:00 UTC, pico às
12:00 UTC), soma a capacidade solar instantânea ao limite de importação da rede
e aplica Equal Share Allocation V1. O rateio igualitário é limitado pelo pedido,
pela potência máxima do carregador e pela potência máxima do veículo; sobras
de participantes limitados são redistribuídas iterativamente.

O resolvedor usa `min(potência alocada total, solar disponível)` como potência
solar e distribui essa parcela proporcionalmente entre as sessões. O restante
vem da rede. O tick valida as potências e os limites antes de persistir uma
`SolarReading` por estação e uma `EnergyReading` por sessão ativa. Energia total,
solar e da rede são potência multiplicada pela duração simulada em horas.
Os acumuladores da sessão somam as parcelas de cada tick e a potência alocada
passa a refletir o tick mais recente. Estações sem sessão `CHARGING` não geram
leituras; o relógio avança mesmo quando não há sessões ativas.

Leituras e acumuladores de todas as estações são confirmados numa transação.
Falha em qualquer estação desfaz o tick inteiro e preserva o instante do relógio.
Uma estação já concluída no mesmo instante é ignorada em nova execução; as
constraints de unicidade impedem leituras duplicadas. O controlador usa um
relógio e lock por processo e não executa ticks automaticamente.

## Cenários demonstráveis

| Critério | Configuração | Resultado verificado |
| --- | --- | --- |
| 56 | Rede 60 kW, solar 0 kW, quatro pedidos de 20 kW | 15 kW por sessão; 60 kW da rede |
| 57 | Carregador 22 kW, veículo 11 kW, pedido de 20 kW | Alocação limitada a 11 kW; a criação normal da sessão já limita o pedido a 11 kW |
| 58 | Rede 15 kW, solar 25 kW, dois pedidos de 20 kW | 40 kW alocados; 25 kW solares e 15 kW da rede |
| Tick integrado | Estação A: rede 10 kW, solar 6 kW, dois pedidos de 12 kW; estação B: rede 5 kW, solar 0 kW, pedido de 9 kW | A: 8 kW por sessão, sendo 3 solares e 5 da rede; B: 5 kW da rede. Leituras e acumuladores usam kWh do intervalo. |

O cenário integrado usa 12:00 UTC para obter o pico solar. O cenário 58 é
testado no resolvedor com solar fornecido explicitamente. O cenário 57 também
é coberto pelo fluxo de criação de sessão nos testes de domínio.

## Invariantes e limites

O resolvedor rejeita entradas negativas ou não finitas, sessões duplicadas e
capacidade total que exceda a faixa finita de `float`. Em cada sessão,
`0 ≤ alocada ≤ pedido`, `alocada ≤ carregador` e `alocada ≤ veículo`.
No agregado, potência da rede não ultrapassa `grid_limit_kw`; solar não
ultrapassa a disponibilidade. O serviço de tick valida resultados recebidos
do resolvedor injetado, inclusive conservação entre potência alocada, solar e
rede e entre suas energias. Pequenas diferenças de arredondamento binário são
aceitas nas somas.

Alertas e analytics derivados citados no fluxo geral do `SPEC.md` ainda não são
produzidos pelo tick; pertencem a fases posteriores. A Fase 4 não altera o
schema nem requer migration adicional.

## Validação desta revisão

Em 16/09/2026, a suíte backend completa executada via `.venv/bin/pytest -q
--cov-report=term` passou com **156 testes** e cobertura total de **97%**.
`.venv/bin/ruff check .` passou sem achados; `.venv/bin/mypy app` passou sem
problemas em **61 arquivos de origem**. Os testes direcionados de alocação,
tick, API de simulação e leituras passaram com **40 testes** antes da correção
do caso de overflow; a suíte completa acima inclui os novos testes. Não houve
alteração frontend nesta revisão, portanto os checks frontend não foram
executados. Os testes usam SQLite em memória; esta revisão não repetiu uma
validação online das migrations em PostgreSQL.
