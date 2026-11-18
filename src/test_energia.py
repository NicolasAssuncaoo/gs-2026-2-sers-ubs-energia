"""Testes dos cálculos (rodar com: python -m unittest discover src)."""
import unittest

import energia
import monitoramento


class TestEnergia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prem = energia.carregar_premissas()
        cls.eqs = energia.carregar_equipamentos()
        cls.clima = energia.carregar_clima()
        cls.res = energia.avaliar(cls.prem, cls.eqs, cls.clima)
        cls.alt = {a["chave"]: a for a in cls.res["alternativas"]}

    def test_formula_do_enunciado(self):
        # E = (P × t) / 1000  ->  1.100 W durante 8 h = 8,8 kWh
        self.assertAlmostEqual(energia.energia_kwh(1100, 8), 8.8)

    def test_consumo_iluminacao_conferido_a_mao(self):
        lamp = next(e for e in self.eqs if e["id"] == "ilum_int")
        # 120 lâmpadas × 44 W × 12 h × 22 dias / 1000 = 1.393,92 kWh
        self.assertAlmostEqual(energia.consumo_equipamento_mes(lamp), 1393.92)
        # 120 × 18 W × 10,2 h × 22 / 1000 = 484,704 kWh
        self.assertAlmostEqual(energia.consumo_equipamento_mes(lamp, True), 484.704)

    def test_total_mensal(self):
        self.assertAlmostEqual(energia.consumo_total_mes(self.eqs), 4363.12, places=2)

    def test_sazonalidade_preserva_media(self):
        fatores = [m["fator_climatizacao"] for m in self.clima]
        self.assertAlmostEqual(sum(fatores) / 12, 1.0)

    def test_perfil_horario_bate_com_consumo_diario(self):
        # soma do perfil de um dia útil = energia diária dos itens de dia útil + itens 24 h
        perfil = energia.perfil_horario(self.eqs, False, True, 1.0)
        diario = sum(e["quantidade"] * energia.energia_kwh(e["potencia_w"], e["horas_dia"]) for e in self.eqs)
        self.assertAlmostEqual(sum(perfil), diario, places=6)

    def test_geracao_fv_diaria(self):
        # 10 kWp × 5 kWh/m²·dia × PR 0,75 = 37,5 kWh/dia
        self.assertAlmostEqual(sum(energia.perfil_fv(10, 5, 0.75, 0)), 37.5)

    def test_dimensionamento_atende_cobertura(self):
        a3 = self.alt["a3"]
        self.assertGreaterEqual(a3["geracao_kwh_mes"], 0.8 * a3["consumo_kwh_mes"] - 1)
        self.assertLessEqual(a3["fv"]["area_m2"], self.prem["area_telhado_util_m2"])

    def test_alternativa_renovavel_incluida(self):
        self.assertTrue(any(a["kwp"] > 0 for a in self.res["alternativas"]))

    def test_economias_positivas_e_coerentes(self):
        for k in ("a1", "a2", "a3"):
            self.assertGreater(self.alt[k]["economia_r_mes"], 0)
        self.assertLess(self.alt["a3"]["custo_r_mes"], self.alt["a1"]["custo_r_mes"])
        self.assertGreaterEqual(self.alt["a3"]["custo_r_mes"],
                                self.prem["custo_disponibilidade_kwh"] * self.prem["tarifa_r_kwh"] - 0.01)

    def test_emissoes_evitadas(self):
        a1 = self.alt["a1"]
        esperado = a1["economia_kwh_mes"] * 12 * self.prem["fator_emissao_kgco2_kwh"]
        self.assertAlmostEqual(a1["emissoes_evitadas_kgco2_ano"], esperado)

    def test_payback_coerente_com_fluxo(self):
        a1 = self.alt["a1"]
        self.assertAlmostEqual(a1["payback_anos"], a1["capex_r"] / (a1["economia_r_mes"] * 12), places=6)

    def test_monitoramento_detecta_as_tres_falhas(self):
        mon = monitoramento.simular_semana()
        tipos = {o["tipo"] for o in mon["ocorrencias"]}
        self.assertEqual(tipos, {"Consumo", "Rede de frio", "Solar"})
        self.assertEqual(mon["resumo"]["ocorrencias"], 3)


if __name__ == "__main__":
    unittest.main()
