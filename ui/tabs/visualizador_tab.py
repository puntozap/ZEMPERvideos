import os
import threading
import customtkinter as ctk
import tkinter as tk
from tkinter import colorchooser

from core.utils import generar_visualizador_audio, output_base_dir, nombre_base_principal
from ui.shared import helpers

def create_tab(parent, context):
    log = context["log"]
    alerta_busy = context["alerta_busy"]
    stop_control = context["stop_control"]
    beep_fin = context["beep_fin"]
    renombrar_si_largo = context["renombrar_si_largo"]

    # Configuración del grid del padre para asegurar que el contenedor se expanda
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
    
    # Layout: 
    # Columna 0: Panel de controles (Izquierda) - Ancho fijo
    # Columna 1: Panel principal (Derecha) - Se expande
    container.grid_columnconfigure(0, weight=0) 
    container.grid_columnconfigure(1, weight=1)
    container.grid_rowconfigure(0, weight=1)

    # --- Panel Izquierdo (Controles) ---
    left_panel = ctk.CTkFrame(container, fg_color="transparent", width=320)
    left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    left_panel.grid_rowconfigure(0, weight=1)
    left_panel.grid_columnconfigure(0, weight=1)
    left_panel.grid_propagate(False) # Mantiene el ancho fijo

    controls_scroll = ctk.CTkScrollableFrame(left_panel, corner_radius=12)
    controls_scroll.grid(row=0, column=0, sticky="nsew")
    controls_scroll.grid_columnconfigure(0, weight=1)

    # --- Contenido del Panel Izquierdo ---
    lbl_title = ctk.CTkLabel(
        controls_scroll, 
        text="Visualizador de Música", 
        font=ctk.CTkFont(size=18, weight="bold")
    )
    lbl_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_desc = ctk.CTkLabel(
        controls_scroll,
        text="Genera un video con ondas reactivas al audio.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2"
    )
    lbl_desc.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    # Selector de archivo
    file_card = ctk.CTkFrame(controls_scroll, fg_color="transparent")
    file_card.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
    file_card.grid_columnconfigure(0, weight=1)

    state = {"path": None}
    
    lbl_file_info = ctk.CTkLabel(file_card, text="(sin archivo)", font=ctk.CTkFont(size=12))
    lbl_file_info.grid(row=0, column=0, sticky="w", pady=(0, 4))

    def on_select_file():
        from ui.dialogs import seleccionar_archivo
        path = seleccionar_archivo("Seleccionar Audio/Video", [("Media", "*.mp3;*.wav;*.mp4;*.mkv;*.mov;*.m4a")])
        if path:
            path = renombrar_si_largo(path)
            if path:
                state["path"] = path
                lbl_file_info.configure(text=os.path.basename(path))
                log(f"Archivo seleccionado: {path}")

    btn_file = ctk.CTkButton(file_card, text="Seleccionar Archivo", command=on_select_file)
    btn_file.grid(row=1, column=0, sticky="ew")

    # Configuración
    conf_card = ctk.CTkFrame(controls_scroll, fg_color="transparent")
    conf_card.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
    conf_card.grid_columnconfigure(1, weight=1)

    # Estilo
    lbl_style = ctk.CTkLabel(conf_card, text="Estilo", font=ctk.CTkFont(size=12))
    lbl_style.grid(row=0, column=0, sticky="w", pady=(0, 4))
    style_var = ctk.StringVar(value="showwaves")
    opt_style = ctk.CTkOptionMenu(conf_card, values=["showwaves", "showspectrum", "avectorscope"], variable=style_var)
    opt_style.grid(row=0, column=1, sticky="e", pady=(0, 4))

    # Resolución
    lbl_res = ctk.CTkLabel(conf_card, text="Resolución", font=ctk.CTkFont(size=12))
    lbl_res.grid(row=1, column=0, sticky="w", pady=(4, 4))
    res_var = ctk.StringVar(value="1920x1080")
    opt_res = ctk.CTkOptionMenu(conf_card, values=["1920x1080", "1280x720", "1080x1920", "720x1280"], variable=res_var)
    opt_res.grid(row=1, column=1, sticky="e", pady=(4, 4))

    # Color
    lbl_color = ctk.CTkLabel(conf_card, text="Color", font=ctk.CTkFont(size=12))
    lbl_color.grid(row=2, column=0, sticky="w", pady=(4, 4))
    color_var = ctk.StringVar(value="#FFFFFF")
    
    color_frame = ctk.CTkFrame(conf_card, fg_color="transparent")
    color_frame.grid(row=2, column=1, sticky="e", pady=(4, 4))
    
    entry_color = ctk.CTkEntry(color_frame, width=80, textvariable=color_var)
    entry_color.pack(side="left", padx=(0, 4))
    
    def pick_color():
        c = colorchooser.askcolor(color=color_var.get())
        if c and c[1]:
            color_var.set(c[1])

    btn_pick = ctk.CTkButton(color_frame, text="🎨", width=30, command=pick_color)
    btn_pick.pack(side="left")

    # Botón Generar
    def iniciar_generacion():
        if not state["path"]:
            log("Selecciona un archivo primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        
        stop_control.clear_stop()
        stop_control.set_busy(True)
        
        try:
            w_str, h_str = res_var.get().split("x")
            width = int(w_str)
            height = int(h_str)
        except:
            width, height = 1920, 1080

        estilo = style_var.get()
        color = color_var.get()
        
        base_dir = output_base_dir(state["path"])
        vis_dir = os.path.join(base_dir, "visualizador")
        os.makedirs(vis_dir, exist_ok=True)
        base_name = nombre_base_principal(state["path"])
        output_path = os.path.join(vis_dir, f"{base_name}_visualizador.mp4")

        def run():
            try:
                log(f"Generando visualizador: {output_path}")
                generar_visualizador_audio(
                    audio_path=state["path"],
                    output_path=output_path,
                    width=width,
                    height=height,
                    estilo=estilo,
                    color=color,
                    log_fn=log
                )
                log("✅ Visualizador generado.")
                beep_fin()
            except Exception as e:
                log(f"❌ Error: {e}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run, daemon=True).start()

    btn_run = ctk.CTkButton(controls_scroll, text="Generar Visualizador", command=iniciar_generacion, height=40)
    btn_run.grid(row=4, column=0, sticky="ew", padx=16, pady=(20, 20))

    # --- Panel Derecho (Logs / Principal) ---
    # Este panel se expande (weight=1 en columna 1 del container)
    log_card, _log_widget, log_local = helpers.create_log_panel(
        container,
        title="Actividad",
        height=0, # Altura 0 para que el layout maneje el tamaño
        mirror_fn=context.get("log_global"),
    )
    log_card.grid(row=0, column=1, sticky="nsew", padx=(0, 0))
    
    def log_seccion(titulo):
        log_local("")
        log_local("========================================")
        log_local(f"=== {titulo}")
        log_local("========================================")

    log = log_local

    return {}