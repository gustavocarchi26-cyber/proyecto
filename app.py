from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from analisis import AVISO, INTERVALOS, PARAMETROS, informe_word, leer_archivo, normalizar, preparar, resumir

st.set_page_config(page_title="Analizador Ambiental Inteligente", page_icon="🌿", layout="wide")
st.title("🌿 Analizador Ambiental Inteligente")
st.write("Explora tus mediciones, identifica variaciones y genera un informe en Word.")
st.info(AVISO)

with st.sidebar:
    st.header("Intervalos didácticos")
    st.caption("Ajusta los límites según tu ejercicio. Los extremos están incluidos.")
    intervalos = {}
    for clave, (nombre, unidad) in PARAMETROS.items():
        st.subheader(f"{nombre} · {unidad}")
        inferior = st.number_input("Mínimo", value=INTERVALOS[clave][0], key=f"min_{clave}")
        superior = st.number_input("Máximo", value=INTERVALOS[clave][1], key=f"max_{clave}")
        intervalos[clave] = (inferior, superior)

archivo = st.file_uploader("Sube tus mediciones (CSV o Excel)", type=["csv", "xlsx", "xls"])
st.caption("Excel: se lee la primera hoja. CSV: separador automático; decimales con coma requieren separador punto y coma o campos entre comillas. Máximo 20 MB y 50.000 filas.")
usar_ejemplo = st.checkbox("Usar datos de ejemplo", value=archivo is None)
ejemplo = Path(__file__).parent / "datos" / "ejemplo.csv"
st.download_button("Descargar CSV de ejemplo", ejemplo.read_bytes(), "ejemplo.csv", "text/csv")
if archivo is None and not usar_ejemplo:
    st.info("Sube un archivo o activa los datos de ejemplo para comenzar.")
    st.stop()
if any(a >= b for a, b in intervalos.values()):
    st.error("Cada mínimo debe ser menor que su máximo.")
    st.stop()
try:
    if usar_ejemplo:
        contenido, nombre = ejemplo.read_bytes(), "ejemplo.csv"
    else:
        if archivo.size > 20 * 1024 * 1024:
            raise ValueError("El archivo supera el límite de 20 MB.")
        contenido, nombre = archivo.getvalue(), archivo.name
    original = leer_archivo(contenido, nombre)
    if len(original) > 50000:
        raise ValueError("El archivo supera las 50.000 filas. Divídelo en archivos menores.")
    st.caption(f"Fuente activa: {nombre} · {len(original)} filas")
    with st.expander("Vista previa del archivo y selección de columnas", expanded=True):
        st.dataframe(original.head(10), hide_index=True, width="stretch")
        st.caption("Selecciona una columna para cada parámetro. Las unidades deben ser °C y NTU; no se convierten automáticamente.")
        columnas = {}
        opciones = list(original.columns)
        if not opciones:
            raise ValueError("El archivo no contiene columnas.")
        for clave, (etiqueta, _) in PARAMETROS.items():
            candidatos = [i for i, c in enumerate(opciones) if clave in normalizar(c)]
            columnas[clave] = st.selectbox(etiqueta, opciones, index=candidatos[0] if candidatos else None, key=f"col_{clave}", placeholder="Selecciona una columna")
    if any(c is None for c in columnas.values()):
        st.info("Selecciona las tres columnas para continuar.")
        st.stop()
    if len(set(columnas.values())) != 3:
        raise ValueError("Selecciona una columna distinta para cada parámetro.")
    datos, invalidos = preparar(original, columnas)
    if sum(invalidos.values()):
        st.warning("Datos ausentes, no numéricos o infinitos excluidos por parámetro: " + ", ".join(f"{PARAMETROS[k][0]}: {v}" for k, v in invalidos.items()))
    if datos.notna().sum().sum() == 0:
        raise ValueError("No hay mediciones numéricas válidas en las columnas seleccionadas.")
    resumen, alertas = resumir(datos, intervalos)
    c1, c2, c3 = st.columns(3)
    c1.metric("Mediciones (filas)", len(datos))
    c2.metric("Valores válidos", int(datos.notna().sum().sum()))
    c3.metric("Valores fuera de intervalo", len(alertas))
    st.subheader("Resumen estadístico")
    st.dataframe(resumen, hide_index=True, width="stretch")
    st.subheader("Gráficos interactivos")
    st.caption("El eje horizontal representa el orden de las filas, comenzando en 1. Usa el cursor y el zoom para explorar.")
    for clave, (etiqueta, unidad) in PARAMETROS.items():
        figura = go.Figure(go.Scatter(x=datos.index, y=datos[clave], mode="lines+markers", name=etiqueta, connectgaps=False))
        inferior, superior = intervalos[clave]
        figura.add_hrect(y0=inferior, y1=superior, fillcolor="green", opacity=0.1, line_width=0)
        for limite in (inferior, superior):
            figura.add_hline(y=limite, line_dash="dash", line_color="orange")
        figura.update_layout(title=f"{etiqueta} ({unidad})", xaxis_title="Medición", yaxis_title=unidad, template="plotly_white")
        st.plotly_chart(figura, width="stretch")
    st.subheader("Valores fuera de los intervalos")
    if alertas.empty:
        st.success("No se encontraron valores fuera de los intervalos didácticos configurados.")
    else:
        st.dataframe(alertas, hide_index=True, width="stretch")
    st.subheader("Informe detallado en Word")
    st.caption("Incluye estadísticas, calidad de los datos, alertas, tres gráficos y recomendaciones de revisión. Los campos siguientes son opcionales.")
    with st.expander("Identificación del informe"):
        proyecto = st.text_input("Proyecto o campaña", max_chars=200)
        lugar = st.text_input("Lugar o punto de muestreo", max_chars=200)
        responsable = st.text_input("Responsable", max_chars=200)
        observaciones = st.text_area("Observaciones del muestreo", max_chars=2000)
    if st.button("Generar informe detallado", type="primary"):
        with st.spinner("Preparando informe y gráficos…"):
            informe = informe_word(resumen, alertas, intervalos, invalidos, nombre, datos,
                                   {"Proyecto": proyecto, "Lugar": lugar, "Responsable": responsable,
                                    "Observaciones": observaciones})
        st.download_button("📄 Descargar informe Word", informe, "informe_ambiental.docx",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document", on_click="ignore")
    st.caption("Si modificas datos, intervalos o identificación, vuelve a generar el informe antes de descargarlo.")
except Exception as error:
    st.error(f"No se pudo analizar el archivo: {error}")
    st.info("Comprueba el formato, la primera hoja de Excel y las columnas seleccionadas. Para Excel utiliza archivos sin contraseña.")
