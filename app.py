POTENCIA_MAXIMA_ESTACAO = 150
VALOR_KWH = 0.95

def calcular_pagamento(energia_consumiada):
    return energia_consumiada * VALOR_KWH

def calcular_demanda_total(demanda):
    return sum(demanda)