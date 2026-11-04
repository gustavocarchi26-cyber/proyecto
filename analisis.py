"""Lectura, análisis e informes sin servicios externos."""
from io import BytesIO
from pathlib import Path
import unicodedata

import pandas as pd
from docx import Document
from docx.shared import Inches
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

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


def informe_word(resumen, alertas, intervalos, invalidos, origen, datos=None, metadatos=None):
    documento = Document()
    documento.add_heading("Analizador Ambiental Inteligente", 0)
    documento.add_paragraph(f"Archivo: {origen}")
    for etiqueta, valor in (metadatos or {}).items():
        if str(valor).strip():
            documento.add_paragraph(f"{etiqueta}: {str(valor).strip()}")
    documento.add_heading("Alcance y metodología", level=1)
    documento.add_paragraph(AVISO)
    documento.add_paragraph("Las alertas usan límites inclusivos: solo se marcan valores menores al mínimo o mayores al máximo. No se imputan datos ausentes o inválidos.")
    documento.add_paragraph("Análisis descriptivo por parámetro. Cada fila representa una medición en el orden del archivo; las líneas del gráfico no representan tiempo transcurrido. Los valores extremos se conservan y no se realiza conversión de unidades.")
    documento.add_heading("Síntesis de resultados", level=1)
    total_validos = int(resumen["Válidos"].sum())
    total_excluidos = sum(invalidos.values())
    documento.add_paragraph(f"Valores válidos analizados: {total_validos}. Valores excluidos: {total_excluidos}. Valores fuera de intervalo: {len(alertas)}. Una fila puede generar alertas en varios parámetros.")
    documento.add_heading("Calidad de los datos e interpretación", level=1)
    for fila, clave in zip(resumen.to_dict("records"), PARAMETROS):
        validos = int(fila["Válidos"])
        excluidos = invalidos[clave]
        total = validos + excluidos
        texto = f"{fila['Parámetro']}: {validos} válidos y {excluidos} excluidos"
        if total:
            texto += f" ({100 * excluidos / total:.1f}% excluido)."
        else:
            texto += "."
        if validos:
            fuera = int(fila["Fuera de intervalo"])
            texto += f" {fuera} de {validos} valores válidos ({100 * fuera / validos:.1f}%) fuera del intervalo didáctico."
        else:
            texto += " Sin datos válidos: no es posible evaluar este parámetro."
        documento.add_paragraph(texto)
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
    if datos is not None:
        documento.add_heading("Gráficos de las mediciones", level=1)
        documento.add_paragraph("Franja verde: intervalo didáctico. Puntos rojos: valores fuera de intervalo. Los huecos corresponden a datos inválidos o ausentes.")
        for clave, (nombre, unidad) in PARAMETROS.items():
            figura = Figure(figsize=(7, 3.3), layout="constrained")
            FigureCanvasAgg(figura)
            eje = figura.subplots()
            serie = datos[clave]
            inferior, superior = intervalos[clave]
            eje.axhspan(inferior, superior, color="green", alpha=0.1)
            eje.axhline(inferior, color="orange", linestyle="--")
            eje.axhline(superior, color="orange", linestyle="--")
            eje.plot(datos.index, serie, color="#245d96", linewidth=1, marker=".", markersize=3)
            fuera = serie[(serie < inferior) | (serie > superior)]
            eje.scatter(fuera.index, fuera, color="#b42318", s=12, zorder=3)
            if not serie.notna().any():
                eje.text(0.5, 0.5, "Sin datos válidos", transform=eje.transAxes, ha="center")
            eje.set(title=nombre, xlabel="Medición (orden de la fila)", ylabel=unidad)
            eje.grid(alpha=0.2)
            imagen = BytesIO()
            figura.savefig(imagen, format="png", dpi=140)
            imagen.seek(0)
            documento.add_picture(imagen, width=Inches(6))
            figura.clear()
    documento.add_heading("Recomendaciones de revisión", level=1)
    documento.add_paragraph("Verifique unidades, transcripción, calibración de instrumentos y contexto del muestreo. Revise los datos excluidos antes de interpretar el resumen. Una alerta describe una comparación numérica y no identifica causas ni riesgos sanitarios.")
    documento.add_paragraph("Para evaluar cumplimiento legal se requieren criterios aplicables al lugar y uso del agua, fuentes verificables y revisión profesional.")
    documento.add_paragraph("Interpretación automática descriptiva. Las alertas requieren revisión del contexto y de la calidad de las mediciones.")
    salida = BytesIO()
    documento.save(salida)
    return salida.getvalue()
