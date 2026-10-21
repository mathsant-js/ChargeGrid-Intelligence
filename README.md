# ChargeGrid Intelligence

Plataforma acadêmica para simular e gerenciar uma infraestrutura de recarga de
veículos elétricos com controle energético, energia solar, billing, analytics e
previsão consultiva de demanda.

O projeto é um **monólito modular** com FastAPI, React e PostgreSQL. O
[`SPEC.md`](SPEC.md) é a fonte de verdade dos requisitos; este README e a
[`arquitetura vigente`](docs/ARCHITECTURE.md) descrevem o estado implementado.
Os documentos `PHASE_*` e da Sprint 3 são registros históricos e não devem ser
usados isoladamente como manual operacional.

## Caminho recomendado

Para preparar e executar a demonstração completa a partir de uma instalação
limpa, use:

```bash
make mvp-smoke
```

Esse comando cria um projeto Docker Compose isolado, aplica as migrations,
carrega o seed, prepara o modelo de ML, inicia backend e frontend, executa o
Golden Path pela API pública e remove os containers e volumes temporários. Ele
não altera o volume `postgres_data` do ambiente de desenvolvimento. Requisitos,
portas alternativas e solução de problemas estão no
[`guia vigente da demo`](docs/MVP_DELIVERY_SMOKE_TEST.md).

Use o roteiro manual da
[`entrega da Sprint 3`](docs/sprint-3/README.md) somente quando precisar manter
as telas abertas para apresentação ou capturar evidências. Ele é preservado
como material histórico, mas recebeu uma indicação clara de quais instruções
continuam válidas.

## Execução de desenvolvimento

Pré-requisitos: Docker com Docker Compose. Para iniciar o ambiente persistente:

```bash
cp .env.example .env
docker compose up --build
```

Serviços disponíveis:

- frontend: <http://localhost:5173>;
- API/health: <http://localhost:8000/api/v1/health>;
- OpenAPI: <http://localhost:8000/docs>;
- PostgreSQL: `localhost:5432`.

O frontend usa `VITE_API_URL`, por padrão
`http://localhost:8000/api/v1`. As rotas `/admin` e `/user` exigem contas com o
papel correspondente. O ambiente comum não cria contas automaticamente; para
dados demonstrativos, siga o guia da demo em vez de executar apenas
`docker compose up`.

Para aplicar migrations manualmente:

```bash
docker compose run --rm backend alembic upgrade head
```

### Execução sem Docker

Requer Python 3.12, Node.js 22+ e PostgreSQL 16.

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload
```

Em outro terminal:

```bash
cd frontend
npm ci
npm run dev
```

## Validação

```bash
make install  # primeira execução local
make check
```

`make check` executa lint, tipos e testes do backend, além de lint, tipos,
testes e build do frontend. `make mvp-smoke` acrescenta a validação integrada
em PostgreSQL 16. Não confunda resultados datados nos documentos de fase com
uma execução atual; somente comandos executados no checkout presente confirmam
o estado atual.

## Estado funcional atual

O MVP implementa autenticação e autorização, veículos, estações, carregadores,
sessões, simulação automática e ticks manuais, alocação Equal Share com limites
físicos e prioridade solar, leituras energéticas, billing, dashboards,
indicadores ESG, alertas e previsão consultiva de demanda. Todas as rotas
públicas pertencem a `/api/v1`.

A previsão de ML não controla a alocação de potência. A simulação, billing e
energia solar são demonstrativos; não há integração com hardware, pagamento
real, OCPP ou Modbus. Consulte a
[`arquitetura vigente`](docs/ARCHITECTURE.md) para responsabilidades, fluxo e
limites.

## Mapa da documentação

A classificação completa está em [`docs/README.md`](docs/README.md).

### Vigente

- [`SPEC.md`](SPEC.md): requisitos e regras de negócio, fonte de verdade;
- [`BRIEFING.md`](BRIEFING.md): contexto do produto, subordinado ao SPEC;
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): arquitetura implementada;
- [`docs/MVP_DELIVERY_SMOKE_TEST.md`](docs/MVP_DELIVERY_SMOKE_TEST.md): preparo,
  execução e diagnóstico da demo atual;
- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md): fluxo de desenvolvimento;
- [`docs/ML_EVALUATION.md`](docs/ML_EVALUATION.md): método e limites da avaliação
  de ML.

### Histórico e evidências

- [`docs/PHASE_1.md`](docs/PHASE_1.md) a
  [`docs/PHASE_9.md`](docs/PHASE_9.md): decisões, aceites e resultados de cada
  fase no momento em que foram registrados;
- [`docs/SPRINT_3_PLAN.md`](docs/SPRINT_3_PLAN.md): plano anterior à entrega;
- [`docs/sprint-3/README.md`](docs/sprint-3/README.md): material e roteiro manual
  da Sprint 3;
- [`docs/sprint-3/EVIDENCE.md`](docs/sprint-3/EVIDENCE.md): evidências datadas;
- [documento da Sprint 3 em PDF](output/pdf/chargegrid_sprint_3.pdf),
  [fonte Markdown](docs/sprint-3/chargegrid_sprint_3.md) e
  [vídeo pitch](video_editado/Pitch_challenge_sprint3.mp4).

Os registros históricos são mantidos para rastreabilidade. Quando divergirem
do código ou da documentação vigente, prevalece a ordem definida em
[`AGENTS.md`](AGENTS.md): `SPEC.md` > `BRIEFING.md` > `README.md` > implementação
existente.
