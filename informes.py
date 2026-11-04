"""Informes Word con tablas de ancho fijo, gráficos y trazabilidad."""
from io import BytesIO

import pandas as pd
from docx import Document
from docx.shared import Inches, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from parametros import AVISO, PARAMETROS, VERSION


def formato(valor):
    if pd.isna(valor):
        return "Sin datos"
    if isinstance(valor, float):
        # Evita mostrar concentraciones pequeñas (p. ej., 0.0001 mg/L) como cero.
        return f"{valor:.6g}"
    return str(valor)


def tabla(documento, encabezados, filas, anchos):
    t = documento.add_table(rows=1, cols=len(encabezados))
    t.style = "Light Shading Accent 1"
    t.autofit = False
    for columna, ancho in zip(t.columns, anchos):
        columna.width = Inches(ancho)
    for celda, texto in zip(t.rows[0].cells, encabezados):
        celda.text = texto
    repetir = OxmlElement("w:tblHeader")
    t.rows[0]._tr.get_or_add_trPr().append(repetir)
    for valores in filas:
        for celda, valor in zip(t.add_row().cells, valores):
            celda.text = formato(valor)
    for fila in t.rows:
        no_dividir = OxmlElement("w:cantSplit")
        fila._tr.get_or_add_trPr().append(no_dividir)
        for celda, ancho in zip(fila.cells, anchos):
            celda.width = Inches(ancho)
            for parrafo in celda.paragraphs:
                parrafo.paragraph_format.space_after = Pt(4)
                ajuste = OxmlElement("w:wordWrap")
                ajuste.set(qn("w:val"), "0")
                parrafo._p.get_or_add_pPr().append(ajuste)
                for run in parrafo.runs:
                    run.font.size = Pt(10)
    return t


