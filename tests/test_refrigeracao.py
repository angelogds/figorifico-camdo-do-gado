import unittest

from backend.server import RefrigeracaoEquipamentoCreate, analisar_leitura_refrigeracao
from pydantic import ValidationError


class RefrigeracaoAnalysisTest(unittest.TestCase):
    equipamento = {'nome': 'Câmara 01', 'temperatura_minima': -18.0, 'temperatura_maxima': -12.0, 'tolerancia': 2.0}

    def test_classifica_temperatura_normal_atencao_e_critica(self):
        self.assertEqual(analisar_leitura_refrigeracao(self.equipamento, {'temperatura': -15.0})['classificacao'], 'normal')
        self.assertEqual(analisar_leitura_refrigeracao(self.equipamento, {'temperatura': -13.0})['classificacao'], 'atencao')
        self.assertEqual(analisar_leitura_refrigeracao(self.equipamento, {'temperatura': -10.0})['tipo_alerta'], 'temperatura_alta')
        self.assertEqual(analisar_leitura_refrigeracao(self.equipamento, {'temperatura': -21.0})['tipo_alerta'], 'temperatura_baixa')

    def test_prioriza_equipamento_desligado_e_detecta_variacao_brusca(self):
        desligado = analisar_leitura_refrigeracao(self.equipamento, {'temperatura': -15.0, 'status_funcionamento': 'desligado'})
        self.assertEqual(desligado['classificacao'], 'equipamento_desligado')
        variacao = analisar_leitura_refrigeracao(self.equipamento, {'temperatura': -13.0}, {'temperatura': -18.0})
        self.assertEqual(variacao['classificacao'], 'variacao_brusca')

    def test_valida_limites_e_horarios_do_equipamento(self):
        with self.assertRaises(ValidationError):
            RefrigeracaoEquipamentoCreate(codigo='CAM-01', nome='Câmara 01', temperatura_minima=-10, temperatura_maxima=-18)
        with self.assertRaises(ValidationError):
            RefrigeracaoEquipamentoCreate(codigo='CAM-01', nome='Câmara 01', temperatura_minima=-18, temperatura_maxima=-10, horarios_leitura=['25:00'])


if __name__ == '__main__':
    unittest.main()
