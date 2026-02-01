# Visualizador de música animado

Este documento describe cómo se implementará el efecto de visualizador de música responsivo que se superpone sobre los videos procesados por el "Transcriptor de Video" cuando el usuario activa la opción.

## Objetivo

- Generar un visualizador que reaccione al audio de cada segmento (voz o música) usando filtros de FFmpeg (`showspectrum`, `showwaves`, `avectorscope` o combinaciones) y producir un video auxiliar con la misma duración.
- Permitir al usuario elegir la posición del visualizador dentro del marco (centro, parte superior, parte inferior) cuando activa la casilla correspondiente; la visualización ocupará todo el ancho del video y tendrá márgenes adecuados para no cortar el contenido original.
- Mantener el visualizador sincronizado con los cortes normales y con los verticales 9:16 (el mismo control debe poder aplicarlo a ambas salidas si corresponde).

## Flujo funcional propuesto

1. **Captura de la opción del usuario.** En la pestaña principal de "Corte" se agrega un checkbox `Visualizador de música` y un selector de posición (`Centro`, `Arriba`, `Abajo`). Estos parámetros se almacenan en el estado compartido y se pasan a `procesar_video`.<br>
2. **Generación del visualizador.** Después de dividir el video (o antes del `overlay` del fondo si el visualizador actúa como capa inferior), se ejecuta un comando FFmpeg para convertir el audio de cada segmento (se puede reutilizar el MP3 que ya se escribe en `output/{base}/audios`) en un clip visual. Por ejemplo:

```
ffmpeg -y -i {audio_segment} -filter_complex "showwaves=s=1080x120:mode=line:colors=white" -pix_fmt yuv420p {visual_path}
```

Usar la resolución del video final para que pueda escalarse horizontalmente; si el video es vertical (1080x1920) se necesita generar un visualizador con esa anchura y un alto proporcional (ej. 1080x240) para luego posicionarlo.
3. **Composición final.** Usar `ffmpeg -filter_complex` para mezclar el video original con el visualizador. Según la posición elegida, el overlay se aplica como:

```
// Arriba
[0:v][1:v]overlay=(W-w)/2:10
// Centro
[0:v][1:v]overlay=(W-w)/2:(H-h)/2
// Abajo
[0:v][1:v]overlay=(W-w)/2:H-h-10
```

Si se desea, el visualizador puede renderizarse con transparencia (`format=rgba`) para no tapar completamente el video.
4. **Integración con fondos y verticales.** El efecto debe poder combinarse con `aplicar_fondo_imagen` y/o con la generación de verticales TikTok/individuales. Para los verticales se genera el visualizador con resolución 1080 de ancho; el overlay puede ajustar la altura en función del alto real (`H` de FFmpeg) para mantenerlo centrado.

## Cambios a realizar

1. `ui/tabs/corte_tab.py` (y/o la pestaña que llame a `procesar_video`) debe exponer:
   - Checkbox `Visualizador de música`.
   - Selector de posición (`Centro`, `Arriba`, `Abajo`).
   - Guardar esos valores en el estado compartido y pasarlos a `procesar_video`. Opcional: vista previa de la posición en el video de control.
2. `core/workflow.py`:
   - Añadir nuevos parámetros (`visualizador=False`, `posicion_visualizador="center"`) a `procesar_video`.
   - Si `visualizador` está activo, generar el clip del visualizador para cada fragmento usando el audio asociado (o reusar el mismo visualizador para verticales si la posición no cambia) y aplicar el overlay antes de salir del proceso.
   - En `aplicar_fondo_imagen` o en una nueva función auxiliar `overlay_visualizador`, aplicar el visualizador con la posición solicitada y asegurarse de mantener la resolución/orientación.
3. `core/utils.py`: añadir funciones auxiliares para generar el visualizador (por ejemplo `generar_visualizador_audio(audio_path, output_path, width, height, estilo)` con presets) y para determinar expresiones de overlay según la posición elegida.

## Consideraciones técnicas

- El visualizador debe reutilizar la pista de audio ya dividida para evitar reabrir el video repetidamente. Si se generan verticales, el tamaño del visualizador debe adaptarse a 1080x(200+) para que el overlay quepa.
- Para evitar sobrecargar el procesamiento, se puede limitar la duración del visualizador a la duración exacta del segmento (misma lógica que se usa para `dividir_video_ffmpeg`).
- El comando FFmpeg puede permitir estilos adicionales (líneas, barras, espectro). Incluir parámetros `estilo_visualizador` y `color` si se quiere en la UI.
- Hay que documentar el nuevo feature en un archivo `.md` (este documento) y quizás añadir pantallas en la UI para explicar los presets.

## Pruebas sugeridas

1. Activar el visualizador en modo central y comprobar que el overlay mantiene el video original intacto y escala correctamente.
2. Probar con verticales y verificar que la posición `Arriba`/`Abajo` respeta las dimensiones 1080x1920.
3. Confirmar que el paso adicional no rompe la generación de `audios`/subtítulos ni la exportación de verticales.

