# API TikTok (Inbox Upload)

Objetivo
- Implementar subida de videos a TikTok como "inbox" (borrador), usando Content Posting API.
- Integrarlo como nueva pestaña en la app.

Requisitos previos
- App creada en TikTok Developers con Content Posting API habilitada.
- Scopes aprobados: video.upload (y opcionalmente user.info.basic).
- Redirect URL autorizada (recomendada): http://127.0.0.1:8765/callback
- Client Key y Client Secret disponibles.

Flujo esperado
1) OAuth login
   - Abrir navegador con authorize URL.
   - Capturar code en callback local (mini servidor).
   - Intercambiar code por access_token/refresh_token.
2) Subida a inbox
   - Init upload (inbox): /v2/post/publish/inbox/video/init/
   - Subir video con PUT a upload_url.
   - Confirmar estado.

Pestaña UI sugerida
- Conectar cuenta (OAuth)
- Mostrar estado de autenticación
- Seleccionar video
- Subir a inbox
- Logs a Actividad

Almacenamiento
- Guardar tokens en output/tiktok_tokens.json
- No guardar en .env

Endpoints de referencia
- OAuth authorize
- OAuth access token
- Init upload (inbox)
- Upload PUT

Notas
- Respetar tamaños/formatos recomendados (MP4, H.264).
- Manejar expiración y refresh_token.
- Manejar errores de red y reintentos.
