import unittest
from io import BytesIO
from pathlib import Path

import pandas as pd
from docx import Document
from streamlit.testing.v1 import AppTest
from analisis import INTERVALOS, leer_archivo, preparar, resumir, informe_word

ROOT = Path(__file__).resolve().parents[1]

class AnalisisTest(unittest.TestCase):
    def test_ejemplo_e_informe(self):
        df = leer_archivo((ROOT / 'datos/ejemplo.csv').read_bytes(), 'ejemplo.csv')
        datos, invalidos = preparar(df, {k:k for k in INTERVALOS})
        resumen, alertas = resumir(datos, INTERVALOS)
        self.assertEqual(resumen['Fuera de intervalo'].tolist(), [2, 1, 2])
        self.assertAlmostEqual(resumen.iloc[0]['Promedio'], 42.8 / 6)
        self.assertEqual(len(alertas), 5)
        doc = Document(BytesIO(informe_word(resumen, alertas, INTERVALOS, invalidos, 'ejemplo.csv')))
        self.assertEqual(len(doc.tables), 6)
        self.assertIn('didácticos', '\n'.join(p.text for p in doc.paragraphs))

    def test_informe_detallado_con_datos_ausentes(self):
        df = pd.DataFrame({'ph':[None, 'error'], 'temperatura':[15, 31], 'turbidez':[0, 5]})
        datos, invalidos = preparar(df, {k:k for k in INTERVALOS})
        resumen, alertas = resumir(datos, INTERVALOS)
        contenido = informe_word(resumen, alertas, INTERVALOS, invalidos, 'prueba.csv',
                                 datos, {'Proyecto':'Campaña de prueba', 'Lugar':'Río de ejemplo'})
        doc = Document(BytesIO(contenido))
        texto = '\n'.join([p.text for p in doc.paragraphs] + [c.text for t in doc.tables for r in t.rows for c in r.cells])
        self.assertEqual(len(doc.inline_shapes), 3)
        self.assertIn('Campaña de prueba', texto)
        self.assertIn('Sin datos válidos: no es posible evaluar', texto)
        self.assertIn('1 de 2 valores válidos (50.0%)', texto)
        self.assertIn('100.0% excluido', texto)
        self.assertIn('no representan normas', texto)

    def test_excel_y_csv_decimal(self):
        df = pd.DataFrame({'ph':[7.0], 'temperatura':[20], 'turbidez':[3]})
        salida = BytesIO()
        df.to_excel(salida, index=False)
        leido = leer_archivo(salida.getvalue(), 'ejemplo.xlsx')
        datos_excel, _ = preparar(leido, {k:k for k in INTERVALOS})
        self.assertEqual(datos_excel.iloc[0].tolist(), [7,20,3])
        csv = b'ph;temperatura;turbidez\n7,2;20,5;3,1\n'
        datos, _ = preparar(leer_archivo(csv, 'a.csv'), {k:k for k in INTERVALOS})
        self.assertEqual(datos.iloc[0].tolist(), [7.2,20.5,3.1])

    def test_invalidos_y_limites_inclusivos(self):
        df = pd.DataFrame({'ph':['6.5','8.5','error'], 'temperatura':[15,30,float('inf')], 'turbidez':[0,5,None]})
        datos, invalidos = preparar(df, {k:k for k in INTERVALOS})
        self.assertEqual(list(invalidos.values()), [1,1,1])
        _, alertas = resumir(datos, INTERVALOS)
        self.assertTrue(alertas.empty)
        with self.assertRaises(ValueError):
            resumir(datos, {**INTERVALOS, 'ph':(8,6)})

    def test_interfaz_y_error_intervalo(self):
        app = AppTest.from_file(str(ROOT / 'app.py')).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual([m.value for m in app.metric], ['6','18','5'])
        self.assertFalse(app.error)
        app.button[0].click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(len(app.get('download_button')), 2)
        app.number_input(key='min_ph').set_value(10.0).run()
        self.assertTrue(app.error)
        self.assertFalse(app.exception)

if __name__ == '__main__':
    unittest.main()
