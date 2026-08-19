# ChargeGrid Intelligence — Technical Specification

## Versão

**Status:** Especificação inicial do MVP
**Projeto:** ChargeGrid Intelligence
**Arquitetura:** Monólito modular
**Interface:** Aplicação Web
**API:** REST/JSON

Este documento é a **fonte de verdade técnica e funcional** do projeto.

Em caso de conflito entre `BRIEFING.md` e `SPEC.md`, as regras explícitas deste documento prevalecem para a implementação.

---

# 1. Objetivos Técnicos

O sistema deverá permitir:

1. persistência de entidades;
2. criação de sessões de recarga;
3. simulação temporal de consumo;
4. cálculo energético;
5. gerenciamento de demanda;
6. alocação virtual de potência;
7. simulação solar;
8. billing;
9. analytics;
10. indicadores ESG;
11. previsão de demanda;
12. classificação de risco;
13. dashboards.

---

# 2. Arquitetura

A aplicação será implementada como **monólito modular**.

```text
Frontend
   │
   │ HTTP / JSON
   ▼
FastAPI
   │
   ├── Auth
   ├── Users
   ├── Vehicles
   ├── Stations
   ├── Chargers
   ├── Sessions
   ├── Energy
   ├── Simulation
   ├── Billing
   ├── Analytics
   ├── Alerts
   └── ML
           │
           ▼
       PostgreSQL
```

Os módulos deverão ser separados logicamente, mas executados dentro da mesma aplicação backend.

---

# 3. Estrutura Inicial do Repositório

```text
chargegrid-intelligence/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── simulation/
│   │   ├── ml/
│   │   ├── analytics/
│   │   └── main.py
│   │
│   ├── migrations/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── types/
│   │   └── utils/
│   │
│   ├── package.json
│   └── Dockerfile
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── models/
│
├── docs/
│
├── scripts/
│
├── .env.example
├── docker-compose.yml
├── AGENTS.md
├── BRIEFING.md
├── SPEC.md
└── README.md
```

A estrutura poderá sofrer pequenos ajustes se houver justificativa técnica, mas não deverá ser convertida para microsserviços.

---

# 4. Stack

## Backend

```text
Python 3.12
FastAPI
Pydantic v2
SQLAlchemy 2
Alembic
PostgreSQL 16
Pytest
```

## Frontend

```text
React
TypeScript
Vite
React Router
Tailwind CSS
Recharts
Vitest
React Testing Library
```

## ML

```text
Pandas
NumPy
Scikit-learn
Joblib
```

## Ambiente

```text
Docker
Docker Compose
```

---

# 5. Convenções

## IDs

As entidades deverão utilizar UUID.

## Datas

Datas serão armazenadas em UTC.

A interface poderá convertê-las para o horário local.

## Valores energéticos

Potência:

```text
kW
```

Energia:

```text
kWh
```

## Valores financeiros

Armazenar valores monetários utilizando decimal, e não `float`.

Moeda inicial:

```text
BRL
```

---

# 6. Papéis de Usuário

```text
ADMIN
USER
```

## ADMIN

Possui acesso administrativo à infraestrutura.

## USER

Possui acesso aos próprios veículos e sessões.

O MVP não necessita de um sistema sofisticado de RBAC.

---

# 7. Entidades

## 7.1 User

Campos mínimos:

```text
id
name
email
password_hash
role
is_active
created_at
updated_at
```

Regras:

* `email` deve ser único;
* senha nunca deve ser armazenada em texto puro.

---

# 7.2 Vehicle

```text
id
user_id
name
brand
model
license_plate
max_charge_power_kw
created_at
updated_at
```

Relacionamento:

```text
User 1:N Vehicle
```

---

# 7.3 ChargingStation

Representa uma instalação/local energético.

```text
id
name
description
grid_limit_kw
is_active
created_at
updated_at
```

Uma estação pode possuir vários carregadores.

---

# 7.4 Charger

```text
id
station_id
name
code
max_power_kw
status
is_active
created_at
updated_at
```

Status:

```text
AVAILABLE
CHARGING
UNAVAILABLE
```

Relacionamento:

```text
ChargingStation 1:N Charger
```

---

# 7.5 ChargingSession

```text
id
user_id
vehicle_id
charger_id

status

started_at
ended_at

requested_power_kw
allocated_power_kw

energy_consumed_kwh
solar_energy_kwh
grid_energy_kwh

tariff_per_kwh
total_cost

created_at
updated_at
```

---

