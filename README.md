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

## Estado atual

As Fases 1 (fundação), 2 (domínio), 3 (simulação e leituras), 4 (gestão
energética) e 5 (billing e histórico de invoices) estão concluídas, com
critérios de saída e evidências documentados. As migrations das Fases 3 e 5
foram validadas online em PostgreSQL. O backend entrega
Users/Auth, Vehicles, Stations, Chargers e Sessions sob `/api/v1`, com JWT,
autorização por papel e propriedade, persistência
via Alembic e regras de início/encerramento de sessão na camada de serviço.

A Fase 3 contém relógio determinístico, provedor solar e o serviço
`app.simulation.tick.execute_tick`. O serviço recebe uma resolução de potência
injetável por estação, valida os limites físicos e persiste as leituras e os
acumuladores em uma transação. O controle ADMIN em `/api/v1/simulation` expõe
status, start, stop, reset e um tick manual (`POST /ticks`), sem loop automático.
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
transação das leituras. O tick ainda não atualiza analytics derivados.

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
