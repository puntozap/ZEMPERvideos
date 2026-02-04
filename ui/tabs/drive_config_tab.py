import threading
import tkinter as tk

import customtkinter as ctk

from core.drive_config import (
    get_oauth_client_secret,
    get_service_account_json,
    load_drive_settings,
    run_oauth_flow,
    set_drive_folder_id,
    set_oauth_client_secret,
    set_service_account_json,
    validate_service_account,
)
from ui.dialogs import mostrar_error, mostrar_info, seleccionar_archivo
from ui.shared import helpers
from ui.shared.tab_shell import create_tab_shell


def create_tab(parent, context):
    log_global = context.get("log_global")
    stop_control = context.get("stop_control")
    drive_state = context.get("drive_state", {})
    drive_folder_var = context.get("drive_folder_var")
    if drive_folder_var is None:
        drive_folder_var = tk.StringVar(value=drive_state.get("folder_id", ""))
    drive_state["folder_id"] = drive_folder_var.get().strip()
    drive_config = load_drive_settings()
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    container, scroll_body = create_tab_shell(parent, padx=16, pady=16)
    container.grid_columnconfigure(0, weight=1)
    container.grid_columnconfigure(1, weight=0)

    log_card, _, log_fn = helpers.create_log_panel(
        container,
        title="Actividad Drive",
        height=180,
        mirror_fn=log_global,
    )
    log_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

    body = ctk.CTkFrame(scroll_body, corner_radius=12)
    body.grid(row=0, column=0, sticky="nsew")
    body.grid_columnconfigure(0, weight=1)

    lbl_title = ctk.CTkLabel(
        body,
        text="Google Drive",
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    lbl_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_info = ctk.CTkLabel(
        body,
        text="Configura Drive con cuenta de servicio o OAuth para subir archivos.",
        wraplength=360,
        text_color="#9aa4b2",
    )
    lbl_info.grid(row=1, column=0, sticky="w", padx=16)

    frame = ctk.CTkFrame(body, corner_radius=8)
    frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(12, 0))
    frame.grid_columnconfigure(0, weight=1)

    service_path = (
        drive_state.get("service_json")
        or drive_config.get("service_json")
        or get_service_account_json()
        or ""
    )
    drive_state["service_json"] = service_path
    status_text = drive_state.get("status") or "Sin configuración."
    if service_path and status_text in {"Sin configuración.", "No configurado"}:
        status_text = "Drive configurado correctamente."
    status_var = tk.StringVar(value=status_text)
    lbl_status = ctk.CTkLabel(frame, textvariable=status_var, text_color="#d7d8de")
    lbl_status.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))

    path_var = tk.StringVar(value=service_path)
    entry_path = ctk.CTkEntry(frame, textvariable=path_var, state="readonly")
    entry_path.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

    def _show_service_instructions():
        mostrar_info(
            "1. Crea un proyecto en Google Cloud y habilita Drive API.\n"
            "2. Crea una cuenta de servicio con acceso editor y descarga el JSON.\n"
            "3. Comparte una carpeta con el service account si usas ID opcional."
        )

    def _select_service_json():
        try:
            file_path = seleccionar_archivo("Seleccionar JSON de servicio", [("JSON", "*.json")])
            if not file_path:
                return
            normalized = set_service_account_json(file_path)
            validate_service_account(normalized)
            path_var.set(normalized)
            status_var.set("Drive configurado correctamente.")
            drive_state["service_json"] = normalized
            drive_state["status"] = "Configurado"
            mostrar_info("Cuenta de servicio cargada y validada.")
        except Exception as exc:
            status_var.set("Error al validar el JSON.")
            mostrar_error(str(exc))

    btn_select = ctk.CTkButton(frame, text="Seleccionar JSON de Drive", command=_select_service_json)
    btn_select.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

    btn_instructions = ctk.CTkButton(
        frame,
        text="¿Cómo configurar?",
        fg_color="#2a70d9",
        command=_show_service_instructions,
    )
    btn_instructions.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 12))

    oauth_frame = ctk.CTkFrame(body, corner_radius=8)
    oauth_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(12, 0))
    oauth_frame.grid_columnconfigure(0, weight=1)

    oauth_path = (
        drive_state.get("oauth_client_secret")
        or drive_config.get("oauth_client_secret")
        or get_oauth_client_secret()
        or ""
    )
    drive_state["oauth_client_secret"] = oauth_path
    oauth_status_text = drive_state.get("oauth_status") or "OAuth no conectado"
    if oauth_path and oauth_status_text == "OAuth no conectado":
        oauth_status_text = "OAuth listo. Presiona conectar."
    oauth_status_var = tk.StringVar(value=oauth_status_text)
    oauth_label = ctk.CTkLabel(oauth_frame, textvariable=oauth_status_var, text_color="#d7d8de")
    oauth_label.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))

    oauth_path_var = tk.StringVar(value=oauth_path)
    oauth_entry = ctk.CTkEntry(oauth_frame, textvariable=oauth_path_var, state="readonly")
    oauth_entry.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

    def _select_oauth_file():
        try:
            file_path = seleccionar_archivo("Seleccionar cliente OAuth", [("JSON", "*.json")])
            if not file_path:
                return
            normalized = set_oauth_client_secret(file_path)
            oauth_path_var.set(normalized)
            drive_state["oauth_client_secret"] = normalized
            oauth_status_var.set("Cliente OAuth listo. Presiona conectar.")
        except Exception as exc:
            oauth_status_var.set("Error al cargar el client secret.")
            mostrar_error(str(exc))

    def _run_oauth_flow():
        def _worker():
            try:
                stop_control.set_busy(True)
                run_oauth_flow(log_fn=log_fn)
                oauth_status_var.set("OAuth conectado correctamente.")
                drive_state["oauth_status"] = "Conectado"
                mostrar_info("Autorización completada.")
            except Exception as exc:
                oauth_status_var.set("Error en autenticación.")
                if log_fn:
                    log_fn(f"OAuth Drive falló: {exc}")
                mostrar_error(str(exc))
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=_worker, daemon=True).start()

    oauth_select = ctk.CTkButton(oauth_frame, text="Seleccionar cliente OAuth", command=_select_oauth_file)
    oauth_select.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 6))

    oauth_button = ctk.CTkButton(oauth_frame, text="Conectar con Google", fg_color="#248f24", command=_run_oauth_flow)
    oauth_button.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 12))

    folder_frame = ctk.CTkFrame(body, corner_radius=8)
    folder_frame.grid(row=4, column=0, sticky="ew", padx=16, pady=(12, 0))
    folder_frame.grid_columnconfigure(0, weight=1)

    lbl_folder = ctk.CTkLabel(
        folder_frame,
        text="Carpeta de Drive",
        font=ctk.CTkFont(size=14, weight="bold"),
    )
    lbl_folder.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))

    entry_folder = ctk.CTkEntry(
        folder_frame,
        textvariable=drive_folder_var,
        placeholder_text="ID de carpeta compartida",
    )
    entry_folder.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

    lbl_folder_help = ctk.CTkLabel(
        folder_frame,
        text="El ID se guardará y reutilizará automáticamente en los envíos.",
        text_color="#9aa4b2",
    )
    lbl_folder_help.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 10))

    def _persist_folder_id(*_):
        value = drive_folder_var.get().strip()
        set_drive_folder_id(value)
        drive_state["folder_id"] = value

    entry_folder.bind("<FocusOut>", _persist_folder_id)
    entry_folder.bind("<Return>", lambda *_: _persist_folder_id())

    return {
        "status_var": status_var,
        "path_var": path_var,
        "oauth_status_var": oauth_status_var,
        "oauth_path_var": oauth_path_var,
    }
