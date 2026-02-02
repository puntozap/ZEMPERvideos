import customtkinter as ctk
import tkinter as tk
import os
from ui.dialogs import seleccionar_imagen

BLEND_OPTIONS = [
    ("Normal", "normal"),
    ("Oscurecer", "darken"),
    ("Multiplicar", "multiply"),
    ("Aclarar", "lighten"),
    ("Pantalla", "screen"),
    ("Superposición", "overlay"),
]


def _blend_label_for_code(code: str) -> str:
    return next((label for label, value in BLEND_OPTIONS if value == code), BLEND_OPTIONS[0][0])

DEFAULTS = {
    "visualizador_exposicion": 0.0,
    "visualizador_contraste": 1.0,
    "visualizador_saturacion": 1.0,
    "visualizador_temperatura": 0.0,
    "visualizador_opacidad": 0.65,
    "visualizador_blend_mode": "lighten",
}


def _build_slider_block(parent, label_text, var, state_key, estado, min_value, max_value, steps, formatter, row):
    block = ctk.CTkFrame(parent, fg_color="transparent")
    block.grid_columnconfigure(0, weight=1)
    block.grid(row=row, column=0, sticky="ew", padx=14, pady=(0, 10))
    lbl = ctk.CTkLabel(block, text=label_text, font=ctk.CTkFont(size=13))
    lbl.grid(row=0, column=0, sticky="w")
    value_lbl = ctk.CTkLabel(block, text="", font=ctk.CTkFont(size=12))
    value_lbl.grid(row=0, column=1, sticky="e")

    def on_change(value):
        val = float(value)
        estado[state_key] = val
        value_lbl.configure(text=formatter(val))

    slider = ctk.CTkSlider(
        block,
        from_=min_value,
        to=max_value,
        number_of_steps=steps,
        variable=var,
        command=on_change,
    )
    slider.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
    on_change(var.get())
    return row + 1, on_change


