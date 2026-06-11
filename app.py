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