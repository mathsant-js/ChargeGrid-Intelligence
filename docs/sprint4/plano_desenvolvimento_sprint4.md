# Plano de Desenvolvimento — Sprint 4

## ChargeGrid Intelligence — Solução Final Integrada e Inovadora GoodWe

## 1. Viabilidade e objetivo

É plenamente possível atender à Sprint 4 sem utilizar hardware real. O projeto já possui boa parte da base necessária:

- runner automático de ticks;
- controles para iniciar, parar e redefinir a simulação;
- relógio acelerado, por padrão com um segundo real representando um minuto simulado;
- persistência do estado do relógio;
- prevenção de ticks concorrentes;
- curva solar determinística;
- interface `EnergyDataProvider`, que desacopla a origem dos dados das regras energéticas;
- alocação Equal Share;
- prioridade solar e limite da rede;
- cobrança e indicadores ESG;
- previsão de demanda com baseline e métricas;
- alertas;
- dashboards administrativo e de usuário;
- cenário Golden Path e smoke test integrado.

O objetivo desta sprint será transformar essas capacidades em uma demonstração final mais automatizada, visual e próxima de uma integração física, mas inteiramente simulada, reproduzível e testável.

## 2. Diagnóstico do estado atual

As principais lacunas para a entrega final são:

- o dashboard não se atualiza automaticamente enquanto a simulação avança;
- a fonte solar continua sendo apenas uma função matemática;
- não existe um modo de reproduzir telemetria como se viesse de um inversor ou gateway;
- documentos e diagramas históricos da Sprint 3 ainda descrevem ticks manuais;
- falta um pacote específico de evidências e resultados da Sprint 4.

## 3. Escopo recomendado

| Incremento | Resultado esperado |
| --- | --- |
| Simulação viva | Runner automático e dashboard atualizando durante a execução |
| Telemetria simulada | Reprodução de dados externos em formato próximo de um gateway energético |
| Demonstração integrada | Cenário automático, reproduzível e quantitativamente verificável |
| Material final | README ou PDF, diagramas, resultados, imagens e roteiro do vídeo |

## 4. Incremento 1 — Tornar a simulação automática visível

O avanço automático já existe no backend. O principal trabalho será completar a experiência no frontend.

### 4.1 Implementação

- Exibir no painel:
  - estado `RUNNING` ou `STOPPED`;
  - instante simulado atual;
  - último tick concluído;
  - velocidade da simulação;
  - origem dos dados: curva solar ou telemetria reproduzida.
- Atualizar periodicamente o dashboard enquanto a simulação estiver rodando.
- Atualizar automaticamente:
  - demanda;
  - solar disponível e utilizado;
  - consumo da rede;
  - gráficos;
  - sessões;
  - alertas;
  - indicadores ESG.
- Adicionar botão “Atualizar agora”.
- Interromper o polling ao sair da página.
- Evitar requisições simultâneas caso uma consulta anterior ainda esteja em andamento.
- Manter os controles administrativos existentes para iniciar, parar e redefinir.

### 4.2 Critérios de aceite

- Depois de clicar em “Iniciar”, o instante simulado avança sem chamadas manuais a `/simulation/ticks`.
- Novas leituras aparecem no dashboard sem recarregar a página.
- “Parar” interrompe a criação de leituras.
- Chamadas repetidas para iniciar não criam runners duplicados.
- Uma falha temporária de consulta não interrompe o simulador.

### 4.3 Testes

- Testar o polling no React com timers falsos.
- Testar o cancelamento das atualizações ao desmontar a tela.
- Testar a atualização dos KPIs e gráficos.
- Manter os testes existentes de runner, concorrência e recuperação de falhas.

## 5. Incremento 2 — Criar um provedor de telemetria simulada

Este incremento responde diretamente ao feedback sobre aproximar o provedor de dados de uma fonte de hardware, sem utilizar equipamento real.

A proposta é implementar um `TelemetryReplayEnergyDataProvider`, responsável por reproduzir um arquivo versionado com medições sintéticas.

### 5.1 Formato sugerido

Um arquivo CSV ou JSON poderá conter:

```text
timestamp
station_code
pv_power_kw
grid_power_kw
load_power_kw
inverter_status
temperature_c
data_quality
```

Para as regras atuais, o campo essencial é `pv_power_kw`. Os demais campos tornam o contrato demonstrável e mais próximo de uma telemetria energética, sem alterar artificialmente as regras do MVP.

### 5.2 Funcionamento

```text
Arquivo de telemetria sintética
            ↓
TelemetryReplayEnergyDataProvider
            ↓
normalização e validação
            ↓
tick da simulação
            ↓
alocação determinística
            ↓
PostgreSQL
            ↓
dashboard, alertas, ML e ESG
```