def create_tab(parent, context):
    estado = context["estado"]
    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.grid(sticky="nsew", padx=0, pady=0)
    container.grid_columnconfigure((0, 1), weight=1)
    container.grid_rowconfigure(1, weight=1)

    header = ctk.CTkLabel(container, text="Ajustes del visualizador", font=ctk.CTkFont(size=15, weight="bold"))
    header.grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 8))

    scroll_area = ctk.CTkScrollableFrame(container, corner_radius=0, fg_color="transparent")
    scroll_area.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=0, pady=0)
    scroll_area.grid_columnconfigure(0, weight=1)
    scroll_area.grid_rowconfigure(0, weight=1)

    content_frame = ctk.CTkFrame(scroll_area, corner_radius=14, fg_color="#1c1f26")
    content_frame.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
    content_frame.grid_columnconfigure(0, weight=1)
    content_frame.grid_columnconfigure(1, weight=1)
    content_frame.grid_rowconfigure(0, weight=1)
    content_frame.grid_rowconfigure(1, weight=0)

    left_panel = ctk.CTkFrame(content_frame, fg_color="transparent")
    left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 7), pady=0)
    left_panel.grid_columnconfigure(0, weight=1)
    left_panel.grid_rowconfigure(0, weight=1)
    left_panel.grid_rowconfigure(1, weight=0)
    left_panel.grid_rowconfigure(2, weight=0)

    slider_section = ctk.CTkScrollableFrame(left_panel, corner_radius=8, fg_color="#22252d")
    slider_section.grid(row=0, column=0, sticky="nsew")
    slider_section.grid_columnconfigure(0, weight=1)
    slider_section.grid_rowconfigure(0, weight=1)

    slider_row = 0
    exposicion_var = tk.DoubleVar(value=estado.get("visualizador_exposicion", DEFAULTS["visualizador_exposicion"]))
    slider_row, exposure_update = _build_slider_block(
        slider_section,
        "Exposición",
        exposicion_var,
        "visualizador_exposicion",
        estado,
        -0.5,
        0.5,
        20,
        lambda v: f"{v:+.2f}",
        slider_row,
    )
    contraste_var = tk.DoubleVar(value=estado.get("visualizador_contraste", DEFAULTS["visualizador_contraste"]))
    slider_row, contrast_update = _build_slider_block(
        slider_section,
        "Contraste",
        contraste_var,
        "visualizador_contraste",
        estado,
        0.5,
        1.5,
        20,
        lambda v: f"{v:.2f}x",
        slider_row,
    )
    saturacion_var = tk.DoubleVar(value=estado.get("visualizador_saturacion", DEFAULTS["visualizador_saturacion"]))
    slider_row, saturation_update = _build_slider_block(
        slider_section,
        "Saturación",
        saturacion_var,
        "visualizador_saturacion",
        estado,
        0.5,
        2.0,
        30,
        lambda v: f"{v:.2f}x",
        slider_row,
    )
    temperatura_var = tk.DoubleVar(value=estado.get("visualizador_temperatura", DEFAULTS["visualizador_temperatura"]))
    slider_row, temperature_update = _build_slider_block(
        slider_section,
        "Temperatura",
        temperatura_var,
        "visualizador_temperatura",
        estado,
        -0.5,
        0.5,
        20,
        lambda v: f"{v:+.2f}",
        slider_row,
    )
    opacidad_var = tk.DoubleVar(value=estado.get("visualizador_opacidad", DEFAULTS["visualizador_opacidad"]))
    slider_row, opacity_update = _build_slider_block(
        slider_section,
        "Transparencia",
        opacidad_var,
        "visualizador_opacidad",
        estado,
        0.2,
        1.0,
        16,
        lambda v: f"{int(v * 100)}%",
        slider_row,
    )

    blend_var = tk.StringVar()
    blend_var.set(_blend_label_for_code(estado.get("visualizador_blend_mode", DEFAULTS["visualizador_blend_mode"])))

    def on_blend_change(_=None):
        selection = blend_var.get()
        modo = next((code for label, code in BLEND_OPTIONS if label == selection), DEFAULTS["visualizador_blend_mode"])
        estado["visualizador_blend_mode"] = modo

    blend_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
    blend_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
    blend_frame.grid_columnconfigure(0, weight=1)
    blend_label = ctk.CTkLabel(blend_frame, text="Modo de combinación", font=ctk.CTkFont(size=13))
    blend_label.grid(row=0, column=0, sticky="w")
    blend_menu = ctk.CTkOptionMenu(
        blend_frame,
        values=[label for label, _ in BLEND_OPTIONS],
        variable=blend_var,
        command=on_blend_change,
    )
    blend_menu.grid(row=0, column=1, sticky="e")
    on_blend_change()

    def restablecer():
        exposicion_var.set(DEFAULTS["visualizador_exposicion"])
        exposure_update(exposicion_var.get())
        contraste_var.set(DEFAULTS["visualizador_contraste"])
        contrast_update(contraste_var.get())
        saturacion_var.set(DEFAULTS["visualizador_saturacion"])
        saturation_update(saturacion_var.get())
        temperatura_var.set(DEFAULTS["visualizador_temperatura"])
        temperature_update(temperatura_var.get())
        opacidad_var.set(DEFAULTS["visualizador_opacidad"])
        opacity_update(opacidad_var.get())
        blend_var.set(_blend_label_for_code(DEFAULTS["visualizador_blend_mode"]))
        on_blend_change()

    btn_reset = ctk.CTkButton(left_panel, text="Restablecer", command=restablecer)
    btn_reset.grid(row=2, column=0, sticky="ew", pady=(10, 0))

    right_panel = ctk.CTkFrame(content_frame, fg_color="transparent")
    right_panel.grid(row=0, column=1, sticky="nsew", padx=(7, 0), pady=0)
    right_panel.grid_columnconfigure(0, weight=1)
    right_panel.grid_rowconfigure(0, weight=0)
    right_panel.grid_rowconfigure(1, weight=0)
    right_panel.grid_rowconfigure(2, weight=1)

    overlay_section = ctk.CTkScrollableFrame(right_panel, corner_radius=8, fg_color="#22252d")
    overlay_section.grid_columnconfigure(0, weight=1)
    overlay_section.grid(row=0, column=0, sticky="nsew")

    overlay_label = ctk.CTkLabel(overlay_section, text="Imagen temporal", font=ctk.CTkFont(size=13))
    overlay_label.grid(row=0, column=0, sticky="w", pady=(0, 4))

    overlay_path_var = tk.StringVar(value=estado.get("visualizador_overlay_image") or "")
    lbl_path = ctk.CTkLabel(overlay_section, textvariable=overlay_path_var, font=ctk.CTkFont(size=11))
    lbl_path.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    def seleccionar_overlay():
        ruta = seleccionar_imagen()
        if ruta:
            estado["visualizador_overlay_image"] = os.path.abspath(ruta)
            overlay_path_var.set(os.path.abspath(ruta))

    btn_select_overlay = ctk.CTkButton(overlay_section, text="Seleccionar imagen", command=seleccionar_overlay)
    btn_select_overlay.grid(row=2, column=0, sticky="w", pady=(6, 0))

    start_var = tk.StringVar(value=str(estado.get("visualizador_overlay_start", 0.0)))
    duration_var = tk.StringVar(value=str(estado.get("visualizador_overlay_duration", 2.0)))

    def _estandarizar_float(value, default):
        try:
            return max(0.0, float(value))
        except Exception:
            return default

    def _sync_overlay_start(*_):
        estado["visualizador_overlay_start"] = _estandarizar_float(start_var.get(), 0.0)

    def _sync_overlay_duration(*_):
        estado["visualizador_overlay_duration"] = max(0.1, _estandarizar_float(duration_var.get(), 2.0))

    def _crear_entry(label, var, row_index):
        frame = ctk.CTkFrame(overlay_section, fg_color="transparent")
        frame.grid_columnconfigure(1, weight=1)
        frame.grid(row=row_index, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        lbl = ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=12))
        lbl.grid(row=0, column=0, sticky="w")
        entry = ctk.CTkEntry(frame, width=100, textvariable=var)
        entry.grid(row=0, column=1, sticky="e")
        return entry

    entry_start = _crear_entry("Inicio (s)", start_var, 3)
    entry_duration = _crear_entry("Duración (s)", duration_var, 4)
    start_var.trace_add("write", _sync_overlay_start)
    duration_var.trace_add("write", _sync_overlay_duration)

    def restablecer_overlay():
        estado["visualizador_overlay_image"] = None
        estado["visualizador_overlay_start"] = 0.0
        estado["visualizador_overlay_duration"] = 2.0
        overlay_path_var.set("")
        start_var.set("0.0")
        duration_var.set("2.0")

    btn_reset_overlay = ctk.CTkButton(right_panel, text="Restablecer imagen", command=restablecer_overlay)
    btn_reset_overlay.grid(row=1, column=0, sticky="ew", pady=(10, 0))

    preview_frame = ctk.CTkFrame(right_panel, fg_color="#1c1f26", corner_radius=10)
    preview_frame.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
    preview_frame.grid_rowconfigure(0, weight=1)
    preview_frame.grid_columnconfigure(0, weight=1)
    preview_label = ctk.CTkLabel(
        preview_frame,
        text="Vista previa del visualizador\n\nEl video y la onda se mostrarán aquí cuando se active la función.",
        font=ctk.CTkFont(size=12),
        justify="center",
        text_color="#8f93a1",
    )
    preview_label.grid(row=0, column=0, pady=20, padx=12)
