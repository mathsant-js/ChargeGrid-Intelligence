# ChargeGrid Intelligence

Plataforma acadêmica para simular e gerenciar uma infraestrutura de recarga de veículos elétricos com controle energético, energia solar, billing, analytics e previsão de demanda.

O projeto usa um **monólito modular**: uma API FastAPI, uma aplicação React e PostgreSQL. A especificação técnica é a fonte de verdade da implementação.

## Pré-requisitos

- Docker com Docker Compose (caminho recomendado); ou
- Python 3.12, Node.js 22+ e PostgreSQL 16 para execução local.

## Início rápido com Docker

```bash
cp .env.example .env
docker compose up --build
```

Serviços:

- frontend: <http://localhost:5173>

O frontend usa `VITE_API_URL` (padrão: `http://localhost:8000/api/v1`). Entre com uma conta existente da API. O token é mantido no armazenamento local do navegador e validado em `/auth/me` ao recarregar; “Sair” ou uma resposta 401 remove a sessão. As rotas `/admin` e `/user` exigem o perfil correspondente.

Em `/admin`, o gestor pode filtrar o dashboard por estação e período, consultar indicadores, gráficos, histórico e alertas, e reconhecer alertas pela API. A previsão e o risco de pico aparecem somente para uma estação com previsão futura válida; na ausência de dados de ML, a tela mostra um estado informativo.
Em `/user`, o usuário consulta a recarga atual, o histórico de sessões e as invoices. O custo durante a recarga é uma estimativa; o valor fechado vem da invoice. Os dados são limitados ao usuário autenticado pela API.
- API: <http://localhost:8000/api/v1/health>
- OpenAPI: <http://localhost:8000/docs>
- PostgreSQL: `localhost:5432`

Para aplicar migrations manualmente:

```bash
docker compose run --rm backend alembic upgrade head
```

## Desenvolvimento local

Backend:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

## Qualidade

```bash
make install # primeira execução
make check
```

O alvo executa testes, lint e verificação de tipos no backend e no frontend, além do build web. Consulte [CONTRIBUTING.md](docs/CONTRIBUTING.md) para o fluxo detalhado.

## Demo da Sprint 3

Execute o [roteiro reproduzível da Sprint 3](docs/sprint-3/README.md) em um banco isolado. Ele inclui comandos de seed, configuração UTC, cenário por endpoints públicos e resultados esperados.

### Documento da Sprint 3 em PDF

Acesse o [documento da Sprint 3 em PDF](output/pdf/chargegrid_sprint_3.pdf).

### Documento da Sprint 3 em Markdown

Acesse o [documento da Sprint 3 em Markdown](docs/sprint-3/chargegrid_sprint_3.md).

### Vídeo pitch da Sprint 3 em MP4

Acesse o [arquivo MP4 do vídeo pitch da Sprint 3](video_editado/Pitch_challenge_sprint3.mp4).

### Vídeo pitch da Sprint 3 no YouTube

