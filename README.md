# zempervideos — Transcriptor de Video

`ZEMPERvideos` es el nombre del repositorio que aloja “Transcriptor de Video”, una herramienta de escritorio (CustomTkinter + Python) diseñada para cortar, subtitular, enriquecer con IA y publicar videos/audios sin salir de una sola aplicación. El flujo integra generación de metadata, exportación de verticales, subida a Drive, YouTube y TikTok, y envíos masivos por WhatsApp con media alojada en Drive.

## Arquitectura al vuelo
- `ui/`: cada pestaña (Corte, Visualizador, Drive, YouTube, WhatsApp, Actividad, etc.) lee y muta el estado compartido definido en `ui/shared/state.py`.  
- `core/`: contiene los módulos de negocio (procesamiento de video, OAuth, Drive, YouTube, TikTok y WhatsApp) y helpers reutilizables (`utils`, `helpers`, `drive_config`).  
- `credentials/`: almacena los secretos guardados, como el `drive_oauth_token.json`, los JSON copiados de cuentas de servicio y client secrets, así como `drive_config.json` con metadatos persistidos (carpeta de Drive, rutas activas).
- `venv/` mantiene el entorno virtual; `requirements.txt` lista dependencias (CustomTkinter, google-api-python-client, OpenAI Whisper, etc.).

## Flujo destacado 
1. **Procesamiento:** corta video/audio con sliders fijos y validaciones, genera subtítulos/visualizadores y exporta MP3, SRT y clips verticales (centro, izquierda, derecha).  
2. **IA y metadata:** partiendo del texto transcrito se proponen título, descripción y etiquetas; también se puede generar un mensaje global para WhatsApp.  
3. **Drive configurado:** la pestaña Drive gestiona cuentas de servicio y OAuth, guarda los JSON seleccionados dentro de `credentials/` y mantiene `drive_config.json` para saber qué credenciales están activas y qué carpeta (ID) se usará para subir media.  
4. **Integración YouTube/TikTok:** se aprovechan los tokens persistidos (refresh tokens) para subir contenido, seleccionar privacidad, miniaturas y enviar bajo el mismo flujo de la pestaña “Descargas”.  
5. **WhatsApp + Drive:** el ID de carpeta configurado se comparte entre Drive y WhatsApp, así que la pestaña de mensajes reutiliza automáticamente la carpeta almacenada y persiste el valor cada vez que se edita, además de poder subir la media antes de enviar.
6. **Actividad y logs:** las acciones (cortes, OAuth, uploads, errores) se reflejan en la pestaña de actividad que sirve para hacer troubleshooting sin salir de la UI.

## Configuración de credenciales
- **Drive:** al seleccionar un JSON de cuenta de servicio o cliente OAuth, el archivo se copia a `credentials/drive_service_account.json` / `credentials/drive_oauth_client_secret.json`, se valida y se registra automáticamente en `drive_config.json`. El flujo OAuth abre un servidor local, solicita `prompt="consent"` y guarda el `refresh_token` en `credentials/drive_oauth_token.json`.  
- **Carpeta persistente:** el campo “Carpeta de Drive” guarda el ID en `drive_config.json`; cualquier cambio se refleja en las pestañas de Drive y WhatsApp gracias a la variable compartida `drive_folder_var`.  
- **WhatsApp:** usa la carpeta guardada para subir media, comparte los archivos y limpia los IDs una vez concluidos los envíos.

## Requisitos
- Python 3.11+ (también probado en 3.13).  
- FFmpeg accesible desde `PATH`.  
- Windows recomendado (por CustomTkinter), aunque el backend puede ejecutarse en otros sistemas si se adapta la interfaz.

## Instalación
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```
Verifica FFmpeg con `ffmpeg -version`.

## Ejecución
```powershell
python app.py
```
La UI se inicia maximizada, fija los submenús y escucha `localhost:4850` para capturar el flujo OAuth cuando se autoriza Drive o YouTube.

## Tips rápidos
- Crea `.env` con `OPENAI_API_KEY=tu_token` para habilitar la generación asistida de títulos/descripciones/hashtags.  
- La pestaña Drive sirve tanto para cuentas de servicio (subir directamente) como para OAuth (caso de WhatsApp/YouTube) y almacena los JSON que se cargan.  
- Cambia el ID de carpeta una sola vez, porque el sistema lo persiste y lo vuelve a usar en cada envío sin pedirlo otra vez.  
- Usa la pestaña de actividad para leer errores de OAuth, Drive y WhatsApp; allí se registran los `refresh_token` faltantes y los fallos de subida.

## Salidas
- `output/{base}/cortes/` → clips normales.  
- `output/{base}/audios/` → MP3.  
- `output/{base}/subtitulos/` → SRT.  
- `output/{base}/verticales/` → versiones 9:16.  
- `output/{base}/subtitulados/` → videos con subtítulos quemados.  
- `output/{base}/download/` → descargas generadas (MP3/MP4).

## Documentación adicional
- `docs/instagram_reel_upload.md`: guía para subir Reels manualmente y vía la API.  
- `docs/youtube_credentials.md` y `docs/youtube_upload.md`: ayuda para registrar JSON y subir videos con OAuth.  
- `api-tik-tok.md` y otros README dentro de `docs/` explican flujos específicos de TikTok y demás integraciones.

Si necesitas que este README también incluya capturas, un diagrama de arquitectura o los pasos exactos de OAuth/WhatsApp, dime y los agrego.
