# Especificación Funcional: Visualizador de Música Animado

## 1. Resumen de la Funcionalidad

Esta funcionalidad permite a los usuarios generar un visualizador de música animado (ondas de audio) y superponerlo en los videos procesados. El objetivo es ofrecer una capa visual dinámica que reaccione al audio del video, mejorando el atractivo del contenido final, especialmente para clips cortos en redes sociales.

La funcionalidad se implementará a través de dos interfaces principales:
1.  Una nueva pestaña dedicada llamada **"Visualizador"** para la generación de clips de visualizador independientes.
2.  Una opción integrada en la pestaña **"Corte"** para aplicar el visualizador directamente durante el proceso de corte y edición de videos.

## 2. Pestaña "Visualizador"

### 2.1. Propósito

Crear un clip de video (MP4) que contenga únicamente la animación del visualizador de música a partir de un archivo de audio o video. Este clip se guarda en `output/{nombre_base}/visualizador/` y puede ser utilizado por el usuario en otros programas de edición.

### 2.2. Componentes de la Interfaz

-   **Selector de archivo**: Un campo para seleccionar un archivo de video o audio local (`.mp4`, `.mov`, `.mp3`, `.wav`, etc.).
-   **Opciones de Estilo**:
    -   **Estilo de visualizador**: Un menú desplegable para elegir el tipo de visualización (ej. `Ondas`, `Espectro`, `Vectorescopio`).
    -   **Color**: Un selector de color para las ondas/barras del visualizador (con soporte para valores hexadecimales, ej. `#FFFFFF`).
    -   **Opacidad**: Un deslizador o campo numérico (0-1) para controlar la transparencia del fondo del visualizador. Un valor de `0` creará un video con fondo transparente (canal alfa).
-   **Opciones de Calidad**:
    -   **Calidad**: Un menú desplegable con opciones (`Baja`, `Media`, `Alta`) que preconfiguran la resolución y los FPS del video de salida para optimizar el rendimiento y el tamaño del archivo.
-   **Botón de Acción**:
    -   `Generar visualizador`: Inicia el proceso de generación del video.
-   **Feedback al Usuario**:
    -   **Barra de progreso**: Muestra el progreso en tiempo real de la codificación de FFmpeg.
    -   **Área de logs**: Informa sobre el estado del proceso y proporciona la ruta del archivo de salida al finalizar.

## 3. Integración en la Pestaña "Corte"

### 3.1. Propósito

Aplicar el efecto de visualizador de música directamente a los videos que se están procesando (cortando en segmentos o generando como videos verticales).

### 3.2. Componentes de la Interfaz

-   **Checkbox `Visualizador de música`**: Un interruptor para activar o desactivar la superposición del visualizador.
-   **Selector de Posición**: Un menú desplegable (`Arriba`, `Centro`, `Abajo`) que se activa cuando el checkbox está marcado. Determina la ubicación vertical del visualizador en el video final.

### 3.3. Comportamiento

-   Cuando la opción está activada, el visualizador se genera para cada segmento de video cortado.
-   El visualizador se adapta automáticamente a la resolución del video de salida (horizontal o vertical 9:16).
-   La posición seleccionada se respeta en el video final, con márgenes adecuados para no interferir con el contenido principal.
-   El visualizador se puede combinar con otros efectos, como la superposición de un fondo de imagen. El visualizador siempre se renderizará por encima del fondo y del video original.

## 4. Requisitos No Funcionales

-   **Rendimiento**: La generación del visualizador debe ser eficiente para no ralentizar excesivamente el flujo de trabajo de procesamiento de video. Se deben reutilizar los archivos de audio intermedios siempre que sea posible.
-   **Compatibilidad**: Los videos generados con el visualizador deben ser compatibles con los reproductores y plataformas de redes sociales más comunes.
-   **Usabilidad**: La interfaz debe ser intuitiva, permitiendo a los usuarios configurar y aplicar el efecto con mínimos pasos.
