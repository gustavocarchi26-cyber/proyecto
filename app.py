from pathlib import Path
from hashlib import sha256

import plotly.graph_objects as go
import streamlit as st

from analisis import informe_word, leer_archivo, normalizar, preparar, resumir
from parametros import AVISO, BASE, INTERVALOS, PARAMETROS, VERSION, ALIAS_META, unidades_admitidas

st.set_page_config(page_title="Analizador Ambiental Inteligente", page_icon="🌿", layout="wide")
st.title("🌿 Analizador Ambiental Inteligente")
st.caption(f"Versión {VERSION}")
st.write("Explora tus mediciones, identifica variaciones y genera un informe en Word.")
st.info(AVISO)
archivo = st.file_uploader("Sube tus mediciones (CSV o Excel)", type=["csv", "xlsx", "xls"])
st.caption("Primera hoja de Excel; CSV con separador automático. Máximo 20 MB y 50.000 filas. Confirma la unidad de cada columna: no se deduce del encabezado.")
usar_ejemplo = st.checkbox("Usar datos de ejemplo", value=archivo is None)
ruta_datos = Path(__file__).parent / "datos"
ejemplo_nombre = st.selectbox("Ejemplo ficticio", ["ejemplo.csv", "ejemplo_ampliado.csv", "ejemplo_validacion.csv"]) if usar_ejemplo else "ejemplo.csv"
st.download_button("Descargar CSV de ejemplo", (ruta_datos / ejemplo_nombre).read_bytes(), ejemplo_nombre, "text/csv")
if archivo is None and not usar_ejemplo:
    st.info("Sube un archivo o activa los datos de ejemplo para comenzar.")
    st.stop()