# 7.6 EnergyReading

Armazena séries temporais da sessão.

```text
id
session_id
timestamp

requested_power_kw
allocated_power_kw

solar_power_kw
grid_power_kw

interval_energy_kwh
solar_energy_kwh
grid_energy_kwh
```

---

# 7.7 SolarReading

```text
id
station_id
timestamp
available_power_kw
```

---

# 7.8 Tariff

```text
id
name
price_per_kwh
currency
is_active
valid_from
valid_until
created_at
```

Somente uma tarifa padrão precisa estar ativa no MVP.

---

# 7.9 Invoice

```text
id
session_id
user_id

energy_kwh
tariff_per_kwh

subtotal
total

status
created_at
closed_at
```

Status:

```text
OPEN
CLOSED
CANCELLED
```

Nenhum pagamento real será processado.

---

# 7.10 Alert

```text
id
station_id
type
severity
title
message
created_at
acknowledged_at
```

Tipos iniciais:

```text
HIGH_DEMAND
PEAK_RISK
HIGH_SOLAR_AVAILABILITY
SESSION_FINISHED
```

Severity:

```text
INFO
WARNING
CRITICAL
```

---

# 7.11 DemandPrediction

```text
id
station_id
generated_at
prediction_for

predicted_demand_kw
capacity_kw
risk_level
model_version
```

Risk:

```text
LOW
MEDIUM
HIGH
```

---

# 7.12 SystemConfiguration

Armazena parâmetros ajustáveis.

Exemplos:

```text
simulation_speed
grid_emission_factor_kg_per_kwh
high_demand_threshold
medium_peak_threshold
high_peak_threshold
```

---

# 8. Estados da Sessão

Estados permitidos:

```text
CREATED
CHARGING
PAUSED
COMPLETED
CANCELLED
```

Fluxo principal:

```text
CREATED
   ↓
CHARGING
   ↓
COMPLETED
```

Fluxos adicionais:

```text
CHARGING
   ↓
PAUSED
   ↓
CHARGING
```

ou:

```text
CREATED / CHARGING / PAUSED
              ↓
          CANCELLED
```

Uma sessão `COMPLETED` ou `CANCELLED` não pode retornar para `CHARGING`.

---

# 9. Regras de Início de Sessão

Uma sessão somente poderá ser iniciada quando:

* usuário estiver ativo;
* veículo pertencer ao usuário;
* carregador estiver ativo;
* carregador estiver `AVAILABLE`;
* não existir outra sessão ativa no mesmo carregador;
* veículo não possuir outra sessão ativa.

No início:

```text
session.status = CHARGING
charger.status = CHARGING
```

---

# 10. Potência Solicitada

A potência solicitada pela sessão será:

```text
requested_power_kw =
min(
    charger.max_power_kw,
    vehicle.max_charge_power_kw
)
```

O simulador poderá permitir valores menores para cenários específicos.

---

# 11. Modelo Energético

Devem existir conceitos separados:

```text
grid_limit_kw
solar_available_kw
requested_power_kw
allocated_power_kw
```

`grid_limit_kw` representa o máximo que a estação pode importar da rede.

Solar não deve ser contabilizada como importação da rede.

---

# 12. Potência Disponível para Recarga

No MVP:

```text
total_energy_supply_capacity_kw =
grid_limit_kw + solar_available_kw
```

Entretanto, a importação da rede nunca poderá ultrapassar:

```text
grid_limit_kw
```

---

# 13. Algoritmo de Gerenciamento de Demanda V1

A política inicial será denominada:

> **Equal Share Allocation**

Considere todas as sessões `CHARGING` da estação.

Calcular:

```text
total_requested_kw =
sum(session.requested_power_kw)
```

E:

```text
total_available_kw =
grid_limit_kw + solar_available_kw
```

## Caso 1

Se:

```text
total_requested_kw <= total_available_kw
```

então cada sessão recebe:

```text
allocated_power_kw =
requested_power_kw
```

## Caso 2

Se:

```text
total_requested_kw > total_available_kw
```

o sistema deverá dividir a potência disponível proporcionalmente.

Para a versão V1, utilizar distribuição igualitária limitada à potência solicitada.

Uma implementação iterativa deverá redistribuir sobras.

Exemplo:

```text
available = 60 kW

A solicita 20
B solicita 20
C solicita 20
D solicita 20
```

Resultado:

```text
A = 15
B = 15
C = 15
D = 15
```

Total:

```text
60 kW
```

---

# 14. Invariantes Energéticas

