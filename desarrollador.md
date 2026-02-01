# Especificación Técnica: Implementación del Visualizador de Música

## 1. Introducción

Este documento detalla la implementación técnica del visualizador de música animado. Se basa en el uso de FFmpeg para la generación de los efectos visuales y su integración en el flujo de trabajo existente de la aplicación.

## 2. Estructura de Módulos y Archivos

### 2.1. Nuevos Archivos

-   `ui/tabs/visualizador_tab.py`: Contendrá la clase `VisualizadorTab`, que define la interfaz de la nueva pestaña "Visualizador".
-   `docs/music_visualizer.md`: Documentación funcional y de planificación (ya existente).
-   `especificacion.md`: Especificación funcional detallada.
-   `desarrollador.md`: Este documento.

### 2.2. Archivos a Modificar

-   `app.py`:
    -   Importar y añadir `VisualizadorTab` al `QTabWidget` principal.
-   `ui/tabs/corte_tab.py`:
    -   Añadir un `QCheckBox("Visualizador de música")`.
    -   Añadir un `QComboBox` para la posición (`Arriba`, `Centro`, `Abajo`).
    -   Actualizar el estado compartido (`SharedState`) con los valores de estos controles.
-   `core/workflow.py`:
    -   Modificar la firma de `procesar_video` para aceptar `visualizador: bool` y `posicion_visualizador: str`.
    -   Dentro de `procesar_video`, invocar a una nueva función `aplicar_visualizador` si `visualizador` es `True`.
    -   Crear una nueva función `generar_visualizador_independiente` que será llamada desde `VisualizadorTab`.
-   `core/utils.py`:
    -   Añadir `generar_visualizador_audio()`: una función de bajo nivel que construye y ejecuta el comando FFmpeg para crear un clip de visualizador a partir de un archivo de audio.
    -   Añadir `obtener_expresion_overlay()`: una función auxiliar que devuelve el string de posicionamiento para el filtro `overlay` de FFmpeg.
-   `ui/shared/state.py`:
    -   Añadir `visualizador` (booleano) y `posicion_visualizador` (string) al `SharedState`.

## 3. Implementación Detallada

### 3.1. `core/utils.py`: Funciones de FFmpeg

#### `generar_visualizador_audio()`

```python
def generar_visualizador_audio(audio_path, output_path, width, height, fps, estilo, color, opacidad, progress_callback=None):
    """
    Genera un video de visualizador de música usando FFmpeg.

    Args:
        audio_path (str): Ruta al archivo de audio.
        output_path (str): Ruta donde se guardará el video de salida.
        width (int): Ancho del video.
        height (int): Alto del video.
        fps (int): Frames por segundo.
        estilo (str): 'showwaves', 'showspectrum', 'avectorscope'.
        color (str): Color en formato FFmpeg (ej. 'white', '#FFFFFF').
        opacidad (float): Valor entre 0.0 y 1.0.
        progress_callback (function): Callback para reportar el progreso.
    """
    # Lógica para construir el comando FFmpeg
    filter_complex = f"[0:a]{estilo}=s={width}x{height}:mode=line:colors={color}"

    # Ajustar formato de píxeles para transparencia
    pix_fmt = "yuv420p"
    if opacidad < 1.0:
        filter_complex += f":split=2[a][b];[a]format=yuva444p,colorchannelmixer=aa={opacidad}[front];[b]nullsink"
        pix_fmt = "yuva444p" # Formato que soporta canal alfa

    command = [
        "ffmpeg", "-y",
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-c:v", "libx264", # O qtrle para transparencia total si es necesario
        "-pix_fmt", pix_fmt,
        "-r", str(fps),
        output_path
    ]

    # Ejecutar el comando y usar 'progress_callback' para el progreso
    # ...
```

#### `obtener_expresion_overlay()`

```python
def obtener_expresion_overlay(posicion: str, margen: int = 10) -> str:
    """Devuelve la expresión de overlay de FFmpeg según la posición."""
    if posicion == "arriba":
        return f"(W-w)/2:{margen}"
    elif posicion == "abajo":
        return f"(W-w)/2:H-h-{margen}"
    else: # centro
        return "(W-w)/2:(H-h)/2"
```

### 3.2. `core/workflow.py`: Flujo de Procesamiento

#### `generar_visualizador_independiente()`

Esta función será el entry point para la pestaña "Visualizador". Orquestará la extracción de audio (si la entrada es un video) y la llamada a `generar_visualizador_audio`.

#### `procesar_video()`

La función será modificada para añadir el visualizador como un paso opcional.

```python
def procesar_video(..., visualizador=False, posicion_visualizador="centro"):
    # ... (lógica existente de corte)

    for segmento in segmentos:
        # ...
        if visualizador:
            audio_segmento = f"output/{base}/audios/{segmento_nombre}.mp3"
            visualizador_clip = f"output/{base}/visualizador/{segmento_nombre}.mp4"
            
            # Obtener resolución del video del segmento
            width, height = obtener_resolucion(segmento_path)

            generar_visualizador_audio(
                audio_path=audio_segmento,
                output_path=visualizador_clip,
                width=width,
                height=int(height * 0.2), # Altura del 20% del video
                # ... otros params
            )
            
            # Aplicar overlay
            video_con_visualizador = aplicar_overlay(segmento_path, visualizador_clip, posicion_visualizador)
            # El resto del flujo usará 'video_con_visualizador'
```

### 3.3. `ui/tabs/visualizador_tab.py`

-   Heredará de `QWidget`.
-   Definirá los controles de la UI (botones, selectores, etc.).
-   El botón "Generar" creará un `QThread` para ejecutar `generar_visualizador_independiente` en segundo plano.
-   Implementará un `progress_callback` que recibirá el progreso de FFmpeg y actualizará la `QProgressBar`. La captura del progreso de FFmpeg se puede hacer a través de `stdout` usando el argumento `-progress pipe:1`.

## 4. Gestión de Dependencias

-   La implementación se basará en **FFmpeg**. Se debe asegurar que el usuario tenga FFmpeg instalado y accesible en el `PATH` del sistema. La aplicación ya parece depender de FFmpeg, por lo que no se requerirían nuevas dependencias de software.

## 5. Pruebas y Verificación

1.  **Prueba unitaria de `generar_visualizador_audio`**: Verificar que genera un archivo de video válido con las dimensiones y formato correctos.
2.  **Prueba de integración en `procesar_video`**:
    -   Activar el visualizador y comprobar que se superpone correctamente en la posición deseada (`arriba`, `centro`, `abajo`).
    -   Verificar que funciona tanto para videos horizontales como verticales (9:16).
    -   Confirmar que no interfiere con otras funcionalidades como la adición de fondos o subtítulos.
3.  **Prueba de la pestaña "Visualizador"**:
    -   Generar un visualizador a partir de un MP3 y un MP4.
    -   Comprobar que la barra de progreso se actualiza correctamente.
    -   Verificar que se genera un video con transparencia si la opacidad es menor a 1.0.
