"""Gera docs/diagrama_solucao.svg (diagrama de blocos da solução) — python src/gerar_diagrama.py"""
import os
import shutil
from html import escape

import energia

RAIZ = energia.RAIZ
W, H = 1280, 760
ENERGIA, DADOS, COMANDO = "#e8590c", "#1c7ed6", "#2b8a3e"


def caixa(x, y, w, h, titulo, linhas, cor, fundo):
    s = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fundo}" stroke="{cor}" stroke-width="2"/>',
         f'<text x="{x + 14}" y="{y + 26}" font-size="15" font-weight="700" fill="{cor}">{escape(titulo)}</text>']
    for i, l in enumerate(linhas):
        s.append(f'<text x="{x + 14}" y="{y + 50 + i * 20}" font-size="13.5" fill="#243447">{escape(l)}</text>')
    return "\n".join(s)


def seta(x1, y1, x2, y2, cor, tipo="", rot=None, rx=0, ry=0):
    dash = {"dados": ' stroke-dasharray="7 5"', "comando": ' stroke-dasharray="2 5"'}.get(tipo, "")
    m = {"#e8590c": "e", "#1c7ed6": "d", "#2b8a3e": "c"}[cor]
    s = f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{cor}" stroke-width="2.5" fill="none"{dash} marker-end="url(#m{m})"/>'
    if rot:
        s += (f'<text x="{(x1 + x2) / 2 + rx}" y="{(y1 + y2) / 2 + ry}" font-size="12" fill="{cor}" '
              f'text-anchor="middle" font-weight="600">{rot}</text>')
    return s


def secao(x, y, w, h, nome):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="none" stroke="#c5d3e3" '
            f'stroke-dasharray="4 4"/><text x="{x + 12}" y="{y - 8}" font-size="13" font-weight="700" '
            f'fill="#5b6b7f" letter-spacing="1">{nome}</text>')


