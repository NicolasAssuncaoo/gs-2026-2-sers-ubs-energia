# Memória de cálculo — UBS Energia Inteligente (SERS)

> Arquivo gerado automaticamente por `src/gerar_dados.py`. Os valores são **projeções** condicionadas às premissas de `dados/premissas.json`, não resultados garantidos.

## 1. Consumo atual por equipamento

Fórmula: **E = (P × t) / 1000**, multiplicada pela quantidade e pelos dias de uso no mês.

| Equipamento | Qtd | P (W) | h/dia | dias/mês | Cálculo | kWh/mês |
|---|---:|---:|---:|---:|---|---:|
| Lâmpada tubular fluorescente T8 40 W + reator (interna) | 120 | 44 | 12,0 | 22 | 120 × 44 × 12,0 × 22 / 1000 | **1.393,9** |
| Refletor externo 100 W (fachada e estacionamento) | 8 | 100 | 12,0 | 30 | 8 × 100 × 12,0 × 30 / 1000 | **288,0** |
| Ar-condicionado split convencional 12.000 BTU/h | 8 | 1.100 | 8,0 | 22 | 8 × 1.100 × 8,0 × 22 / 1000 | **1.548,8** |
| Câmara refrigerada de vacinas (rede de frio) | 2 | 150 | 24,0 | 30 | 2 × 150 × 24,0 × 30 / 1000 | **216,0** |
| Computador + monitor (recepção e consultórios) | 15 | 120 | 10,0 | 22 | 15 × 120 × 10,0 × 22 / 1000 | **396,0** |
| Autoclave de esterilização | 1 | 2.500 | 2,0 | 22 | 1 × 2.500 × 2,0 × 22 / 1000 | **110,0** |
| Equipo odontológico + compressor | 1 | 1.200 | 5,0 | 22 | 1 × 1.200 × 5,0 × 22 / 1000 | **132,0** |
| Geladeira e bebedouros (copa) | 3 | 80 | 24,0 | 30 | 3 × 80 × 24,0 × 30 / 1000 | **172,8** |
| Outros (impressoras / nebulizadores / rede) | 1 | 400 | 12,0 | 22 | 1 × 400 × 12,0 × 22 / 1000 | **105,6** |
| **Total** | | | | | | **4.363,1 kWh/mês** |

Custo estimado: 4.363,1 kWh × R$ 1,01 = **R$ 4.406,73/mês** (mês de 30 dias).

Na simulação mês a mês (seção 4) usam-se os dias reais de cada mês (média de 30,4) e a variação sazonal da climatização, por isso o consumo médio fica em 4.373 kWh/mês.

## 2. Medidas de eficiência (Alternativa 1)

| Medida | Investimento (R$) | Economia (kWh/mês) | Economia (R$/mês) | Retorno (anos) |
|---|---:|---:|---:|---:|
| Troca por LED tubular 18 W | 4.800,00 | 823,7 | 831,92 | 0,5 |
| Sensores de presença | 1.800,00 | 85,5 | 86,39 | 1,7 |
| Refletores LED 50 W com fotocélula | 1.280,00 | 156,0 | 157,56 | 0,7 |
| Ar-condicionado inverter + automação | 24.800,00 | 532,4 | 537,72 | 3,8 |
| Desligamento automático de TI | 0,00 | 39,6 | 40,00 | — |
| Monitoramento IoT (medição e alertas) | 1.500,00 | 0,0 | 0,00 | — |

## 3. Dimensionamento fotovoltaico

Geração específica: Σ(irradiação diária × dias × PR 0,75) = **1.278 kWh/kWp·ano** (106,5 kWh/kWp·mês).

| Alternativa | Consumo anual (kWh) | Alvo 80% (kWh) | kWp necessário | Módulos de 580 Wp | kWp instalado | Área (m²) |
|---|---:|---:|---:|---:|---:|---:|
| A2 — Solar fotovoltaica | 52.470 | 41.976 | 32,85 | 57 | 33,06 | 148,2 |
| A3 — Eficiência + solar (recomendada) | 32.798 | 26.238 | 20,53 | 36 | 20,88 | 93,6 |

Valor da energia injetada na rede: 1 − (Fio B 30% da tarifa × 60% não compensado em 2026) = **82% do kWh comprado**.

## 4. Comparação das alternativas (período de referência: 1 mês médio de um ano)

| Indicador | Situação atual (referência) | A1 — Eficiência energética | A2 — Solar fotovoltaica | A3 — Eficiência + solar (recomendada) |
|---|---:|---:|---:|---:|
| Consumo da UBS (kWh/mês) | 4.373 | 2.733 | 4.373 | 2.733 |
| Geração solar (kWh/mês) | — | — | 3.520 | 2.223 |
| Energia líquida da rede (kWh/mês) | 4.373 | 2.733 | 852 | 510 |
| Economia energética (kWh/mês) | — | 1.639 | 3.520 | 3.863 |
| Economia energética (%) | — | 37,5 | 80,5 | 88,3 |
| Custo de energia (R$/mês) | 4.416,25 | 2.760,47 | 1.039,92 | 626,03 |
| Redução de custo (R$/mês) | — | 1.655,78 | 3.376,32 | 3.790,21 |
| Participação renovável (%) | — | — | 80,5 | 81,3 |
| Emissões evitadas (kg CO₂/ano) | — | 1.178 | 2.530 | 2.777 |
| Investimento (R$) | — | 34.180,00 | 92.568,00 | 92.644,00 |
| Retorno simples (anos) | — | 1,7 | 2,3 | 2,1 |
| Saldo em 25 anos (R$) | — | 462.553 | 829.423 | 986.970 |

## 5. Sensibilidade do retorno (anos)

| Cenário | A1 | A2 | A3 |
|---|---:|---:|---:|
| Cenário base | 1,7 | 2,3 | 2,1 |
| Tarifa -20% | 2,2 | 3,0 | 2,6 |
| Tarifa +20% | 1,4 | 1,9 | 1,7 |
| Custo FV -20% | 1,7 | 1,9 | 1,8 |
| Custo FV +20% | 1,7 | 2,8 | 2,3 |
| PR 0,70 | 1,7 | 2,5 | 2,2 |
| PR 0,80 | 1,7 | 2,2 | 2,0 |

## 6. Monitoramento (semana simulada de Nov, alternativa A3)

- Consumo da semana: 682 kWh; geração solar: 458 kWh
- Ocorrências: 3 (17 horas com alerta) | Horas da rede de frio fora de 2–8 °C: 2 | Desperdício detectado: 7,7 kWh

- **Qua 20h → Qui 05h (10 h)** — Consumo: Consumo fora do expediente: 1,7 kW (esperado 0,9 kW). Verificar ar-condicionado ou iluminação ligados.
- **Sex 03h → Sex 04h (2 h)** — Rede de frio: Câmara de vacinas a 8,6 °C (faixa segura: 2 a 8 °C). Acionar a equipe.
- **Sáb 10h → Sáb 14h (5 h)** — Solar: Geração de 3,9 kWh, esperado 8,7 kWh para a irradiação medida. Verificar inversor ou sujeira nos módulos.
