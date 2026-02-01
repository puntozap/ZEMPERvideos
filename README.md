# Transcriptor de Video

Editor de video de escritorio orientado a la creación de cortes precisos, verticales optimizados para redes y flujos multiformato: corta segmentos por minutos o rangos seleccionados, genera subtítulos automáticos, exporta audio, aplica postprocesos y permite subir directamente a YouTube con metadata asistida por IA.

## Características principales
- **Corte por minutos, rango y entradas manuales:** controla inicio y fin con sliders, campos `mm:ss` sincronizados con el slider, validaciones estrictas y soporte para procesar todo el metraje en una sola operación.
- **Verticales 9:16 avanzados:** genera versiones corridas o individuales con recortes por centro/izquierda/derecha, zoom animado, relleno de color, tarjeta final (imagen + texto) y campos dedicados para personalizar cada bloque.
- **Extracción de audio y subtítulos:** exporta MP3 limpios, crea SRT desde video o audio y quema subtítulos con estilos configurables.
- **Generación de metadata con IA:** aprovecha la transcripción del corte para proponer título, descripción y etiquetas (prefijo `#{texto}`) que se llenan automáticamente al pulsar el botón “Generar metadata”.
- **Subida integrada a YouTube:** selecciona el archivo resultante, ajusta privacidad (public, unlisted, private), indica si es Short o largo, carga miniatura, y utiliza un flujo resumable con OAuth para subir y registrar enlaces directos.
- **Automatización “Agregar todo”:** utiliza lo que ya se hizo (cortes, subtítulos, IA) y sube automáticamente el contenido en modo oculto, con opción para incluir o excluir subtítulos en la carga final.
- **Gestión de credenciales OAuth:** registra múltiples `client_secret` en `credentials/`, inicia un servidor en `localhost:4850` para capturar códigos, guarda refresh tokens y actualiza el botón de registro con los datos necesarios.
- **Panel de actividad y logs:** cada evento (corte, upload, generación IA, error) queda documentado en la pestaña de actividad; la interfaz incluye scroll general y subpestañas fijas para YouTube, Corte, Subtítulos, IA, Descargas y más.

## Requisitos
- Python 3.11+ (probado también en 3.13).
- FFmpeg instalado y accesible desde `PATH`.
- Windows recomendado para compatibilidad total con la interfaz CustomTkinter, aunque puede ejecutarse en otros sistemas.

## Instalación paso a paso
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```
Verifica que FFmpeg funcione:
```powershell
ffmpeg -version
```

## Ejecución
```powershell
python app.py
```
El programa inicia maximizado, mantiene las subpestañas fijas dentro de cada módulo (como en Corte y YouTube) y activa la escucha en el puerto 4850 para OAuth si hay credenciales pendientes.

## Configuración adicional
- **OpenAI:** crea un `.env` en la raíz con `OPENAI_API_KEY=tu_token` para permitir que la IA genere títulos, descripciones y hashtags desde la transcripción.
- **Credenciales YouTube:** coloca tus JSON `client_secret_*.json` dentro de `credentials/`. La app detecta todas las credenciales válidas, muestra la activa en `.active_credentials` y guarda automáticamente el refresh token en archivos con timestamp. Esa carpeta está ignorada por Git (`credentials/*.json`) para proteger los secretos.
- **Miniaturas y videos existentes:** la pestaña de miniatura lista los clips short y largos ya cargados en YouTube y permite asociar un `videoId` para subir una imagen nueva.

## Flujo de YouTube
- Desde la pestaña “YouTube” puedes navegar entre “¿Qué es?”, “Configuración” y “Subir video”; las subpestañas se mantienen visibles y todo el contenido tiene scroll si necesita más espacio.
- Selecciona el archivo resultado del corte (individual o vertical), escribe el título, descripción y etiquetas (el sistema los formatea como `#{texto}`) o usa “Generar metadata” para llenar esos campos con IA.
- Indica duración declarada, privacidad, si es Short, elige miniatura (puede cargarse desde la nueva pestaña) y toca “Subir video” para iniciar una carga resumable con feedback continuo en la sección de actividad.
- “Agregar todo” procesa, genera subtítulos y dispara la subida automáticamente en modo oculto; puedes optar por incluir subtítulos en la carga final o dejar un video únicamente con metadata y miniatura.

## Salidas
- `output/{base}/cortes/`: clips normales exportados.
- `output/{base}/verticales/vertical-corte_###/`: cortes verticales corridos con numeración.
- `output/{base}/verticales/vertical-individual_###/`: verticales individuales con ajustes por bloque.
- `output/{base}/audios/`: MP3 extraídos.
- `output/{base}/subtitulos/`: SRT derivados.
- `output/{base}/subtitulados/`: videos subtitulados (si no provienen de verticales generados).
- `output/{base}/download/`: descargas directas de YouTube (MP3/MP4).

## Notas importantes
- Todos los archivos respetan el patrón `Nombre_parte_001.mp4`, `Nombre_parte_002.mp4`, etc., e incluyen metadatos en la nomenclatura para facilitar la organización.
- Si activas la tarjeta final, el clip editado se concatena con la imagen + texto configurada, ajustando la duración de cierre automáticamente.

## Resolución rápida de problemas
- Si FFmpeg no responde, confirma que existe en `PATH` y que el ejecutable es accesible desde la terminal del entorno virtual.
- Si la generación de SRT falla, verifica codecs de audio, niveles de ruido o duración excesiva de silencio.
- Si YouTube devuelve 403 o fallas de conexión, actualiza la credencial en la pestaña de YouTube, fuerza el refresh token desde el navegador y asegúrate de que el proyecto tiene habilitado el API de YouTube Data v3.

---
