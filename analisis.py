"""Lectura, análisis e informes sin servicios externos."""
from io import BytesIO
from pathlib import Path
import unicodedata

import pandas as pd
from docx import Document

PARAMETROS = {"ph": ("pH", "sin unidad"), "temperatura": ("Temperatura", "°C"),
              "turbidez": ("Turbidez", "NTU")}
INTERVALOS = {"ph": (6.5, 8.5), "temperatura": (15.0, 30.0), "turbidez": (0.0, 5.0)}
AVISO = ("Intervalos didácticos: no representan normas ambientales ni permiten "
         "determinar potabilidad, seguridad o cumplimiento legal. Verifique las unidades de origen.")


def leer_archivo(contenido, nombre):
    extension = Path(nombre).suffix.lower()
    if extension == ".csv":
        try:
            return pd.read_csv(BytesIO(contenido), sep=None, engine="python", encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(BytesIO(contenido), sep=None, engine="python", encoding="latin-1")
    if extension in (".xlsx", ".xls"):
        return pd.read_excel(BytesIO(contenido), sheet_name=0)
    raise ValueError("Utilice CSV, XLSX o XLS.")


def normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", str(texto).lower().strip())
                   if not unicodedata.combining(c))


def preparar(df, columnas):
    if df.empty:
        raise ValueError("El archivo no contiene mediciones.")
    resultado = pd.DataFrame(index=range(len(df)))
    invalidos = {}
    for parametro, columna in columnas.items():
        original = df[columna].reset_index(drop=True)
        numerico = pd.to_numeric(original.astype(str).str.strip().str.replace(",", ".", regex=False), errors="coerce")
        numerico = numerico.replace([float("inf"), -float("inf")], float("nan"))
        invalidos[parametro] = int(numerico.isna().sum())
        resultado[parametro] = numerico
    resultado.index += 1
    resultado.index.name = "Medición"
    return resultado, invalidos


def resumir(datos, intervalos):
    filas = []
    alertas = []
    for clave, (etiqueta, unidad) in PARAMETROS.items():
        serie = datos[clave].dropna()
        minimo, maximo = intervalos[clave]
        if minimo >= maximo:
            raise ValueError(f"{etiqueta}: el mínimo debe ser menor que el máximo.")
        fuera = serie[(serie < minimo) | (serie > maximo)]
        filas.append({"Parámetro": etiqueta, "Unidad": unidad, "Válidos": len(serie),
                      "Promedio": serie.mean(), "Mínimo": serie.min(), "Máximo": serie.max(),
                      "Fuera de intervalo": len(fuera)})
        for indice, valor in fuera.items():
            alertas.append({"Medición": indice, "Parámetro": etiqueta, "Valor": valor,
                            "Unidad": unidad, "Límite inferior": minimo, "Límite superior": maximo})
    return pd.DataFrame(filas), pd.DataFrame(alertas)


def informe_word(resumen, alertas, intervalos, invalidos, origen):
    documento = Document()
    documento.add_heading("Analizador Ambiental Inteligente", 0)
    documento.add_paragraph(f"Archivo: {origen}")
    documento.add_paragraph(AVISO)
    documento.add_paragraph("Las alertas usan límites inclusivos: solo se marcan valores menores al mínimo o mayores al máximo. No se imputan datos ausentes o inválidos.")
    documento.add_heading("Intervalos utilizados", level=1)
    for clave, (nombre, unidad) in PARAMETROS.items():
        documento.add_paragraph(f"{nombre}: {intervalos[clave][0]} a {intervalos[clave][1]} {unidad}. Datos excluidos: {invalidos[clave]}.")
    for titulo, tabla in (("Resumen estadístico", resumen), ("Mediciones fuera de intervalo", alertas)):
        documento.add_heading(titulo, level=1)
        if tabla.empty:
            documento.add_paragraph("No se detectaron mediciones fuera de los intervalos configurados.")
            continue
        t = documento.add_table(rows=1, cols=len(tabla.columns))
        t.style = "Light Shading Accent 1"
        for celda, nombre in zip(t.rows[0].cells, tabla.columns):
            celda.text = str(nombre)
        for fila in tabla.itertuples(index=False, name=None):
            for celda, valor in zip(t.add_row().cells, fila):
                celda.text = "Sin datos" if pd.isna(valor) else (f"{valor:.2f}" if isinstance(valor, float) else str(valor))
    documento.add_paragraph("Interpretación automática descriptiva. Las alertas requieren revisión del contexto y de la calidad de las mediciones.")
    salida = BytesIO()
    documento.save(salida)
    return salida.getvalue()