def main():
    res = energia.avaliar()
    a3 = next(a for a in res["alternativas"] if a["chave"] == "a3")
    kwp, mod = a3["kwp"], a3["fv"]["modulos"]
    fmt = lambda v: f"{v:.2f}".replace(".", ",")
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
         'font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif">',
         '<defs>'] + [f'<marker id="m{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                      f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
                      for k, c in (("e", ENERGIA), ("d", DADOS), ("c", COMANDO))] + ['</defs>',
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         '<text x="40" y="44" font-size="24" font-weight="800" fill="#0f2a44">Diagrama de blocos — UBS Energia '
         'Inteligente (alternativa recomendada A3)</text>',
         '<text x="40" y="68" font-size="14" fill="#5b6b7f">Contribuição SERS ao Neighborhood Action Dashboard · '
         'diagrama conceitual, sem circuito elétrico detalhado</text>']

    # seções
    p += [secao(28, 100, 300, 330, "FONTES DE ENERGIA"), secao(352, 100, 250, 330, "DISTRIBUIÇÃO E MEDIÇÃO"),
          secao(626, 100, 300, 330, "EQUIPAMENTOS CONSUMIDORES"), secao(950, 100, 302, 330, "INDICADORES NO DASHBOARD"),
          secao(28, 470, 1224, 268, "DADOS, LÓGICA E PROCESSAMENTO")]
    # fontes
    p.append(caixa(44, 116, 268, 120, f"Sistema fotovoltaico {fmt(kwp)} kWp",
                   [f"{mod} módulos de 580 Wp no telhado", "orientação norte, inclinação ~23°",
                    "→ inversor on-grid (CC → CA)"], ENERGIA, "#fff4e6"))
    p.append(caixa(44, 256, 268, 150, "Rede da distribuidora (SIN)",
                   ["Enel SP — baixa tensão (B3)", "supre o que o sol não cobre", "recebe o excedente (créditos,",
                    "Lei 14.300/2022)", ], ENERGIA, "#fff4e6"))
    # distribuição
    p.append(caixa(368, 116, 218, 150, "Quadro geral + medidor",
                   ["medidor bidirecional", "da distribuidora", "medidores internos por", "circuito (IoT)"],
                   ENERGIA, "#fff4e6"))
    p.append(caixa(368, 286, 218, 120, "Circuito prioritário",
                   ["rede de frio separada,", "com nobreak", "(vacinas nunca desligam)"], ENERGIA, "#fff4e6"))
    # consumidores
    cons = [("Iluminação LED + sensores", "120 tubos 18 W · 8 refletores 50 W"),
            ("Ar-condicionado inverter", "8 splits de 12.000 BTU/h"),
            ("TI e equipamentos de saúde", "computadores, autoclave, odonto"),
            ("Câmaras de vacinas (2)", "carga crítica 24 h, de 2 a 8 °C")]
    for i, (t, l) in enumerate(cons):
        y = 116 + i * 76
        p.append(f'<rect x="642" y="{y}" width="268" height="64" rx="10" fill="#fff4e6" stroke="{ENERGIA}" stroke-width="2"/>'
                 f'<text x="656" y="{y + 26}" font-size="15" font-weight="700" fill="{ENERGIA}">{t}</text>'
                 f'<text x="656" y="{y + 48}" font-size="13" fill="#243447">{l}</text>')
    # indicadores
    inds = ["Consumo de energia (kWh/mês)", "Economia energética (kWh/mês e %)", "Redução de custo (R$/mês)",
            "Participação renovável (%)", "Emissões evitadas (kg CO₂/ano)", "Retorno do investimento (anos)",
            "Alertas: consumo, rede de frio, solar"]
    p.append(f'<rect x="966" y="116" width="270" height="290" rx="12" fill="#e7f5ff" stroke="{DADOS}" stroke-width="2"/>'
             f'<text x="980" y="142" font-size="14.5" font-weight="700" fill="{DADOS}">Neighborhood Action Dashboard</text>')
    for i, t in enumerate(inds):
        p.append(f'<text x="982" y="{172 + i * 32}" font-size="13.5" fill="#243447">● {escape(t)}</text>')
    # dados/lógica
    p.append(caixa(44, 488, 300, 230, "Sensores e dados de consumo",
                   ["sensores de corrente (SCT-013)", "por circuito", "sensores de presença nas salas",
                    "termômetros das câmaras", "de vacinas", "dados do inversor solar",
                    "(geração e irradiação)"], DADOS, "#e7f5ff"))
    p.append(caixa(380, 488, 420, 230, "Lógica de monitoramento e automação (ESP32)",
                   ["apaga luzes após 10 min sem presença",
                    "desliga o ar fora do horário (7h às 19h) e em sala vazia",
                    "alarme se a vacina sair da faixa de 2 a 8 °C",
                    "alerta: consumo noturno > esperado × 1,2 + 0,3 kW",
                    "alerta: geração < 70% do esperado pela irradiação",
                    "envia leituras a cada 15 min (MQTT/HTTP)"], DADOS, "#e7f5ff"))
    p.append(caixa(836, 488, 400, 230, "Processamento (Python)",
                   ["energia.py: E = P × t / 1000, consumo,", "geração solar, custos, CO₂ e retorno",
                    "monitoramento.py: compara medido × esperado", "e gera as ocorrências",
                    "gerar_dados.py: resultados/ +", "dashboard/dados_energia.js"], DADOS, "#e7f5ff"))
    # setas de energia
    p += [seta(312, 176, 366, 176, ENERGIA),
          f'<path d="M314,330 L340,330 L340,240 L366,240" stroke="{ENERGIA}" stroke-width="2.5" fill="none" '
          'marker-start="url(#me)" marker-end="url(#me)"/>',
          seta(586, 160, 640, 148, ENERGIA), seta(586, 190, 640, 224, ENERGIA), seta(586, 230, 640, 300, ENERGIA),
          seta(586, 346, 640, 376, ENERGIA)]
    # setas de dados / comandos
    p += [seta(194, 410, 194, 486, DADOS, "dados", rot="medições", rx=36), seta(344, 600, 378, 600, DADOS, "dados"),
          seta(800, 600, 834, 600, DADOS, "dados"), seta(1036, 488, 1036, 410, DADOS, "dados", rot="indicadores", rx=48),
          seta(700, 488, 760, 412, COMANDO, "comando", rot="liga/desliga luzes e ar (relés)", rx=96, ry=6),
          seta(476, 268, 476, 284, ENERGIA)]
    # legenda
    lx, ly = 540, 742
    p += [f'<line x1="{lx}" y1="{ly - 4}" x2="{lx + 34}" y2="{ly - 4}" stroke="{ENERGIA}" stroke-width="3"/>'
          f'<text x="{lx + 42}" y="{ly}" font-size="13" fill="#243447">fluxo de energia</text>',
          f'<line x1="{lx + 170}" y1="{ly - 4}" x2="{lx + 204}" y2="{ly - 4}" stroke="{DADOS}" stroke-width="3" '
          f'stroke-dasharray="7 5"/><text x="{lx + 212}" y="{ly}" font-size="13" fill="#243447">dados</text>',
          f'<line x1="{lx + 290}" y1="{ly - 4}" x2="{lx + 324}" y2="{ly - 4}" stroke="{COMANDO}" stroke-width="3" '
          f'stroke-dasharray="2 5"/><text x="{lx + 332}" y="{ly}" font-size="13" fill="#243447">comandos de automação</text>']
    p.append("</svg>")
    os.makedirs(os.path.join(RAIZ, "docs"), exist_ok=True)
    destino = os.path.join(RAIZ, "docs", "diagrama_solucao.svg")
    with open(destino, "w", encoding="utf-8") as f:
        f.write("\n".join(p))
    shutil.copy(destino, os.path.join(RAIZ, "dashboard", "diagrama_solucao.svg"))
    print("docs/diagrama_solucao.svg gerado")


if __name__ == "__main__":
    main()
