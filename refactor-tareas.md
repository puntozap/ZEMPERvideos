# Actividades de refactor (main_window.py)

## 1. Preparar estructura
- [x] Crear carpeta `ui/tabs/`
- [x] Crear carpeta `ui/shared/`
- [x] Agregar `__init__.py` en cada carpeta

## 2. Helpers compartidos
- [x] Mover `log()` y `log_seccion()` a `ui/shared/helpers.py`
- [x] Mover `limpiar_entry()` a `ui/shared/helpers.py`
- [x] Mover `alerta_busy()` a `ui/shared/helpers.py`
- [x] Mover funciones `abrir_*` (videos, audios, subtitulos, descargas) a `ui/shared/helpers.py`
- [x] Mover renombrado de archivos largos a `ui/shared/helpers.py`

## 3. Estado compartido
- [x] Crear `ui/shared/state.py` con:
  - `estado`, `rango`, `rango_ind`
  - `srt_state`, `sub_state`, `ai_state`
  - `stop_control`

## 4. Preview
- [x] Mover `SimpleVideoPlayer` a `ui/shared/preview.py`
- [x] Mover preview de subtitulos (canvas/box) a `ui/shared/preview.py`

## 5. Pestañas (extraer una por una)
- [x] Corte editado -> `ui/tabs/corte_tab.py`
- [x] Corte individual -> `ui/tabs/corte_individual_tab.py`
- [x] Subtitulos -> `ui/tabs/srt_tab.py`
- [x] Subtitular video -> `ui/tabs/subtitular_tab.py`
- [x] IA Clips -> `ui/tabs/ia_clips_tab.py`
- [x] IA TikTok -> `ui/tabs/ia_tiktok_tab.py`
- [x] Audio MP3 -> `ui/tabs/audio_tab.py`
- [x] YouTube MP3 -> `ui/tabs/youtube_mp3_tab.py`
- [x] YouTube MP4 -> `ui/tabs/youtube_mp4_tab.py`
- [x] Actividad -> `ui/tabs/actividad_tab.py`

## 6. main_window.py limpio
- [x] Dejar solo layout principal, header y tabs principales
- [x] Importar y llamar `create_tab(parent, context)` por cada tab

## 7. Validacion
- [ ] Ejecutar app y validar cada tab
- [ ] Probar flujos principales (corte, srt, subtitular, descargas)
- [ ] Ajustar imports cruzados
