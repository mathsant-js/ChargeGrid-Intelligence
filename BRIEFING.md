# ChargeGrid Intelligence

## Briefing do Projeto

**Projeto:** EV Challenge 2026
**Sprint:** Sprint 1 — Apresentação do Projeto Sustentável
**Equipe:** Equipe 3
**Instituições:** FIAP × GoodWe
**Área:** Mobilidade elétrica, gestão energética, sustentabilidade e inteligência artificial

---

# 1. Conceito

> **ChargeGrid Intelligence — Transformando cada recarga em inteligência acionável.**

O **ChargeGrid Intelligence** é uma plataforma de software para gerenciamento inteligente de infraestrutura de recarga de veículos elétricos.

A solução transforma dados produzidos durante sessões de carregamento em informações úteis para:

* gerenciamento energético;
* controle de demanda;
* utilização de energia solar;
* billing;
* análise financeira;
* sustentabilidade;
* Machine Learning;
* apoio à tomada de decisão.

A plataforma funcionará como uma **camada de software e inteligência sobre o ecossistema de carregamento**, com arquitetura preparada para futura integração com equipamentos reais.

Nesta etapa acadêmica, não será necessário desenvolver hardware próprio nem depender de carregadores físicos.

---

# 2. Visão do Produto

O crescimento da mobilidade elétrica aumenta a necessidade de infraestrutura de recarga eficiente, escalável e energeticamente inteligente.

Disponibilizar carregadores, isoladamente, não resolve todos os problemas.

Quando diversos veículos utilizam uma instalação simultaneamente, surgem desafios relacionados a:

* concentração de demanda;
* limite de potência da instalação;
* aumento de custos;
* aproveitamento de energia renovável;
* planejamento operacional;
* cobrança;
* monitoramento;
* sustentabilidade.

Ao mesmo tempo, cada sessão de recarga produz dados que podem auxiliar o gestor a entender e melhorar a operação.

O ChargeGrid Intelligence propõe utilizar esses dados para transformar:

> **recarga → dados → informação → inteligência → decisão energética.**

---

# 3. Problemas que o Projeto Busca Resolver

## 3.1 Falta de inteligência energética

Infraestruturas de recarga podem operar sem considerar adequadamente a demanda combinada de diversos carregadores.

Exemplo:

```text
Limite disponível da rede: 60 kW

Carregador A → solicita 20 kW
Carregador B → solicita 20 kW
Carregador C → solicita 20 kW

Total solicitado → 60 kW
```

Se um quarto carregador solicitar 20 kW:

```text
Demanda solicitada → 80 kW
Limite da rede      → 60 kW
```

O ChargeGrid Intelligence deverá identificar a restrição e redistribuir virtualmente a potência disponível.

---

## 3.2 Billing

Uma infraestrutura comercial de recarga precisa associar sessões a usuários, consumo e custos.

A plataforma deverá permitir:

1. identificar o usuário;
2. identificar o veículo;
3. selecionar um carregador;
4. iniciar uma sessão;
5. registrar energia consumida;
6. aplicar uma tarifa;
7. finalizar a sessão;
8. calcular o valor devido;
9. gerar um registro financeiro da sessão;
10. disponibilizar histórico.

Nesta versão, o billing será **simulado**.

Não haverá integração obrigatória com gateway financeiro.

---

## 3.3 Subutilização dos dados

Cada sessão pode produzir dados como:

* horário;
* duração;
* energia consumida;
* potência solicitada;
* potência efetivamente entregue;
* energia proveniente da rede;
* energia solar utilizada;
* custo;
* usuário;
* veículo;
* carregador.

Esses dados podem ser utilizados para:

* dashboards;
* alertas;
* relatórios;
* previsão;
* análise de utilização;
* planejamento energético;
* indicadores ambientais.

---

## 3.4 Aproveitamento de energia solar

Quando houver geração fotovoltaica disponível, a plataforma deverá considerar essa energia antes de calcular a necessidade de importação da rede.

Exemplo:

```text
Demanda de carregamento: 40 kW
Energia solar:          25 kW
Energia da rede:        15 kW
```

O sistema deverá registrar separadamente a contribuição solar e a contribuição da rede.

---

## 3.5 Antecipação de picos

Somente reagir a uma demanda elevada pode ser insuficiente.

A plataforma deverá possuir uma camada preditiva capaz de utilizar dados históricos para estimar a demanda futura e classificar risco de pico.

