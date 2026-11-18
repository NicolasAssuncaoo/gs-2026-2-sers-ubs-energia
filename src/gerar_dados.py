"""
Gera os resultados da análise e os dados do dashboard.

Uso:
    python src/gerar_dados.py

Saídas:
    resultados/consumo_por_equipamento.csv
    resultados/comparacao_alternativas.csv
    resultados/serie_mensal.csv
    resultados/sensibilidade.csv
    resultados/monitoramento_semana.csv
    resultados/memoria_de_calculo.md
    dashboard/dados_energia.js   (lido pelo dashboard/index.html)
"""
import csv
import json
import os

import energia
import monitoramento

RAIZ = energia.RAIZ
RES = os.path.join(RAIZ, "resultados")
DASH = os.path.join(RAIZ, "dashboard")


def br(v, casas=0):
    """Formata número no padrão brasileiro."""
    if v is None:
        return "—"
    s = f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def salvar_csv(nome, linhas):
    with open(os.path.join(RES, nome), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)


def main():
    os.makedirs(RES, exist_ok=True)
    res = energia.avaliar()
    prem, eqs, alts = res["premissas"], res["equipamentos"], res["alternativas"]
    sens = energia.sensibilidade()
    mon = monitoramento.simular_semana()
    alt = {a["chave"]: a for a in alts}

    # --- consumo por equipamento -------------------------------------------------
    consumo_eq = []
    for e in eqs:
        antes = energia.consumo_equipamento_mes(e)
        depois = energia.consumo_equipamento_mes(e, True)
        consumo_eq.append(dict(equipamento=e["equipamento"], categoria=e["categoria"], quantidade=e["quantidade"],
                               potencia_w=e["potencia_w"], horas_dia=e["horas_dia"], dias_mes=e["dias_mes"],
                               kwh_mes_atual=round(antes, 1),
                               potencia_eficiente_w=e["potencia_eficiente_w"],
                               horas_dia_eficiente=e["horas_dia_eficiente"],
                               kwh_mes_eficiente=round(depois, 1), economia_kwh_mes=round(antes - depois, 1),
                               critico=e["critico"]))
    salvar_csv("consumo_por_equipamento.csv", consumo_eq)

    # --- comparação -------------------------------------------------------------
    comp = []
    for a in alts:
        comp.append(dict(alternativa=a["nome"], potencia_fv_kwp=round(a["kwp"], 2),
                         consumo_kwh_mes=round(a["consumo_kwh_mes"], 1),
                         geracao_fv_kwh_mes=round(a["geracao_kwh_mes"], 1),
                         energia_rede_liquida_kwh_mes=round(a["rede_liquida_kwh_mes"], 1),
                         economia_kwh_mes=round(a["economia_kwh_mes"], 1), economia_pct=round(a["economia_pct"], 1),
                         custo_r_mes=round(a["custo_r_mes"], 2), economia_r_mes=round(a["economia_r_mes"], 2),
                         participacao_renovavel_pct=round(a["participacao_renovavel_pct"], 1),
                         emissoes_evitadas_kgco2_ano=round(a["emissoes_evitadas_kgco2_ano"], 1),
                         investimento_r=round(a["capex_r"], 2),
                         payback_anos=round(a["payback_anos"], 1) if a["payback_anos"] else "",
                         saldo_25_anos_r=round(a["saldo_25_anos_r"], 2)))
    salvar_csv("comparacao_alternativas.csv", comp)

    serie = []
    for i, m in enumerate(res["clima"]):
        linha = dict(mes=m["mes"])
        for a in alts:
            mm = a["meses"][i]
            linha[f"{a['chave']}_consumo_kwh"] = round(mm["consumo_kwh"], 1)
            linha[f"{a['chave']}_geracao_kwh"] = round(mm["geracao_kwh"], 1)
            linha[f"{a['chave']}_custo_r"] = round(mm["custo_r"], 2)
        serie.append(linha)
    salvar_csv("serie_mensal.csv", serie)
    salvar_csv("sensibilidade.csv", [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in s.items()}
                                     for s in sens])
    salvar_csv("monitoramento_semana.csv", mon["serie"])

    # --- memória de cálculo (markdown) -----------------------------------------
    t = prem["tarifa_r_kwh"]
    md = ["# Memória de cálculo — UBS Energia Inteligente (SERS)", "",
          "> Arquivo gerado automaticamente por `src/gerar_dados.py`. Os valores são **projeções** "
          "condicionadas às premissas de `dados/premissas.json`, não resultados garantidos.", "",
          "## 1. Consumo atual por equipamento", "",
          "Fórmula: **E = (P × t) / 1000**, multiplicada pela quantidade e pelos dias de uso no mês.", "",
          "| Equipamento | Qtd | P (W) | h/dia | dias/mês | Cálculo | kWh/mês |", "|---|---:|---:|---:|---:|---|---:|"]
    total = 0
    for e, c in zip(eqs, consumo_eq):
        total += c["kwh_mes_atual"]
        md.append(f"| {e['equipamento']} | {e['quantidade']} | {br(e['potencia_w'])} | {br(e['horas_dia'], 1)} | "
                  f"{e['dias_mes']} | {e['quantidade']} × {br(e['potencia_w'])} × {br(e['horas_dia'], 1)} × "
                  f"{e['dias_mes']} / 1000 | **{br(c['kwh_mes_atual'], 1)}** |")
    md += [f"| **Total** | | | | | | **{br(total, 1)} kWh/mês** |", "",
           f"Custo estimado: {br(total, 1)} kWh × R$ {br(t, 2)} = **R$ {br(total * t, 2)}/mês** (mês de 30 dias).", "",
           "Na simulação mês a mês (seção 4) usam-se os dias reais de cada mês (média de 30,4) e a variação "
           "sazonal da climatização, por isso o consumo médio fica em "
           f"{br(alt['atual']['consumo_kwh_mes'], 0)} kWh/mês.", "",
           "## 2. Medidas de eficiência (Alternativa 1)", "",
           "| Medida | Investimento (R$) | Economia (kWh/mês) | Economia (R$/mês) | Retorno (anos) |",
           "|---|---:|---:|---:|---:|"]
    for m in res["medidas"]:
        md.append(f"| {m['medida']} | {br(m['custo'], 2)} | {br(m['economia_kwh_mes'], 1)} | "
                  f"{br(m['economia_r_mes'], 2)} | {br(m['payback_anos'], 1) if m['payback_anos'] else '—'} |")
    gk = res["geracao_kwh_kwp_ano"]
    md += ["", "## 3. Dimensionamento fotovoltaico", "",
           f"Geração específica: Σ(irradiação diária × dias × PR {br(prem['taxa_desempenho_pr'], 2)}) = "
           f"**{br(gk, 0)} kWh/kWp·ano** ({br(gk / 12, 1)} kWh/kWp·mês).", "",
           "| Alternativa | Consumo anual (kWh) | Alvo 80% (kWh) | kWp necessário | Módulos de 580 Wp | kWp instalado | Área (m²) |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for k in ("a2", "a3"):
        a = alt[k]
        fv = a["fv"]
        anual = a["consumo_kwh_mes"] * 12
        md.append(f"| {a['nome']} | {br(anual)} | {br(anual * 0.8)} | {br(fv['kwp_necessario'], 2)} | "
                  f"{fv['modulos']} | {br(fv['kwp'], 2)} | {br(fv['area_m2'], 1)} |")
    md += ["", "Valor da energia injetada na rede: 1 − (Fio B 30% da tarifa × 60% não compensado em 2026) = "
               "**82% do kWh comprado**.", "",
           "## 4. Comparação das alternativas (período de referência: 1 mês médio de um ano)", "",
           "| Indicador | " + " | ".join(a["nome"] for a in alts) + " |", "|---|" + "---:|" * len(alts)]
    linhas = [
        ("Consumo da UBS (kWh/mês)", "consumo_kwh_mes", 0), ("Geração solar (kWh/mês)", "geracao_kwh_mes", 0),
        ("Energia líquida da rede (kWh/mês)", "rede_liquida_kwh_mes", 0),
        ("Economia energética (kWh/mês)", "economia_kwh_mes", 0), ("Economia energética (%)", "economia_pct", 1),
        ("Custo de energia (R$/mês)", "custo_r_mes", 2), ("Redução de custo (R$/mês)", "economia_r_mes", 2),
        ("Participação renovável (%)", "participacao_renovavel_pct", 1),
        ("Emissões evitadas (kg CO₂/ano)", "emissoes_evitadas_kgco2_ano", 0),
        ("Investimento (R$)", "capex_r", 2), ("Retorno simples (anos)", "payback_anos", 1),
        ("Saldo em 25 anos (R$)", "saldo_25_anos_r", 0)]
    for rot, k, c in linhas:
        md.append(f"| {rot} | " + " | ".join(br(a[k], c) if a[k] else "—" for a in alts) + " |")
    md += ["", "## 5. Sensibilidade do retorno (anos)", "", "| Cenário | A1 | A2 | A3 |", "|---|---:|---:|---:|"]
    for s in sens:
        md.append(f"| {s['cenario']} | {br(s['payback_a1'], 1)} | {br(s['payback_a2'], 1)} | {br(s['payback_a3'], 1)} |")
    md += ["", "## 6. Monitoramento (semana simulada de " + mon["resumo"]["mes"] + ", alternativa A3)", "",
           f"- Consumo da semana: {br(mon['resumo']['consumo_semana_kwh'], 0)} kWh; geração solar: "
           f"{br(mon['resumo']['geracao_semana_kwh'], 0)} kWh",
           f"- Ocorrências: {mon['resumo']['ocorrencias']} ({mon['resumo']['alertas']} horas com alerta) | Horas da rede de frio fora de 2–8 °C: "
           f"{mon['resumo']['horas_rede_frio_fora']} | Desperdício detectado: "
           f"{br(mon['resumo']['desperdicio_detectado_kwh'], 1)} kWh", ""]
    for o in mon["ocorrencias"]:
        periodo = o["inicio"] if o["horas"] == 1 else f"{o['inicio']} → {o['fim']} ({o['horas']} h)"
        md.append(f"- **{periodo}** — {o['tipo']}: {o['mensagem']}")
    with open(os.path.join(RES, "memoria_de_calculo.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    # --- dados do dashboard ------------------------------------------------------
    def limpa(a):
        return {k: v for k, v in a.items() if k not in ("meses", "fv", "fluxo")} | {
            "meses": [{k: round(v, 2) if isinstance(v, float) else v for k, v in m.items()} for m in a["meses"]],
            "fluxo": [{k: round(v, 2) if isinstance(v, float) else v for k, v in f.items()} for f in a["fluxo"]],
            "fv": a["fv"]}
    dados = dict(
        gerado_por="src/gerar_dados.py",
        premissas=prem["_bruto"],
        equipamentos=consumo_eq,
        medidas=[{k: v for k, v in m.items() if k != "ids"} for m in res["medidas"]],
        alternativas=[limpa(a) for a in alts],
        sensibilidade=sens,
        geracao_kwh_kwp_ano=gk,
        monitoramento=mon,
        qualitativo=json.load(open(os.path.join(RAIZ, "dados", "alternativas_qualitativo.json"), encoding="utf-8")),
    )
    os.makedirs(DASH, exist_ok=True)
    with open(os.path.join(DASH, "dados_energia.js"), "w", encoding="utf-8") as f:
        f.write("// Gerado automaticamente por src/gerar_dados.py — não editar à mão.\n")
        f.write("window.DADOS_SERS = " + json.dumps(dados, ensure_ascii=False) + ";\n")

    print("Resultados gerados em resultados/ e dashboard/dados_energia.js")
    for a in alts:
        print(f"  {a['nome']:<42} {a['rede_liquida_kwh_mes']:8.0f} kWh/mês  R$ {a['custo_r_mes']:8.2f}/mês  "
              f"payback {a['payback_anos'] or 0:4.1f} anos")
    print(f"  Monitoramento: {mon['resumo']['ocorrencias']} ocorrências na semana simulada")


if __name__ == "__main__":
    main()
