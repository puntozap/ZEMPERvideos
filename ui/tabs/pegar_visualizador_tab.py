import os
import threading
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from core.utils import (
    nombre_base_principal,
    output_base_dir,
    overlay_visualizador,
)
from ui.dialogs import seleccionar_video


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


def _clamp_color(value: float) -> int:
    return max(0, min(255, int(value)))


def _overlay_color(exposure, contrast, saturation, temperature, blend_mode):
    contrast_adj = (contrast - 1.0) * 50
    exposure_adj = exposure * 120
    saturation_adj = (saturation - 1.0) * 80
    temperature_adj = temperature * 60
    base_red = 150 + exposure_adj + saturation_adj
    base_green = 120 + saturation_adj - temperature_adj
    base_blue = 210 - temperature_adj + contrast_adj
    if blend_mode == "darken":
        modifier = 0.75
    elif blend_mode == "multiply":
        modifier = 0.65
    elif blend_mode == "screen":
        modifier = 1.2
    elif blend_mode == "overlay":
        modifier = 1.1
    elif blend_mode == "lighten":
        modifier = 1.05
    else:
        modifier = 1.0
    return (
        _clamp_color(base_red * modifier + contrast_adj),
        _clamp_color(base_green * modifier + contrast_adj),
        _clamp_color(base_blue * modifier + contrast_adj),
    )


class VisualOverlayPreview:
    def __init__(self, parent):
        self.card = ctk.CTkFrame(parent, fg_color="#1c1f26", corner_radius=10)
        self.card.grid(row=0, column=0, sticky="nsew")
        self.card.grid_columnconfigure(0, weight=1)
        self.card.grid_rowconfigure(1, weight=1)

        lbl = ctk.CTkLabel(
            self.card,
            text="Vista previa simulada",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        lbl.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))

        container = tk.Frame(self.card, bg="#10131a")
        container.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        container.grid_propagate(False)
        container.configure(height=220)

        self.label = tk.Label(container, bg="#0b0d14", text="")
        self.label.pack(fill="both", expand=True)
        self._photo = None

    def render(self, exposure, contrast, saturation, temperature, opacity, blend_mode):
        width = 320
        height = 200
        base = Image.new("RGBA", (width, height), "#0a0d18")
        overlay_color = _overlay_color(exposure, contrast, saturation, temperature, blend_mode)
        overlay = Image.new(
            "RGBA",
            (width, height),
            overlay_color + (_clamp_color(opacity * 255),),
        )
        combined = Image.alpha_composite(base, overlay)
        draw = ImageDraw.Draw(combined)
        for offset in range(6):
            x = 30 + offset * 40
            y0 = height - 40 - offset * 4
            y1 = height - 20 - offset * 3
            draw.line(
                [(x, y0), (x, y1)],
                fill=(255, 255, 255, 90),
                width=4,
            )
        draw.rectangle([28, 30, width - 28, height - 60], outline=(255, 255, 255, 40), width=2)
        draw.text((width / 2, 36), f"Modo: {blend_mode.title()}", fill="#d3d6ff", anchor="ma")
        self._photo = ImageTk.PhotoImage(combined)
        self.label.configure(image=self._photo, text="")