def informe_word(resumen, alertas, intervalos, invalidos, origen, datos=None, metadatos=None):
    documento = Document()
    seccion = documento.sections[0]
    seccion.page_width, seccion.page_height = Inches(8.27), Inches(11.69)
    seccion.left_margin = seccion.right_margin = Inches(0.65)
    documento.styles["Normal"].font.size = Pt(10)
    documento.add_heading("Analizador Ambiental Inteligente", 0)
    documento.add_paragraph(f"Versión {VERSION} · Archivo: {origen}")
    documento.add_heading("Identificación del informe", level=1)
    campos = metadatos or {}
    identificacion = [(k, v) for k, v in campos.items() if str(v).strip() and k not in ("Observaciones", "Observaciones de campo")]
    if identificacion:
        tabla(documento, ["Campo", "Información declarada"], identificacion, [2.1, 4.8])
    else:
        documento.add_paragraph("No se proporcionó identificación general.")
    documento.add_heading("Observaciones de campo", level=1)
    documento.add_paragraph(campos.get("Observaciones de campo") or campos.get("Observaciones") or "No se proporcionaron observaciones generales.")
    meta_filas = datos.attrs.get("metadatos", pd.DataFrame()) if datos is not None else pd.DataFrame()
    if not meta_filas.empty:
        documento.add_heading("Identificación y observaciones por muestra", level=1)
        for indice, fila in meta_filas.iterrows():
            valores = [(k, v) for k, v in fila.items() if pd.notna(v) and str(v).strip()]
            if valores:
                documento.add_heading(f"Medición {indice}", level=2)
                tabla(documento, ["Campo", "Información del archivo"], valores, [2.1, 4.8])
    documento.add_heading("Alcance y metodología del análisis de datos", level=1)
    documento.add_paragraph(AVISO)
    documento.add_paragraph("Las estadísticas describen únicamente valores cuantificados finitos. Los ausentes, inválidos e inferiores al límite de cuantificación (LC/LQ) se excluyen sin reemplazarlos por cero ni por fracciones del LC. Los promedios de este subconjunto pueden no representar todas las muestras.")
    documento.add_paragraph("La anotación <número se trata como resultado inferior al LC declarado por el usuario. No se deduce un LC a partir de ND. El resultado original se conserva. No se comparan resultados inferiores a LC con intervalos ni se concluye que cumplan un límite.")
    documento.add_paragraph("Los gráficos siguen el orden de las filas, no el tiempo transcurrido. Solo se convierte µg/L a mg/L (división por 1000) cuando se declara esa unidad de origen. No se convierten especies químicas, conductividad en sólidos ni métodos analíticos.")
    documento.add_heading("Resultados", level=1)
    documento.add_paragraph(f"Valores cuantificados: {int(resumen['Válidos'].sum())}. Excluidos de estadísticas: {sum(invalidos.values())}. Alertas numéricas: {len(alertas)}. Una fila puede generar alertas para varios parámetros.")
    claves = list(datos.columns) if datos is not None else [k for k, v in PARAMETROS.items() if v[0] in resumen['Parámetro'].tolist()]
    detalle = datos.attrs.get("detalle", pd.DataFrame()) if datos is not None else pd.DataFrame()
    for clave in claves:
        nombre, unidad = PARAMETROS[clave]
        fila = resumen.loc[resumen["Parámetro"] == nombre].iloc[0]
        documento.add_heading(f"{nombre} · {unidad}", level=2)
        limites = intervalos.get(clave)
        documento.add_paragraph(f"Intervalo didáctico inclusivo: {formato(limites[0])} a {formato(limites[1])} {unidad}." if limites is not None else "Sin intervalo de comparación: no evaluado. No hay límite legal configurado.")
        if datos is not None:
            origen_unidad = datos.attrs.get("unidades_origen", {}).get(clave, unidad)
            documento.add_paragraph(f"Unidad de origen: {origen_unidad}. Unidad de cálculo: {unidad}.")
        validos, excluidos = int(fila["Válidos"]), invalidos[clave]
        total = validos + excluidos
        documento.add_paragraph(f"{validos} válidos y {excluidos} excluidos" + (f" ({100 * excluidos / total:.1f}% excluido)." if total else "."))
        if not detalle.empty:
            conteos = detalle.loc[detalle["Parámetro"] == nombre, "Estado"].value_counts()
            documento.add_paragraph("Calidad: " + "; ".join(f"{estado}: {conteos.get(estado, 0)}" for estado in ("Cuantificado", "Ausente", "Inválido", "Inferior a LC")) + ".")
        if not validos:
            documento.add_paragraph("Sin datos válidos: no es posible evaluar este parámetro.")
        elif limites is not None:
            fuera = int(fila["Fuera de intervalo"])
            documento.add_paragraph(f"{fuera} de {validos} valores válidos ({100 * fuera / validos:.1f}%) fuera del intervalo didáctico.")
        tabla(documento, ["Estadística", f"Resultado ({unidad})"], [(campo, fila[campo]) for campo in ("Válidos", "Promedio", "Mínimo", "Máximo")], [2.4, 4.5])
        alertas_parametro = alertas.loc[alertas["Parámetro"] == nombre]
        if not alertas_parametro.empty:
            documento.add_paragraph("Mediciones fuera del intervalo didáctico:")
            tabla(documento, ["Medición", "Valor", "Límite inferior", "Límite superior"],
                  alertas_parametro[["Medición", "Valor", "Límite inferior", "Límite superior"]].itertuples(index=False, name=None), [1.0, 1.5, 2.2, 2.2])
        elif limites is not None and validos:
            documento.add_paragraph("No se detectaron alertas entre los valores cuantificados. Los valores no cuantificados no se evaluaron.")
        if datos is not None:
            figura = Figure(figsize=(7, 3.3), layout="constrained")
            FigureCanvasAgg(figura)
            eje = figura.subplots()
            serie = datos[clave]
            if limites is not None:
                inferior, superior = limites
                eje.axhspan(inferior, superior, color="green", alpha=0.1)
                for limite in limites:
                    eje.axhline(limite, color="orange", linestyle="--")
                fuera = serie[(serie < inferior) | (serie > superior)]
                eje.scatter(fuera.index, fuera, color="#b42318", s=12, zorder=3)
            eje.plot(datos.index, serie, color="#245d96", linewidth=1, marker=".", markersize=3)
            if not serie.notna().any():
                eje.text(0.5, 0.5, "Sin datos cuantificados", transform=eje.transAxes, ha="center")
            eje.set(title=nombre, xlabel="Medición (orden de la fila)", ylabel=unidad)
            eje.grid(alpha=0.2)
            imagen = BytesIO()
            figura.savefig(imagen, format="png", dpi=140)
            imagen.seek(0)
            documento.add_picture(imagen, width=Inches(6.8))
            figura.clear()
    if not detalle.empty:
        documento.add_heading("Trazabilidad de datos no cuantificados", level=1)
        pendientes = detalle[detalle["Estado"] != "Cuantificado"]
        if pendientes.empty:
            documento.add_paragraph("Todos los valores seleccionados son numéricos finitos.")
        for nombre, grupo in pendientes.groupby("Parámetro", sort=False):
            documento.add_heading(nombre, level=2)
            tabla(documento, ["Medición", "Original", "Estado", "LC declarado"],
                  [(r["Medición"], r["Original"] or "(vacío)", r["Estado"], formato(r["LC declarado"]) + " " + r["Unidad de cálculo"] if pd.notna(r["LC declarado"]) else "No indicado") for r in grupo.to_dict("records")], [0.9, 1.8, 2.0, 2.2])
    documento.add_heading("Interpretación descriptiva y limitaciones", level=1)
    documento.add_paragraph("Las alertas son comparaciones numéricas con intervalos didácticos elegidos por el usuario. No identifican causas, contaminación, seguridad, potabilidad ni cumplimiento legal. Sin intervalo significa no evaluado, no ausencia de riesgo.")
    documento.add_heading("Recomendaciones de revisión", level=1)
    documento.add_paragraph("Revise unidades, especie química, método analítico, calibración y contexto del muestreo. Confirme el significado de los resultados inferiores a LC con el laboratorio. La evaluación normativa requiere fuentes verificables, criterios aplicables y revisión profesional.")
    salida = BytesIO()
    documento.save(salida)
    return salida.getvalue()
