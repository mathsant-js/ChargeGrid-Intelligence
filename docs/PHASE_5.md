# Fase 5 — Billing e histórico de invoices

## Escopo e critérios

Revisão final feita contra `SPEC.md` (tarifa, invoice, cobrança Pay-per-Use,
fechamento e critérios de aceite 59–61) e `BRIEFING.md` (Fase 5: tarifas,
custo, invoices e histórico). O billing é simulado, sem processamento de
pagamento. A interface de dashboards pertence à Fase 6.

## Comportamento entregue

Ao encerrar uma sessão, o backend calcula `energy_kwh × tariff_per_kwh`,
arredonda o total para centavos e cria uma invoice `CLOSED` na mesma transação.
A invoice guarda energia, tarifa aplicada, subtotal, total e datas do fechamento.
Esses valores são registros históricos: alterar a tarifa posteriormente não
recalcula invoices existentes.

O início exige uma tarifa ativa válida no instante real de abertura da sessão;
a sessão guarda o preço selecionado. A migration `20260916_0011` desativa
tarifas ativas antigas, mantendo a mais recente por `valid_from`, `created_at`
e `id`, e cria um índice único para permitir no máximo uma tarifa ativa. Nesta
revisão, a atualização foi expressa em SQL para funcionar também na geração
offline do Alembic.

`GET /api/v1/billing/invoices` lista invoices por `created_at` e `id`, em ordem
crescente estável. Aceita os filtros opcionais `user_id` (UUID) e `status`
(`OPEN`, `CLOSED` ou `CANCELLED`), que podem ser combinados. Uma lista sem
resultados retorna `[]`. `GET /api/v1/billing/invoices/{invoice_id}` retorna a
invoice solicitada ou 404 se ela não existir ou não estiver visível.

Ambos os endpoints exigem bearer token (401 quando ausente ou inválido). ADMIN
pode listar e consultar qualquer invoice. USER vê apenas as próprias; um filtro
`user_id` de outra pessoa retorna 404, assim como o acesso por ID a uma invoice
alheia. O filtro pelo próprio ID é permitido.

## Fluxo integrado executado

O teste `test_phase_5_session_ticks_close_and_invoice_history` cria usuário,
veículo, estação e carregador; usa a tarifa ativa válida de R$ 0,92/kWh;
inicia a sessão; executa três ticks de 60 segundos a 11 kW; encerra a sessão;
e consulta a invoice pela listagem e por ID. As três leituras somam 0,55 kWh,
com parcelas solar e da rede positivas cuja soma corresponde ao total. A
sessão termina `COMPLETED`, com potência alocada zero e `total_cost` de
R$ 0,51. O carregador volta a `AVAILABLE`. A única invoice da sessão fica
`CLOSED`, registra 0,5500 kWh e R$ 0,9200/kWh, com subtotal e total de
R$ 0,51 (`0,55 × 0,92`, arredondado para centavos).

## Validação e comandos executados

Os testes cobrem autorização por papel e propriedade, 401, 404, filtros,
ordenação com timestamps iguais e preservação dos valores históricos após
alteração da tarifa. O OpenAPI declara autenticação e respostas de erro para
ambos os endpoints, além dos parâmetros de filtro.

Em 16/09/2026, em `backend/`, foram executados:

```text
.venv/bin/pytest -q tests/test_simulation_api.py::test_phase_5_session_ticks_close_and_invoice_history  # 1 passou
.venv/bin/pytest -q --no-cov                                                       # 166 passaram
.venv/bin/ruff check .                                                             # passou
.venv/bin/mypy app                                                                  # passou, 62 arquivos
.venv/bin/alembic heads                                                             # 20260916_0011 (head)
.venv/bin/alembic upgrade head --sql                                                # passou após correção
```

Um PostgreSQL 16 temporário e isolado recebeu `alembic upgrade head` até
`20260916_0011`; `alembic current` confirmou o head e `alembic check` não
encontrou operações pendentes. Depois de `alembic downgrade 20260916_0010`,
foram inseridas duas tarifas ativas legadas e executado novamente
`alembic upgrade head`: a tarifa mais recente ficou ativa, a antiga foi
desativada e o índice `uq_tariffs_one_active` foi criado. O contêiner foi
removido após a validação. `git diff --check` passou.

## Limitações concretas

O fluxo integrado de API foi executado com SQLite em memória, como os demais
testes backend; no PostgreSQL foram validadas as migrations e a estrutura,
sem repetir o fluxo HTTP completo. A simulação avança por ticks manuais do
ADMIN e não tem agendamento automático. A interface de dashboards da Fase 6
não faz parte desta entrega.
