from datetime import date
import random

def compute_score(processes, today=date.today()):
    """
    Calcula o score de reputação (0 a 100) baseado nos processos.
    Score 100 = Melhor Reputação
    """
    weight = {
        "improbidade": 9,
        "execucao": 5,
        "falencia": 8,
        "trabalhista": 3,
        "civel": 1
    }
    
    score_raw = 0
    total_processos = len(processes)
    
    for p in processes:
        # Ponderação básica por tipo de processo
        type_lower = p.get("type", "civel").lower()
        base_weight = weight.get(type_lower, 1)
        
        # Ponderação por Recência (Processos recentes pesam mais)
        last_movement = p.get("last_movement_date", None)
        recency_mult = 1.0
        
        if last_movement:
            try:
                # Calcula a idade do processo em dias
                age_days = (today - last_movement).days
                if age_days < 365:
                    recency_mult = 2.0  # Dobra o peso se for do último ano
                elif age_days < 730:
                    recency_mult = 1.5
            except Exception:
                pass # Ignora se a data for inválida

        score_raw += base_weight * recency_mult

    # Adiciona peso cumulativo pelo número total de processos
    score_raw += total_processos * 0.5 

    # Normaliza o score: Max (0, 100 - (Peso Bruto Limitado a 100))
    penalty = min(score_raw, 100)
    score_normalized = max(0, 100 - penalty)
    
    # Simulação de variação
    final_score = score_normalized - random.uniform(0, 3) 
    
    return round(max(0, final_score), 1)