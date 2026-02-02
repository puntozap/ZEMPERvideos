import os
import threading
import customtkinter as ctk
import tkinter as tk
from ui.dialogs import seleccionar_video


def _parse_float(value, fallback=0.0):
    try:
        text = (value or "").strip().replace(",", ".")
        return max(0.0, float(text))
    except Exception:
        return fallback


def create_tab(parent, context):
    estado = context["estado"]
    log = context["log"]
    log_seccion = context["log_seccion"]
    stop_control = context["stop_control"]
    alerta_busy = context["alerta_busy"]
    generar_visualizador_fn = context["generar_visualizador_fn"]

    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
    container.grid_columnconfigure(0, weight=1)
    container.grid_rowconfigure(0, weight=1)

    scroll = ctk.CTkScrollableFrame(container, corner_radius=12, fg_color="#1c1f26")
    scroll.grid(row=0, column=0, sticky="nsew")
    scroll.grid_columnconfigure(0, weight=1)
    scroll.grid_rowconfigure(0, weight=1)

    info_frame = ctk.CTkFrame(scroll, fg_color="#22252d")
    info_frame.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
    info_frame.grid_columnconfigure(1, weight=1)

    header = ctk.CTkLabel(
        info_frame,
        text="Cortar visualizador (solo onda sonora)",
        font=ctk.CTkFont(size=16, weight="bold"),
    )
    header.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

    path_var = tk.StringVar(value=estado.get("path") or "Ninguno")

    def seleccionar_ruta():
        ruta = seleccionar_video()
        if ruta:
            ruta = os.path.abspath(ruta)
            estado["path"] = ruta
            path_var.set(ruta)
            log(f"Video seleccionado para visualizador: {ruta}")

    btn_select = ctk.CTkButton(
        info_frame,
        text="Seleccionar video",
        command=seleccionar_ruta,
        width=160,
    )
    btn_select.grid(row=1, column=0, sticky="w", pady=(0, 4))

    lbl_path = ctk.CTkLabel(info_frame, textvariable=path_var, text_color="#9aa4b2")
    lbl_path.grid(row=2, column=0, columnspan=2, sticky="w")

    controls_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
    controls_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
    controls_frame.grid_columnconfigure(1, weight=1)

    start_var = tk.StringVar(value="0.0")
    duration_var = tk.StringVar(value="0.0")
    fps_var = tk.StringVar(value="30")

    def _crear_entry(label_text, var, row_index, tooltip=None):
        lbl = ctk.CTkLabel(controls_frame, text=label_text, font=ctk.CTkFont(size=12))
        lbl.grid(row=row_index, column=0, sticky="w")
        entry = ctk.CTkEntry(controls_frame, width=120, textvariable=var)
        entry.grid(row=row_index, column=1, sticky="e", pady=2)
        return entry

    _crear_entry("Inicio (s)", start_var, 0)
    _crear_entry("Duración (s, 0=todo)", duration_var, 1)
    _crear_entry("FPS", fps_var, 2)

    status_var = tk.StringVar(value="El visualizador se generará en output/.../visualizador/")

    status_label = ctk.CTkLabel(info_frame, textvariable=status_var, font=ctk.CTkFont(size=12), text_color="#8f93a1")
    status_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def _set_status(text: str):
        info_frame.after(0, lambda: status_var.set(text))

    def iniciar_visualizador():
        path = estado.get("path")
        if not path:
            log("Selecciona un video para generar el visualizador.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        inicio = _parse_float(start_var.get(), 0.0)
        duracion = _parse_float(duration_var.get(), 0.0)
        fps = max(12, min(60, int(_parse_float(fps_var.get(), 30))))
        estado["visualizador_color"] = estado.get("visualizador_color", "#FFFFFF")
        estado["visualizador_margen"] = estado.get("visualizador_margen", 0)
        stop_control.set_busy(True)
        log_seccion("Cortar visualizador")
        _set_status("Generando visualizador...")

        def worker():
            try:
                salida = generar_visualizador_fn(
                    path,
                    inicio_sec=inicio,
                    duracion_sec=(duracion if duracion > 0 else None),
                    estilo="showwaves",
                    color=estado.get("visualizador_color", "#FFFFFF"),
                    margen_horizontal=int(estado.get("visualizador_margen", 0)),
                    exposicion=estado.get("visualizador_exposicion", 0.0),
                    contraste=estado.get("visualizador_contraste", 1.0),
                    saturacion=estado.get("visualizador_saturacion", 1.0),
                    temperatura=estado.get("visualizador_temperatura", 0.0),
                    fps=fps,
                    logs=log,
                    progress_callback=lambda done, total: _set_status(f"Segmento {done}/{total} generado..."),
                )
                log(f"Visualizador generado: {salida}")
                _set_status(f"Visualizador listo: {os.path.basename(salida)}")
            except Exception as exc:
                log(f"Error visualizador: {exc}")
                _set_status(f"Error: {exc}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    btn_generate = ctk.CTkButton(
        info_frame,
        text="Generar visualizador",
        command=iniciar_visualizador,
        fg_color="#2875ff",
        hover_color="#1f5cd1",
    )
    btn_generate.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(14, 0))