O Machine Learning terá papel **consultivo e preditivo**, e não será responsável diretamente pelas regras críticas de segurança e controle energético.

---

# 4. Objetivo Geral

Desenvolver uma plataforma de software capaz de **simular, gerenciar, analisar e otimizar sessões de recarga de veículos elétricos**, utilizando regras de gestão energética, dados históricos e Machine Learning para apoiar decisões relacionadas a consumo, demanda, energia solar, sustentabilidade e cobrança.

---

# 5. Objetivos Específicos

O projeto deverá:

* gerenciar usuários;
* gerenciar veículos;
* gerenciar estações e carregadores;
* registrar sessões de carregamento;
* simular consumo energético;
* monitorar demanda;
* limitar virtualmente a utilização da rede;
* distribuir potência entre sessões;
* simular geração fotovoltaica;
* priorizar energia solar;
* calcular energia proveniente da rede;
* implementar billing pay-per-use;
* registrar histórico;
* gerar indicadores ambientais;
* disponibilizar dashboards;
* emitir alertas;
* gerar dataset histórico;
* treinar um modelo preditivo simples;
* estimar demanda futura;
* classificar risco de pico;
* apresentar recomendações ao gestor;
* possuir arquitetura preparada para integração futura com hardware real.

---

# 6. Proposta de Valor

O diferencial do ChargeGrid Intelligence não é apenas iniciar ou finalizar uma recarga.

O produto busca integrar:

**Mobilidade elétrica + Gestão energética + Energia solar + Dados + Machine Learning + Sustentabilidade + Billing**

em uma única plataforma demonstrável.

---

# 7. Personas

## 7.1 Gestor / Administrador

Responsável pela infraestrutura de recarga.

Deverá conseguir:

* cadastrar estações;
* cadastrar carregadores;
* configurar limites energéticos;
* configurar tarifas;
* acompanhar carregadores;
* acompanhar sessões;
* visualizar demanda;
* visualizar utilização solar;
* acessar previsões;
* receber alertas;
* visualizar billing;
* acessar indicadores ambientais;
* consultar histórico.

---

## 7.2 Usuário / Motorista

Pessoa que utiliza a infraestrutura.

Deverá conseguir:

* possuir cadastro;
* cadastrar veículos;
* iniciar sessão;
* acompanhar sessão atual;
* finalizar sessão;
* visualizar energia consumida;
* visualizar custo;
* visualizar utilização de energia solar;
* visualizar histórico.

---

# 8. Escopo do MVP

## 8.1 Funcionalidades obrigatórias

### Administração

* usuários;
* veículos;
* estações;
* carregadores;
* configurações energéticas;
* tarifas.

### Recarga

* início de sessão;
* atualização simulada da sessão;
* cálculo de energia;
* encerramento;
* histórico.

### Gestão energética

* limite da rede;
* potência solicitada;
* potência alocada;
* redistribuição automática;
* geração solar simulada;
* prioridade solar.

### Billing

* tarifa por kWh;
* cálculo de custo;
* fechamento da sessão;
* invoice simulada.

### Analytics

* demanda atual;
* energia consumida;
* energia solar utilizada;
* energia da rede;
* custo;
* sessões ativas;
* utilização da infraestrutura.

### Machine Learning

* dataset histórico;
* baseline;
* modelo preditivo;
* previsão de demanda;
* classificação de risco.

### Sustentabilidade

* energia solar utilizada;
* percentual solar;
* estimativa de CO₂ evitado;
* economia estimada.

### Alertas

* demanda elevada;
* risco de pico;
* disponibilidade solar;
* encerramento de sessão.

---

# 9. Escopo Secundário

Caso o MVP obrigatório esteja concluído, poderão ser adicionados:

* planos corporativos;
* franquia mensal de kWh;
* relatórios exportáveis;
* filtros avançados;
* comparação entre estações;
* diferentes políticas de alocação de potência;
* recomendações energéticas mais sofisticadas.

Esses recursos não deverão atrasar o fluxo principal.

---

# 10. Fora do Escopo

Nesta versão não serão desenvolvidos:

