# Sprint 3 — Plano de desenvolvimento e evidências

## Objetivo e limite

Entregar uma demonstração reproduzível do protótipo **simulado** do ChargeGrid
Intelligence, com código, diagramas e resultados que representem o mesmo fluxo.
O cenário segue `SPEC.md` §§ 54–55 e o Golden Path de `BRIEFING.md` § 17.
`SPEC.md` continua sendo a fonte de verdade para regras de negócio.

Esta sprint prepara e evidencia o fluxo já implementado: sessões, alocação
igualitária, limite da rede, prioridade solar, leituras, alertas, billing,
indicadores de sustentabilidade e dashboards. Previsão automática de demanda e
classificação de risco pertencem à Fase 7; a apresentação deve identificar
claramente essa lacuna, sem preencher o dashboard com uma previsão inventada.
Integração com carregadores, inversores ou medidores físicos permanece futura.

## Estado de partida

- `backend/tests/test_phase_6_flow.py` já exercita o cenário integrado pela API.
- `backend/app/simulation/control.py` executa ticks manuais, um por chamada a
  `POST /api/v1/simulation/ticks`; não existe agendador de ticks.
- `backend/app/simulation/energy_data.py` calcula solar por curva determinística
  entre 06:00 e 18:00 UTC, com pico às 12:00 UTC.
- `frontend/src/pages/AdminDashboardPage.tsx` e `UserDashboardPage.tsx`
  consultam APIs existentes e oferecem atualização manual da tela.
- Não existe seed oficial nem roteiro operacional para a demonstração. O
  `docs/ARCHITECTURE.md` ainda descreve simulação e analytics como futuros.
- A API de sustentabilidade lê o fator de emissão de
  `GRID_EMISSION_FACTOR_KG_PER_KWH` (`backend/app/core/config.py`); não se deve
  atribuir o valor exibido ao registro `SystemConfiguration` sem mudar o código.

## Entregas de código, em ordem

| Etapa | Mudança pequena e verificável | Aceite |
| --- | --- | --- |
| 1. Dados iniciais | Criar um comando de seed em `backend/` ou `scripts/` que use os modelos e a configuração existentes: 1 ADMIN, 4 USER, 4 veículos de 20 kW, 1 estação com limite de rede de 60 kW, 4 carregadores de 22 kW, 1 tarifa ativa e configuração ESG. Identificar os registros da demo para permitir reexecução sem duplicatas. Receber senhas por variáveis de ambiente, sem gravá-las no Git. | Uma instalação limpa recebe os dados previstos no `SPEC.md` § 54; uma segunda execução é segura. |
| 2. Relógio reproduzível | Se o ensaio ao vivo confirmar a necessidade, acrescentar uma configuração **opt-in para desenvolvimento/demonstração** que inicialize o `SimulationClock` em um instante UTC escolhido, próximo de 12:00 UTC. Sem a configuração, manter o início no horário corrente. Validar entrada e documentar que o processo da API deve ter um único controlador de simulação na demo. | O primeiro tick pode ser repetido no pico solar em um banco de demo isolado; produção mantém o comportamento atual. |
| 3. Roteiro executável | Criar script de demonstração que use **endpoints públicos**, autentique cada usuário e imprima respostas relevantes. Sequência: iniciar três sessões; tick sem solar; iniciar a quarta; tick sem solar; alterar `station_peak_solar_kw` pela API administrativa; tick com solar; consultar leituras, alertas e dashboards; encerrar uma sessão; consultar invoice e sustentabilidade. Não escrever diretamente nas tabelas durante o fluxo. | Saída verificável de 60 kW na rede, depois 4 × 15 kW, depois aproximadamente 80 kW totais (20 solar + 60 rede), respeitando limites individuais. |
| 4. Interface e ajustes | Ensaiar `/admin` e `/user` com os dados do script. Corrigir apenas defeitos que impeçam a demonstração ou tornem dados exibidos enganosos. Se comandos na UI forem necessários, colocá-los em um componente administrativo que chame a API existente; não duplicar regras energéticas em React. | Prints mostram sessões, gráficos solar/rede, alerta, histórico, cobrança e indicadores com valores coerentes com as respostas da API. |
| 5. Regressão | Acrescentar testes para seed, configuração opcional do relógio e script/fluxo onde houver risco real de regressão. Reaproveitar o teste integrado existente para as invariantes energéticas. Executar `make check` e ensaio com PostgreSQL via Docker Compose. | Testes, lint, tipos e build passam; o cenário funciona em banco limpo e pode ser repetido. |

