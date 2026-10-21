# Contrato de replay de telemetria

O `TelemetryReplayEnergyDataProvider` reproduz medições sintéticas de um arquivo
CSV versionado. Ele representa a fronteira que futuramente poderia receber
telemetria de um gateway energético; não implementa nem alega comunicação
Modbus, conexão GoodWe ou hardware real.

## Configuração

```env
ENERGY_DATA_PROVIDER=telemetry_replay
TELEMETRY_REPLAY_PATH=../data/raw/sprint4_telemetry.csv
```

O provider padrão permanece `curve`. No Docker Compose, o caminho padrão aponta
para o arquivo montado em `/data/raw/sprint4_telemetry.csv` a partir do diretório
de trabalho `/app`.

## Colunas

| Campo | Regra |
| --- | --- |
| `timestamp` | ISO 8601 com fuso horário; normalizado para UTC |
| `station_code` | Identificador não vazio; no MVP corresponde ao nome único usado no cenário |
| `pv_power_kw` | Finito e não negativo; limitado ao pico solar da estação no consumo |
| `grid_power_kw` | Finito e não negativo; informativo, não controla a alocação |
| `load_power_kw` | Finito e não negativo; informativo, não controla a alocação |
| `inverter_status` | Texto não vazio e informativo |
| `temperature_c` | Número finito e informativo |
| `data_quality` | `GOOD`, `ESTIMATED` ou `SYNTHETIC` |

A busca exige correspondência exata de `station_code` e instante UTC. Uma
amostra ausente produz 0 kW e qualidade `MISSING`. Duplicatas são rejeitadas ao
carregar o arquivo. Assim, o replay é determinístico e falha cedo quando o
dataset é inválido.

## Limite de responsabilidade

O provider informa a disponibilidade solar, a origem e a qualidade da amostra.
O tick valida a potência contra o pico da estação e entrega o valor ao alocador
Equal Share. Campos de rede e carga do CSV não substituem as regras do domínio,
e nenhuma telemetria pode ultrapassar limites de rede, carregador, veículo ou
potência solicitada.
