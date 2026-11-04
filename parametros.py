"""Catálogo de parámetros. Unidades de salida; no contiene límites legales."""
VERSION = "0.3.0"
PARAMETROS = {
    "ph": ("pH", "sin unidad"),
    "temperatura": ("Temperatura", "°C"),
    "turbidez": ("Turbidez", "NTU"),
    "oxigeno_disuelto": ("Oxígeno disuelto (O₂)", "mg/L"),
    "conductividad": ("Conductividad eléctrica", "µS/cm"),
    "solidos_disueltos": ("Sólidos disueltos totales", "mg/L"),
    "nitratos_no3": ("Nitratos como NO₃⁻", "mg/L"),
    "nitratos_n": ("Nitratos expresados como N", "mg/L"),
    "fosfatos_po4": ("Fosfatos como PO₄³⁻", "mg/L"),
    "fosfatos_p": ("Fosfatos expresados como P", "mg/L"),
    "plomo": ("Plomo (Pb)", "mg/L"),
    "cadmio": ("Cadmio (Cd)", "mg/L"),
    "arsenico": ("Arsénico (As)", "mg/L"),
    "mercurio": ("Mercurio (Hg)", "mg/L"),
}
BASE = ["ph", "temperatura", "turbidez"]
# Solo se conservan los intervalos del ejemplo didáctico original.
INTERVALOS = {"ph": (6.5, 8.5), "temperatura": (15.0, 30.0), "turbidez": (0.0, 5.0)}
AVISO = ("Intervalos didácticos: no representan normas ambientales ni permiten "
         "determinar potabilidad, seguridad o cumplimiento legal. Verifique las unidades de origen.")
METADATOS = ["Código de muestra", "Fecha", "Lugar", "Responsable", "Método analítico", "Observaciones de campo"]
ALIAS_META = {
    "Código de muestra": "codigo_muestra", "Fecha": "fecha", "Lugar": "lugar",
    "Responsable": "responsable", "Método analítico": "metodo_analitico",
    "Observaciones de campo": "observaciones_campo",
}


def unidades_admitidas(clave):
    unidad = PARAMETROS[clave][1]
    return ["mg/L", "µg/L"] if unidad == "mg/L" else [unidad]
