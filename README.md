# 🌿 Analizador Ambiental Inteligente · v0.3.0

Aplicación en español para explorar mediciones ambientales. Conserva pH, temperatura y turbidez y añade oxígeno disuelto, conductividad, sólidos disueltos, nutrientes y metales. Todos los parámetros son opcionales: puede analizarse uno solo. Construida con Python, Streamlit, pandas, Plotly y python-docx. Todas las herramientas son gratuitas y no se necesitan claves API ni servicios de inteligencia artificial. El análisis es estadístico y mediante reglas configurables.

## Qué permite hacer

- Subir CSV, XLSX y XLS o usar datos de ejemplo.
- Seleccionar las columnas de cada parámetro y consultar una vista previa.
- Calcular promedio, mínimo y máximo con los datos numéricos válidos.
- Explorar gráficos con zoom y cursor.
- Ajustar intervalos y ver cada medición fuera de ellos.
- Descargar un informe Word detallado con identificación del proyecto, estadísticas, porcentajes de alertas y datos excluidos, gráficos de todos los parámetros activos y recomendaciones de revisión.

**Los intervalos iniciales son exclusivamente didácticos:** pH 6,5–8,5; temperatura 15–30 °C; turbidez 0–5 NTU. No son normas ambientales. No determinan potabilidad, seguridad ni cumplimiento legal. Los límites están incluidos; solo se marca lo que queda por debajo o por encima. Los nuevos parámetros no tienen intervalos predefinidos. No se incluyen límites legales. Solo se convierte µg/L a mg/L cuando se declara esa unidad de origen.

## Ejecutar en Windows, paso a paso

1. Instala Python 3.12 desde https://www.python.org/downloads/ y marca **Add Python to PATH**. Instala Git desde https://git-scm.com/download/win si utilizarás GitHub desde la terminal.
2. Descarga el repositorio desde GitHub con **Code → Download ZIP** y descomprímelo, o clónalo:

   ```bat
   git clone https://github.com/gustavocarchi26-cyber/proyecto.git
   cd proyecto
   ```

3. Abre la carpeta del proyecto en el Explorador de archivos. Escribe `cmd` en la barra de dirección y pulsa Enter. Ejecuta, una línea a la vez:

   ```bat
   py -3.12 -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   .venv\Scripts\python.exe -m streamlit run app.py
   ```

   No necesitas activar el entorno virtual. Si `py` no existe, vuelve a instalar Python o usa `python` en su lugar y comprueba `python --version`.

4. Streamlit abrirá el navegador. Si no lo hace, introduce `http://localhost:8501` en tu navegador de Windows. Al principio verás el ejemplo ya analizado.
5. Para usar tu archivo, súbelo y desmarca **Usar datos de ejemplo** si sigue marcado. Revisa la fuente activa, elige los parámetros, sus columnas y sus unidades de origen. Puedes mantener solo los tres originales o elegir otros. Ajusta los límites en la barra lateral y ve a **Informe detallado en Word**. Puedes completar proyecto, lugar, responsable y observaciones. Pulsa **Generar informe detallado** y después **Descargar informe Word** para guardar el documento. Si cambias los datos o los límites, genera nuevamente el informe.
6. Detén la aplicación con `Ctrl+C` en la terminal. Para abrirla otro día, repite únicamente el último comando del paso 3 desde la carpeta del proyecto.

Si el puerto está ocupado, añade `--server.port 8502` al comando de Streamlit.

## Formato de los datos

Consulta `datos/ejemplo.csv` y `datos/ejemplo.xlsx`. Una fila es una medición; se requiere una columna diferente para cada parámetro seleccionado. La columna `fecha` es opcional: los gráficos utilizan el orden de las filas, no el tiempo.

```csv
fecha,ph,temperatura,turbidez
2026-01-01,7.1,22,3
2026-01-02,7.4,23,4
```

Para decimales con coma, usa punto y coma como separador (`7,1;22;3`). Se admite CSV UTF-8 y, como alternativa, Latin-1. En Excel se lee únicamente la primera hoja, con encabezados en su primera fila y sin contraseña. Se aceptan hasta 20 MB y 50.000 filas; Excel se carga antes de comprobar el número de filas, así que evita libros muy grandes.

Los valores vacíos, no numéricos, infinitos e inferiores al límite de cuantificación se excluyen de las estadísticas por parámetro, se distinguen por estado y se contabilizan en pantalla y en el informe. No se rellenan ni se eliminan filas enteras por un valor faltante. Un parámetro sin valores válidos muestra estadísticas sin datos. No se descartan valores extremos automáticamente.

## Archivos

