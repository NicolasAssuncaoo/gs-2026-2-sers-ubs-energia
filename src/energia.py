"""
Contribuição SERS ao Neighborhood Action Dashboard — UBS Energia Inteligente
Cálculos energéticos, financeiros e ambientais (somente biblioteca padrão).

Fórmula base (enunciado, item 4.2):  E = (P × t) / 1000
    E = energia (kWh), P = potência (W), t = tempo de funcionamento (h)
"""
import csv
import json
import math
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.path.join(RAIZ, "dados")
HORAS = list(range(24))
DIAS_UTEIS = 22


# ---------------------------------------------------------------------------
# Leitura dos dados
# ---------------------------------------------------------------------------
def carregar_equipamentos(caminho=None):
    caminho = caminho or os.path.join(DADOS, "equipamentos.csv")
    with open(caminho, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for l in linhas:
        for k in ("quantidade", "dias_mes", "inicio_h"):
            l[k] = int(l[k])
        for k in ("potencia_w", "horas_dia", "potencia_eficiente_w", "horas_dia_eficiente"):
            l[k] = float(l[k])
    return linhas


def carregar_clima(caminho=None):
    caminho = caminho or os.path.join(DADOS, "clima_mensal.csv")
    with open(caminho, encoding="utf-8") as f:
        meses = list(csv.DictReader(f))
    for m in meses:
        m["dias"] = int(m["dias"])
        m["irradiacao_kwh_m2_dia"] = float(m["irradiacao_kwh_m2_dia"])
        m["fator_climatizacao"] = float(m["fator_climatizacao"])
    # normaliza o fator de climatização para média anual = 1 (preserva o consumo anual)
    media = sum(m["fator_climatizacao"] for m in meses) / 12
    for m in meses:
        m["fator_climatizacao"] /= media
    return meses


def carregar_premissas(caminho=None):
    caminho = caminho or os.path.join(DADOS, "premissas.json")
    with open(caminho, encoding="utf-8") as f:
        p = json.load(f)
    v = {k: d["valor"] for k, d in p.items() if isinstance(d, dict) and "valor" in d}
    v["custos_eficiencia"] = {k: d["valor"] for k, d in p["custos_eficiencia"].items()}
    v["_bruto"] = p
    return v


# ---------------------------------------------------------------------------
# Consumo
# ---------------------------------------------------------------------------
def energia_kwh(potencia_w, horas):
    """E = (P × t) / 1000"""
    return potencia_w * horas / 1000


def consumo_equipamento_mes(eq, eficiente=False):
    """kWh/mês de um item (quantidade × potência × horas/dia × dias/mês)."""
    p = eq["potencia_eficiente_w"] if eficiente else eq["potencia_w"]
    h = eq["horas_dia_eficiente"] if eficiente else eq["horas_dia"]
    return eq["quantidade"] * energia_kwh(p, h) * eq["dias_mes"]


def consumo_total_mes(equipamentos, eficiente=False):
    return sum(consumo_equipamento_mes(e, eficiente) for e in equipamentos)


def dias_operacao(eq, mes):
    """Itens 24h/externos usam os dias do mês; os demais, 22 dias úteis."""
    return mes["dias"] if eq["dias_mes"] >= 30 else DIAS_UTEIS


def consumo_mensal_serie(equipamentos, clima, eficiente=False):
    """Consumo de cada mês do ano (kWh), com sazonalidade na climatização."""
    serie = []
    for m in clima:
        total = 0.0
        for e in equipamentos:
            p = e["potencia_eficiente_w"] if eficiente else e["potencia_w"]
            h = e["horas_dia_eficiente"] if eficiente else e["horas_dia"]
            kwh = e["quantidade"] * energia_kwh(p, h) * dias_operacao(e, m)
            if e["categoria"] == "Climatização":
                kwh *= m["fator_climatizacao"]
            total += kwh
        serie.append(total)
    return serie


# ---------------------------------------------------------------------------
# Perfil horário (dia útil e fim de semana) — base do monitoramento
# ---------------------------------------------------------------------------
def perfil_horario(equipamentos, eficiente=False, dia_util=True, fator_clima=1.0):
    """Potência média (kW) em cada hora do dia."""
    carga = [0.0] * 24
    for e in equipamentos:
        if not dia_util and e["dias_mes"] < 30:
            continue
        p = (e["potencia_eficiente_w"] if eficiente else e["potencia_w"]) * e["quantidade"] / 1000
        h = e["horas_dia_eficiente"] if eficiente else e["horas_dia"]
        if e["categoria"] == "Climatização":
            p *= fator_clima
        restante = h
        hora = e["inicio_h"]
        while restante > 1e-9:
            fr = min(1.0, restante)
            carga[hora % 24] += p * fr
            restante -= fr
            hora += 1
    return carga


DURACAO_DIA = [13.3, 12.9, 12.3, 11.7, 11.2, 10.9, 11.0, 11.4, 12.0, 12.6, 13.1, 13.4]


def perfil_fv(kwp, irradiacao, pr, idx_mes):
    """Geração horária (kWh) de um dia médio: curva senoidal entre nascer e pôr do sol."""
    energia_dia = kwp * irradiacao * pr
    dur = DURACAO_DIA[idx_mes]
    nascer = 12 - dur / 2
    pesos = []
    for h in HORAS:
        meio = h + 0.5
        x = (meio - nascer) / dur
        pesos.append(math.sin(math.pi * x) if 0 < x < 1 else 0.0)
    s = sum(pesos)
    return [energia_dia * w / s for w in pesos]


# ---------------------------------------------------------------------------
# Fotovoltaico
# ---------------------------------------------------------------------------
def geracao_kwh_kwp_ano(clima, pr):
    return sum(m["irradiacao_kwh_m2_dia"] * m["dias"] * pr for m in clima)


def dimensionar_fv(consumo_anual, clima, prem):
    """Potência necessária para gerar a cobertura-alvo do consumo anual, limitada pelo telhado."""
    pr = prem["taxa_desempenho_pr"]
    alvo = consumo_anual * prem["cobertura_alvo_fv"]
    kwp_necessario = alvo / geracao_kwh_kwp_ano(clima, pr)
    modulos = math.ceil(kwp_necessario * 1000 / prem["modulo_wp"])
    max_modulos = int(prem["area_telhado_util_m2"] // prem["modulo_area_m2"])
    limitado = modulos > max_modulos
    modulos = min(modulos, max_modulos)
    kwp = modulos * prem["modulo_wp"] / 1000
    return dict(modulos=modulos, kwp=kwp, area_m2=modulos * prem["modulo_area_m2"],
                limitado_pelo_telhado=limitado, kwp_necessario=kwp_necessario)


# ---------------------------------------------------------------------------
# Simulação mensal de uma alternativa
# ---------------------------------------------------------------------------
def simular(equipamentos, clima, prem, eficiente=False, kwp=0.0, degradacao=1.0):
    tarifa = prem["tarifa_r_kwh"]
    valor_credito = 1 - prem["fio_b_fracao_tarifa"] * prem["fio_b_nao_compensado"]
    minimo = prem["custo_disponibilidade_kwh"]
    pr = prem["taxa_desempenho_pr"]
    consumo = consumo_mensal_serie(equipamentos, clima, eficiente)
    meses = []
    credito_kwh = 0.0
    for i, m in enumerate(clima):
        fv_dia = perfil_fv(kwp * degradacao, m["irradiacao_kwh_m2_dia"], pr, i) if kwp else [0.0] * 24
        ger = sum(fv_dia) * m["dias"]
        # autoconsumo: horas em que geração e carga acontecem juntas
        util = perfil_horario(equipamentos, eficiente, True, m["fator_climatizacao"])
        fds = perfil_horario(equipamentos, eficiente, False, m["fator_climatizacao"])
        auto_util = sum(min(c, g) for c, g in zip(util, fv_dia))
        auto_fds = sum(min(c, g) for c, g in zip(fds, fv_dia))
        n_fds = m["dias"] - DIAS_UTEIS
        autoconsumo = min(auto_util * DIAS_UTEIS + auto_fds * n_fds, ger, consumo[i])
        injetada = ger - autoconsumo
        importada = consumo[i] - autoconsumo
        # compensação: kWh injetado vale "valor_credito" kWh importado (Fio B não compensado)
        credito_kwh += injetada * valor_credito
        abatido = min(credito_kwh, max(0.0, importada - minimo))
        credito_kwh -= abatido
        faturado = max(importada - abatido, minimo)
        meses.append(dict(mes=m["mes"], consumo_kwh=consumo[i], geracao_kwh=ger,
                          autoconsumo_kwh=autoconsumo, injetada_kwh=injetada,
                          importada_kwh=importada, faturado_kwh=faturado,
                          custo_r=faturado * tarifa))
    return meses


def custo_eficiencia(equipamentos, prem):
    c = prem["custos_eficiencia"]
    itens = {e["id"]: e for e in equipamentos}
    medidas = [
        dict(medida="Troca por LED tubular 18 W", ids=["ilum_int"],
             custo=itens["ilum_int"]["quantidade"] * (c["lampada_led_tubular"] + c["mao_obra_por_lampada"])),
        dict(medida="Sensores de presença", ids=[],
             custo=c["qtd_sensores_presenca"] * c["sensor_presenca_instalado"]),
        dict(medida="Refletores LED 50 W com fotocélula", ids=["ilum_ext"],
             custo=itens["ilum_ext"]["quantidade"] * c["refletor_led_50w_com_fotocelula"]),
        dict(medida="Ar-condicionado inverter + automação", ids=["ar"],
             custo=itens["ar"]["quantidade"] * (c["ar_inverter_12k"] + c["instalacao_ar"])),
        dict(medida="Desligamento automático de TI", ids=["ti"], custo=0.0),
        dict(medida="Monitoramento IoT (medição e alertas)", ids=[], custo=c["monitoramento_iot"]),
    ]
    for md in medidas:
        md["economia_kwh_mes"] = sum(consumo_equipamento_mes(itens[i]) - consumo_equipamento_mes(itens[i], True)
                                     for i in md["ids"])
    # separa a economia da iluminação interna em "troca por LED" (potência) e "sensores" (horas)
    li = itens["ilum_int"]
    so_led = li["quantidade"] * energia_kwh(li["potencia_eficiente_w"], li["horas_dia"]) * li["dias_mes"]
    medidas[0]["economia_kwh_mes"] = consumo_equipamento_mes(li) - so_led
    medidas[1]["economia_kwh_mes"] = so_led - consumo_equipamento_mes(li, True)
    for md in medidas:
        md["economia_r_mes"] = md["economia_kwh_mes"] * prem["tarifa_r_kwh"]
        md["payback_anos"] = (md["custo"] / (md["economia_r_mes"] * 12)) if md["economia_r_mes"] > 0 else None
    return medidas


def fluxo_caixa(capex, economia_ano_1, prem, tem_fv, economia_fv_ano_1=0.0, capex_fv=0.0):
    """Fluxo anual por 25 anos (sem reajuste tarifário: conservador)."""
    anos, acumulado, payback = [], -capex, None
    for ano in range(1, prem["horizonte_anos"] + 1):
        deg = (1 - prem["degradacao_fv_ano"]) ** (ano - 1)
        econ = (economia_ano_1 - economia_fv_ano_1) + economia_fv_ano_1 * deg
        custo = 0.0
        if tem_fv:
            custo += capex_fv * prem["om_fv_fracao_capex_ano"]
            if ano == prem["troca_inversor_ano"]:
                custo += capex_fv * prem["troca_inversor_fracao_capex"]
        liquido = econ - custo
        anterior = acumulado
        acumulado += liquido
        if payback is None and acumulado >= 0:
            payback = ano - 1 + (-anterior / liquido if liquido > 0 else 0)
        anos.append(dict(ano=ano, fluxo_r=liquido, acumulado_r=acumulado))
    return anos, payback


def avaliar(prem=None, equipamentos=None, clima=None):
    """Roda as 4 situações e devolve tudo o que o dashboard e o README usam."""
    prem = prem or carregar_premissas()
    equipamentos = equipamentos or carregar_equipamentos()
    clima = clima or carregar_clima()
    fe = prem["fator_emissao_kgco2_kwh"]

    cons_atual_ano = sum(consumo_mensal_serie(equipamentos, clima))
    cons_efic_ano = sum(consumo_mensal_serie(equipamentos, clima, True))
    fv_a2 = dimensionar_fv(cons_atual_ano, clima, prem)
    fv_a3 = dimensionar_fv(cons_efic_ano, clima, prem)

    medidas = custo_eficiencia(equipamentos, prem)
    capex_efic = sum(m["custo"] for m in medidas)
    capex_fv2 = fv_a2["kwp"] * 1000 * prem["custo_fv_r_wp"]
    capex_fv3 = fv_a3["kwp"] * 1000 * prem["custo_fv_r_wp"]

    defs = [
        ("atual", "Situação atual (referência)", False, 0.0, 0.0, 0.0, None),
        ("a1", "A1 — Eficiência energética", True, 0.0, capex_efic, 0.0, None),
        ("a2", "A2 — Solar fotovoltaica", False, fv_a2["kwp"], capex_fv2, capex_fv2, fv_a2),
        ("a3", "A3 — Eficiência + solar (recomendada)", True, fv_a3["kwp"], capex_efic + capex_fv3, capex_fv3, fv_a3),
    ]
    alternativas = []
    base = None
    for chave, nome, efic, kwp, capex, capex_fv, fv in defs:
        meses = simular(equipamentos, clima, prem, efic, kwp)
        cons = sum(m["consumo_kwh"] for m in meses)
        ger = sum(m["geracao_kwh"] for m in meses)
        custo = sum(m["custo_r"] for m in meses)
        rede_liq = max(cons - ger, 0)
        r = dict(chave=chave, nome=nome, eficiente=efic, kwp=kwp, fv=fv, capex_r=capex, meses=meses,
                 consumo_kwh_mes=cons / 12, geracao_kwh_mes=ger / 12, custo_r_mes=custo / 12,
                 rede_liquida_kwh_mes=rede_liq / 12,
                 autoconsumo_pct=(sum(m["autoconsumo_kwh"] for m in meses) / ger * 100) if ger else 0.0,
                 participacao_renovavel_pct=min(ger, cons) / cons * 100)
        if base is None:
            base = r
        r["economia_kwh_mes"] = base["rede_liquida_kwh_mes"] - r["rede_liquida_kwh_mes"]
        r["economia_pct"] = r["economia_kwh_mes"] / base["rede_liquida_kwh_mes"] * 100
        r["economia_r_mes"] = base["custo_r_mes"] - r["custo_r_mes"]
        r["emissoes_kgco2_ano"] = r["rede_liquida_kwh_mes"] * 12 * fe
        r["emissoes_evitadas_kgco2_ano"] = r["economia_kwh_mes"] * 12 * fe
        if capex:
            # parte da economia que vem do FV (sofre degradação)
            sem_fv = simular(equipamentos, clima, prem, efic, 0.0)
            econ_fv_ano = (sum(m["custo_r"] for m in sem_fv) - custo)
            fluxo, pb = fluxo_caixa(capex, r["economia_r_mes"] * 12, prem, kwp > 0, econ_fv_ano, capex_fv)
            r["fluxo"] = fluxo
            r["payback_anos"] = pb
            r["saldo_25_anos_r"] = fluxo[-1]["acumulado_r"]
        else:
            r["fluxo"], r["payback_anos"], r["saldo_25_anos_r"] = [], None, 0.0
        alternativas.append(r)

    return dict(premissas=prem, equipamentos=equipamentos, clima=clima, medidas=medidas,
                alternativas=alternativas,
                geracao_kwh_kwp_ano=geracao_kwh_kwp_ano(clima, prem["taxa_desempenho_pr"]))


def sensibilidade():
    """Payback das alternativas com FV quando uma premissa varia."""
    base = carregar_premissas()
    casos = [
        ("Cenário base", {}),
        ("Tarifa -20%", {"tarifa_r_kwh": base["tarifa_r_kwh"] * 0.8}),
        ("Tarifa +20%", {"tarifa_r_kwh": base["tarifa_r_kwh"] * 1.2}),
        ("Custo FV -20%", {"custo_fv_r_wp": base["custo_fv_r_wp"] * 0.8}),
        ("Custo FV +20%", {"custo_fv_r_wp": base["custo_fv_r_wp"] * 1.2}),
        ("PR 0,70", {"taxa_desempenho_pr": 0.70}),
        ("PR 0,80", {"taxa_desempenho_pr": 0.80}),
    ]
    linhas = []
    for nome, mud in casos:
        p = dict(base)
        p.update(mud)
        res = avaliar(p)
        alt = {a["chave"]: a for a in res["alternativas"]}
        linhas.append(dict(cenario=nome, payback_a1=alt["a1"]["payback_anos"],
                           payback_a2=alt["a2"]["payback_anos"], payback_a3=alt["a3"]["payback_anos"]))
    return linhas
