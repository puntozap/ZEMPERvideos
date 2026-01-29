# Actividades de refactor (main_window.py)

## 1. Preparar estructura
- [ ] Crear carpeta `ui/tabs/`
- [ ] Crear carpeta `ui/shared/`
- [ ] Agregar `__init__.py` en cada carpeta

## 2. Helpers compartidos
- [ ] Mover `log()` y `log_seccion()` a `ui/shared/helpers.py`
- [ ] Mover `limpiar_entry()` a `ui/shared/helpers.py`
- [ ] Mover `alerta_busy()` a `ui/shared/helpers.py`
- [ ] Mover funciones `abrir_*` (videos, audios, subtitulos, descargas) a `ui/shared/helpers.py`
- [ ] Mover renombrado de archivos largos a `ui/shared/helpers.py`

## 3. Estado compartido
- [ ] Crear `ui/shared/state.py` con:
  - `estado`, `rango`, `rango_ind`
  - `srt_state`, `sub_state`, `ai_state`
  - `stop_control`

## 4. Preview
- [ ] Mover `SimpleVideoPlayer` a `ui/shared/preview.py`
- [ ] Mover preview de subtitulos (canvas/box) a `ui/shared/preview.py`

## 5. Pestañas (extraer una por una)
- [ ] Corte editado -> `ui/tabs/corte_tab.py`
- [ ] Corte individual -> `ui/tabs/corte_individual_tab.py`
- [ ] Subtitulos -> `ui/tabs/srt_tab.py`
- [ ] Subtitular video -> `ui/tabs/subtitular_tab.py`
- [ ] IA Clips -> `ui/tabs/ia_clips_tab.py`
- [ ] IA TikTok -> `ui/tabs/ia_tiktok_tab.py`
- [ ] Audio MP3 -> `ui/tabs/audio_tab.py`
- [ ] YouTube MP3 -> `ui/tabs/youtube_mp3_tab.py`
- [ ] YouTube MP4 -> `ui/tabs/youtube_mp4_tab.py`
- [ ] Actividad -> `ui/tabs/actividad_tab.py`

## 6. main_window.py limpio
- [ ] Dejar solo layout principal, header y tabs principales
- [ ] Importar y llamar `create_tab(parent, context)` por cada tab

## 7. Validacion
- [ ] Ejecutar app y validar cada tab
- [ ] Probar flujos principales (corte, srt, subtitular, descargas)
- [ ] Ajustar imports cruzados

