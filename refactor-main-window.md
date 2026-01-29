# Refactor UI (main_window.py)

Objetivo
- Separar en modulos por pestaña
- Mejorar legibilidad
- Reducir tamaño
- Evitar duplicacion

Propuesta de estructura

ui/
  main_window.py            # solo wiring general y layout principal
  tabs/
    __init__.py
    corte_tab.py            # Corte editado
    corte_individual_tab.py # Corte individual
    srt_tab.py              # Generar subtitulos
    subtitular_tab.py       # Subtitular video
    ia_clips_tab.py         # IA Clips
    ia_tiktok_tab.py        # IA TikTok
    audio_tab.py            # Audio MP3
    youtube_mp3_tab.py      # YouTube MP3
    youtube_mp4_tab.py      # YouTube MP4
    actividad_tab.py        # Actividad
  shared/
    __init__.py
    state.py                # estados compartidos (paths, rango, stop)
    helpers.py              # utils de UI (logs, popups, limpieza, renombrar)
    preview.py              # preview video / subtitulos

Plan recomendado
1) Extraer helpers comunes
   - log(), log_seccion(), alerta_busy(), limpiar_entry()
   - renombrar largo y renombrar relacionados
   - abrir carpeta (videos, audios, subtitulos, descargas)

2) Extraer estados compartidos
   - estado (path, es_audio, fondo)
   - rango, rango_ind
   - sub_state, srt_state, ai_state
   - stop_control (busy/stop)

3) Extraer pestañas 1 por 1
   - mover widgets + handlers a archivos en ui/tabs/
   - cada tab expone create_tab(parent, context)

4) Crear un context comun
   - context = {log, log_seccion, stop_control, helpers, estado, rango, ...}
   - se pasa a cada tab

5) Limpiar main_window.py
   - queda solo la estructura principal, header y tabs principales
   - carga tabs con funciones

Beneficios
- main_window.py mucho mas corto
- codigo de cada pestaña aislado
- se evita duplicacion de funciones y estados
- mantenimiento mas simple

Notas
- Se debe validar imports cruzados
- Si se usa preview de subtitulos, moverla a shared/preview.py
- Revisar rutas absolutas / output

