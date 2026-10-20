# Mapa da documentação

Este índice separa instruções vigentes de registros históricos. A data de uma
evidência informa quando ela foi obtida; não garante que o mesmo resultado foi
reexecutado no checkout atual.

## Documentação vigente

| Documento | Uso |
| --- | --- |
| [`../SPEC.md`](../SPEC.md) | Fonte de verdade para requisitos e regras de negócio. |
| [`../BRIEFING.md`](../BRIEFING.md) | Contexto e objetivos do produto, subordinados ao SPEC. |
| [`../README.md`](../README.md) | Entrada do projeto, execução e navegação. |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Arquitetura e fluxo implementados no estado atual. |
| [`MVP_DELIVERY_SMOKE_TEST.md`](MVP_DELIVERY_SMOKE_TEST.md) | Procedimento oficial para preparar, executar e diagnosticar a demo. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Instalação de desenvolvimento e verificações. |
| [`ML_EVALUATION.md`](ML_EVALUATION.md) | Metodologia, métricas e limites do modelo atual. |

## Registros históricos

Os documentos abaixo preservam decisões, limitações, comandos e resultados do
momento de cada entrega. Afirmações como “ainda não existe” ou contagens de
testes podem ter sido superadas por fases posteriores.

- [`PHASE_1.md`](PHASE_1.md) a [`PHASE_9.md`](PHASE_9.md): evolução do MVP;
- [`PHASE_6_ANALYTICS.md`](PHASE_6_ANALYTICS.md): contrato consolidado durante a
  Fase 6; confira o OpenAPI para o contrato executável atual;
- [`SPRINT_3_PLAN.md`](SPRINT_3_PLAN.md): plano anterior à implementação da
  entrega;
- [`sprint-3/README.md`](sprint-3/README.md),
  [`sprint-3/EVIDENCE.md`](sprint-3/EVIDENCE.md) e materiais associados:
  entrega acadêmica e evidências da Sprint 3.

## Como preparar a demo

1. A partir da raiz, confirme Docker e Docker Compose disponíveis.
2. Execute `make mvp-smoke` para a validação completa, isolada e descartável.
3. Se precisar apresentar as telas, siga a execução manual em
   [`MVP_DELIVERY_SMOKE_TEST.md`](MVP_DELIVERY_SMOKE_TEST.md), que encaminha ao
   roteiro da Sprint 3 apenas para a parte interativa.
4. Consulte [`ARCHITECTURE.md`](ARCHITECTURE.md) para explicar o fluxo e
   [`ML_EVALUATION.md`](ML_EVALUATION.md) para explicar as métricas.

Não monte um procedimento novo combinando comandos de diferentes documentos
de fase. O smoke test é o caminho operacional canônico.
