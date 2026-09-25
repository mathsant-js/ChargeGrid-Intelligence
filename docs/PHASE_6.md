# Fase 6 — Integração e limites

**Estado histórico da entrega:** concluída quanto a dashboards e integração;
o risco de pico, então dependente da Fase 7, foi posteriormente implementado e
validado. Consulte `PHASE_7.md` e `PHASE_9.md` para o estado final do MVP.

## Entregue

- Dashboard administrativo com filtros de estação e período, KPIs de demanda,
  rede, solar, sessões, faturamento e CO₂, gráficos, histórico e alertas.
  Leituras das sessões no mesmo instante são somadas nos gráficos para mostrar
  a demanda e a divisão solar/rede da instalação por tick.
- Dashboard do usuário com sessão atual, estimativa durante a recarga, histórico
  e invoices fechadas, restritos ao usuário autenticado.
- APIs de analytics e sustentabilidade descritas em
  [PHASE_6_ANALYTICS.md](PHASE_6_ANALYTICS.md).
- Alerta `HIGH_DEMAND` por episódio de importação elevada e
  `SESSION_FINISHED` no encerramento; reconhecimento administrativo pela API.

## Cenário integrado executado

`backend/tests/test_phase_6_flow.py` usa os endpoints públicos e um relógio
simulado fixo. Três sessões de 20 kW fazem um tick sem solar: 60 kW da rede e
um alerta `HIGH_DEMAND`. A quarta sessão começa e outro tick sem solar
redistribui a potência para 15 kW por sessão. A disponibilidade solar é então
configurada para 20 kW e o terceiro tick aloca 20 kW por sessão: 80 kW ao
todo, cerca de 20 kW solares e 60 kW da rede. A soma de energia nos três ticks
é cerca de 3,333 kWh. Ao encerrar a quarta sessão, o carregador fica
disponível, a invoice `CLOSED` é de R$ 0,54 e os dashboards passam a mostrar
uma sessão concluída, o faturamento e o histórico do usuário. A API de
sustentabilidade retorna a fração solar e o CO₂ evitado com fator de emissão
configurado em 0,4 kg/kWh para o teste.

## Limites no momento desta fase

- O KPI de risco de pico só aparece quando há uma previsão futura válida para
  a estação. O pipeline que produz previsões e classificações é trabalho da
  Fase 7; por isso o Golden Path completo ainda não foi demonstrado.
- Os ticks são acionados manualmente por `POST /api/v1/simulation/ticks`.
- O cenário acima é reproduzível como teste automatizado; não há seed oficial
  nem roteiro operacional pronto para uma demonstração manual completa.
- Os filtros de período aplicam-se às séries e indicadores da API; as listas de
  sessões e alertas da tela administrativa ainda são históricas.

## Validação

O teste integrado e os testes de interface cobrem o fluxo e a agregação dos
gráficos. `make check` verifica lint, tipos, testes e build. A geração de
`/openapi.json` é testada. Não houve alteração de schema nesta integração,
portanto não foi criada migration.
