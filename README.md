# 🌿 Analizador Ambiental Inteligente

Aplicación en español para explorar mediciones de pH, temperatura (°C) y turbidez (NTU). Construida con Python, Streamlit, pandas, Plotly y python-docx. Todas las herramientas son gratuitas y no se necesitan claves API ni servicios de inteligencia artificial. El análisis es estadístico y mediante reglas configurables.

## Qué permite hacer

- Subir CSV, XLSX y XLS o usar datos de ejemplo.
- Seleccionar las columnas de cada parámetro y consultar una vista previa.
- Calcular promedio, mínimo y máximo con los datos numéricos válidos.
- Explorar gráficos con zoom y cursor.
- Ajustar intervalos y ver cada medición fuera de ellos.
- Descargar un informe Word detallado con identificación del proyecto, estadísticas, porcentajes de alertas y datos excluidos, tres gráficos y recomendaciones de revisión.

**Los intervalos iniciales son exclusivamente didácticos:** pH 6,5–8,5; temperatura 15–30 °C; turbidez 0–5 NTU. No son normas ambientales. No determinan potabilidad, seguridad ni cumplimiento legal. Los límites están incluidos; solo se marca lo que queda por debajo o por encima. No se convierten unidades automáticamente.

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
5. Para usar tu archivo, súbelo y desmarca **Usar datos de ejemplo** si sigue marcado. Revisa la fuente activa y selecciona las tres columnas. Ajusta los límites en la barra lateral y ve a **Informe detallado en Word**. Puedes completar proyecto, lugar, responsable y observaciones. Pulsa **Generar informe detallado** y después **Descargar informe Word** para guardar el documento. Si cambias los datos o los límites, genera nuevamente el informe.
6. Detén la aplicación con `Ctrl+C` en la terminal. Para abrirla otro día, repite únicamente el último comando del paso 3 desde la carpeta del proyecto.

Si el puerto está ocupado, añade `--server.port 8502` al comando de Streamlit.

## Formato de los datos

Consulta `datos/ejemplo.csv` y `datos/ejemplo.xlsx`. Una fila es una medición; se requiere una columna diferente para cada parámetro. La columna `fecha` es opcional: los gráficos utilizan el orden de las filas, no el tiempo.

```csv
fecha,ph,temperatura,turbidez
2026-01-01,7.1,22,3
2026-01-02,7.4,23,4
```

Para decimales con coma, usa punto y coma como separador (`7,1;22;3`). Se admite CSV UTF-8 y, como alternativa, Latin-1. En Excel se lee únicamente la primera hoja, con encabezados en su primera fila y sin contraseña. Se aceptan hasta 20 MB y 50.000 filas; Excel se carga antes de comprobar el número de filas, así que evita libros muy grandes.

Los valores vacíos, no numéricos o infinitos se excluyen por parámetro y se contabilizan en pantalla y en el informe. No se rellenan ni se eliminan filas enteras por un valor faltante. Un parámetro sin valores válidos muestra estadísticas sin datos. No se descartan valores extremos automáticamente.

## Archivos

- `app.py`: interfaz y gráficos.
- `analisis.py`: lectura, cálculos y generación de Word.
- `requirements.txt`: dependencias.
- `datos/`: archivos de ejemplo.
- `tests/test_app.py`: pruebas de cálculos, archivos, informes e interfaz.

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
git add app.py analisis.py requirements.txt README.md .gitignore datos tests
git commit -m "Crear Analizador Ambiental Inteligente"
git push -u origin HEAD:main
```

El último comando envía la rama local a `main`. Si hay cambios previos en GitHub y el envío es rechazado, no uses `--force`: descarga e integra esos cambios primero. Si pide identificar al autor, configura `git config user.name "Tu nombre"` y `git config user.email "Tu correo"` y vuelve a ejecutar el commit. Git puede abrir el navegador para iniciar sesión en GitHub; no necesitas poner tokens dentro del código.

Si trabajas desde esta interfaz, guarda primero los cambios mediante sus opciones de Git o ejecutando esos comandos en la terminal del entorno. Después podrás clonarlos en Windows. Nunca subas `.venv` ni archivos ambientales privados; `.gitignore` ya excluye el entorno virtual.

## Informe detallado

Los gráficos del Word son imágenes estáticas generadas con Matplotlib; los de la aplicación siguen siendo interactivos con Plotly. El porcentaje de alertas se calcula sobre los valores válidos de cada parámetro. El porcentaje de exclusión se calcula sobre todas sus filas. Un parámetro sin datos válidos se indica explícitamente y no se interpreta como ausencia de alertas. La identificación es opcional y se utiliza únicamente en el documento. La generación se realiza al pulsar el botón para evitar repetirla en cada ajuste. No se utiliza IA ni se hacen diagnósticos sanitarios o normativos.