- `app.py`: interfaz y gráficos.
- `analisis.py`: lectura, clasificación y cálculos.
- `parametros.py`: catálogo, especies, unidades y versión.
- `informes.py`: tablas, gráficos y generación de Word.
- `requirements.txt`: dependencias.
- `datos/`: archivos de ejemplo.
- `tests/test_app.py` y `tests/test_v03.py`: pruebas de regresión, cálculos, unidades, LC, informes e interfaz.

## Comprobar el funcionamiento

Desde la carpeta del proyecto en Windows:

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

En Linux/macOS, usa `.venv/bin/python` en lugar de `.venv\Scripts\python.exe`.

Los archivos subidos se procesan en la memoria del servidor Streamlit. La aplicación no los guarda deliberadamente en disco ni los envía a APIs. Si la ejecutas en otro servidor, los datos se procesarán allí: usa solo información que estés autorizado a cargar. Para una instalación local, los datos se procesan en tu computadora.

## Guardar los cambios en GitHub

En la terminal, dentro de la carpeta del proyecto:

```bat
git status
git add app.py analisis.py parametros.py informes.py requirements.txt README.md .gitignore datos tests
git commit -m "Crear Analizador Ambiental Inteligente"
git push -u origin HEAD:main
```

El último comando envía la rama local a `main`. Si hay cambios previos en GitHub y el envío es rechazado, no uses `--force`: descarga e integra esos cambios primero. Si pide identificar al autor, configura `git config user.name "Tu nombre"` y `git config user.email "Tu correo"` y vuelve a ejecutar el commit. Git puede abrir el navegador para iniciar sesión en GitHub; no necesitas poner tokens dentro del código.

Si trabajas desde esta interfaz, guarda primero los cambios mediante sus opciones de Git o ejecutando esos comandos en la terminal del entorno. Después podrás clonarlos en Windows. Nunca subas `.venv` ni archivos ambientales privados; `.gitignore` ya excluye el entorno virtual.

## Informe detallado

Los gráficos del Word son imágenes estáticas generadas con Matplotlib; los de la aplicación siguen siendo interactivos con Plotly. El porcentaje de alertas se calcula sobre los valores válidos de cada parámetro. El porcentaje de exclusión se calcula sobre todas sus filas. Un parámetro sin datos válidos se indica explícitamente y no se interpreta como ausencia de alertas. La identificación es opcional y se utiliza únicamente en el documento. La generación se realiza al pulsar el botón para evitar repetirla en cada ajuste. No se utiliza IA ni se hacen diagnósticos sanitarios o normativos.


## Novedades de la versión 0.3

### Parámetros y especies admitidos

Los identificadores son encabezados sugeridos para CSV/Excel. También se aceptan columnas con otros nombres mediante selección manual. No se adivina la especie a partir de una columna genérica llamada `nitratos` o `fosfatos`.

| Identificador | Resultado expresado como | Unidad de cálculo |
|---|---|---|
| `ph` | pH | Sin unidad |
| `temperatura` | Temperatura | °C |
| `turbidez` | Turbidez | NTU |
| `oxigeno_disuelto` | Oxígeno disuelto, O₂ | mg/L |
| `conductividad` | Conductividad eléctrica | µS/cm |
| `solidos_disueltos` | Sólidos disueltos totales | mg/L |
| `nitratos_no3` | Ion nitrato, NO₃⁻ | mg/L como NO₃⁻ |
| `nitratos_n` | Nitratos expresados como nitrógeno, N | mg/L como N |
| `fosfatos_po4` | Fosfatos como PO₄³⁻ | mg/L como PO₄³⁻ |
| `fosfatos_p` | Fosfatos expresados como fósforo, P | mg/L como P |
| `plomo`, `cadmio`, `arsenico`, `mercurio` | Pb, Cd, As, Hg, respectivamente | mg/L del elemento |

No se deduce si un metal es total o disuelto, su estado de oxidación ni el método de preparación. Esa información debe declararse en el método/observaciones. No se convierte entre NO₃⁻ y N, entre PO₄³⁻ y P ni entre conductividad y sólidos disueltos.

### Unidades y validación

