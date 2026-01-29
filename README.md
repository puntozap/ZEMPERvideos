# Transcriptor de Video

App de escritorio para cortar videos, convertir a vertical TikTok, extraer audio en MP3, generar SRT, quemar subtitulos y crear un cierre (imagen + texto) al final. Incluye pestaña IA para generar descripcion/hashtags desde un SRT con OpenAI.

## Caracteristicas
- Corte por minutos y rango (sliders).
- Corte individual vertical 9:16 con recorte (centro/izq/der), zoom, color de relleno, zoom in/out y tarjeta final (imagen + texto).
- Extraer audio en MP3 (sin WAV).
- YouTube MP3 y YouTube MP4 (descarga directa).
- Generar SRT desde audio o video.
- Quemar SRT en video con configuracion de estilo.
- IA TikTok: resumen, descripcion y hashtags desde un SRT.
- Actividad con logs por proceso.

## Requisitos
- Python 3.11+ (funciona en 3.13)
- FFmpeg en PATH
- Windows recomendado

## Instalacion
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Verifica FFmpeg:
```powershell
ffmpeg -version
```

## Ejecutar
```powershell
python app.py
```

## OpenAI (IA TikTok)
Crea un archivo `.env` en la raiz con:
```
OPENAI_API_KEY=tu_token
```

## Salidas
Todo se guarda dentro de `output/`:
- `output/videos/` cortes, verticales y subtitulados
- `output/audios/` mp3
- `output/subtitulos/` srt
- `output/downloads/` YouTube

## Notas
- Los videos se nombran con el nombre original y parte: `Nombre_parte_001.mp4`.
- Si usas tarjeta final, el clip se agrega al final del video con duracion configurable.

## Troubleshooting rapido
- Si falla FFmpeg, verifica PATH.
- Si no genera SRT, revisa que el audio tenga contenido.

---