O provider deverá:

- localizar a amostra correspondente ao instante simulado;
- validar timestamps, valores finitos e potências não negativas;
- limitar a geração ao pico configurado da estação;
- definir comportamento explícito para amostras ausentes;
- informar a origem e a qualidade da amostra;
- ser determinístico e reproduzível;
- nunca alterar diretamente a alocação de potência.

### 5.3 Seleção do provider

Utilizar uma configuração explícita, por exemplo:

```text
ENERGY_DATA_PROVIDER=curve
ENERGY_DATA_PROVIDER=telemetry_replay
```

O padrão deve continuar sendo `curve`, preservando o comportamento existente.

O componente não deve ser chamado de `ModbusEnergyDataProvider`, pois não haverá comunicação Modbus real. A nomenclatura correta evita alegar uma integração inexistente.

### 5.4 Relação com o ecossistema GoodWe

A apresentação poderá explicar que:

- inversores e gateways fornecem telemetria energética;
- o provider simulado representa a camada que receberia essas medições;
- uma integração futura poderia adaptar Modbus ou outra interface permitida pelo equipamento;
- o motor de gestão não depende da origem física dos dados;
- trocar a curva pela telemetria não altera as invariantes energéticas.

Isso constitui uma prova de substituibilidade arquitetural, e não uma alegação de conexão real com um inversor GoodWe.

### 5.5 Testes

- Leitura correta de uma amostra.
- Rejeição de potência negativa, `NaN` e timestamp inválido.
- Geração limitada ao pico da estação.
- Comportamento previsível para ausência de amostra.
- Repetição determinística.
- Execução integrada de tick usando o novo provider.
- Confirmação das invariantes:
  - potência alocada não negativa;
  - limites individuais respeitados;
  - potência da rede abaixo do limite;
  - solar utilizado abaixo do solar disponível.

## 6. Incremento 3 — Criar um cenário automático de demonstração

O projeto já possui o Golden Path. A Sprint 4 deverá acrescentar uma variante voltada ao avanço automático e à telemetria reproduzida.

### 6.1 Sequência proposta

1. Preparar o banco e o modelo de ML.
2. Carregar quatro usuários, veículos e carregadores.
3. Selecionar o provider de telemetria.
4. Iniciar três sessões de 20 kW.
5. Iniciar o simulador automático.
6. Mostrar 60 kW atendidos.
7. Iniciar a quarta sessão.
8. Mostrar Equal Share com quatro sessões.
9. Avançar para amostras com maior geração solar.
10. Mostrar o solar reduzindo a importação da rede.
11. Gerar a previsão de demanda.
12. Mostrar a classificação de risco e a recomendação.
13. Mostrar um alerta de alta demanda ou alta disponibilidade solar.
14. Encerrar uma sessão.
15. Mostrar invoice, energia solar, economia e CO₂ evitado.

As ações das sessões poderão continuar sendo chamadas pela API ou pela interface. O runner automático deverá cuidar dos ticks, mas não deverá inventar ações de usuário.

### 6.2 Resultados quantitativos mínimos

| Indicador | Resultado esperado |
| --- | ---: |
| Demanda solicitada | 80 kW |
| Limite da rede | 60 kW |
| Solar disponível | 20 kW |
| Potência total atendida | 80 kW |
| Potência da rede | 60 kW |
| Potência solar | 20 kW |
| Violações dos limites | 0 |
| Energia total | Valor obtido na execução |
| Participação solar | Valor calculado |
| CO₂ evitado | Valor calculado |
| Valor da sessão | Valor calculado |
| Risco previsto | `LOW`, `MEDIUM` ou `HIGH` |
| Métricas de ML | MAE, RMSE e R² |

Os valores de energia, cobrança e CO₂ não deverão ser fixados antes da execução final. A documentação deverá registrar os números efetivamente produzidos pelo cenário validado.

## 7. Incremento 4 — Melhorias pequenas de interface

Para maximizar a clareza da demonstração:

- exibir um badge “Dados simulados” sempre visível;
- exibir a fonte dos dados:
  - “Curva solar sintética”;
  - “Replay de telemetria sintética”;
- exibir o relógio simulado;
- mostrar o horário da última atualização;
- indicar o estado da comunicação;
- apresentar gráfico de solar disponível, solar utilizado e rede;
- destacar visualmente o limite da rede;
- apresentar painel de eventos recentes;
- exibir a recomendação operacional do modelo.

A recomendação existente poderá ser apresentada como um assistente operacional determinístico. Não é necessário adicionar LLM, chatbot ou API externa.

## 8. Itens fora do escopo

Para manter a solução simples, correta e demonstrável, não deverão ser implementados:

