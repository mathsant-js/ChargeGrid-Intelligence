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

## Estado atual

As Fases 1 (fundação), 2 (domínio), 3 (simulação e leituras) e 4 (gestão energética)
estão concluídas, com critérios de saída e evidências documentados. As migrations
da Fase 3 foram validadas online em PostgreSQL. O backend entrega
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
Esta etapa ainda não gera alertas nem atualiza analytics derivados por tick.

Cada estação processada recebe uma `SolarReading` única por timestamp simulado;
cada sessão recebe uma `EnergyReading` única por timestamp. Uma reexecução no
mesmo instante ignora estações já concluídas. Constraints no banco impedem
duplicatas mesmo em escrita concorrente, e uma falha desfaz todo o tick. O
relógio avança apenas depois do commit. O chamador deve passar uma sessão de
banco sem transação ativa e um relógio iniciado; em caso de erro pode repetir
o mesmo tick após corrigir a causa.
