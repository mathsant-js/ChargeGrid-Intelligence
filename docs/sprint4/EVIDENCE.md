# Baseline da Sprint 4

## Identificação

Baseline executado em **20/10/2026**, no fuso `America/Sao_Paulo`, sobre o
commit `5cfa368` da branch `codex/closing-gaps-mvp`.

Antes da execução havia apenas `config.toml` como arquivo não rastreado. Esse
arquivo local foi preservado e não faz parte desta evidência. A etapa não
alterou regras de negócio nem schema do banco.

## Resultado de `make check`

O comando terminou com código zero.

| Verificação | Resultado observado |
| --- | --- |
| Ruff | Aprovado |
| mypy | Aprovado em 76 arquivos-fonte |
| Pytest | 231 testes aprovados em 75,48 s |
| Cobertura backend | 95% (2.596 statements, 129 não cobertos) |
| ESLint | Aprovado, sem warnings |
| TypeScript | Aprovado |
| Vitest | 35 testes aprovados em 6 arquivos |
| Build Vite | Aprovado; 639 módulos transformados |

## Resultado de `make mvp-smoke`

O primeiro acionamento no ambiente restrito não conseguiu acessar o socket do
Docker. O mesmo comando foi repetido com acesso autorizado ao daemon e terminou
com `[passed]`. A limitação inicial era do ambiente de execução, não uma falha
da aplicação.

O ensaio aprovado confirmou:

- Docker Engine servidor 29.7.2, Docker Compose 5.4.0 e PostgreSQL 16;
- migrations aplicadas até `20261012_0013 (head)`;
- `alembic check` sem novas operações detectadas;
- seed determinístico com 1 administrador, 4 usuários, 4 veículos, 1 estação,
  4 carregadores, 1 tarifa e configuração ESG;
- artefato de ML preparado com avaliação temporal, baseline e métricas;
- backend, frontend e banco em estado `healthy`;
- Golden Path executado exclusivamente pela API pública;
- health, OpenAPI e frontend acessíveis;
- remoção dos containers, rede e volumes exclusivos ao final.

### Resultados funcionais observados

| Marco | Resultado |
| --- | --- |
| Três sessões | 3 × 20 kW; 60 kW da rede |
| Quarta sessão sem solar | 4 × 15 kW; 60 kW da rede |
| Quatro sessões com solar | 80 kW atendidos; 20 kW solar + 60 kW rede |
| Invariantes | Nenhuma violação detectada pelo roteiro |
| Previsão | 76,5336 kW; risco `HIGH`; horizonte de 60 min |
| Alertas | `HIGH_DEMAND`, `HIGH_SOLAR_AVAILABILITY` e `PEAK_RISK` |
| Sessão encerrada | `COMPLETED`; carregador liberado |
| Invoice | `CLOSED`; R$ 0,47 para 0,5833 kWh a R$ 0,8000/kWh |
| Sustentabilidade agregada | 20% solar; 0,8 kg de CO2 evitado; economia teórica de R$ 1,60 |
| Dashboard | Faturamento atualizado para R$ 0,47 e histórico do usuário atualizado |

Os valores de sustentabilidade agregam também o histórico causal criado pelo
preparo do modelo; não representam somente os três ticks do cenário.

### Métricas de ML observadas

| Modelo | MAE | RMSE | R² |
| --- | ---: | ---: | ---: |
| Baseline histórico (fold final) | 11,0964 | 14,1227 | 0,8259 |
| `HistGradientBoostingRegressor` selecionado | 10,9178 | 13,8498 | 0,8330 |

O corte foi temporal e a avaliação usou janela expansiva. O modelo permaneceu
consultivo: a alocação determinística continuou responsável pelas invariantes
energéticas.

## Diagnóstico inicial para a Sprint 4

O baseline comprova que o runner automático, a persistência do relógio, o
bloqueio contra ticks concorrentes, a curva solar, o Golden Path, ML, alertas,
billing e ESG estão operacionais. Permanecem como lacunas deliberadas das
próximas etapas:

- o dashboard só recarrega por ação do usuário; ainda não há polling;
- a tela não apresenta toda a identificação operacional planejada para a
  simulação viva;
- só existe o provider da curva solar determinística;
- não existe dataset nem provider de replay de telemetria;
- o cenário oficial ainda usa ticks manuais determinísticos;
- diagramas, capturas e roteiro final específicos da Sprint 4 ainda não foram
  produzidos.

Essas lacunas estão registradas na
[`matriz de rastreabilidade`](traceability-matrix.md) e não são tratadas como
funcionalidades concluídas.

## Etapa 4 — Golden Path automático

Executada em **20/10/2026** por `make mvp-smoke`, em PostgreSQL 16 limpo. O
smoke selecionou `telemetry_replay`, iniciou o runner uma única vez e observou
os ticks pela API pública de histórico. O roteiro não chamou
`/simulation/ticks` nem acessou o banco diretamente.

| Marco | Resultado observado |
| --- | --- |
| Três sessões | 60 kW solicitados e atendidos pela rede |
| Quarta sessão, sem solar | 80 kW solicitados; Equal Share em 60 kW; rede em 60 kW |
| Replay às 12:02 UTC | 80 kW atendidos; 20 kW solar + 60 kW rede |
| Invariantes | 0 violações |
| Energia agregada | 12,3667 kWh |
| Participação solar agregada | 19,1375% |
| CO₂ evitado | 0,9467 kg |
| Economia solar teórica | R$ 1,89 |
| Sessão encerrada | 1,175 kWh; invoice fechada em R$ 0,94 |
| Previsão | 76,8243 kW; risco `HIGH`; recomendação determinística exibida |
| Alertas | `HIGH_DEMAND`, `HIGH_SOLAR_AVAILABILITY` e `PEAK_RISK` |

