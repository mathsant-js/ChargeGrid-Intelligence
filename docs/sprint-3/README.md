# Sprint 3 — demonstração reproduzível

**Equipe:** Equipe 3 (FIAP × GoodWe)  
**Disciplina:** Pensamento Computacional e Automação com Python

**Integrantes:**

- Bernardo Zauza Amorim
- Bruno Almeida de Oliveira
- Gabriel Góes Nunes Pereira
- Guilherme Vinciguerra Carvalho
- Marcos Peterson Martins Pereira
- Matheus Jorge Santana

Este roteiro demonstra, por simulação, o cenário energético de `SPEC.md` §§ 54–55 e o Golden Path consultivo de ML. As leituras solares, energia, billing e previsão são simulados; não representam medições físicas.

## Arquitetura e escolhas

- [Arquitetura executada em PNG](diagrams/architecture.png) ([fonte Mermaid](architecture.mmd)) e [sequência da demo em PNG](diagrams/sequence.png) ([fonte Mermaid](sequence.mmd)) representam o fluxo conferido contra a API.
- O monólito modular usa React, FastAPI, SQLAlchemy e PostgreSQL. O controlador de simulação recebe ticks manuais; `SimulationEnergyDataProvider` fornece a curva solar UTC. O alocador Equal Share respeita os limites de rede, carregador e veículo. A API calcula billing e analytics.
- A simulação não possui controle físico ou OCPP/Modbus. O preparo de ML é separado do seed de domínio; o script orquestra a inferência por endpoint público.

## Reprodução em banco de demo limpo

Use um banco isolado e um único processo controlador da API. Edite `.env` localmente para definir `APP_ENV=demo`, `DEMO_SIMULATION_START_UTC=2026-09-18T11:58:00Z` e `GRID_EMISSION_FACTOR_KG_PER_KWH=0.4`. O relógio determinístico só é aceito quando `APP_ENV=demo` (ou no ambiente isolado da suíte); desenvolvimento comum, staging e produção rejeitam essa configuração. O horário é deliberadamente próximo do pico solar UTC. O fator da API vem dessa variável de ambiente; o seed registra o mesmo 0,4 em `SystemConfiguration`. Guarde `DEMO_ADMIN_PASSWORD` e `DEMO_USER_PASSWORD` somente no ambiente, com pelo menos oito caracteres cada.

```bash
cp .env.example .env
# edite .env conforme acima; não a adicione ao Git
read -rsp 'Senha ADMIN da demo: ' DEMO_ADMIN_PASSWORD; echo
read -rsp 'Senha USER da demo: ' DEMO_USER_PASSWORD; echo
export DEMO_ADMIN_PASSWORD DEMO_USER_PASSWORD
docker compose up -d db
docker compose run --rm backend alembic upgrade head
docker compose run --rm -e DEMO_ADMIN_PASSWORD -e DEMO_USER_PASSWORD backend python -m app.demo_seed
docker compose run --rm backend python -m app.ml.demo_prepare --demo-start 2026-09-18T11:58:00+00:00
docker compose up --build --wait -d backend frontend
DEMO_ADMIN_PASSWORD="$DEMO_ADMIN_PASSWORD" DEMO_USER_PASSWORD="$DEMO_USER_PASSWORD" python3 scripts/sprint3_demo.py | tee /tmp/chargegrid-sprint3-evidence.txt
```

O seed aceita reexecução sem duplicar entidades. O roteiro exige banco limpo e sessão de simulação parada, pois cria sessões e leituras novas. O relógio configurado é opt-in e só vale em `demo`/`test`; sem ele, inicia no horário atual. A suíte força seu próprio ambiente de teste e ignora um relógio de demo presente no `.env`, portanto `make check` não exige limpar a variável manualmente. Reinicie a API após mudar `.env`.

Confira os [resultados do ensaio](EVIDENCE.md). Além do fluxo energético, o roteiro chama `POST /api/v1/predictions/demand/run` e exige capacidade de 80 kW, horizonte de 60 minutos, risco `HIGH`, recomendação e alerta `PEAK_RISK` com thresholds 0,70/0,90. Ele compara as leituras antes/depois para provar que a previsão não altera a alocação.

Abra [OpenAPI](http://localhost:8000/docs), [dashboard administrativo](http://localhost:5173/admin) e [dashboard do usuário](http://localhost:5173/user). Entre com as contas `sprint3-admin@demo.invalid` e `sprint3-user-4@demo.invalid`; ambas usam as senhas definidas no ambiente. Atualize manualmente as telas após o roteiro. Capture prints da API, gráficos, histórico, alerta, invoice e sustentabilidade para o PDF/vídeo. Ainda não há prints versionados, pois dependem do ensaio visual no ambiente de entrega.

## Roteiro do vídeo (até cinco minutos)

1. Mostrar a arquitetura e explicar tick manual e solar simulada.
2. Iniciar três sessões e mostrar 3 × 20 kW.
3. Iniciar a quarta e mostrar o rateio 4 × 15 kW, limitado a 60 kW da rede.
4. Configurar 20 kW de pico solar pela API e mostrar o terceiro tick de cerca de 80 kW.
5. Mostrar leituras, alerta e dashboards atualizados.
6. Mostrar demanda prevista, capacidade, horizonte de 60 minutos, risco `HIGH`, recomendação e `PEAK_RISK`.
7. Encerrar a quarta sessão, mostrar invoice, tarifa e CO₂ evitado.
8. Explicar que o modelo é consultivo e que o baseline venceu o ensaio documentado.

Esta entrega do EV Challenge 2026 aplica Pensamento Computacional e Automação com Python à modelagem do cenário, ao controlador de simulação, ao seed reproduzível, à orquestração das chamadas HTTP e à validação automática dos limites energéticos. Inclua as evidências visuais capturadas antes da apresentação.
