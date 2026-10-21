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

