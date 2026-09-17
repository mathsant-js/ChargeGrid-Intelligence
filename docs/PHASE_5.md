# Fase 5 — Billing e histórico de invoices

## Comportamento entregue

Ao encerrar uma sessão, o backend calcula `energy_kwh × tariff_per_kwh`,
arredonda o total para centavos e cria uma invoice `CLOSED` na mesma transação.
A invoice guarda energia, tarifa aplicada, subtotal, total e datas do fechamento.
Esses valores são registros históricos: alterar a tarifa posteriormente não
recalcula invoices existentes.

`GET /api/v1/billing/invoices` lista invoices por `created_at` e `id`, em ordem
crescente estável. Aceita os filtros opcionais `user_id` (UUID) e `status`
(`OPEN`, `CLOSED` ou `CANCELLED`), que podem ser combinados. Uma lista sem
resultados retorna `[]`. `GET /api/v1/billing/invoices/{invoice_id}` retorna a
invoice solicitada ou 404 se ela não existir ou não estiver visível.

Ambos os endpoints exigem bearer token (401 quando ausente ou inválido). ADMIN
pode listar e consultar qualquer invoice. USER vê apenas as próprias; um filtro
`user_id` de outra pessoa retorna 404, assim como o acesso por ID a uma invoice
alheia. O filtro pelo próprio ID é permitido.

## Validação

Os testes cobrem autorização por papel e propriedade, 401, 404, filtros,
ordenação com timestamps iguais e preservação dos valores históricos após
alteração da tarifa. O OpenAPI declara autenticação e respostas de erro para
ambos os endpoints, além dos parâmetros de filtro.
