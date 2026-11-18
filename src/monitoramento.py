"""
Simulação de uma semana de monitoramento (dados horários) da alternativa recomendada (A3).

Os dados são SIMULADOS a partir do perfil horário calculado em energia.py, com ruído
e três falhas inseridas de propósito, para demonstrar a lógica de alertas do dashboard:
  1) ar-condicionado esquecido ligado na madrugada de quarta-feira;
  2) câmara de vacinas acima de 8 °C na madrugada de sexta-feira;
  3) parte do sistema solar desligada no sábado (geração abaixo da irradiação medida).
"""
import random

import energia

DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
NEBULOSIDADE = [1.00, 0.95, 0.45, 1.00, 0.90, 1.00, 0.85]   # fração da irradiação de um dia médio
EXPEDIENTE = range(7, 19)


def n(v):
    return f"{v:.1f}".replace(".", ",")


def regras_alerta(hora_txt, consumo, esperado, temp, geracao, geracao_esperada):
    """Lógica de automação/monitoramento (mesma regra descrita no diagrama)."""
    alertas = []
    h = int(hora_txt.split()[1][:2])
    if h not in EXPEDIENTE and consumo > esperado * 1.2 + 0.3:
        alertas.append(("Consumo", f"Consumo fora do expediente: {n(consumo)} kW (esperado {n(esperado)} kW). "
                                   "Verificar ar-condicionado ou iluminação ligados."))
    if temp < 2 or temp > 8:
        alertas.append(("Rede de frio", f"Câmara de vacinas a {n(temp)} °C (faixa segura: 2 a 8 °C). Acionar a equipe."))
    if geracao_esperada > 1.0 and geracao < 0.7 * geracao_esperada:
        alertas.append(("Solar", f"Geração de {n(geracao)} kWh, esperado {n(geracao_esperada)} kWh para a irradiação "
                                 "medida. Verificar inversor ou sujeira nos módulos."))
    return alertas


def simular_semana(mes_idx=10, semente=42):
    rnd = random.Random(semente)
    prem = energia.carregar_premissas()
    eqs = energia.carregar_equipamentos()
    clima = energia.carregar_clima()
    res = energia.avaliar(prem, eqs, clima)
    a3 = next(a for a in res["alternativas"] if a["chave"] == "a3")
    m = clima[mes_idx]
    util = energia.perfil_horario(eqs, True, True, m["fator_climatizacao"])
    fds = energia.perfil_horario(eqs, True, False, m["fator_climatizacao"])
    fv_medio = energia.perfil_fv(a3["kwp"], m["irradiacao_kwh_m2_dia"], prem["taxa_desempenho_pr"], mes_idx)

    serie, alertas = [], []
    for d, nome in enumerate(DIAS):
        base = util if d < 5 else fds
        for h in range(24):
            esperado = base[h]
            consumo = esperado * (1 + rnd.uniform(-0.06, 0.06))
            if d == 2 and h >= 20:                       # falha 1: ar esquecido ligado (qua 20h -> qui 6h)
                consumo += 0.77
            if d == 3 and h < 6:
                consumo += 0.77
            irr_fator = NEBULOSIDADE[d] * (1 + rnd.uniform(-0.05, 0.05))
            geracao_esperada = fv_medio[h] * irr_fator
            geracao = geracao_esperada * (1 + rnd.uniform(-0.03, 0.03))
            if d == 5 and 10 <= h <= 14:                 # falha 3: metade do arranjo desligada (sábado)
                geracao *= 0.45
            temp = 4.6 + rnd.uniform(-0.6, 0.6)
            if d == 4 and 2 <= h <= 4:                   # falha 2: câmara de vacinas aquecendo (sexta)
                temp = [7.4, 8.6, 8.9][h - 2]
            hora_txt = f"{nome} {h:02d}h"
            for tipo, msg in regras_alerta(hora_txt, consumo, esperado, temp, geracao, geracao_esperada):
                alertas.append(dict(quando=hora_txt, tipo=tipo, mensagem=msg))
            serie.append(dict(dia=nome, hora=h, consumo_kw=round(consumo, 3), esperado_kw=round(esperado, 3),
                              geracao_kw=round(geracao, 3), rede_kw=round(consumo - geracao, 3),
                              temp_vacina_c=round(temp, 2)))

    ocorrencias = agrupar(alertas)
    consumo_sem = sum(s["consumo_kw"] for s in serie)
    geracao_sem = sum(s["geracao_kw"] for s in serie)
    excesso = sum(max(0, s["consumo_kw"] - s["esperado_kw"]) for s in serie
                  if s["hora"] not in EXPEDIENTE and s["consumo_kw"] > s["esperado_kw"] * 1.2 + 0.3)
    resumo = dict(consumo_semana_kwh=consumo_sem, geracao_semana_kwh=geracao_sem,
                  autossuficiencia_pct=geracao_sem / consumo_sem * 100,
                  horas_rede_frio_fora=sum(1 for s in serie if not 2 <= s["temp_vacina_c"] <= 8),
                  alertas=len(alertas), ocorrencias=len(ocorrencias), desperdicio_detectado_kwh=excesso, mes=m["mes"])
    return dict(serie=serie, alertas=alertas, ocorrencias=ocorrencias, resumo=resumo)


def agrupar(alertas):
    """Junta alertas do mesmo tipo em horas seguidas numa única ocorrência."""
    ocorr = []
    for i, a in enumerate(alertas):
        a["indice"] = DIAS.index(a["quando"].split()[0]) * 24 + int(a["quando"].split()[1][:2])
        ult = ocorr[-1] if ocorr else None
        if ult and ult["tipo"] == a["tipo"] and a["indice"] == ult["fim_indice"] + 1:
            ult["fim"], ult["fim_indice"], ult["horas"] = a["quando"], a["indice"], ult["horas"] + 1
        else:
            ocorr.append(dict(tipo=a["tipo"], inicio=a["quando"], fim=a["quando"], fim_indice=a["indice"],
                              horas=1, mensagem=a["mensagem"]))
    for o in ocorr:
        o.pop("fim_indice")
    return ocorr
