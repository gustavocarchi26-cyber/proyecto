"""Regresiones de unidades, resultados censurados, opcionalidad e informes."""
from io import BytesIO
from pathlib import Path
import unittest
import zipfile

import pandas as pd
from docx import Document
from docx.oxml.ns import qn
from streamlit.testing.v1 import AppTest

from analisis import preparar, resumir, leer_archivo, informe_word
from parametros import PARAMETROS, INTERVALOS

ROOT = Path(__file__).resolve().parents[1]


class Version03Test(unittest.TestCase):
    def test_metales_microgramos_y_lc_no_son_cero(self):
        df = pd.DataFrame({'Pb': ['10', '20', '<5', '<LC', '', 'ND', 'infinito', '0']})
        datos, excluidos = preparar(df, {'plomo': 'Pb'}, {'plomo': 'µg/L'})
        resumen, alertas = resumir(datos, {'plomo': (0.0, 0.015)})
        self.assertAlmostEqual(resumen.iloc[0]['Promedio'], 0.01)
        self.assertEqual(resumen.iloc[0]['Válidos'], 3)
        self.assertEqual(excluidos['plomo'], 5)
        self.assertEqual(alertas['Medición'].tolist(), [2])
        self.assertTrue(pd.isna(datos.loc[3, 'plomo']))
        detalle = datos.attrs['detalle']
        self.assertEqual(detalle['Estado'].tolist(), ['Cuantificado', 'Cuantificado', 'Inferior a LC', 'Inferior a LC', 'Ausente', 'Inválido', 'Inválido', 'Cuantificado'])
        self.assertEqual(detalle.loc[2, 'Original'], '<5')
        self.assertAlmostEqual(detalle.loc[2, 'LC declarado'], 0.005)

    def test_no_conversion_ambigua_ni_especies(self):
        with self.assertRaises(ValueError):
            preparar(pd.DataFrame({'x': [1]}), {'nitratos_no3': 'x'}, {'nitratos_no3': 'mg N/L'})
        with self.assertRaises(ValueError):
            preparar(pd.DataFrame({'x': [1]}), {'conductividad': 'x'}, {'conductividad': 'mg/L'})
        df = pd.DataFrame({'no3': [4.0], 'n': [1.0]})
        datos, _ = preparar(df, {'nitratos_no3':'no3', 'nitratos_n':'n'})
        self.assertEqual(datos.iloc[0].tolist(), [4.0, 1.0])

    def test_todos_los_parametros_opcionales_sin_intervalo(self):
        df = pd.DataFrame({clave: [1.0, 3.0] for clave in PARAMETROS})
        datos, _ = preparar(df, {clave:clave for clave in PARAMETROS})
        resumen, alertas = resumir(datos, {})
        self.assertEqual(len(resumen), 14)
        self.assertEqual(resumen['Promedio'].tolist(), [2.0] * 14)
        self.assertEqual(resumen['Mínimo'].tolist(), [1.0] * 14)
        self.assertEqual(resumen['Máximo'].tolist(), [3.0] * 14)
        self.assertTrue(resumen['Fuera de intervalo'].isna().all())
        self.assertTrue(alertas.empty)
        uno, _ = preparar(df, {'mercurio':'mercurio'})
        self.assertEqual(uno.columns.tolist(), ['mercurio'])

    def test_invalidos_y_intervalos_no_finitos(self):
        df = pd.DataFrame({'x': ['<0', '<-1', '<1e999', '<=3', '10 mg/L', '1e999', '1,5', '<0,5', '< LQ']})
        datos, _ = preparar(df, {'plomo':'x'})
        self.assertEqual(datos.notna().sum().sum(), 1)
        self.assertEqual(datos.loc[7, 'plomo'], 1.5)
        self.assertEqual(datos.attrs['detalle']['Estado'].tolist().count('Inferior a LC'), 2)
        for limites in ((float('nan'), 1), (0, float('inf')), (1,1), (3,1)):
            with self.assertRaises(ValueError):
                resumir(datos, {'plomo': limites})
        with self.assertRaises(ValueError):
            preparar(df, {'plomo':'x', 'cadmio':'x'})

    def test_identificacion_codigos_originales_y_precision_word(self):
        df = leer_archivo(b'codigo_muestra,fecha,metodo_analitico,mercurio\n0001,01/02/2026,Metodo declarado,0.0001\n0002,02/02/2026,Metodo declarado,<0.00005\n', 'a.csv')
        self.assertEqual(df.loc[0,'codigo_muestra'], '0001')
        datos, excluidos = preparar(df, {'mercurio':'mercurio'}, columnas_meta={'Código de muestra':'codigo_muestra', 'Fecha':'fecha', 'Método analítico':'metodo_analitico'})
        resumen, alertas = resumir(datos, {})
        contenido = informe_word(resumen, alertas, {}, excluidos, 'a.csv', datos,
                                 {'Lugar':'Lugar declarado', 'Responsable':'Responsable declarado', 'Observaciones de campo':'Agua observada en campo'})
        doc = Document(BytesIO(contenido))
        texto = '\n'.join([p.text for p in doc.paragraphs] + [c.text for t in doc.tables for r in t.rows for c in r.cells])
        for esperado in ('0001', '01/02/2026', 'Metodo declarado', 'Lugar declarado', 'Responsable declarado', '<0.00005', '0.0001', 'Sin intervalo', 'Observaciones de campo', 'Resultados', 'Interpretación descriptiva'):
            self.assertIn(esperado, texto)
        self.assertEqual(len(doc.inline_shapes), 1)
        ancho = doc.sections[0].page_width - doc.sections[0].left_margin - doc.sections[0].right_margin
        for t in doc.tables:
            self.assertLessEqual(sum(c.width for c in t.columns), ancho)
            self.assertEqual(t._tbl.tblPr.find(qn('w:tblLayout')).get(qn('w:type')), 'fixed')
            self.assertIsNotNone(t.rows[0]._tr.trPr.find(qn('w:tblHeader')))
            for row in t.rows:
                self.assertIsNotNone(row._tr.trPr.find(qn('w:cantSplit')))
        with zipfile.ZipFile(BytesIO(contenido)) as paquete:
            self.assertIn('word/media/image1.png', paquete.namelist())

    def test_solo_censurados_informa_sin_evaluar(self):
        datos, excluidos = preparar(pd.DataFrame({'x':['<LC', '<0.01']}), {'cadmio':'x'})
        resumen, alertas = resumir(datos, {'cadmio': (0, 1)})
        self.assertEqual(resumen.iloc[0]['Válidos'], 0)
        self.assertTrue(pd.isna(resumen.iloc[0]['Promedio']))
        doc = Document(BytesIO(informe_word(resumen, alertas, {'cadmio':(0,1)}, excluidos, 'x.csv', datos)))
        self.assertIn('Sin datos válidos', '\n'.join(p.text for p in doc.paragraphs))

    def test_interfaz_ampliada_y_generacion(self):
        app = AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
        next(s for s in app.selectbox if s.label == 'Ejemplo ficticio').select('ejemplo_ampliado.csv').run(timeout=30)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(len(app.multiselect[0].value), 14)
        self.assertEqual(app.metric[0].value, '3')
        # El nuevo intervalo no se inventa: los campos aparecen vacíos.
        app.checkbox(key='comparar_plomo').check().run(timeout=30)
        self.assertIsNone(app.number_input(key='min_plomo').value)
        app.number_input(key='min_plomo').set_value(0.0)
        app.number_input(key='max_plomo').set_value(0.006).run(timeout=30)
        app.button[0].click().run(timeout=60)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(len(app.get('download_button')), 2)
        # Un archivo de metales funciona sin los tres parámetros originales.
        next(s for s in app.selectbox if s.label == 'Ejemplo ficticio').select('ejemplo_validacion.csv').run(timeout=30)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertNotIn('ph', app.multiselect[0].value)


if __name__ == '__main__':
    unittest.main()