def _build_slider_block(parent, label_text, var, state_key, estado, min_value, max_value, steps, formatter, row, post_change=None):
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
        if post_change:
            post_change()

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
    log = context["log"]
    stop_control = context["stop_control"]
    alerta_busy = context["alerta_busy"]
    beep_fin = context.get("beep_fin")

    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)
    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
    container.grid_columnconfigure(0, weight=0)
    container.grid_columnconfigure(1, weight=1)
    container.grid_rowconfigure(0, weight=1)

    left_panel = ctk.CTkFrame(container, fg_color="transparent", width=360)
    left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    left_panel.grid_rowconfigure(0, weight=1)
    left_panel.grid_columnconfigure(0, weight=1)
    left_panel.grid_propagate(False)

    controls_scroll = ctk.CTkScrollableFrame(left_panel, corner_radius=12, fg_color="#1c1f26")
    controls_scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
    controls_scroll.grid_columnconfigure(0, weight=1)

    lbl_title = ctk.CTkLabel(
        controls_scroll,
        text="Pegar visualizador",
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    lbl_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_desc = ctk.CTkLabel(
        controls_scroll,
        text="Selecciona el video base y el visualizador ya generado para superponerlos.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2",
    )
    lbl_desc.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    file_card = ctk.CTkFrame(controls_scroll, fg_color="transparent")
    file_card.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
    file_card.grid_columnconfigure(0, weight=1)

    base_path_var = tk.StringVar(value=os.path.basename(estado.get("pegar_visualizador_base_video") or "") or "Sin video base")
    overlay_path_var = tk.StringVar(value=os.path.basename(estado.get("pegar_visualizador_overlay_video") or "") or "Sin visualizador")

    lbl_base = ctk.CTkLabel(file_card, textvariable=base_path_var, font=ctk.CTkFont(size=12))
    lbl_base.grid(row=0, column=0, sticky="w")

    def _seleccionar_archivo(key, display_var, label_text):
        ruta = seleccionar_video()
        if not ruta:
            return
        ruta = os.path.abspath(ruta)
        estado[key] = ruta
        display_var.set(os.path.basename(ruta))
        log(f"{label_text}: {ruta}")

    btn_base = ctk.CTkButton(file_card, text="Seleccionar video base", command=lambda: _seleccionar_archivo("pegar_visualizador_base_video", base_path_var, "Video base"))
    btn_base.grid(row=1, column=0, sticky="ew", pady=(8, 4))

    lbl_overlay = ctk.CTkLabel(file_card, textvariable=overlay_path_var, font=ctk.CTkFont(size=12))
    lbl_overlay.grid(row=2, column=0, sticky="w", pady=(8, 0))

    btn_overlay = ctk.CTkButton(file_card, text="Seleccionar visualizador", command=lambda: _seleccionar_archivo("pegar_visualizador_overlay_video", overlay_path_var, "Visualizador"))
    btn_overlay.grid(row=3, column=0, sticky="ew", pady=(8, 4))

    def restablecer_rutas():
        estado["pegar_visualizador_base_video"] = None
        estado["pegar_visualizador_overlay_video"] = None
        base_path_var.set("Sin video base")
        overlay_path_var.set("Sin visualizador")

    btn_reset_paths = ctk.CTkButton(file_card, text="Restablecer rutas", command=restablecer_rutas, fg_color="#272b35")
    btn_reset_paths.grid(row=4, column=0, sticky="ew", pady=(4, 8))

    slider_section = ctk.CTkScrollableFrame(controls_scroll, corner_radius=8, fg_color="#22252d")
    slider_section.grid(row=3, column=0, sticky="nsew", padx=0, pady=(0, 12))
    slider_section.grid_columnconfigure(0, weight=1)

    slider_row = 0
    preview = None

    def refresh_preview():
        if not preview:
            return
        preview.render(
            estado.get("visualizador_exposicion", 0.0),
            estado.get("visualizador_contraste", 1.0),
            estado.get("visualizador_saturacion", 1.0),
            estado.get("visualizador_temperatura", 0.0),
            estado.get("visualizador_opacidad", 0.65),
            estado.get("visualizador_blend_mode", "lighten"),
        )

    exposicion_var = tk.DoubleVar(value=estado.get("visualizador_exposicion", 0.0))
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
        post_change=refresh_preview,
    )

    contraste_var = tk.DoubleVar(value=estado.get("visualizador_contraste", 1.0))
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
        post_change=refresh_preview,
    )

    saturacion_var = tk.DoubleVar(value=estado.get("visualizador_saturacion", 1.0))
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
        post_change=refresh_preview,
    )

    temperatura_var = tk.DoubleVar(value=estado.get("visualizador_temperatura", 0.0))
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
        post_change=refresh_preview,
    )

    opacidad_var = tk.DoubleVar(value=estado.get("visualizador_opacidad", 0.65))
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
        post_change=refresh_preview,
    )

    blend_var = tk.StringVar()
    blend_var.set(_blend_label_for_code(estado.get("visualizador_blend_mode", "lighten")))

    def on_blend_change(_=None):
        selection = blend_var.get()
        modo = next((code for label, code in BLEND_OPTIONS if label == selection), "lighten")
        estado["visualizador_blend_mode"] = modo
        refresh_preview()

    blend_frame = ctk.CTkFrame(slider_section, fg_color="transparent")
    blend_frame.grid(row=slider_row, column=0, sticky="ew", padx=(12, 12), pady=(4, 0))
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

    def restablecer_sliders():
        exposicion_var.set(0.0)
        exposure_update(exposicion_var.get())
        contraste_var.set(1.0)
        contrast_update(contraste_var.get())
        saturacion_var.set(1.0)
        saturation_update(saturacion_var.get())
        temperatura_var.set(0.0)
        temperature_update(temperatura_var.get())
        opacidad_var.set(0.65)
        opacity_update(opacidad_var.get())
        blend_var.set(_blend_label_for_code("lighten"))
        on_blend_change()

    btn_reset_sliders = ctk.CTkButton(controls_scroll, text="Restablecer sliders", command=restablecer_sliders, fg_color="#272b35")
    btn_reset_sliders.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 10))

    right_panel = ctk.CTkFrame(container, fg_color="transparent")
    right_panel.grid(row=0, column=1, sticky="nsew")
    right_panel.grid_columnconfigure(0, weight=1)
    right_panel.grid_rowconfigure(0, weight=0)
    right_panel.grid_rowconfigure(1, weight=1)
    right_panel.grid_rowconfigure(2, weight=0)

    info_lbl = ctk.CTkLabel(
        right_panel,
        text="Se muestra un ejemplo sin afectar los archivos originales; modifica los sliders para ver el resultado.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2",
        wraplength=340,
        justify="left",
    )
    info_lbl.grid(row=0, column=0, sticky="w", padx=12, pady=(0, 12))

    preview_container = ctk.CTkFrame(right_panel, fg_color="transparent")
    preview_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
    preview_container.grid_rowconfigure(0, weight=1)
    preview_container.grid_columnconfigure(0, weight=1)

    preview = VisualOverlayPreview(preview_container)
    refresh_preview()

    btn_apply = ctk.CTkButton(
        right_panel,
        text="Aplicar overlay",
        command=lambda: _aplicar_overlay(log, estado, stop_control, alerta_busy, beep_fin),
        height=42,
    )
    btn_apply.grid(row=2, column=0, sticky="ew", padx=12, pady=(10, 0))

    return {}


