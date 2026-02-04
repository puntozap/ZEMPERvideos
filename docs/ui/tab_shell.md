# Pantallas base con scroll

Esta guía explica cómo se ha reestructurado el flujo de creación de pestañas para que cada pantalla (tab) comparta un shell genérico que ya incluye scroll y un layout consistente.

## Por qué existe este cambio

- La ventana principal (`ui/main_window.py`) ya monta todas las pestañas mediante funciones `create_tab(parent, context)`. Cada módulo actúa como un componente autónomo, pero hasta ahora muchos definían su propio marco interior sin scroll, lo que dejaba espacios vacíos cuando el contenido excedía la altura del tab (especialmente en pestañas como Drive).
- Para evitar repetir la misma configuración y garantizar que todas las pestañas puedan desplazarse cuando su contenido crezca, se agregó `ui/shared/tab_shell.py`, que entrega un `container` y un `CTkScrollableFrame` listo para usar. Así, cada nueva pantalla puede aprovechar automáticamente el scroll sin pensar en detalles de layout.

## Cómo usar la base nueva

1. Dentro de tu módulo de pestaña, importa el helper:

   ```python
   from ui.shared.tab_shell import create_tab_shell
   ```

2. En `create_tab(parent, context)` configura el padre como siempre (`parent.grid_columnconfigure(0, weight=1)` y `parent.grid_rowconfigure(0, weight=1)`) y luego llama al helper:

   ```python
   container, scroll_body = create_tab_shell(parent, padx=16, pady=16)
   ```

   - `container` es el frame que ya está pegado al tab principal y sirve para colocar secciones anchas (logs, paneles laterales, etc.).
   - `scroll_body` es el `CTkScrollableFrame` donde añadiremos el contenido principal. Dentro del scroll puedes añadir un `ctk.CTkFrame` con `corner_radius` para agrupar widgets, o colocar varias tarjetas directamente.

3. Si necesitas paneles extra (por ejemplo el log de actividad que se coloca al lado derecho en la pestaña Drive), puedes seguir usando `container` y agregar filas/columnas adicionales. La idea es que el `scroll_body` ocupe la columna principal (0) y cualquier panel lateral pueda ir en columna 1 o superior.

4. Dentro del `scroll_body` construye tu contenido habitual (etiquetas, botones, entradas). Asegúrate de que el scroll se quede con `grid_columnconfigure(0, weight=1)` cuando lo necesites para que se expanda correctamente.

5. Si dispones de un estado compartido (`context`), conserva el patrón actual (`estado`, `rango`, `log`, etc.) para que las pestañas puedan comunicarse con la lógica principal (`core`).

6. Cuando la pantalla deba ser registrada en la ventana principal, llama a tu módulo desde `ui/main_window.py`, pasando el frame de la pestaña y el contexto necesario. Todos los tabs nuevos deberían seguir esta firma para mantener el comportamiento común.

## Ejemplo esquemático

```python
def create_tab(parent, context):
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    container, scroll_body = create_tab_shell(parent, padx=12, pady=12)
    scroll_body.grid_columnconfigure(0, weight=1)

    body = ctk.CTkFrame(scroll_body, corner_radius=12)
    body.grid(row=0, column=0, sticky="nsew")
    body.grid_columnconfigure(0, weight=1)

    # aquí agregas tus widgets dentro de `body`
```

## ¿Qué sigue?

- Si la pestaña necesita dividirse en paneles (logueo, barra lateral, etc.), usa `container` para posicionarlos y reserva la columna principal para el `scroll_body`.
- Documenta en el módulo qué dependencias del `context` se esperan (estado, funciones de log, controles).
- Cuando hagas refactors, conserva el helper para que el scroll quede siempre garantizado.
