POTENCIA_MAXIMA_ESTACAO = 150
VALOR_KWH = 0.95

def calcular_pagamento(energia_consumida):
    return energia_consumida * VALOR_KWH

def calcular_demanda_total(demandas):
    return sum(demandas)

def distribuir_potencia(demandas):
    demanda_total = calcular_demanda_total(demandas)
    
    distribuicao = []
    
    for demanda in demandas:
        percentual = demanda / demanda_total
        
        potencia_recebida = percentual * POTENCIA_MAXIMA_ESTACAO
        
        distribuicao.append(potencia_recebida)
    
    return distribuicao

def exibir_relatorio(veiculos, demandas, distribuicao): 
    print("\n" + "=" * 60)
    print("RELATÓRIO DE CARREGAMENTO")
    print("=" * 60)
    
    for i in range(len(veiculos)): 
        pagamento = calcular_pagamento(demandas[i])
        
        print(f"\nVeículo: {veiculos[i]}")
        print(f"Energia necessária: {demandas[i]:.2f} kWh")
        print(f"Potência recebida: {distribuicao[i]:.2f} kW")
        print(f"Valor a pagar: R$ {pagamento:.2f}")
        print("\n" + "=" * 60)
        
def main():
    print("=" * 60)
    print("CHARGEGRID INTELLIGENCE")
    print("Simulação de Demanda e Tarifação")
    print("=" * 60)

    quantidade = int(
        input("\nQuantos veículos estão carregando? ")
    )

    veiculos = []
    demandas = []

    for i in range(quantidade):

        print(f"\nVeículo {i + 1}")

        nome = input("Identificação: ")

        energia = float(
            input(
                "Energia necessária (kWh): "
            )
        )

        veiculos.append(nome)
        demandas.append(energia)

    demanda_total = sum(demandas)

    print("\n" + "=" * 60)
    print("ANÁLISE DA DEMANDA")
    print("=" * 60)

    print(
        f"Demanda total: "
        f"{demanda_total:.2f} kWh"
    )

    print(
        f"Capacidade da estação: "
        f"{POTENCIA_MAXIMA_ESTACAO:.2f} kW"
    )

    if demanda_total > POTENCIA_MAXIMA_ESTACAO:

        print("\nALERTA:")
        print(
            "Demanda acima da capacidade."
        )

        print(
            "Aplicando balanceamento "
            "inteligente..."
        )

    else:

        print(
            "\nDemanda dentro da "
            "capacidade da estação."
        )

    distribuicao = distribuir_potencia(
        demandas
    )

    exibir_relatorio(
        veiculos,
        demandas,
        distribuicao
    )

main()