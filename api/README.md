# API - Transcriptor Video

Cada vez que se agrega un endpoint nuevo, esta carpeta debe actualizarse con la documentacion correspondiente.

## Ejecutar API

```powershell
py api\api_server.py
```

Por defecto corre en `http://localhost:8000`.

## Estructura

- `api/api_server.py`: servidor principal.
- `api/api_youtube.py`: endpoints de YouTube.

## Endpoints

### Health

**GET** `/health`

Respuesta:
```json
{ "status": "ok" }
```

### Descargar YouTube (MP4)

**POST** `/youtube/download`

Body JSON:
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

Campos:
- `url` (string, requerido): URL del video.

Respuesta:
```json
{ "ok": true, "path": "output/..." }
```

Errores:
- `500`: error de descarga (yt-dlp / bloqueos).

## Notas

- La ruta `path` es local al servidor.