Assista ao [vídeo pitch da Sprint 3 no YouTube](https://youtu.be/caGX1bfDN7s).

Após configurar `.env` com `APP_ENV=demo` e
`DEMO_SIMULATION_START_UTC=2026-09-18T11:58:00Z`, exporte as duas senhas e siga
esta ordem a partir de um volume PostgreSQL novo:

```bash
docker compose up -d db
docker compose run --rm backend alembic upgrade head
docker compose run --rm -e DEMO_ADMIN_PASSWORD -e DEMO_USER_PASSWORD backend python -m app.demo_seed
docker compose run --rm backend python -m app.ml.demo_prepare \
  --demo-start 2026-09-18T11:58:00+00:00
docker compose up --build --wait -d backend frontend
python3 scripts/sprint3_demo.py
```

O preparo de ML gera 90 dias determinísticos (seed 42), aplica split temporal
com uma lacuna de 60 minutos, avalia baseline e Random Forest, persiste o
artefato e cria somente o histórico causal explicitado para a demo. O roteiro
chama `POST /api/v1/predictions/demand/run`, mostra demanda prevista,
capacidade, horizonte, risco e recomendação e confirma `PEAK_RISK` em `HIGH`
sem alterar os thresholds oficiais ou a alocação de potência.

## Documentação

- [Briefing](BRIEFING.md)
- [Especificação técnica](SPEC.md)
- [Instruções para agentes](AGENTS.md)
- [Arquitetura](docs/ARCHITECTURE.md)
- [Fase 1 — Fundação (concluída)](docs/PHASE_1.md)
- [Fase 2 — Domínio (concluída)](docs/PHASE_2.md)
- [Fase 3 — Simulação e leituras (concluída)](docs/PHASE_3.md)
- [Fase 4 — Gestão energética (concluída)](docs/PHASE_4.md)
- [Fase 5 — Billing e histórico de invoices (concluída)](docs/PHASE_5.md)
- [Fase 6 — Contratos da API de analytics](docs/PHASE_6_ANALYTICS.md)
- [Fase 6 — Integração e limites](docs/PHASE_6.md)
- [Fase 7 — ML, treinamento e inferência](docs/PHASE_7.md)
- [Fase 8 — ESG e alertas](docs/PHASE_8.md)
- [Fase 9 — Auditoria final do MVP](docs/PHASE_9.md)

## Estado atual

As Fases 1 a 9 do MVP foram implementadas e auditadas, com limitações e
resultados de comandos registrados em [docs/PHASE_9.md](docs/PHASE_9.md).
As migrations foram validadas em PostgreSQL 16. O backend entrega
Users/Auth, Vehicles, Stations, Chargers e Sessions sob `/api/v1`, com JWT,
autorização por papel e propriedade, persistência
via Alembic e regras de início/encerramento de sessão na camada de serviço.

A Fase 3 contém relógio determinístico, provedor solar e o serviço
`app.simulation.tick.execute_tick`. O serviço recebe uma resolução de potência
injetável por estação, valida os limites físicos e persiste as leituras e os
acumuladores em uma transação. O controle ADMIN em `/api/v1/simulation` expõe
status, start, stop, reset e um tick manual (`POST /ticks`). `POST /start`
também inicia um runner assíncrono no lifecycle do FastAPI, que executa um tick
por intervalo real do relógio (um segundo por padrão); `POST /stop` cancela e
aguarda esse runner. O tick manual permanece disponível para testes e
demonstrações controladas.
O controle de simulação usa a política Equal Share Allocation V1 da Fase 4:
divide a capacidade da rede mais a geração solar entre sessões `CHARGING` de
cada estação, respeita pedido, carregador e veículo, e redistribui sobras.
A potência solar disponível cobre primeiro a demanda alocada e é rateada
proporcionalmente; a parcela restante vem da rede, limitada por estação.
Cada tick corresponde à duração configurada do relógio (60 segundos simulados
por padrão), calcula energia em kWh e atualiza os acumuladores das sessões.
O tick também cria `HIGH_DEMAND` quando a importação da rede atinge o limiar
configurado em `SystemConfiguration` (0,85 na ausência de configuração). O
alerta é emitido uma vez por episódio de alta demanda e participa da mesma
transação das leituras. Analytics e dashboards consultam as leituras persistidas.

Cada estação processada recebe uma `SolarReading` única por timestamp simulado;
cada sessão recebe uma `EnergyReading` única por timestamp. Uma reexecução no
mesmo instante ignora estações já concluídas. Constraints no banco impedem
duplicatas mesmo em escrita concorrente, e uma falha desfaz todo o tick. O
relógio avança apenas depois do commit. O chamador deve passar uma sessão de
banco sem transação ativa e um relógio iniciado; em caso de erro pode repetir
o mesmo tick após corrigir a causa.

Na Fase 5, a sessão captura a tarifa ativa válida no início. Ao encerrar, o
backend calcula o custo Pay-per-Use, cria uma invoice `CLOSED` e registra um
alerta na mesma transação. O histórico de invoices está disponível em
`GET /api/v1/billing/invoices` e `GET /api/v1/billing/invoices/{invoice_id}`,
com acesso restrito às próprias invoices para usuários comuns. Consulte
[a validação da Fase 5](docs/PHASE_5.md) para os critérios de aceite e testes.
Listagem e reconhecimento de alertas em `/api/v1/alerts` exigem papel ADMIN.

A integração da Fase 6 cobre os dashboards administrativo e do usuário, os
gráficos de demanda/solar/rede e faturamento, alertas e os indicadores de
sustentabilidade. Um teste integrado percorre início de sessões, três ticks,
redistribuição de potência, prioridade solar, alerta, encerramento, invoice e
atualização das respostas dos dashboards. Os gráficos do gestor somam leituras
simultâneas para mostrar a demanda total de cada tick. Veja os resultados e
limites em [docs/PHASE_6.md](docs/PHASE_6.md).

A Fase 7 disponibiliza inferência administrativa explícita em
`POST /api/v1/predictions/demand/run`. Ela carrega o artefato configurado em
`DEMAND_MODEL_PATH`, monta features apenas com leituras já disponíveis,
persiste a previsão de 60 minutos, classifica o risco com os thresholds de
`SystemConfiguration` e cria `PEAK_RISK` uma vez por episódio `HIGH`. A
previsão é estritamente consultiva e não altera a alocação energética. Consulte
[docs/PHASE_7.md](docs/PHASE_7.md) para preparo do modelo, pré-condições e
respostas de erro. O simulador executa ticks automaticamente enquanto RUNNING,
sem deixar de aceitar ticks manuais pela API.
