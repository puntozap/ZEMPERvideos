# Ruta de carga a YouTube

Este documento describe cómo exponer una ruta interna que permita subir cualquier video (larga duración o Shorts) a YouTube usando la API oficial. La ruta acepta metadatos mínimos y utiliza OAuth 2.0 con `youtube.upload`. Los Shorts se determinan enviando videos verticales y/o con duración ≤ 60 segundos.

## Autenticación

1. Crea un proyecto en Google Cloud Console y habilita la API de YouTube Data v3.
2. Genera credenciales OAuth 2.0 (tipo `Desktop` o `Web`) y almacena `client_id` y `client_secret`.
3. Solicita el scope `https://www.googleapis.com/auth/youtube.upload`.
4. Guarda el token (access + refresh) y renueva automáticamente cuando caduque.

## Endpoint propuesto

```http
POST /api/youtube/upload
Content-Type: multipart/form-data
Authorization: Bearer <token_activo>
```

### Campos obligatorios

- `video_file`: binario del video.
- `title`: texto (máx. 100 caracteres).
- `description`: texto, recomienda incluir `#Shorts` si aplica.
- `duration`: segundos (número). Permite determinar si se trata de un Short.
- `tags`: arreglo opcional de strings.
- `privacy`: `public` | `private` | `unlisted`.
- `is_short`: booleano opcional; si `true`, forzar ratio 9:16 y duración ≤ 60 seg.

### Validaciones

- Si `duration` ≤ 60 y/o `is_short` es `true`, asegúrate de subir un video vertical (o 1:1) para que YouTube lo clasifique como Short.
- `title` y `description` no pueden estar vacíos.
- El token debe ser válido; si falla, responde `401`.

## Flujo interno

1. Recibir archivo y metadatos desde la ruta.
2. Validar duración vs. metadata. Si la duración excede los 60 s y `is_short` es `true`, rechazar.
3. Iniciar carga en la API de YouTube usando `videos.insert?part=snippet,status`.
4. Usar `uploadType=resumable` para archivos grandes.
5. Adjuntar:
   - `snippet.title`
   - `snippet.description` (valorar `#Shorts` si aplica).
   - `snippet.tags`
   - `status.privacyStatus`
6. Subir bytes del video en bloques.
7. YouTube devolverá el `videoId`.

## Manejo de errores

- Si el upload falla, devolver `500` con mensaje del error de la API (`errors[0].message`).
- Si falta autenticación o el scope, responder `401`.
- Si el archivo excede 15 GB, YouTube rechaza; cortar el archivo o usar compresión antes de reenviar.

## Consideraciones adicionales

- Mantén `videos.update` disponible para modificar título, descripción o visibilidad posterior.
- Para Shorts, puedes incluir `#Shorts` en la descripción y verificar la relación de aspecto del video.
- Siempre que hagas uploads grandes, implementa un mecanismo de reintento para la sesión resumable.

## Cliente local

La pestaña YouTube en la aplicación de escritorio ya consume `core.youtube_upload.upload_video(...)` y el backend de credenciales:

- `core.youtube_credentials` controla el archivo activo dentro de `credentials/` y expone `load_active_credentials()` para que el uploader recupere `client_id`, `client_secret`, `refresh_token` y `token_uri`.
- `core.youtube_upload` renueva tokens, inicia la sesión resumable (`videos.insert` con `uploadType=resumable`) y envía el binario en `PUT` al `Location` devuelto.
- El botón “Subir video” en `ui.tabs.youtube_upload_tab` valida títulos, descripción, duración en mm:ss y el flag Short, luego ejecuta `upload_video()` en un hilo aparte mientras escribe el resultado en el panel de “Actividad YouTube”.

Si el backend de Google no está listo, el botón solo muestra las validaciones en el log; una vez que se habilite la ruta `/api/youtube/upload`, puedes reemplazar ese hilo por una llamada a la API y reutilizar los mismos campos de entrada.

