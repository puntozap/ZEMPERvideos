import customtkinter as ctk


def create_tab(parent, context):
    log_state = context["log_state"]
    abrir_transcripciones = context["abrir_transcripciones"]
    eliminar_audios = context["eliminar_audios"]
    stop_control = context["stop_control"]

    parent.grid_columnconfigure(0, weight=2)
    parent.grid_columnconfigure(1, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    logs_card = ctk.CTkFrame(parent, corner_radius=12)
    logs_card.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    logs_card.grid_rowconfigure(1, weight=1)
    logs_card.grid_columnconfigure(0, weight=1)

    lbl_logs = ctk.CTkLabel(logs_card, text="Actividad", font=ctk.CTkFont(size=15, weight="bold"))
    lbl_logs.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

    txt_logs = ctk.CTkTextbox(logs_card, corner_radius=8)
    txt_logs.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
    txt_logs.configure(state="disabled")
    log_state["widget"] = txt_logs

    tools = ctk.CTkFrame(parent, corner_radius=12)
    tools.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
    tools.grid_columnconfigure(0, weight=1)

    lbl_tools = ctk.CTkLabel(tools, text="Herramientas", font=ctk.CTkFont(size=15, weight="bold"))
    lbl_tools.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

    btn_abrir = ctk.CTkButton(tools, text="Abrir Transcripciones", command=abrir_transcripciones, height=40)
    btn_abrir.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))

    btn_eliminar = ctk.CTkButton(
        tools,
        text="Eliminar Audios",
        command=eliminar_audios,
        fg_color="#b91c1c",
        hover_color="#991b1b",
        height=40,
    )
    btn_eliminar.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))

    btn_stop = ctk.CTkButton(
        tools,
        text="Detener procesos",
        command=lambda: stop_control.request_stop(context["log"]),
        fg_color="#b45309",
        hover_color="#92400e",
        height=40,
    )
    btn_stop.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 12))

    return {
        "txt_logs": txt_logs,
    }