Estas regras nunca poderão ser violadas:

```text
allocated_power_kw >= 0
```

```text
allocated_power_kw <= requested_power_kw
```

```text
allocated_power_kw <= charger.max_power_kw
```

```text
allocated_power_kw <= vehicle.max_charge_power_kw
```

```text
total_grid_power_kw <= grid_limit_kw
```

Nenhuma regra de Machine Learning poderá violar essas invariantes.

---

# 15. Prioridade Solar

Energia solar será utilizada antes da energia da rede.

Para uma demanda instantânea:

```text
solar_used_kw =
min(
    total_allocated_power_kw,
    solar_available_kw
)
```

Depois:

```text
grid_used_kw =
max(
    total_allocated_power_kw - solar_used_kw,
    0
)
```

Deve sempre valer:

```text
grid_used_kw <= grid_limit_kw
```

---

# 16. Rateio da Energia Solar entre Sessões

A energia solar poderá ser distribuída proporcionalmente à potência alocada.

Para uma sessão:

```text
session_solar_power_kw =
session_allocated_power_kw
×
solar_used_kw / total_allocated_power_kw
```

Se:

```text
total_allocated_power_kw = 0
```

então:

```text
session_solar_power_kw = 0
```

A potência restante será considerada proveniente da rede.

---

# 17. Cálculo de Energia

Para um intervalo:

```text
energy_kwh =
power_kw × interval_hours
```

Exemplo:

```text
15 kW durante 5 minutos

interval_hours = 5 / 60

energy =
15 × 5/60
= 1,25 kWh
```

A mesma lógica deverá ser utilizada para:

* energia total;
* energia solar;
* energia da rede.

Deve sempre valer aproximadamente:

```text
energy_consumed_kwh =
solar_energy_kwh + grid_energy_kwh
```

Diferenças mínimas de arredondamento são aceitáveis.

---

# 18. Simulador

O simulador representa equipamentos físicos.

Ele deverá ser isolado das regras de domínio para permitir substituição futura por integração real.

---

# 19. Relógio do Simulador

Configuração inicial:

```text
1 segundo real = 1 minuto simulado
```

Esse fator deverá ser configurável.

O sistema não deverá depender de sessões de duração real para demonstrar comportamento.

---

# 20. Tick de Simulação

A cada tick:

1. recuperar sessões ativas;
2. determinar geração solar;
3. calcular demanda solicitada;
4. executar alocação;
5. calcular potência solar;
6. calcular potência da rede;
7. calcular energia do intervalo;
8. persistir `EnergyReading`;
9. atualizar acumuladores da sessão;
10. verificar alertas;
11. atualizar analytics necessários.

---

# 21. Simulação Solar

O MVP poderá utilizar uma curva determinística de geração solar.

Exemplo conceitual:

```text
00h ───────── 0
06h ───────── início
12h ───────── pico
18h ───────── próximo de zero
20h ───────── 0
```

A função poderá receber:

```text
timestamp
station_peak_solar_kw
```

e retornar:

```text
solar_available_kw
```

Ruído opcional poderá ser adicionado posteriormente.

O comportamento deverá ser reprodutível em testes.

---

# 22. Billing

O MVP implementará apenas cobrança simulada.

Modelo obrigatório:

```text
PAY_PER_USE
```

Cálculo:

```text
subtotal =
energy_consumed_kwh × tariff_per_kwh
```

No MVP:

```text
total = subtotal
```

Não serão aplicados:

* impostos reais;
* descontos complexos;
* taxa fixa;
* processamento de cartão.

---

# 23. Fechamento da Sessão

Ao finalizar:

```text
session.status = COMPLETED
session.ended_at = now
charger.status = AVAILABLE
```

O sistema deverá:

1. finalizar os acumuladores;
2. calcular custo;
3. criar invoice;
4. fechar invoice;
5. produzir alerta;
6. disponibilizar dados no histórico.

---

# 24. Indicadores ESG

## Participação solar

```text
solar_percentage =
solar_energy_kwh /
energy_consumed_kwh
× 100
```

Se consumo for zero:

```text
solar_percentage = 0
```

---

# 25. CO₂ Evitado

O MVP utilizará um fator configurável:

```text
grid_emission_factor_kg_per_kwh
```

Fórmula:

```text
avoided_co2_kg =
solar_energy_kwh
×
grid_emission_factor_kg_per_kwh
```

O valor do fator utilizado deverá ser exibível ou documentado.