- hardware real;
- conexão com inversores reais;
- alegações de comunicação Modbus ou OCPP real;
- bateria ou armazenamento, pois isso não está modelado no `SPEC.md`;
- microsserviços, filas ou Redis;
- controle automático de potência pelo ML;
- gêmeo digital complexo;
- IA generativa apenas para cumprir o item de assistente virtual.

A inovação será demonstrada pela combinação de telemetria reproduzida, automação, previsão consultiva, gestão energética determinística e indicadores ambientais.

## 9. Plano de execução

### Etapa 1 — Baseline e rastreabilidade

- Executar `make check` e `make mvp-smoke`.
- Registrar o estado inicial.
- Manter os materiais da entrega em `docs/sprint4/`.
- Elaborar uma matriz “requisito → implementação → teste → evidência”.

### Etapa 2 — Dashboard vivo

- Implementar atualização periódica.
- Exibir relógio e estado da simulação.
- Adicionar testes de frontend.
- Verificar o comportamento durante start e stop.

### Etapa 3 — Telemetria reproduzida

- Evoluir o contrato do provider com a menor mudança coerente possível.
- Criar um dataset sintético versionado.
- Implementar o provider e a configuração.
- Injetá-lo no controlador.
- Adicionar testes unitários e integrados.

### Etapa 4 — Golden Path automático

- Criar roteiro ou script específico da Sprint 4.
- Utilizar apenas APIs públicas durante o fluxo.
- Produzir uma saída resumida com os resultados.
- Atualizar o smoke test caso a nova capacidade possa ser validada de maneira estável.

### Etapa 5 — Documentação e diagramas

Produzir:

- arquitetura final;
- sequência do fluxo;
- tabela de resultados;
- explicação de sustentabilidade;
- explicação da aderência ao ecossistema GoodWe;
- limitações conhecidas;
- instruções de reprodução;
- screenshots atuais.

### Etapa 6 — Validação final

Executar:

```bash
make check
make mvp-smoke
```

Também ensaiar manualmente:

- login administrativo;
- início da simulação;
- atualização automática;
- entrada da quarta sessão;
- utilização solar;
- geração de alerta;
- previsão de demanda;
- encerramento de sessão;
- invoice e ESG.

## 10. Estrutura recomendada para a documentação final

```text
docs/sprint4/
├── plano_desenvolvimento_sprint4.md
├── README.md
├── EVIDENCE.md
├── architecture.mmd
├── sequence.mmd
├── telemetry-contract.md
├── results.md
├── video-script.md
├── diagrams/
└── screenshots/
```

O README final deverá conter:

1. Título do projeto.
2. Equipe envolvida.
3. Problema abordado.
4. Solução proposta.
5. Arquitetura final.
6. Fluxo integrado.
7. Automação da simulação.
8. Telemetria simulada.
9. Compatibilidade conceitual com GoodWe.
10. Gestão energética.
11. Machine Learning e baseline.
12. Resultados quantitativos.
13. Sustentabilidade.
14. Diferenciais inovadores.
15. Tecnologias utilizadas.
16. Como executar.
17. Como validar.
18. Limitações e trabalhos futuros.

## 11. Roteiro sugerido para o vídeo de até cinco minutos

| Tempo | Conteúdo |
| --- | --- |
| 0:00–0:30 | Problema, proposta e aviso de que os dados são simulados |
| 0:30–1:00 | Arquitetura e provider substituível |
| 1:00–2:15 | Sessões e simulação avançando automaticamente |
| 2:15–3:00 | Quarta sessão, limite da rede e prioridade solar |
| 3:00–3:35 | Telemetria reproduzida e proximidade com integração física |
| 3:35–4:10 | Previsão, risco e alertas |
| 4:10–4:40 | Billing, participação solar, economia e CO₂ evitado |
| 4:40–5:00 | Resultados, limitações e evolução futura |

## 12. Definição de pronto

A Sprint 4 estará concluída quando:

- a simulação avançar automaticamente;
- o dashboard acompanhar esse avanço;
- a fonte solar puder ser trocada por telemetria sintética reproduzida;
- todas as invariantes energéticas continuarem protegidas;
- o Golden Path funcionar de ponta a ponta;
- testes, tipos, lint e build passarem;
- o smoke test funcionar em um PostgreSQL limpo;
- os resultados reais da execução estiverem documentados;
- os diagramas corresponderem ao código;
- o vídeo puder ser gravado sem edições manuais no banco;
- a documentação declarar claramente o que é simulado.

## 13. Ordem de prioridade

A ordem recomendada de implementação é:

```text
dashboard vivo
    ↓
replay de telemetria
    ↓
cenário automático
    ↓
evidências e documentação final
```

Essa sequência responde diretamente ao feedback recebido e melhora a apresentação sem aumentar desnecessariamente a complexidade do MVP.
