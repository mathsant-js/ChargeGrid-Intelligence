# ChargeGrid Intelligence — entrega Sprint 4

> Demonstração acadêmica com dados, equipamentos, billing e telemetria
> **simulados**. Não existe conexão física com inversores, gateways ou estações
> de recarga GoodWe.

**Equipe:** Equipe 3 — FIAP × GoodWe

**Disciplina:** Pensamento Computacional e Automação com Python

**Integrantes:** Bernardo Zauza Amorim, Bruno Almeida de Oliveira, Gabriel Góes
Nunes Pereira, Guilherme Vinciguerra Carvalho, Marcos Peterson Martins Pereira
e Matheus Jorge Santana.

## Estado da execução

| Etapa | Estado | Material |
| --- | --- | --- |
| 1 — Baseline e rastreabilidade | Concluída em 20/10/2026 | [`EVIDENCE.md`](EVIDENCE.md) e [`traceability-matrix.md`](traceability-matrix.md) |
| 2 — Dashboard vivo | Concluída em 20/10/2026 | `frontend/src/pages/AdminDashboardPage.tsx` |
| 3 — Telemetria reproduzida | Concluída em 20/10/2026 | [`telemetry-contract.md`](telemetry-contract.md) e `data/raw/sprint4_telemetry.csv` |
| 4 — Golden Path automático | Concluída em 20/10/2026 | `scripts/sprint4_demo.py` |
| 5 — Documentação e diagramas | Concluída em 20/10/2026 | este guia, diagramas, resultados, roteiro e capturas |
| 6 — Validação final | Revalidada em 21/10/2026 | [`EVIDENCE.md`](EVIDENCE.md), `make check` e `make mvp-smoke` |

O plano completo está em
[`plano_desenvolvimento_sprint4.md`](plano_desenvolvimento_sprint4.md).

## Problema e solução

Infraestruturas de recarga precisam atender vários veículos sem ultrapassar a
rede contratada, aproveitar geração solar e oferecer informação operacional.
O ChargeGrid resolve esse recorte com um monólito modular que:

- cria e encerra sessões de recarga;
- avança um relógio acelerado por um runner automático;
- aplica Equal Share com limites físicos e prioridade solar;
- persiste leituras, billing simulado, alertas e indicadores ESG;
- apresenta um dashboard que acompanha a simulação;
- prevê demanda a 60 minutos, compara o modelo com um baseline e produz uma
  recomendação estritamente consultiva.

## Arquitetura final

![Arquitetura final da Sprint 4](diagrams/architecture.svg)

[Fonte Mermaid](architecture.mmd). O frontend React consome a API FastAPI sob
`/api/v1`. O backend executa como monólito modular, usa SQLAlchemy e PostgreSQL
e seleciona por configuração entre curva solar e replay de telemetria. A fonte
fornece apenas disponibilidade solar; `EqualSharePowerResolver` continua sendo
o único responsável pela alocação e por suas invariantes.

## Fluxo integrado

![Sequência do Golden Path automático](diagrams/sequence.svg)

[Fonte Mermaid](sequence.mmd). O endpoint de início cria um único runner por
processo. Cada tick bloqueia o checkpoint persistido, amostra a fonte
energética, aloca potência, grava leituras e avança o relógio na mesma
transação. O dashboard faz polling apenas enquanto o estado é `RUNNING`, evita
consultas sobrepostas e mantém uma atualização manual disponível.

## Automação e telemetria simulada

O relógio usa, por padrão, um segundo real para um minuto simulado. Start e
stop são idempotentes, ticks concorrentes são serializados no PostgreSQL e uma
falha isolada não encerra o runner.

`ENERGY_DATA_PROVIDER` aceita:

- `curve` — padrão, curva solar UTC determinística;
- `telemetry_replay` — procura uma amostra exata por estação e instante em um
  CSV versionado.

O replay valida timestamps com fuso, valores finitos e potências não negativas,
limita o fotovoltaico ao pico da estação e retorna zero com qualidade `MISSING`
quando não existe amostra. O contrato detalhado está em
[`telemetry-contract.md`](telemetry-contract.md).

## Aderência conceitual ao ecossistema GoodWe

O desenho se conecta a capacidades documentadas pela própria GoodWe, sem
confundi-las com funcionalidades já integradas:

| Referência GoodWe | Capacidade oficial relevante | Correspondência no ChargeGrid |
| --- | --- | --- |
| EzLogger Pro | coleta e registra dados de inversores; comunica-se por RS485 e Ethernet | fronteira `EnergyDataProvider` e contrato de replay de telemetria |
| EzLogger 3000R | encaminhamento para sistema de gestão por Modbus-TCP | possível adaptador futuro, isolado das regras de alocação |
| SEMS+ | monitoramento de potência, corrente, duração e energia de carregamento | dashboard, histórico energético, sessões e alertas |
| HCA G2 | carregamento com aproveitamento solar, monitoramento remoto e integração ao SEMS+ | prioridade solar, composição solar/rede e visão operacional |