try:
    if usar_ejemplo:
        contenido, nombre = (ruta_datos / ejemplo_nombre).read_bytes(), ejemplo_nombre
    else:
        if archivo.size > 20 * 1024 * 1024:
            raise ValueError("El archivo supera el límite de 20 MB.")
        contenido, nombre = archivo.getvalue(), archivo.name
    original = leer_archivo(contenido, nombre)
    if original.empty:
        raise ValueError("El archivo no contiene mediciones.")
    if len(original) > 50000:
        raise ValueError("El archivo supera las 50.000 filas. Divídelo en archivos menores.")
    fuente = sha256(contenido).hexdigest()[:12]
    opciones = list(original.columns)
    st.caption(f"Fuente activa: {nombre} · {len(original)} filas")
    detectados = [k for k in PARAMETROS if any(normalizar(c) == k or normalizar(c).startswith(k + "_") for c in opciones)]
    seleccion = st.multiselect("Parámetros a analizar (todos son opcionales)", list(PARAMETROS),
                              default=detectados, format_func=lambda k: PARAMETROS[k][0], key=f"parametros_{fuente}")
    st.caption("Nitratos como NO₃⁻ y nitratos expresados como N son resultados diferentes; lo mismo ocurre con fosfatos como PO₄³⁻ y como P. Confirma la especie con el laboratorio. No hay conversión entre ellas.")
    if not seleccion:
        st.info("Selecciona al menos un parámetro. No es obligatorio incluir pH, temperatura ni turbidez.")
        st.stop()
    columnas, unidades, columnas_meta = {}, {}, {}
    with st.expander("Vista previa del archivo y selección de columnas", expanded=True):
        st.dataframe(original.head(10), hide_index=True, width="stretch")
        st.caption("Una sola unidad por columna. Solo se convierte µg/L → mg/L; no se admiten unidades mezcladas ni valores con unidades dentro de las celdas.")
        for clave in seleccion:
            etiqueta, unidad = PARAMETROS[clave]
            candidatos = [i for i, c in enumerate(opciones) if normalizar(c) == clave or normalizar(c).startswith(clave + "_")]
            columnas[clave] = st.selectbox(etiqueta, opciones, index=candidatos[0] if candidatos else None,
                                           key=f"col_{clave}_{fuente}", placeholder="Selecciona una columna")
            unidades[clave] = st.selectbox(f"Unidad de origen · {etiqueta}", unidades_admitidas(clave),
                                           key=f"unidad_{clave}_{fuente}")
            if unidades[clave] != unidad:
                st.caption(f"Conversión declarada: {unidades[clave]} a {unidad} (÷ 1000), incluidos los LC numéricos.")
    with st.expander("Columnas de identificación y observaciones por muestra (opcional)"):
        st.caption("La fecha se conserva tal como está declarada; no se infieren formatos. Estos campos aparecerán por fila en el Word.")
        for etiqueta, alias in ALIAS_META.items():
            candidatos = [i for i, c in enumerate(opciones) if normalizar(c) == alias]
            columna = st.selectbox(etiqueta, opciones, index=candidatos[0] if candidatos else None,
                                    key=f"meta_{alias}_{fuente}", placeholder="Sin columna")
            if columna is not None:
                columnas_meta[etiqueta] = columna
    if any(c is None for c in columnas.values()):
        st.info("Selecciona una columna para cada parámetro activo, o desactiva los que no necesitas.")
        st.stop()
    if len(set(columnas_meta.values())) != len(columnas_meta):
        raise ValueError("Selecciona columnas distintas para cada campo de identificación.")
    if set(columnas_meta.values()) & set(columnas.values()):
        raise ValueError("Una columna de identificación no puede ser también una medición numérica.")
    intervalos = {}
    with st.sidebar:
        st.header("Intervalos didácticos")
        st.caption("No se incluyen límites legales. En los nuevos parámetros la comparación está desactivada hasta que definas un intervalo para tu ejercicio.")
        for clave in seleccion:
            etiqueta, unidad = PARAMETROS[clave]
            st.subheader(f"{etiqueta} · {unidad}")
            activo = st.checkbox("Comparar con intervalo didáctico", value=clave in BASE, key=f"comparar_{clave}")
            if activo:
                inicial = INTERVALOS.get(clave, (None, None))
                if clave not in BASE:
                    st.caption("Introduce ambos límites para tu ejercicio. No hay valores predefinidos.")
                inferior = st.number_input("Mínimo", value=inicial[0], key=f"min_{clave}")
                superior = st.number_input("Máximo", value=inicial[1], key=f"max_{clave}")
                intervalos[clave] = (inferior, superior)
            else:
                intervalos[clave] = None
    if any(limites is not None and any(v is None for v in limites) for limites in intervalos.values()):
        st.info("Completa ambos límites de cada intervalo activado o desactiva su comparación.")
        st.stop()
    datos, invalidos = preparar(original, columnas, unidades, columnas_meta)
    resumen, alertas = resumir(datos, intervalos)
    detalle = datos.attrs["detalle"]
    st.subheader("Validación y calidad de los datos")
    st.caption("Se distinguen cuantificados, ausentes, inválidos e inferiores a LC. <0.01, <LC o <LQ no se reemplazan por cero ni se comparan con intervalos. ND se marca inválido porque su significado y límite no están especificados.")
    calidad = detalle.groupby(["Parámetro", "Estado"], sort=False).size().unstack(fill_value=0)
    st.dataframe(calidad, width="stretch")
    if sum(invalidos.values()):
        st.warning(f"{sum(invalidos.values())} valores no cuantificados excluidos de estadísticas. Revisa su estado y original; las demás mediciones se conservan.")
    with st.expander("Ver resultados originales y límites de cuantificación"):
        st.dataframe(detalle, hide_index=True, width="stretch")
    c1, c2, c3 = st.columns(3)
    c1.metric("Mediciones (filas)", len(datos))
    c2.metric("Valores válidos", int(datos.notna().sum().sum()))
    c3.metric("Valores fuera de intervalo", len(alertas))
    st.subheader("Resumen estadístico")
    st.caption("Sin intervalo significa no evaluado. Las estadísticas usan solo valores cuantificados; pueden no representar el conjunto completo de muestras.")
    st.dataframe(resumen, hide_index=True, width="stretch")
    st.subheader("Gráficos interactivos")
    st.caption("Eje horizontal: orden de las filas desde 1. Los huecos representan resultados no cuantificados. La franja verde, si aparece, es didáctica.")
    for clave in seleccion:
        etiqueta, unidad = PARAMETROS[clave]
        figura = go.Figure(go.Scatter(x=datos.index, y=datos[clave], mode="lines+markers", name=etiqueta, connectgaps=False))
        if intervalos[clave] is not None:
            inferior, superior = intervalos[clave]
            figura.add_hrect(y0=inferior, y1=superior, fillcolor="green", opacity=0.1, line_width=0)
            for limite in (inferior, superior):
                figura.add_hline(y=limite, line_dash="dash", line_color="orange")
        figura.update_layout(title=f"{etiqueta} ({unidad})", xaxis_title="Medición", yaxis_title=unidad, template="plotly_white")
        st.plotly_chart(figura, width="stretch")
    st.subheader("Valores fuera de los intervalos")
    if alertas.empty:
        st.info("No hay alertas numéricas. Los parámetros sin intervalo y los resultados no cuantificados no se evaluaron; esto no indica seguridad ni cumplimiento legal.")
    else:
        st.dataframe(alertas, hide_index=True, width="stretch")
    st.subheader("Informe detallado en Word")
    st.caption("Incluye observaciones de campo, identificación por muestra, resultados, gráficos e interpretación descriptiva en secciones separadas.")
    campos = {}
    with st.expander("Identificación general del informe (opcional)"):
        for etiqueta in ("Proyecto", "Código de muestra", "Fecha", "Lugar", "Responsable", "Método analítico"):
            campos[etiqueta] = st.text_input(etiqueta, max_chars=200, key=f"general_{etiqueta}")
        campos["Observaciones de campo"] = st.text_area("Observaciones de campo", max_chars=2000)
    if st.button("Generar informe detallado", type="primary"):
        with st.spinner("Preparando informe y gráficos…"):
            informe = informe_word(resumen, alertas, intervalos, invalidos, nombre, datos, campos)
        st.download_button("📄 Descargar informe Word", informe, "informe_ambiental_v0.3.docx",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document", on_click="ignore")
    st.caption("Si modificas datos, intervalos o identificación, vuelve a generar el informe antes de descargarlo.")
except Exception as error:
    st.error(f"No se pudo analizar el archivo: {error}")
    st.info("Revisa el formato, las columnas y las unidades seleccionadas. Para Excel utiliza archivos sin contraseña.")