Nunca deverá existir um número oculto hardcoded sem identificação.

---

# 26. Economia Solar

Definição do MVP:

```text
solar_savings =
solar_energy_kwh × tariff_per_kwh
```

Esse indicador representa o valor teórico da energia que teria sido comprada da rede.

Não representa necessariamente economia financeira real da instalação.

A interface deverá tratá-lo como:

> **economia estimada**

---

# 27. Machine Learning

## Objetivo

Prever a demanda agregada da estação para:

```text
próximos 60 minutos
```

Saída principal:

```text
predicted_demand_kw
```

---

# 28. Features do Modelo

Features mínimas:

```text
hour
day_of_week
is_weekend
active_sessions
current_demand_kw
historical_avg_demand_kw
solar_available_kw
```

Features adicionais poderão ser avaliadas se houver dados suficientes.

---

# 29. Target

```text
demand_kw_next_60_minutes
```

O pipeline de dataset deverá impedir vazamento de dados futuros para features do passado.

---

# 30. Dataset Simulado

Dataset inicial recomendado:

```text
90 dias simulados
intervalos de 5 minutos
```

Colunas mínimas:

```text
timestamp
hour
day_of_week
is_weekend
active_sessions
requested_power_kw
allocated_power_kw
solar_available_kw
solar_used_kw
grid_power_kw
total_demand_kw
```

---

# 31. Baseline

Antes do modelo ML, deverá existir um baseline simples.

Inicialmente:

```text
média histórica para
hora + dia da semana
```

Isso permitirá comparar o modelo treinado contra uma referência simples.

---

# 32. Modelo Inicial

Modelo recomendado:

```text
RandomForestRegressor
```

A escolha poderá ser alterada caso experimentos demonstrem vantagem clara de outro modelo simples.

Não utilizar Deep Learning.

---

# 33. Métricas do Modelo

Registrar pelo menos:

```text
MAE
RMSE
R²
```

A comparação principal deverá ser:

```text
modelo ML
vs
baseline
```

O objetivo acadêmico é demonstrar avaliação, e não apenas treinamento.

---

# 34. Classificação de Risco

Baseada na relação:

```text
predicted_demand_kw / effective_capacity_kw
```

Inicialmente:

```text
LOW
< 70%
```

```text
MEDIUM
>= 70% e < 90%
```

```text
HIGH
>= 90%
```

Os thresholds deverão ser configuráveis.

---

# 35. Recomendações

O sistema poderá derivar recomendações determinísticas da previsão.

Exemplo:

```text
HIGH

"Alta probabilidade de utilização próxima ao limite.
Considere restringir a potência de novas sessões."
```

O texto não precisa ser gerado por IA generativa.

---

# 36. Alertas

## HIGH_DEMAND

Disparar quando:

```text
current_grid_power_kw /
grid_limit_kw
>= high_demand_threshold
```

Valor inicial recomendado:

```text
0.85
```

---

## PEAK_RISK

Disparar quando:

```text
risk_level = HIGH
```

---

## HIGH_SOLAR_AVAILABILITY

Pode ser disparado quando houver geração solar significativa configurada.

Não é obrigatório gerar repetidamente o mesmo alerta a cada tick.

---

## SESSION_FINISHED

Criado após encerramento bem-sucedido.

---

# 37. API

Prefixo:

```text
/api/v1
```

---

# 38. Health

```text
GET /api/v1/health
```

Resposta:

```json
{
  "status": "ok"
}
```

---

# 39. Auth

```text
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

Autenticação poderá utilizar JWT para o MVP.

---

# 40. Users

```text
GET    /api/v1/users
POST   /api/v1/users
GET    /api/v1/users/{id}
PATCH  /api/v1/users/{id}
```

---

# 41. Vehicles

```text
GET    /api/v1/vehicles
POST   /api/v1/vehicles
GET    /api/v1/vehicles/{id}
PATCH  /api/v1/vehicles/{id}
DELETE /api/v1/vehicles/{id}
```

---

# 42. Stations

```text
GET    /api/v1/stations
POST   /api/v1/stations
GET    /api/v1/stations/{id}
PATCH  /api/v1/stations/{id}
```

---

# 43. Chargers

```text
GET    /api/v1/chargers
POST   /api/v1/chargers
GET    /api/v1/chargers/{id}
PATCH  /api/v1/chargers/{id}
```

---

# 44. Sessions

```text
GET  /api/v1/sessions
GET  /api/v1/sessions/{id}