O provider de replay representa a fronteira na qual um adaptador autorizado
entregaria medições ao motor. A prova desta Sprint é de **substituibilidade
arquitetural**: trocar a curva por replay não altera sessão, banco, API,
dashboard ou regras de alocação. Os campos do replay são um contrato acadêmico,
não uma reprodução de registradores proprietários.

Isso não comprova nem alega comunicação real GoodWe, Modbus ou OCPP. Uma
integração física futura exigiria confirmar protocolo, autenticação, unidade,
frequência, qualidade e tratamento de indisponibilidade do equipamento alvo.

## Conexão com a disciplina

Os conteúdos de Pensamento Computacional e Automação com Python aparecem de
forma verificável no sistema:

- decomposição do problema em módulos de sessão, energia, simulação, billing,
  analytics e ML;
- algoritmo determinístico Equal Share, com invariantes testáveis;
- automação temporal pelo runner assíncrono e tratamento explícito de falhas;
- abstração de entrada por provider, permitindo curva ou replay sem duplicar
  regras de negócio;
- processamento e validação de dados com Python, Pandas e Pydantic;
- modelo preditivo avaliado contra baseline com separação temporal;
- testes automatizados e cenário reproduzível como verificação do algoritmo.

## Gestão energética e segurança

Antes de persistir um tick, o backend garante:

```text
0 <= potência alocada
potência alocada <= pedido, carregador e veículo
potência total da rede <= limite da estação
solar utilizado <= solar disponível
```

O solar complementa a capacidade da rede e tem prioridade na composição da
energia. O ML jamais sobrescreve essas regras.

## Machine Learning e baseline

O pipeline usa features causais, horizonte de 60 minutos, divisão temporal e
janela expansiva. A seleção compara modelos simples com a média histórica por
hora e dia da semana. Na execução documentada, o
`HistGradientBoostingRegressor` venceu por RMSE. MAE, RMSE e R² estão em
[`results.md`](results.md) e na documentação de avaliação geral em
[`../ML_EVALUATION.md`](../ML_EVALUATION.md).

## Resultados e sustentabilidade

No marco principal, quatro sessões solicitaram 80 kW. O sistema entregou 20 kW
solares mais 60 kW da rede, sem violar o limite. O ensaio acumulou 12,3667 kWh,
19,1375% de participação solar, 0,9467 kg de CO₂ evitado e R$ 1,89 de economia
solar teórica. Uma sessão encerrou com 1,175 kWh e invoice de R$ 0,94.

O CO₂ evitado é calculado como energia solar multiplicada pelo fator de emissão
configurado da rede. A economia representa o valor teórico da energia solar que
teria sido comprada pela tarifa; não é promessa de economia financeira real.
Veja a [tabela integral e seu escopo](results.md).

### Avaliação crítica dos impactos

| Dimensão | Benefício demonstrado | Limite da evidência |
| --- | --- | --- |
| Viabilidade técnica | fluxo completo reproduzível em monólito modular e PostgreSQL | ainda depende de telemetria simulada e de um runner por instância |
| Eficiência energética | solar é consumido antes da rede e a demanda respeita 60 kW | não mede perdas elétricas, eficiência do inversor ou bateria |
| Ambiental | contabiliza participação solar e CO₂ evitado com fórmula explícita | resultado depende do fator de emissão configurado e não é inventário de ciclo de vida |
| Econômica | calcula billing e custo de energia solar evitada | não inclui CAPEX, manutenção, demanda contratada ou tarifa horária real |
| Social | pode apoiar disponibilidade previsível da recarga e decisões transparentes do gestor | não houve estudo com usuários, acessibilidade social ou implantação comunitária |
| Inovação | combina automação, ML consultivo, alertas, ESG e fonte substituível | não há atuação sobre hardware, assistente virtual ou otimização autônoma real |

A solução demonstra que dados operacionais podem reduzir decisões reativas e
explicitar o uso de renováveis. Ela não demonstra, por si só, redução real de
emissões ou retorno financeiro de uma instalação GoodWe; esses resultados
exigiriam medição física, série histórica representativa e análise econômica do
local.

## Diferenciais demonstrados

- simulação viva e reproduzível sem depender da duração real de uma recarga;
- fonte de dados substituível com qualidade explícita;
- alocação determinística separada de telemetria e ML;
- rastreabilidade de requisitos, testes e evidências;
- integração de energia, previsão, alertas, billing e ESG no mesmo Golden Path.

## Tecnologias

Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL 16,
Pytest, React, TypeScript, Vite, Recharts, Vitest, Pandas, NumPy,
Scikit-learn, Joblib, Docker e Docker Compose.

O CSV de replay representa medições que poderiam ser produzidas por inversor,
medidor e gateway: potência fotovoltaica, potência da rede, carga, estado do
inversor, temperatura e qualidade. O [contrato de telemetria](telemetry-contract.md)
explica quais campos controlam o MVP e quais permanecem apenas informativos.

