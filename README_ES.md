# TextCleaner

Herramienta de limpieza de textos OCR en español, diseñada principalmente para limpiar textos en Markdown generados por MinerU, herramientas OCR o programas de análisis de PDF.

Versión actual: v1.2.0

## Funciones principales

TextCleaner está orientado a textos académicos, informes, libros y otros resultados OCR en español. Ayuda a los usuarios a realizar automáticamente tareas habituales de limpieza textual, por ejemplo:

* Eliminar líneas en blanco innecesarias, espacios anómalos y ruido de formato generado por OCR
* Reparar palabras cortadas en español:
  * Cortes con guion entre líneas, por ejemplo: situa-ción → situación
  * Cortes sin guion entre líneas, por ejemplo: situa\nción → situación
  * Cortes de palabra dentro de una línea
* Restaurar parcialmente tildes perdidas en español, por ejemplo: politica → política
* Eliminar números de notas al pie y números de anotaciones
* Eliminar bloques de fórmulas y ruido relacionado con fórmulas
* Eliminar portadas, páginas de copyright e índices de libros o informes
* Eliminar referencias, Bibliografía, Notas, apéndices, publicidad, páginas de suscripción y otros contenidos ajenos al cuerpo principal
* Permitir la limpieza de archivos Markdown mediante arrastrar y soltar
* Permitir el procesamiento por lotes de archivos Markdown
* Asistencia para la revisión de PDF
* División de archivos PDF grandes
* Recuento de formas/tokens

## Funciones aún no disponibles

* Llamada automática por lotes a MinerU para analizar archivos PDF

Esta función todavía presenta problemas conocidos. En la versión actual, se recomienda analizar primero los PDF manualmente con MinerU y después colocar los archivos Markdown generados en `output/mineru_raw/` para su limpieza.

## Casos de uso

Esta herramienta es adecuada para:

* Limpieza de textos en español después del OCR de documentos PDF
* Reorganización secundaria de resultados generados por MinerU
* Preprocesamiento de archivos Markdown antes de la construcción de corpus
* Limpieza por lotes de textos académicos, informes sectoriales, libros y otros documentos

## Instalación y uso

Para la primera instalación, descomprime el único archivo ZIP incluido en la carpeta del proyecto dentro del directorio del programa.

- macOS: Ejecuta `1_首次安装_macOS.command` durante la primera instalación y después arrastra los archivos a `TextCleaner.app`.
- Windows: Ejecuta `1_首次安装_Windows.bat` durante la primera instalación y después arrastra los archivos a `2_拖放清洗_Windows.bat`.

Ejecución desde el código fuente:

```bash
python3 -m pip install -r requirements.txt
python3 "textcleaner V1.2.py"
```

## Entradas habituales

- Doble clic en `拆分大PDF.command`: divide los PDF de más de 250 páginas en volúmenes de 200 páginas y los guarda en `pdf_split/` en el Escritorio.
- Doble clic en `TextCleaner.app`: limpia los archivos Markdown arrastrados.
- Ejecutar `textcleaner V1.2.py`: limpia los archivos Markdown ubicados en `output/mineru_raw/`.

## Estructura de directorios

- `data/`: frases de parada y palabras candidatas
- `docs/`: documentación del proyecto e instrucciones de uso
- `tests/`: pruebas automáticas
- `output/`: entrada, salida y registros de TextCleaner

## Pruebas

```bash
python3 -m pytest
```

## Más información

Consulta:

- `docs/README.md`
- `docs/PDF拆分使用说明.txt`
- `docs/拖放程序使用说明.txt`