POST /api/v1/sessions/start
POST /api/v1/sessions/{id}/stop
```

Opcional posteriormente:

```text
POST /api/v1/sessions/{id}/pause
POST /api/v1/sessions/{id}/resume
```

---

# 45. Energy

```text
GET /api/v1/energy/current
GET /api/v1/energy/history
```

Filtros poderão incluir:

```text
station_id
from
to
```

---

# 46. Solar

```text
GET /api/v1/solar/current
GET /api/v1/solar/history
```

---

# 47. Billing

```text
GET /api/v1/billing/invoices
GET /api/v1/billing/invoices/{id}
```

---

# 48. Analytics

```text
GET /api/v1/analytics/dashboard
GET /api/v1/analytics/sustainability
```

---

# 49. Predictions

```text
GET /api/v1/predictions/demand
```

Exemplo de resposta:

```json
{
  "predicted_demand_kw": 58.2,
  "capacity_kw": 60,
  "risk_level": "HIGH",
  "prediction_horizon_minutes": 60
}
```

---

# 50. Alerts

```text
GET   /api/v1/alerts
PATCH /api/v1/alerts/{id}/acknowledge
```

---

# 51. Simulation

Endpoints administrativos opcionais:

```text
GET  /api/v1/simulation/status
POST /api/v1/simulation/start
POST /api/v1/simulation/stop
POST /api/v1/simulation/reset
```

São úteis principalmente para a demonstração.

---

# 52. Dashboard Administrativo

O frontend deverá possuir uma tela principal contendo:

### KPIs

```text
Demanda atual
Limite da rede
Energia solar atual
Energia da rede
Sessões ativas
Faturamento
CO₂ evitado
Risco de pico
```

### Visualizações

* demanda ao longo do tempo;
* solar vs rede;
* sessões;
* faturamento;
* histórico;
* alertas.

---

# 53. Dashboard do Usuário

Deverá conter:

### Sessão atual

```text
status
charger
vehicle
duration
power
energy
solar percentage
cost
```

### Histórico

Lista de sessões anteriores.

---

# 54. Seeds

O projeto deverá possuir dados de demonstração reproduzíveis.

Seed inicial:

```text
1 administrador
4 usuários
4 veículos
1 estação
4 carregadores
1 tarifa
configuração ESG
```

Carregadores:

```text
CH-01 → 22 kW
CH-02 → 22 kW
CH-03 → 22 kW
CH-04 → 22 kW
```

Estação:

```text
grid_limit_kw = 60
```

Esses valores deverão permitir demonstrar o Golden Path.

---

# 55. Cenário Oficial de Demonstração

Preparar cenário reproduzível em que:

```text
CH-01 solicita 20 kW
CH-02 solicita 20 kW
CH-03 solicita 20 kW
```

Depois:

```text
CH-04 solicita 20 kW
```

Sem energia solar:

```text
4 × 15 kW = 60 kW
```

Com:

```text
solar_available_kw = 20
grid_limit_kw = 60
```

a instalação poderá atender até:

```text
80 kW
```

desde que respeitados os limites individuais dos carregadores e veículos.

O dashboard deverá mostrar separadamente solar e rede.

---

# 56. Critérios de Aceite — Demand Management

Dado:

```text
grid_limit_kw = 60
solar_available_kw = 0
```

e quatro sessões solicitando:

```text
20 kW cada
```

quando a política de alocação for executada,

então:

```text
cada sessão recebe 15 kW
```

e:

```text
total_grid_power_kw = 60
```

---

# 57. Critério de Aceite — Limite Individual

Dado:

```text
charger.max_power_kw = 22
vehicle.max_charge_power_kw = 11
```

então:

```text
requested_power_kw <= 11
```

---

# 58. Critério de Aceite — Solar

Dado:

```text
total_allocated = 40 kW
solar_available = 25 kW
```

então:

```text
solar_used = 25 kW
grid_used = 15 kW
```

---

# 59. Critério de Aceite — Billing

Dado:

```text
energy_consumed = 25 kWh
tariff = R$ 0,92/kWh
```

então:

```text
total = R$ 23,00
```

considerando arredondamento monetário apropriado.

---

# 60. Critério de Aceite — Energia

Para cada sessão concluída:

```text
energy_consumed_kwh
≈
solar_energy_kwh + grid_energy_kwh
```

---

# 61. Critério de Aceite — Sessão

Quando uma sessão é encerrada:

```text
session.status = COMPLETED
charger.status = AVAILABLE
invoice.status = CLOSED
```

---

# 62. Critério de Aceite — ML

O pipeline deverá:

1. carregar dataset;
2. separar treino e teste temporalmente;
3. calcular baseline;
4. treinar modelo;
5. calcular métricas;
6. persistir modelo;
7. carregar modelo na aplicação;
8. produzir previsão.

Uma execução de treinamento não poderá ser considerada concluída sem métricas.

---

# 63. Testes Obrigatórios

Cobertura deverá priorizar regras críticas.

## Backend

Testar:

* cálculo de requested power;
* algoritmo de alocação;
* invariantes energéticas;
* prioridade solar;
* cálculo de energia;
* billing;
* transições de sessão;
* classificação de risco;
* principais endpoints.

## Frontend

Testar pelo menos:

* componentes críticos;
* renderização dos estados;
* tratamento de erros;
* fluxo básico de sessão quando adequado.

---

# 64. Requisitos Não Funcionais

A aplicação deverá possuir:

* tipagem;
* validação de entrada;
* migrations;
* tratamento de erros;
* logs;
* variáveis de ambiente;
* `.env.example`;
* API OpenAPI;
* dados seed;
* testes automatizados;
* Docker Compose;
* documentação de execução.

---

# 65. Segurança Básica

Não deverão ser commitados:

* senhas;
* tokens;
* chaves;
* secrets;
* `.env`.

Senhas deverão ser armazenadas somente como hashes.

A validação de autorização deverá ocorrer no backend.

---

# 66. Tratamento de Erros

A API deverá utilizar erros HTTP semanticamente adequados.

Exemplos:

```text
400 → requisição inválida
401 → não autenticado
403 → sem permissão
404 → recurso inexistente
409 → conflito de estado
422 → validação
500 → erro inesperado
```

Erros internos não deverão expor stack traces ao cliente.

---

# 67. Logging

Registrar eventos relevantes, incluindo:

* startup;
* shutdown;
* início de sessão;
* término de sessão;
* falhas;
* execução do simulador;
* treinamento ML;
* erros de integração.

Não registrar senhas ou tokens.

---

# 68. Banco de Dados

Alterações de schema deverão utilizar Alembic.

Não alterar banco manualmente como método de desenvolvimento normal.

---

# 69. Definition of Done

Uma funcionalidade somente será considerada concluída quando:

1. requisito estiver implementado;
2. regra de negócio estiver correta;
3. persistência estiver correta quando aplicável;
4. API estiver integrada quando aplicável;
5. frontend estiver integrado quando aplicável;
6. testes relevantes existirem;
7. testes existentes continuarem passando;
8. lint/type-check aplicável estiver passando;
9. documentação necessária estiver atualizada;
10. não houver secrets adicionados ao repositório.

---

# 70. Ordem de Implementação

A implementação deverá privilegiar **vertical slices**.

Ordem recomendada:

```text
1. Scaffold
2. Database
3. Users/Auth
4. Stations/Chargers
5. Vehicles
6. Sessions
7. Energy Simulator
8. Demand Management
9. Solar
10. Billing
11. Dashboard
12. Alerts
13. ESG
14. Dataset
15. ML
16. Prediction UI
17. Polish
```

Não construir todas as telas antes das regras principais funcionarem.

---

# 71. Prioridade Arquitetural

Priorizar:

```text
Correctness
↓
Simplicity
↓
Testability
↓
Maintainability
↓
Performance optimization
```

O projeto não possui requisitos que justifiquem otimizações prematuras.

---

# 72. Regra contra Overengineering

Não adicionar tecnologias apenas porque seriam comuns em sistemas empresariais.

Particularmente, não introduzir sem requisito explícito:

```text
Redis
Celery
Kafka
RabbitMQ
GraphQL
Kubernetes
microservices
event sourcing
CQRS
Terraform
LLMs
vector databases
```

---

# 73. Integração Futura

O simulador deverá ser projetado atrás de interfaces ou serviços claros.

Exemplo conceitual:

```text
EnergyDataProvider
```

Hoje:

```text
SimulationEnergyDataProvider
```

Futuramente:

```text
OcppEnergyDataProvider
ModbusEnergyDataProvider
```

Não é necessário implementar os providers futuros.

O objetivo é apenas evitar acoplamento desnecessário.

---

# 74. Princípio Final

O sistema deve favorecer uma demonstração integrada e confiável.

Quando houver conflito entre:

```text
sofisticação
vs
funcionalidade demonstrável
```

escolher:

> **funcionalidade demonstrável.**