def _aplicar_overlay(log, estado, stop_control, alerta_busy, beep_fin):
    base_video = estado.get("pegar_visualizador_base_video")
    overlay_video = estado.get("pegar_visualizador_overlay_video")
    if not base_video or not overlay_video:
        log("Selecciona el video base y el visualizador antes de aplicar.")
        return
    if stop_control.is_busy():
        alerta_busy()
        return
    stop_control.clear_stop()
    stop_control.set_busy(True)

    def run():
        try:
            base_dir = output_base_dir(base_video)
            vis_dir = os.path.join(base_dir, "visualizador_pegado")
            os.makedirs(vis_dir, exist_ok=True)
            base_name = nombre_base_principal(base_video)
            output_path = os.path.join(vis_dir, f"{base_name}_pegado.mp4")
            overlay_visualizador(
                video_path=base_video,
                visual_path=overlay_video,
                output_path=output_path,
                posicion=estado.get("posicion_visualizador", "centro"),
                margen=int(estado.get("visualizador_margen", 0)),
                opacidad=estado.get("visualizador_opacidad", 0.65),
                modo_combinacion=estado.get("visualizador_blend_mode", "lighten"),
                log_fn=log,
            )
            log(f"✔ Visualizador pegado guardado en {output_path}")
            if beep_fin:
                beep_fin()
        except Exception as exc:
            log(f"✘ No se pudo pegar: {exc}")
        finally:
            stop_control.set_busy(False)

    threading.Thread(target=run, daemon=True).start()
