"""Lectura y cálculos descriptivos. Sin APIs ni criterios legales."""
from io import BytesIO
from pathlib import Path
import math
import re
import unicodedata

import pandas as pd
from parametros import AVISO, INTERVALOS, PARAMETROS, unidades_admitidas
from informes import informe_word

NUMERO = r"[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?"
LC = re.compile(rf"<\s*({NUMERO})", re.IGNORECASE)


def leer_archivo(contenido, nombre):
    extension = Path(nombre).suffix.lower()
    if extension == ".csv":
        try:
            return pd.read_csv(BytesIO(contenido), sep=None, engine="python", encoding="utf-8-sig", keep_default_na=False, dtype=str)
        except UnicodeDecodeError:
            return pd.read_csv(BytesIO(contenido), sep=None, engine="python", encoding="latin-1", keep_default_na=False, dtype=str)
    if extension in (".xlsx", ".xls"):
        return pd.read_excel(BytesIO(contenido), sheet_name=0, keep_default_na=False, dtype=str)
    raise ValueError("Utilice CSV, XLSX o XLS.")


def normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", str(texto).lower().strip())
                   if not unicodedata.combining(c))


def factor_unidad(clave, unidad):
    # No se deducen unidades del valor ni se convierten especies químicas.
    unidad = unidad.replace("μ", "µ").replace("ug/L", "µg/L")
    if unidad not in unidades_admitidas(clave):
        raise ValueError(f"Unidad no admitida para {PARAMETROS[clave][0]}: {unidad}")
    return 0.001 if unidad == "µg/L" else 1.0


def clasificar(valor, factor):
    """Estado, valor cuantificado o NaN, y LC numérico si está declarado."""
    if pd.isna(valor) or not str(valor).strip():
        return "Ausente", float("nan"), None
    texto = str(valor).strip()
    coincidencia = LC.fullmatch(texto)
    if coincidencia:
        limite = float(coincidencia[1].replace(",", ".")) * factor
        if math.isfinite(limite) and limite > 0:
            return "Inferior a LC", float("nan"), limite
        return "Inválido", float("nan"), None
    if texto.upper().replace(" ", "") in ("<LC", "<LQ"):
        return "Inferior a LC", float("nan"), None
    if re.fullmatch(NUMERO, texto):
        numero = float(texto.replace(",", ".")) * factor
        if math.isfinite(numero):
            return "Cuantificado", numero, None
    return "Inválido", float("nan"), None


def preparar(df, columnas, unidades=None, columnas_meta=None):
    if df.empty:
        raise ValueError("El archivo no contiene mediciones.")
    if not columnas:
        raise ValueError("Seleccione al menos un parámetro.")
    if len(set(columnas.values())) != len(columnas):
        raise ValueError("Selecciona una columna distinta para cada parámetro.")
    resultado = pd.DataFrame(index=pd.RangeIndex(1, len(df) + 1, name="Medición"))
    invalidos, registros = {}, []
    for clave, columna in columnas.items():
        unidad = (unidades or {}).get(clave, PARAMETROS[clave][1])
        factor = factor_unidad(clave, unidad)
        valores = []
        for indice, original in enumerate(df[columna].tolist(), start=1):
            estado, numero, limite = clasificar(original, factor)
            valores.append(numero)
            registros.append({"Medición": indice, "Parámetro": PARAMETROS[clave][0],
                              "Original": "" if pd.isna(original) else str(original),
                              "Estado": estado, "Unidad de origen": unidad,
                              "Unidad de cálculo": PARAMETROS[clave][1], "LC declarado": limite})
        resultado[clave] = valores
        invalidos[clave] = int(resultado[clave].isna().sum())
    resultado.attrs["detalle"] = pd.DataFrame(registros)
    resultado.attrs["unidades_origen"] = {k: (unidades or {}).get(k, PARAMETROS[k][1]) for k in columnas}
    resultado.attrs["metadatos"] = df[list((columnas_meta or {}).values())].reset_index(drop=True).rename(
        columns={columna: etiqueta for etiqueta, columna in (columnas_meta or {}).items()})
    resultado.attrs["metadatos"].index = resultado.index
    return resultado, invalidos


def resumir(datos, intervalos):
    filas, alertas = [], []
    for clave in datos.columns:
        etiqueta, unidad = PARAMETROS[clave]
        serie = datos[clave].dropna()
        limites = intervalos.get(clave)
        fuera = serie.iloc[0:0]
        if limites is not None:
            minimo, maximo = limites
            if not (math.isfinite(minimo) and math.isfinite(maximo) and minimo < maximo):
                raise ValueError(f"{etiqueta}: el mínimo debe ser menor que el máximo y ambos deben ser finitos.")
            fuera = serie[(serie < minimo) | (serie > maximo)]
            for indice, valor in fuera.items():
                alertas.append({"Medición": indice, "Parámetro": etiqueta, "Valor": valor,
                                "Unidad": unidad, "Límite inferior": minimo, "Límite superior": maximo})
        filas.append({"Parámetro": etiqueta, "Unidad": unidad, "Válidos": len(serie),
                      "Promedio": serie.mean(), "Mínimo": serie.min(), "Máximo": serie.max(),
                      "Fuera de intervalo": len(fuera) if limites is not None else None})
    return pd.DataFrame(filas), pd.DataFrame(alertas, columns=["Medición", "Parámetro", "Valor", "Unidad", "Límite inferior", "Límite superior"])
