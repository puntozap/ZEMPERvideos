# Cómo subir un Reel a Instagram

## Antes de empezar
- Asegúrate de tener la app de Instagram actualizada en tu dispositivo móvil.
- Cuenta con el video finalizado en resolución vertical (preferible 9:16) y duración máxima 90 segundos (consulta el límite vigente).
- Prepara el audio, subtítulos o stickers si los usarás desde la galería de Instagram o un archivo local.
- Si el Reel va asociado a una cuenta profesional, confirma que iniciaste sesión en esa cuenta antes de subir.

## Pasos para subir el Reel
1. **Abrir Instagram y tocar el icono “+”** que aparece en la parte inferior central (o superior derecha en algunas versiones) y elegir “Reel”.
2. **Seleccionar el video** desde tu librería o grabar directamente desde la app. Si traes el archivo desde el escritorio, transfiérelo al teléfono (puedes usar AirDrop, cable USB o servicios en la nube) antes de subir.
3. **Editar el Reel en Instagram**:
   - Ajusta el punto de inicio si necesitas recortar segmentos.
   - Aplica filtros, despeja el audio o sincroniza el clip con la música que elijas desde “Audio” o “Música”.
   - Añade texto, subtítulos o stickers arrastrándolos sobre el lienzo y programando su aparición (mantén presionado el elemento para abrir su timeline).
4. **Definir la portada** tocando “Portada” y eligiendo un fotograma propio o subiendo una imagen personalizada para que se vea en el feed.
5. **Escribir el texto del Reel** en el campo “Escribe un pie de foto”. Usa hashtags relevantes (por ejemplo `#Reel`, `#Tutorial`, `#Viral`) y menciona cuentas con `@`.
6. **Ajustar la visibilidad y la publicación**:
   - Decide si el Reel se comparte también en el feed o solo en Reels.
   - Activa o desactiva comentarios, guarda automático y permite que otros remezclen tu Reel desde las opciones avanzadas.
7. **Publicar** tocando “Compartir”. Instagram procesará el video y lo dejará disponible en tu perfil bajo la pestaña “Reels”.

## Publicar via API de Instagram
1. **Registro y configuración**: crea tu app en el portal oficial de Meta for Developers (`https://developers.facebook.com/apps/`), habilita Instagram Graph API y vincula tu cuenta profesional a una Página de Facebook. Desde ahí solicita permisos (`instagram_basic`, `instagram_content_publish`, `pages_read_engagement`) y completa App Review/ Page Publishing Authorization.
2. **Requisitos**: necesitas una cuenta profesional (Business o Creator) conectada a una Página de Facebook, crear una app en developers.facebook.com y solicitar los permisos `instagram_basic`, `instagram_content_publish` y `pages_read_engagement`. Para producción también deberás pasar App Review y completar la verificación de la Página (dos factores, Page Publishing Authorization). Guarda un token de usuario con esos permisos, que caduca cada 60 días.
1. **Requisitos**: necesitas una cuenta profesional (Business o Creator) conectada a una Página de Facebook, crear una app en developers.facebook.com y solicitar los permisos `instagram_basic`, `instagram_content_publish` y `pages_read_engagement`. Para producción también deberás pasar App Review y completar la verificación de la Página (dos factores, Page Publishing Authorization). Guarda un token de usuario con esos permisos, que caduca cada 60 días.
2. **Crear un contenedor de medios**: haz `POST https://graph.facebook.com/v{version}/{ig-user-id}/media` con parámetros como:
   - `media_type=REELS`, `video_url=<URL pública>`, `caption=<texto>` y `share_to_feed=true` si quieres que aparezca también en el feed.
   - Si el video no tiene URL accesible, usa `upload_type=resumable` para obtener un `upload_session_id`, sube los trozos y luego vuelve a intentar crear el contenedor.  
   - Opcional: pasa `cover_url`, `thumb_offset`, `child_attachments` o `collaborators` según necesites.
3. **Verificar estado**: consulta `GET https://graph.facebook.com/v{version}/{container_id}?fields=status_code,status`. El valor `FINISHED` indica que Instagram procesó el archivo y está listo para publicar; `IN_PROGRESS` significa que todavía está procesando y `ERROR` indica un fallo (revisa `status` para detalles).
4. **Publicar el Reel**: cuando el contenedor esté listo, ejecuta `POST https://graph.facebook.com/v{version}/{ig-user-id}/media_publish?creation_id={container_id}`. Instagram devolverá el `id` definitivo del post. Si necesitas programar la publicación, esta llamada debe hacerse cuando estés listo para publicar (no hay scheduling nativo).
5. **Límites y buenas prácticas**:
   - El video debe cumplir codecs H.264/HEVC, audio AAC@48kHz, 23‑60 fps, resolución preferible 9:16, <300 MB y duración ≤15 minutos; la portada portada debe ser sRGB y <8 MB.
   - Cada cuenta puede crear hasta ~400 contenedores y publicar unos 100 posts totales en 24 h. Haz gestión de reintentos y guarda el estado del `creation_id` porque expira a las 24 h.
   - Para subtítulos, adjunta `caption` o sube un archivo SRT (si la API lo permite en tu versión) antes de publicar.
   - Documenta cada envío en tus registros (fecha, contenedor, estado) para poder rescatar errores y reintentos.
6. **Enlaces útiles**:
   - Referencia oficial del endpoint `media`: [https://developers.facebook.com/docs/instagram-api/reference/ig-user/media](https://developers.facebook.com/docs/instagram-api/reference/ig-user/media)
   - Publicar contenedores: [https://developers.facebook.com/docs/instagram-api/reference/ig-user/media_publish](https://developers.facebook.com/docs/instagram-api/reference/ig-user/media_publish)
   - Guía de métricas, límites y permisos: [https://developers.facebook.com/docs/instagram-api](https://developers.facebook.com/docs/instagram-api)

## Sugerencias
- Si vas a reutilizar el mismo video en otras plataformas (TikTok, YouTube Shorts), exporta versiones separadas con el nombre `Reel_{fecha}` para identificarlos fácilmente.
- Conserva el archivo final en la carpeta `output/{proyecto}/reels/` para mantener ordenados los resultados de cada sesión de edición.
- Aprovecha las métricas de Instagram después de publicar: abre el Reel y presiona los tres puntos > “Ver estadísticas” para revisar alcance, interacciones y guardados.

## Seguridad y buenas prácticas
- No compartas tokens o accesos. Si estás trabajando con herramientas externas, verifica que estén autorizadas con OAuth desde “Configuración > Seguridad > Aplicaciones y sitios web”.
- Usa subtítulos automáticos o manuales para mejorar la accesibilidad del Reel.
