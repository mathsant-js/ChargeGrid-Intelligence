# Arquitetura executada

O ChargeGrid Intelligence é um monólito modular. O navegador React consome a API REST FastAPI sob `/api/v1`; os serviços usam SQLAlchemy e PostgreSQL. Os contratos HTTP são Pydantic. Consulte os [diagramas da Sprint 3](sprint-3/README.md) para as conexões do fluxo de demonstração.

O serviço `charging_sessions` valida início e encerramento, captura tarifa e cria invoice simulada. O controlador em `simulation/control.py` executa apenas ticks manuais por `POST /simulation/ticks`. O provedor `SimulationEnergyDataProvider` calcula geração solar simulada pela curva UTC; o alocador `EqualSharePowerResolver` aplica limites individuais e de rede e prioriza solar. `simulation/tick.py` persiste leituras, acumuladores e alertas na mesma transação. Analytics e dashboards consultam dados persistidos pela API. O navegador não calcula as regras de energia.

A previsão de demanda e a classificação de risco ainda não são produzidas automaticamente. Não há integração física, agendador de ticks ou comandos para carregadores. O pacote `repositories` permanece reservado, sem camada ativa. Todas as alterações de esquema usam Alembic; datas são UTC, IDs são UUID e valores monetários usam tipos decimais.