* carregadores físicos;
* inversores;
* Smart Meters;
* gateways;
* instalação elétrica;
* firmware;
* RFID físico;
* comunicação Modbus real;
* OCPP real;
* integração obrigatória com hardware;
* pagamentos reais;
* Stripe;
* Mercado Pago;
* aplicativo mobile nativo;
* microsserviços;
* Kubernetes;
* Kafka;
* RabbitMQ;
* MLOps avançado;
* Deep Learning;
* redes neurais;
* IA generativa como parte central do produto;
* chatbot;
* infraestrutura cloud complexa.

---

# 11. Princípio de Desenvolvimento

A prioridade do projeto será:

> **correção → simplicidade → integração → demonstração → sofisticação**

Sempre que houver duas soluções possíveis, deverá ser escolhida a solução mais simples que:

* cumpra os requisitos;
* possa ser testada;
* seja compreensível pela equipe;
* possa ser apresentada;
* permita evolução futura.

---

# 12. Arquitetura de Alto Nível

```text
┌─────────────────────────────┐
│          Usuário            │
│      Gestor / Motorista     │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│           Frontend          │
│    React + TypeScript       │
└──────────────┬──────────────┘
               │ REST
               ▼
┌─────────────────────────────┐
│           FastAPI           │
│      Backend modular        │
└──────────────┬──────────────┘
               │
 ┌─────────────┼───────────────┐
 ▼             ▼               ▼
Database    Energy         Billing
PostgreSQL Logic           Service
               │
        ┌──────┴──────┐
        ▼             ▼
   Simulation        ML
       Engine      Prediction
        │             │
        └──────┬──────┘
               ▼
          Analytics
```

A arquitetura será um **monólito modular**.

Não serão utilizados microsserviços no MVP.

---

# 13. Stack Tecnológica

## Frontend

* React;
* TypeScript;
* Vite;
* React Router;
* biblioteca HTTP para consumo da API;
* Recharts para gráficos;
* Tailwind CSS para estilização.

## Backend

* Python 3.12;
* FastAPI;
* Pydantic v2;
* SQLAlchemy 2;
* Alembic.

## Banco

* PostgreSQL 16.

## Machine Learning e dados

* Pandas;
* NumPy;
* Scikit-learn;
* Joblib.

## Testes

### Backend

* Pytest.

### Frontend

* Vitest;
* React Testing Library.

## Ambiente

* Docker;
* Docker Compose.

---

# 14. Machine Learning

O Machine Learning será uma camada auxiliar.

Ele não substituirá regras determinísticas relacionadas a:

* limites de potência;
* cálculo de custo;
* cálculo energético;
* encerramento de sessão.

O objetivo inicial será:

> **prever demanda agregada futura e classificar o risco de pico.**

O projeto deverá comparar pelo menos:

1. baseline simples;
2. modelo de Machine Learning.

O modelo deve ser simples, explicável e integrado ao produto.

---

# 15. Sustentabilidade

O projeto deverá produzir indicadores relacionados a:

* energia total consumida;
* energia solar utilizada;
* energia importada da rede;
* participação solar;
* estimativa de emissões evitadas;
* economia financeira associada à geração solar.

Todos os cálculos deverão possuir fórmulas explícitas e parâmetros configuráveis.

---

# 16. Billing

O MVP utilizará:

> **Pay-per-Use**

Fórmula básica:

```text
custo = energia_consumida_kWh × tarifa_R$_por_kWh
```

O sistema poderá representar uma invoice, mas não processará dinheiro real.

Modelos de assinatura e SaaS pertencem à visão comercial futura.

---

# 17. Golden Path da Demonstração

O projeto deverá ser otimizado para demonstrar o seguinte cenário:

```text
1. Existem três carregadores ativos.

2. A utilização da instalação está próxima do limite.

3. Um quarto veículo inicia uma recarga.

4. A demanda solicitada ultrapassaria o limite permitido.

5. O ChargeGrid Intelligence detecta a situação.

6. O sistema redistribui virtualmente a potência.

7. Há geração solar disponível.

8. Parte da energia utilizada vem da geração fotovoltaica.

9. O sistema calcula a energia restante proveniente da rede.

10. O modelo prevê demanda elevada para o próximo período.

11. O dashboard apresenta risco de pico.

12. O gestor recebe um alerta.

13. Uma sessão é encerrada.

14. O sistema calcula:
    - energia consumida;
    - energia solar;
    - energia da rede;
    - custo;
    - CO₂ evitado.

15. O dashboard é atualizado.
```

Esse fluxo será a principal referência de sucesso do MVP.

---

