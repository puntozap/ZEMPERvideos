# Analítica de YouTube (videos y shorts)

Este documento muestra cómo usar las funciones nuevas de `core.youtube_api` y el script `scripts/test_youtube_analytics.py` para probar rápidamente los datos analíticos de tus videos y shorts.

## Requisitos previos

1. La credencial activa debe incluir el scope `https://www.googleapis.com/auth/yt-analytics.readonly`. El módulo ya lo aplica como `YOUTUBE_ANALYTICS_SCOPE` dentro de `core.youtube_credentials.DEFAULT_SCOPES`, pero si tienes una credencial registrada anteriormente debes volver a autorizarla para que Google expida un refresh token con ese scope. Usa la pestaña **YouTube** para generar la URL OAuth y pegar el nuevo `refresh_token` antes de registrar.
2. La cuenta debe tener acceso al canal cuyos videos quieres analizar.
3. Para listar comentarios desde la pestaña Analítica, la credencial debe incluir `https://www.googleapis.com/auth/youtube.force-ssl` (también incluido en `DEFAULT_SCOPES`).

## API disponible

- `core.youtube_api.obtener_analitica_videos(...)`: llama directamente al endpoint `reports` de YouTube Analytics y devuelve cada fila como un dict (`views`, `estimatedMinutesWatched`, `averageViewDuration`, etc.). Puedes personalizar `start_date`, `end_date`, `ids`, `metrics`, `dimensions` y `filters`. El valor por defecto de `ids` es `channel==MINE`, por lo que no necesitas pasarlo si estás trabajando con el canal autenticado.
- `core.youtube_api.obtener_analitica_videos_y_shorts(...)`: extiende la anterior y enriquece cada fila con `video_id`, `video_title`, `duration_seconds` e `is_short`, separando el resultado en listados de videos largos y shorts.

## Script de prueba

El script `scripts/test_youtube_analytics.py` imprime un resumen de las métricas solicitadas y muestra los primeros `N` videos por categoría. Para ejecutarlo:

```bash
python scripts/test_youtube_analytics.py --start-date 2026-01-01 --end-date 2026-01-31 --max-results 20 --sample 5
```

También puedes pasar `--metrics views,estimatedMinutesWatched,likes` o `--filters video==VIDEO_ID` para concentrarte en un video concreto. El script usa `log_fn=print`, así que verás trazas de la llamada a la API en la consola.

## Qué buscar en la respuesta

- Las propiedades `video_id` y `video_title` vienen del `reports` y del listado de uploads, respectivamente.
- `duration_seconds` y `is_short` se calculan en base a la duración del video (`<= 60s` implica short).
- `rows["videos"]` y `rows["shorts"]` permiten comparar fácilmente vistas/tiempo entre formatos largos y cortos.

## Siguientes pasos

1. Usa la estructura de datos devuelta (`rows["videos"]`, `rows["shorts"]`) para generar gráficas o resúmenes personalizados.
2. Integra el script en la interfaz (nueva pestaña `YouTube Analytics`) si quieres mostrar los datos dentro de la app.

> La pestaña “Analítica” ya está disponible en la ventana principal. Usa **Cargar videos** para obtener un dropdown por título, selecciona uno y verás `views`, `likes`, `comentarios` y un top de países (vistas por país).