- Confirma la unidad de **cada columna** en la interfaz. La unidad no se deduce de su encabezado. Para resultados de concentración puedes elegir mg/L o µg/L; se normalizan a mg/L y se registra la unidad de origen. 10 µg/L equivale a 0,01 mg/L. No se mezclan unidades en una columna.
- Para conductividad se admiten únicamente µS/cm; temperatura en °C y turbidez en NTU. Convierte otras unidades fuera de la aplicación con un procedimiento apropiado, o solicita soporte explícito antes de cargarlas.
- Las celdas numéricas pueden usar punto o coma decimal y notación científica. No se admiten separadores de miles: `1,234` significa 1.234. Los valores con unidades dentro de la celda (`10 mg/L`), texto no reconocido, infinitos y números que desborden se marcan inválidos. Los valores finitos, incluidos extremos o negativos, se conservan para revisión; la aplicación no certifica plausibilidad física ni calidad de laboratorio.
- Una celda vacía es **Ausente**. `ND` o `NA` son **Inválidos**, pues no se conoce su significado ni su límite. No se interpretan como cero.
- `<0.01`, `<0,01`, `<LC` y `<LQ` se registran como **Inferior a LC**. Cuando se declara un número debe ser positivo y finito; se guarda y convierte su unidad si procede. `<LC`/`<LQ` conservan el resultado sin inventar un límite numérico. Confirma que `<número` represente realmente un LC en tu fuente, no otro tipo de límite.
- Los resultados inferiores a LC no son inválidos ni ausentes: tienen su propia categoría. Se excluyen de promedio, mínimo, máximo, gráficos numéricos y comparaciones, sin sustituirlos por cero, LC/2 ni LC. Se conserva el texto original y no se concluye cumplimiento a partir de esos valores. Los promedios representan solo el subconjunto cuantificado.
- Los límites didácticos se expresan en la unidad de cálculo. Los nuevos parámetros comienzan **sin comparación**; si activas una, debes introducir ambos límites. No evaluado no significa sin riesgo. Los tres intervalos originales siguen disponibles como ejercicios.

### Identificación e informe Word

En **Columnas de identificación y observaciones por muestra** puedes mapear `codigo_muestra`, `fecha`, `lugar`, `responsable`, `metodo_analitico` y `observaciones_campo`. Son opcionales y se incluyen por fila cuando existen. Los códigos de texto conservan sus ceros iniciales; en Excel almacénalos como texto, ya que el formato visual de una celda numérica no se reproduce. Las fechas se conservan tal como se leen, sin inferir día/mes.

También hay campos generales opcionales de proyecto, código, fecha, lugar, responsable, método y observaciones. El Word separa identificación, observaciones de campo, resultados e interpretación descriptiva. Incluye estadísticas y un gráfico por parámetro, alertas, calidad y una relación de originales no cuantificados. Los datos de identificación proporcionados se reproducen; no se inventan resultados ni métodos.

Las tablas se dividen por parámetro, con anchos fijos dentro de una página A4, encabezados repetidos y filas que no se dividen entre páginas. Se evita la tabla anterior de siete columnas comprimidas y se desactiva el corte de palabras dentro de las celdas. La apariencia final depende del visor de Word; códigos sin espacios excepcionalmente largos pueden requerir ajuste manual. Las concentraciones pequeñas se representan con seis cifras significativas (incluida notación científica), evitando redondearlas automáticamente a cero.

### Cómo probar v0.3

1. Ejecuta las pruebas desde la raíz del proyecto:

   ```bat
   .venv\Scripts\python.exe -m unittest discover -s tests -v
   ```

2. Inicia Streamlit con el comando habitual y selecciona **ejemplo.csv**: deben conservarse 6 filas, 18 valores válidos y 5 alertas.
3. Elige **ejemplo_ampliado.csv**: datos totalmente ficticios con los 14 campos del catálogo, códigos, fechas y observaciones. Hay resultados `<LC` y `<0.001`. Confirma mg/L para las concentraciones de este ejemplo. Verifica que los nuevos parámetros no tengan comparación activada.
4. Activa un intervalo de ejercicio para plomo, escribe mínimo `0` y máximo `0.006` mg/L: el valor `0.008` genera una alerta; `<0.003` se mantiene sin evaluar.
5. Selecciona **ejemplo_validacion.csv**, también ficticio: elige **µg/L** para plomo, cadmio, arsénico y mercurio, y conserva µS/cm para conductividad. Por ejemplo, el promedio de los valores cuantificados de plomo debe ser `0.015` mg/L; no se incorporan `ND` ni la celda vacía.
6. Genera el Word y revisa identificación, observaciones, resultados, LC y gráficos. Ábrelo en Word o LibreOffice para comprobar su presentación. Los tests verifican contenido y estructura de tablas, pero no sustituyen la revisión visual en tu visor.

Los CSV ampliados son exclusivamente datos ficticios para validar software. No representan muestras reales, relaciones químicas comprobadas, normas ni valores recomendados.

### Streamlit Community Cloud

Se mantienen `app.py` y `requirements.txt` en la raíz. No hay servicios adicionales, claves API ni dependencias nuevas en v0.3. Tras actualizar la rama configurada, Community Cloud debe volver a desplegar la aplicación. El entorno local de referencia usa Python 3.12; la comprobación local no sustituye la validación del despliegue público. Para uso con muchos datos, genera informes con archivos de tamaño razonable: gráficos y tablas de muestras/LC de decenas de miles de filas pueden consumir memoria y tardar.