## Como reproduzir

Pré-requisitos: Docker Engine com Docker Compose e portas 18000/15173 livres.
Na raiz do repositório:

```bash
make mvp-smoke
```

Esse é o caminho mais seguro: cria um projeto isolado, aplica migrations,
carrega seed, prepara ML, sobe os serviços, executa o Golden Path apenas pela
API pública e remove containers e volumes ao final. A saída JSON contém os
resultados quantitativos.

Para uma apresentação com a interface aberta, copie `.env.example` para um
`.env` local, selecione `ENERGY_DATA_PROVIDER=telemetry_replay`, indique
`TELEMETRY_REPLAY_PATH`, defina as senhas da demo somente no ambiente e siga a
mesma sequência usada por [`scripts/mvp_smoke.sh`](../../scripts/mvp_smoke.sh),
omitindo o cleanup até terminar a apresentação. Nunca versione o `.env`.

Contas do seed:

- gestor: `sprint3-admin@demo.invalid`;
- usuários: `sprint3-user-1@demo.invalid` a
  `sprint3-user-4@demo.invalid`.

As senhas são os valores definidos em `DEMO_ADMIN_PASSWORD` e
`DEMO_USER_PASSWORD`; não existem senhas fixas no repositório.

## Como validar

```bash
make check
make mvp-smoke
```

`make check` executa lint, tipos, testes backend/frontend e build. O smoke
valida migrations e o fluxo integrado em PostgreSQL limpo. A revalidação de
21/10/2026 aprovou ambos. O ensaio reproduzível pela API pública confirmou
login administrativo, start/stop, atualização por ticks automáticos, entrada
da quarta sessão, uso solar, previsão, alertas, encerramento, invoice e ESG;
os testes do dashboard validaram o polling e a atualização imediata da tela.

## Evidências visuais

As capturas abaixo foram feitas em 20/10/2026 sobre o build de produção, após o
Golden Path automático. Elas mostram dados simulados.

![Dashboard do gestor com KPIs da Sprint 4](screenshots/dashboard-gestor-sprint4.jpg)

![Tela de operação com infraestrutura e controle](screenshots/operacao-sprint4.jpg)

As capturas foram produzidas antes da correção do rótulo fixo e podem mostrar
“Curva solar sintética”. No build atual, o dashboard obtém a origem pelo
endpoint de status e diferencia “Curva solar sintética” de “Replay de
telemetria sintética”. O rótulo descreve a fonte de dados e não deve ser
interpretado como conexão física.

## Limitações e trabalhos futuros

- não há hardware, protocolo Modbus/OCPP, pagamento real ou bateria;
- telemetria, billing, emissões, economia e demanda são simulações acadêmicas;
- o processo automático pressupõe um runner por instância; o lock do banco
  evita duplicidade de ticks, mas não substitui coordenação operacional de um
  deployment distribuído;
- no servidor Vite de desenvolvimento, o `React.StrictMode` pode deixar a tela
  administrativa em “Carregando” após a remontagem; o build de produção usado
  nas capturas carrega normalmente;
- o replay usa correspondência exata e fallback zero; interpolação e retenção
  da última amostra ficariam para um contrato futuro explícito;
- o modelo depende do artefato treinado e de histórico causal compatível;
- uma integração GoodWe real dependeria de documentação e acesso autorizados
  ao equipamento específico.

## Referências técnicas

Fontes oficiais consultadas em 21/10/2026:

- [GoodWe — HCA G2 Series](https://en.goodwe.com/hca-g2): carregador AC,
  aproveitamento solar, comunicação e integração ao SEMS+;
- [GoodWe — manual do SEMS+](https://en.goodwe.com/Ftp/EN/Downloads/User%20Manual/GW_SEMS-PLUS_User-Manual-EN.pdf): monitoramento de recarga, modos solares e controle dinâmico de carga;
- [GoodWe — EzLogger Pro](https://us.goodwe.com/ezlogger-pro-monitoring-device):
  aquisição de dados de inversores, RS485 e Ethernet;
- [GoodWe — manual do EzLogger 3000R](https://br.goodwe.com/Ftp/EN/Downloads/User%20Manual/GW_Ezlogger%203000R_User%20Manual-EN.pdf): encaminhamento Modbus-TCP para sistema de gestão.

Essas referências justificam a direção de integração. Nenhuma delas comprova
compatibilidade automática com o CSV do projeto; um adaptador futuro precisará
ser validado contra o modelo e firmware efetivamente disponíveis.

## Materiais da entrega

- [evidências de execução](EVIDENCE.md);
- [matriz de rastreabilidade](traceability-matrix.md);
- [resultados quantitativos](results.md);
- [contrato de telemetria](telemetry-contract.md);
- [roteiro do vídeo](video-script.md);
- [arquitetura Mermaid](architecture.mmd) e
  [sequência Mermaid](sequence.mmd).

