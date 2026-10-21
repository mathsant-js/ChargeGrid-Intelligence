# Roteiro de demonstração — até cinco minutos

| Tempo | Tela / ação | Mensagem principal |
| --- | --- | --- |
| 0:00–0:25 | Título e dashboard | O ChargeGrid gerencia recarga, demanda, solar, cobrança, ESG e previsão. Todos os dados e equipamentos desta demonstração são simulados. |
| 0:25–0:55 | Diagrama de arquitetura | O sistema é um monólito modular. O provider substituível desacopla o motor energético da origem dos dados. |
| 0:55–1:30 | Dashboard e estado da simulação | Iniciar o runner. Mostrar relógio simulado, último tick, velocidade, atualização automática e botão de atualização imediata. |
| 1:30–2:10 | Três sessões e gráfico | Três veículos pedem e recebem 20 kW: total de 60 kW, dentro do limite da rede. |
| 2:10–2:45 | Entrada da quarta sessão | Com 80 kW pedidos e sem solar, Equal Share distribui 15 kW por sessão e mantém a rede em 60 kW. |
| 2:45–3:15 | Marco de telemetria às 12:02 UTC | O replay oferece 20 kW solares; as quatro sessões recebem 80 kW, compostos por 20 kW solar e 60 kW da rede. |
| 3:15–3:45 | Previsão e alertas | Gerar previsão, mostrar risco `HIGH`, recomendação determinística e alertas. Ressaltar que ML é consultivo. |
| 3:45–4:20 | Encerrar quarta sessão | Mostrar sessão concluída, 1,175 kWh e invoice simulada de R$ 0,94. |
| 4:20–4:45 | Painel ESG e resultados | Mostrar participação solar, 0,9467 kg de CO₂ evitado, economia teórica e zero violações. |
| 4:45–5:00 | Limitações e fechamento | Não há hardware, Modbus/OCPP ou pagamento real. A arquitetura demonstra como uma futura integração física substituiria apenas o provider. |

Antes da gravação, execute `make check`, prepare uma instância demonstrativa
conforme o README desta pasta e mantenha a estação selecionada no dashboard.
Não apresente o replay como comunicação real com equipamentos GoodWe.

