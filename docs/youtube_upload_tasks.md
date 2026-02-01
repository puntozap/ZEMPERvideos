# Ruta de carga a YouTube – Lista de tareas

Lista pensada para marcar el progreso de la implementación que subirá videos (cortos y largos) a YouTube. Puedes ir tachando cada tarea cuando esté terminada.

- [ ] **Configurar credenciales**: Crear proyecto en Google Cloud, habilitar YouTube Data API, generar OAuth 2.0 y asegurar que el backend almacene `client_id`, `client_secret` y refresco de tokens.
- [ ] **Definir endpoint `/api/youtube/upload`**: Registrar ruta en el servidor actual y preparar la recepción de `multipart/form-data` con `video_file`, metadatos y token bearer.
- [ ] **Validar payload y metadatos**: Verificar formato mm:ss si aplica, duración vs. `is_short`, privacidad y campos obligatorios antes de tocar la API de YouTube.
- [ ] **Implementar flujo de subida**: Usar `videos.insert?part=snippet,status` con `uploadType=resumable`; pasar `title`, `description` (y `#Shorts` si aplica), `tags`, `privacyStatus` y cargar el file en bloques.
- [ ] **Sincronizar con tokens**: Reutilizar el token OAuth, refrescar cuando expire y responder `401` si no es válido o no tiene scope.
- [ ] **Manejo de errores y reintentos**: Detectar errores de YouTube, responder con el mensaje relevante y soportar reanudar uploads pausados.
- [ ] **Callbacks/actualizaciones**: Guardar el `videoId` resultante y exponer una opción para actualizar metadatos con `videos.update`.
- [ ] **Documentación y pruebas manuales**: Validar con un video real (Short y largo) y registrar en este mismo repositorio cómo se probó.