O preparo executado no mesmo smoke manteve o corte temporal e registrou MAE,
RMSE e R² do baseline e dos candidatos. O vencedor observado continuou sendo
`HistGradientBoostingRegressor`, com MAE 10,9178, RMSE 13,8498 e R² 0,8330;
o baseline do fold final obteve MAE 11,0964, RMSE 14,1227 e R² 0,8259.

Após a implementação, `make check` também terminou com código zero: Ruff e
mypy aprovados, **249 testes backend** e **40 testes frontend** aprovados,
ESLint e TypeScript aprovados e build Vite concluído. A primeira tentativa do
smoke ficou sem acesso ao socket do Docker no ambiente restrito; a repetição
autorizada acessou o daemon e terminou com `[passed]`, removendo containers,
rede e volumes isolados ao final.

## Etapa 5 — Documentação e diagramas

Concluída em **20/10/2026** a partir do código e dos resultados da etapa 4.
Foram produzidos:

- README final com equipe, problema, solução, reprodução, validação,
  sustentabilidade, aderência conceitual à GoodWe e limitações;
- arquitetura e sequência em Mermaid, acompanhadas de SVGs versionados;
- tabela quantitativa separada, com escopo explícito dos valores ESG;
- roteiro de vídeo de até cinco minutos;
- duas capturas atuais do build de produção: dashboard do gestor e operação.

Para preparar as capturas, foi criado um projeto Docker Compose isolado, com
PostgreSQL limpo, migrations, seed, artefato de ML e replay de telemetria. O
`scripts/sprint4_demo.py` foi executado novamente e reproduziu os mesmos marcos
da etapa 4: 80 kW atendidos com 20 kW solares e 60 kW da rede, zero violações,
12,3667 kWh, 19,1375% solar, 0,9467 kg de CO₂ evitado, invoice de R$ 0,94 e
risco `HIGH`.

A revisão visual também identificou duas limitações agora documentadas: o
rótulo da fonte no dashboard está fixo como curva solar mesmo com replay ativo;
e o servidor Vite de desenvolvimento pode permanecer em “Carregando” após a
remontagem do `React.StrictMode`. O build de produção capturado carregou os
KPIs, previsão, ESG, gráficos, histórico e alertas corretamente. Nenhum código
de negócio ou schema foi alterado nesta etapa.

## Etapa 6 — Validação final

Executada em **20/10/2026** sobre uma árvore de trabalho inicialmente limpa.

`make check` terminou com código zero e confirmou:

- Ruff aprovado;
- mypy aprovado em 76 arquivos-fonte;
- 249 testes backend aprovados em 74,66 s, com 95% de cobertura;
- ESLint e TypeScript aprovados;
- 40 testes frontend aprovados em 6 arquivos;
- build Vite aprovado, com 639 módulos transformados.

O primeiro `make mvp-smoke` não teve permissão para acessar o socket do Docker
no ambiente restrito. A repetição autorizada do mesmo alvo terminou com
`[passed]`. Em PostgreSQL 16 limpo, ela aplicou migrations até
`20261012_0013 (head)`, confirmou que o metadata Alembic não exige novas
operações, preparou seed e modelo, iniciou os três serviços como `healthy` e
removeu ao final os containers, volumes e rede exclusivos do ensaio.

O Golden Path pela API pública cobriu os itens funcionais da etapa: login
administrativo, início e parada do simulador, ticks automáticos, entrada da
quarta sessão, Equal Share, prioridade solar, previsão, alertas, encerramento,
invoice e ESG. Os resultados reproduziram a etapa 4: 80 kW solicitados, 60 kW
da rede, 20 kW solares, zero violações, risco `HIGH`, invoice de R$ 0,94,
19,1375% de participação solar e 0,9467 kg de CO₂ evitado. Os testes frontend
com timers falsos confirmaram a atualização automática e sua interrupção
quando a simulação para.

## Revalidação após revisão final — 21/10/2026

Após expor a fonte de dados no status da simulação, corrigir o rótulo do
dashboard e consolidar a documentação, os dois comandos canônicos foram
executados novamente no checkout atual.

`make check` terminou com código zero:

- Ruff e mypy aprovados;
- 249 testes backend aprovados, com 95% de cobertura;
- ESLint e TypeScript aprovados;
- 41 testes frontend aprovados em 6 arquivos;
- build Vite aprovado, com 639 módulos transformados.

`make mvp-smoke` exigiu acesso autorizado ao socket do Docker no ambiente de
execução e então terminou com `[passed]`. O ensaio aplicou migrations até
`20261012_0013 (head)`, não encontrou diferenças de metadata, iniciou banco,
backend e frontend saudáveis e removeu os recursos isolados ao final.

O Golden Path reproduziu 80 kW atendidos por 20 kW solares e 60 kW da rede,
zero violações, 12,3667 kWh agregados, 19,1375% de participação solar, 0,9467 kg
de CO₂ evitado, economia teórica de R$ 1,89, invoice de R$ 0,94, previsão de
76,8243 kW e risco `HIGH`.