# 18. Dashboard do Gestor

Deverá apresentar no mínimo:

* demanda atual;
* limite da rede;
* capacidade ainda disponível;
* geração solar atual;
* consumo proveniente da rede;
* consumo proveniente da solar;
* número de carregadores ativos;
* sessões ativas;
* demanda prevista;
* risco de pico;
* faturamento;
* energia consumida;
* energia renovável utilizada;
* CO₂ evitado;
* alertas recentes.

---

# 19. Dashboard do Usuário

Deverá apresentar:

* veículo;
* carregador;
* estado da sessão;
* duração;
* potência atual;
* energia acumulada;
* participação solar;
* custo acumulado;
* histórico de sessões.

---

# 20. Roadmap

## Fase 1 — Fundação

* repositório;
* estrutura;
* Docker;
* banco;
* migrations;
* FastAPI;
* frontend;
* configuração.

## Fase 2 — Domínio

* usuários;
* veículos;
* estações;
* carregadores;
* sessões.

## Fase 3 — Simulação

* relógio simulado;
* carregadores;
* consumo;
* geração solar;
* leituras energéticas.

## Fase 4 — Gestão Energética

* limite da rede;
* demanda solicitada;
* alocação de potência;
* prioridade solar.

## Fase 5 — Billing

* tarifas;
* custo;
* invoices;
* histórico.

## Fase 6 — Dashboards

* gestor;
* usuário;
* gráficos;
* alertas.

## Fase 7 — Machine Learning

* dataset;
* baseline;
* treinamento;
* avaliação;
* persistência do modelo;
* previsão;
* classificação de risco.

## Fase 8 — ESG

* energia renovável;
* CO₂ evitado;
* economia;
* relatórios.

## Fase 9 — Finalização

* testes;
* correções;
* UX;
* seeds;
* demonstração;
* README;
* documentação;
* pitch.

---

# 21. Organização da Equipe

## Backend / Arquitetura

* FastAPI;
* regras de negócio;
* integração;
* arquitetura.

## Banco de Dados

* PostgreSQL;
* modelagem;
* migrations;
* consultas.

## Frontend

* React;
* componentes;
* dashboards;
* UX.

## Energia / Simulação

* consumo;
* carregadores;
* demanda;
* geração solar;
* algoritmo de potência.

## Machine Learning / Dados

* dataset;
* análise;
* baseline;
* treinamento;
* avaliação;
* integração.

## Produto / QA / Documentação

* requisitos;
* critérios de aceite;
* testes funcionais;
* documentação;
* apresentação;
* validação.

As responsabilidades não representam barreiras rígidas. Integrantes poderão colaborar entre áreas.

---

# 22. Critério de Sucesso

O projeto será considerado tecnicamente bem-sucedido quando conseguir demonstrar de ponta a ponta:

* API funcional;
* banco persistente;
* frontend funcional;
* simulador;
* múltiplos carregadores;
* sessões;
* gestão de demanda;
* utilização solar;
* billing;
* dashboards;
* indicadores ambientais;
* modelo preditivo integrado;
* alertas;
* testes das regras críticas.

O sucesso do projeto não será medido pela quantidade de tecnologias utilizadas.

Será medido pela capacidade de demonstrar claramente que:

> **dados de recarga podem ser utilizados para tornar uma infraestrutura de eletropostos mais inteligente, previsível, econômica e sustentável.**

---

# 23. Visão de Futuro

A arquitetura deverá permitir futuramente:

```text
Carregadores reais
        ↓
Smart Meter
        ↓
Inversor fotovoltaico
        ↓
Gateway / OCPP / Modbus
        ↓
ChargeGrid Intelligence
        ↓
Energy Management
        ↓
Machine Learning
        ↓
Analytics
        ↓
Gestor / Usuário
```

A versão acadêmica representa a camada de software e inteligência desse ecossistema.

---

# 24. Resultado Esperado

Ao final do projeto, a equipe deverá possuir uma aplicação web capaz de simular uma infraestrutura de carregamento e demonstrar como seus dados podem ser utilizados para:

* controlar demanda;
* distribuir potência;
* aproveitar geração solar;
* prever picos;
* realizar billing;
* calcular indicadores ambientais;
* gerar alertas;
* apoiar decisões operacionais.

O ChargeGrid Intelligence deverá parecer um **produto integrado**, e não uma coleção independente de funcionalidades.
