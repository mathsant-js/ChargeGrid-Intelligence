# ChargeGrid Intelligence

## Integrantes

| Nome                            | RM     |
| ------------------------------- | ------ |
| Bernardo Zauza Amorim           | 568808 |
| Bruno Almeida De Oliveira       | 572648 |
| Gabriel Góes Nunes Pereira      | 571735 |
| Guilherme Vinciguerra Carvalho  | 571951 |
| Marcos Peterson Martins Pereira | 573857 |
| Matheus Jorge Santana           | 574166 |

## Descrição da Solução

O ChargeGrid Intelligence é um projeto para gestão de postos de carregamento de carros elétricos com análise de dados do posto. A branch ```simulacao_tarifacao_demanda``` possui uma prova de conceito desenvolvida em Python para simular o gerenciamento de demanda energética em estações de carregamento de veículos elétricos em ambientes comerciais.

A solução foi criada com base nos desafios apresentados pela GoodWe, considerando cenários onde diversos veículos realizam carregamento simultaneamente, exigindo controle de consumo, distribuição de potência e tarifação dos usuários.

O sistema permite cadastrar veículos em carregamento, calcular a demanda total da estação, verificar a capacidade disponível, distribuir a potência entre os veículos conectados e calcular automaticamente o valor a ser pago por cada usuário com base no consumo energético informado.

A proposta busca demonstrar de forma simples e funcional conceitos presentes no ChargeGrid Intelligence, como:

* Gerenciamento inteligente de demanda;
* Balanceamento de carga;
* Tarifação automática;
* Monitoramento do consumo energético;
* Suporte à tomada de decisão operacional.


## Objetivo do Projeto

Simular o funcionamento básico de uma estação comercial de carregamento de veículos elétricos, permitindo analisar o impacto da demanda energética e calcular os custos associados ao carregamento.


## Funcionalidades

* Cadastro de múltiplos veículos em carregamento;
* Registro da energia necessária para cada veículo;
* Cálculo da demanda total da estação;
* Verificação da capacidade máxima disponível;
* Simulação de balanceamento inteligente de potência;
* Cálculo automático de tarifação por kWh consumido;
* Exibição de relatório completo no terminal.


## Arquitetura e Fluxo do Sistema

O sistema foi desenvolvido utilizando apenas Python puro e execução via terminal.

### Fluxo de funcionamento

```text
INÍCIO
   │
   ▼
Receber quantidade de veículos
   │
   ▼
Receber dados de cada veículo
   │
   ▼
Calcular demanda total
   │
   ▼
Comparar com a capacidade da estação
   │
   ▼
Aplicar balanceamento de potência
   │
   ▼
Calcular valor do carregamento
   │
   ▼
Gerar relatório individual
   │
   ▼
Exibir relatório final
   │
   ▼
FIM
```

### Estrutura lógica

```text
main()
│
├── Entrada de dados
│
├── Análise da demanda
│
├── Distribuição de potência
│
├── Cálculo de pagamento
│
└── Exibição de relatório
```


## Gerenciamento de Demanda

O sistema calcula a demanda total somando a energia necessária de todos os veículos conectados.

Exemplo:

```text
EV001 → 60 kWh
EV002 → 40 kWh
EV003 → 50 kWh

Demanda Total = 150 kWh
```

Esse valor é comparado com a capacidade máxima da estação para verificar se existe risco de sobrecarga.


## Tarifação

O valor do carregamento é calculado utilizando uma tarifa fixa por kWh.

Fórmula utilizada:

```text
Valor = Energia Consumida × Valor do kWh
```

Exemplo:

```text
Energia Consumida = 40 kWh
Valor do kWh = R$ 0,95

Pagamento = R$ 38,00
```


## Balanceamento Inteligente

Quando vários veículos estão conectados simultaneamente, a potência disponível é distribuída proporcionalmente à demanda energética de cada veículo.

Essa abordagem simula o conceito de balanceamento de carga utilizado em estações comerciais para evitar sobrecarga da infraestrutura elétrica.


## Exemplo de Saída

```text
============================================================
CHARGEGRID INTELLIGENCE
Simulação de Demanda e Tarifação
============================================================

ANÁLISE DA DEMANDA

Demanda total: 150.00 kWh
Capacidade da estação: 150.00 kW

Demanda dentro da capacidade da estação.

============================================================
RELATÓRIO DE CARREGAMENTO
============================================================

Veículo: EV001
Energia necessária: 60.00 kWh
Potência recebida: 60.00 kW
Valor a pagar: R$ 57.00
```


## Como Executar

### Pré-requisitos

* Python 3.10 ou superior

### Executando o projeto

Clone o repositório:

```bash
git clone -b simulacao_tarifacao_demanda https://github.com/mathsant-js/ChargeGrid_IntelligencePlatform.git
```

Acesse a pasta do projeto:

```bash
cd chargegrid-intelligence
```

Execute o programa:

```bash
python app.py
```


## Vídeo Demonstrativo

Link do vídeo pitch (YouTube Não Listado):
> https://youtu.be/ikWwzE1RMOU

## Quadro Kanban da equipe

Link do quadro Kanban da equipe (GitHub Project)
> https://github.com/users/mathsant-js/projects/4


## Materiais Técnicos Relevantes

### GoodWe

Empresa especializada em soluções para energia renovável, armazenamento energético e mobilidade elétrica.

### ChargeGrid Intelligence

Plataforma voltada para gerenciamento inteligente de estações de carregamento de veículos elétricos.

### Conceitos Aplicados

* Mobilidade elétrica;
* Infraestrutura de carregamento;
* Gerenciamento de demanda energética;
* Balanceamento de carga;
* Tarifação de energia;
* Sistemas de monitoramento;
* Automação com Python.

### Tecnologias Utilizadas

* Python 3
* Terminal (CLI)
* Estruturas de repetição
* Estruturas condicionais
* Funções
* Listas