O script de demonstração é um **orquestrador de chamadas**, não um novo motor de
simulação. O servidor continua responsável por autenticação, transições de
sessão, alocação, cálculo energético, persistência e faturamento.
Para a demo, definir no ambiente o mesmo fator de emissão registrado na
configuração seed e documentar que a API usa a variável de ambiente.

## Diagramas e rastreabilidade

Criar em `docs/sprint-3/` dois diagramas Mermaid versionáveis e exportar PNGs
para o PDF/vídeo somente após conferir o fluxo executado. A tabela determina o
que cada seta pode afirmar:

| Diagrama | Elementos e conexões permitidos | Código que comprova |
| --- | --- | --- |
| Arquitetura executada | Navegador React → API REST FastAPI → serviços de sessão, simulação, energia, billing e analytics → SQLAlchemy/PostgreSQL. O simulador fornece dados solares; o dashboard lê dados pela API. | `frontend/src/api/client.ts`, `backend/app/api/router.py`, `backend/app/services/`, `backend/app/simulation/`, `backend/app/db/`. |
| Sequência da demo | USER inicia sessão → ADMIN aciona tick → controlador consulta sessões e solar → alocador calcula potência → tick grava leituras/alerta → dashboards consultam API → USER encerra sessão → serviço cria invoice. | `backend/app/api/routes/sessions.py`, `simulation.py`, `backend/app/simulation/tick.py`, `backend/app/services/energy_allocation.py`, `charging_sessions.py`, rotas de analytics/billing. |

Revisar `docs/ARCHITECTURE.md` para retirar afirmações antigas de que
simulação e analytics não funcionam. Diagramas devem indicar **tick manual**,
**solar simulada** e **cobrança simulada**. Não desenhar fluxo de ML treinado,
controle de hardware, OCPP/Modbus, agendador ou comandos físicos, pois não
existem nessa implementação. Se uma dessas funções for implementada numa fase
posterior, atualizar os diagramas na mesma alteração de código.

## Evidências e apresentação

1. Registrar saída do roteiro com os valores por tick, kWh, alerta, invoice e
   CO₂ evitado, incluindo tarifa e fator de emissão usados. Distinguir
   claramente medições **simuladas** de medições reais.
2. Capturar prints da API/OpenAPI e dos dashboards após atualizar as telas.
3. Escrever `docs/sprint-3/README.md` (ou seção equivalente no README raiz)
   com título, integrantes informados pela equipe, diagramas, escolhas
   técnicas, resultados, instruções de reprodução e relação com a disciplina.
4. Preparar roteiro e vídeo de até cinco minutos: arquitetura; três sessões;
   quarta sessão e redistribuição; solar; dados/alerta; encerramento,
   faturamento e sustentabilidade; limites conhecidos.
5. Atualizar o README raiz com um link para a entrega e comandos exatos de
   execução. Manter credenciais e arquivos `.env` fora do repositório.

## Compatibilidade com as próximas fases

- Manter o monólito modular, os contratos `/api/v1` e as regras de energia nos
  serviços existentes. O script da sprint não deve ser importado pelo backend
  de produção.
- Preservar `EnergyDataProvider` como fronteira da origem solar: esta sprint
  usa `SimulationEnergyDataProvider`; provedores físicos futuros não precisam
  ser implementados agora.
- Não alterar o esquema do banco para conveniência da apresentação. Se uma
  mudança de esquema se mostrar indispensável, criar migration Alembic e teste.
- Não criar previsão artificial para completar o KPI de risco. A Fase 7 deverá
  integrar dataset, baseline, treinamento, métricas e inferência nos contratos
  existentes, sem interferir nas invariantes de potência.
- Incorporar na `main` somente o código e a documentação revisados, após
  `make check`, ensaio da demo e revisão dos diagramas contra o código final.

## Critério de fechamento da sprint

A entrega estará pronta quando outra pessoa conseguir iniciar um ambiente
limpo, executar o seed e o roteiro, obter os resultados previstos, abrir as
telas e confirmar que cada conexão desenhada corresponde a uma chamada ou
serviço implementado. Os materiais devem declarar as limitações atuais e
responder aos itens específicos do enunciado acadêmico da Sprint 3.
