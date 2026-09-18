# Fase 6 — Contratos da API de analytics

`GET /api/v1/analytics/dashboard` e `GET /api/v1/analytics/sustainability` exigem JWT. ADMIN consulta todas as sessões; USER consulta somente as próprias. O filtro `user_id` é permitido para ADMIN e para o próprio USER; outro ID retorna 404. `station_id` limita os dados aos carregadores da estação indicada. IDs válidos sem registros retornam indicadores zerados.

Ambas as rotas aceitam `station_id`, `user_id`, `from` e `to`. Datas devem incluir fuso horário; os limites são inclusivos e `from` não pode ser posterior a `to` (422). Sem filtros de data, usa-se todo o histórico.

## Dashboard

Retorna `station_id`, `user_id`, `session_count`, `completed_session_count`, `energy_consumed_kwh`, `solar_energy_kwh`, `grid_energy_kwh`, `billed_total` e `currency` (`BRL`). As três energias são somas das `EnergyReading` persistidas, sem somar novamente os acumuladores da sessão. O período filtra as leituras por `timestamp`, as sessões iniciadas por `started_at`, as concluídas por `ended_at` e as invoices `CLOSED` por `closed_at`. `billed_total` usa `Invoice.total`, sem recalcular pela tarifa atual. Uma sessão sem leitura não acrescenta energia. Invoices abertas ou canceladas não entram no faturamento.

## Sustentabilidade

Retorna os filtros efetivos, as três energias, `solar_percentage`, `avoided_co2_kg`, `grid_emission_factor_kg_per_kwh`, `estimated_solar_savings` e `currency` (`BRL`). O percentual é `solar_energy_kwh / energy_consumed_kwh × 100`, ou zero quando o consumo é zero. CO₂ evitado é energia solar vezes `GRID_EMISSION_FACTOR_KG_PER_KWH`; a configuração tem padrão explícito `0.0` e deve ser definida para obter um indicador de CO₂ diferente de zero. A economia estimada soma a energia solar de cada leitura multiplicada pela tarifa capturada na respectiva sessão; o total é arredondado para centavos. É uma estimativa teórica da compra evitada da rede, não economia financeira real.

As respostas não incluem previsões de demanda, classificação de pico nem séries derivadas de ML.

## Dashboard do usuário

`GET /api/v1/user/dashboard` exige JWT de perfil USER e retorna a sessão atual, o histórico de sessões encerradas e as invoices do usuário autenticado. O servidor filtra sessões e invoices pelo ID do token; não aceita ID de usuário por parâmetro. Veículo e carregador são apresentados pelo nome. A duração considera o horário atual para sessões em andamento e `ended_at` para sessões encerradas. O percentual solar usa os acumuladores da sessão e é zero quando a energia consumida é zero.

`estimated_cost` aparece somente na sessão em andamento e usa a energia acumulada multiplicada pela tarifa capturada no início da sessão, com arredondamento para centavos. `invoice_total` aparece somente quando há invoice fechada e é a fonte do custo final. A interface identifica explicitamente o valor durante a recarga como estimativa.
