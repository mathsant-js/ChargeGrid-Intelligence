# Fase 8 — ESG e alertas

## Escopo consolidado

O relatório `GET /api/v1/analytics/sustainability` aceita `station_id`, `from` e `to` e apresenta energia total, solar e da rede, participação solar, CO₂ evitado, fator de emissão utilizado e economia solar estimada. O fator de emissão vem exclusivamente de `SystemConfiguration`; na ausência dessa configuração, a API retorna `503` em vez de aplicar um valor ambiental implícito.

As fórmulas do SPEC foram preservadas:

- participação solar = energia solar / energia total × 100; com consumo zero, o resultado é zero;
- CO₂ evitado = energia solar × fator de emissão configurado;
- economia estimada = soma da energia solar de cada leitura × tarifa registrada na respectiva sessão.

A economia é apresentada como estimativa teórica da energia que teria sido comprada da rede e não como economia financeira real da instalação.

## Critérios dos alertas

- `HIGH_DEMAND`: entrada da rede / limite da rede alcança o limiar configurado;
- `PEAK_RISK`: previsão da Fase 7 entra no nível `HIGH`;
- `HIGH_SOLAR_AVAILABILITY`: geração solar disponível / pico solar configurado da estação alcança `high_solar_availability_threshold`;
- `SESSION_FINISHED`: encerramento bem-sucedido da sessão.

Os alertas de condição são emitidos apenas na entrada de um episódio: ticks consecutivos acima do limiar não repetem o alerta; depois que a condição fica abaixo do limiar, uma nova subida inicia outro episódio. Estações com pico solar zero não geram `HIGH_SOLAR_AVAILABILITY`.

## Critérios de aceite

- filtros de estação e período afetam todos os totais ESG;
- consumo zero produz participação solar igual a zero;
- fator ambiental exibido é o mesmo fator configurado usado no cálculo;
- economia aparece explicitamente como “economia estimada” e “teórica”;
- limiares aceitam somente proporções no intervalo `(0, 1]`;
- o dashboard administrativo apresenta o relatório ESG completo;
- `HIGH_DEMAND`, `PEAK_RISK` e `SESSION_FINISHED` permanecem ativos;
- alertas por condição são deduplicados por episódio.

## Resultados dos testes

Resultados executados em 24/09/2026:

- backend: `209 passed`, cobertura total de 96%;
- frontend: `31 passed`;
- Ruff: aprovado;
- mypy: aprovado em 74 arquivos;
- ESLint: aprovado;
- build de produção Vite/TypeScript: aprovado (com o aviso informativo já existente sobre tamanho do bundle).

A suíte cobre fórmulas ESG, consumo zero, fator configurado, filtros, validação de limites, episódios de alerta solar e de demanda, integração do risco de pico e apresentação administrativa.
