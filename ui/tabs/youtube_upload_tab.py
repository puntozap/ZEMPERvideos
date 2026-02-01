import json
import re
import threading
import time
import tkinter as tk
from pathlib import Path
import webbrowser

import customtkinter as ctk

from core.youtube_credentials import (
    available_credentials,
    find_active_credentials_file,
    load_active_credentials,
    register_credentials,
    DEFAULT_SCOPES,
)
from core.youtube_oauth import build_oauth_url, exchange_code_for_tokens
from core.youtube_upload import YouTubeUploadError, upload_video, set_thumbnail
from core.utils import obtener_duracion_segundos
from core.ai_youtube import generar_textos_youtube
from ui.dialogs import mostrar_error, mostrar_info, seleccionar_archivo
from ui.shared import helpers
from core.oauth_redirect_server import CALLBACK_FILE, REDIRECT_PORT, start_redirect_server
from core.youtube_api import listar_videos_subidos


def _parse_mm_ss(value: str) -> float:
    text = (value or "").strip()
    if not text or ":" not in text:
        raise ValueError("Formato mm:ss requerido.")
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError("Formato mm:ss requerido.")
    minutes, seconds = parts
    try:
        minutes_value = float(minutes.strip().replace(",", "."))
        seconds_value = float(seconds.strip().replace(",", "."))
    except ValueError:
        raise ValueError("Los minutos y segundos deben ser numéricos.")
    if minutes_value < 0 or seconds_value < 0 or seconds_value >= 60:
        raise ValueError("Segundos debe estar entre 00 y 59.")
    return minutes_value * 60 + seconds_value


def _format_mm_ss(seconds_value: float) -> str:
    seconds_value = max(0.0, seconds_value)
    minutes = int(seconds_value // 60)
    seconds = int(seconds_value % 60)
    return f"{minutes:02d}:{seconds:02d}"


def _extract_oauth_info(path: Path) -> dict[str, list[str] | str]:
    try:
        with path.open("r", encoding="utf-8") as source:
            payload = json.load(source)
    except Exception:
        return {}
    installed = payload.get("installed") or payload.get("web")
    if not isinstance(installed, dict):
        return {}
    redirect_uris = installed.get("redirect_uris") or installed.get("redirectUris") or []
    if isinstance(redirect_uris, str):
        redirect_uris = [redirect_uris]
    return {
        "client_id": installed.get("client_id", ""),
        "client_secret": installed.get("client_secret", ""),
        "redirect_uris": [uri for uri in redirect_uris if isinstance(uri, str)],
    }


_oauth_server = None
_server_lock = threading.Lock()


def _ensure_oauth_server():
    global _oauth_server
    with _server_lock:
        if _oauth_server is None:
            _oauth_server = start_redirect_server()
    return _oauth_server


def create_tab(parent, context):
    log_global = context.get("log_global")
    stop_control = context.get("stop_control")
    youtube_state = context.get("youtube_state", {})

    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
    container.grid_columnconfigure(0, weight=1)
    container.grid_columnconfigure(1, weight=0)
    container.grid_rowconfigure(0, weight=1)

    log_card, _txt_widget, log = helpers.create_log_panel(
        container,
        title="Actividad YouTube",
        height=220,
        mirror_fn=log_global,
    )
    log_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

    card = ctk.CTkFrame(container, corner_radius=12)
    card.grid(row=0, column=0, sticky="nsew")
    card.grid_columnconfigure(0, weight=1)
    card.grid_rowconfigure(1, weight=1)

    lbl_title = ctk.CTkLabel(
        card,
        text="Canal YouTube",
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    lbl_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    tabview = ctk.CTkTabview(card, corner_radius=8)
    tabview.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
    tabview.add("¿Qué es?")
    tabview.add("Configuración")
    tabview.add("Subir video")
    tabview.add("Miniatura")

    about_tab = tabview.tab("¿Qué es?")
    config_tab = tabview.tab("Configuración")
    upload_tab = tabview.tab("Subir video")
    thumbnail_tab = tabview.tab("Miniatura")
    def _create_tab_body(tab_frame):
        tab_frame.grid_columnconfigure(0, weight=1)
        tab_frame.grid_rowconfigure(0, weight=1)
        body = ctk.CTkScrollableFrame(tab_frame, corner_radius=0)
        body.grid(row=0, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        return body

    about_body = _create_tab_body(about_tab)
    config_body = _create_tab_body(config_tab)
    upload_body = _create_tab_body(upload_tab)
    thumbnail_body = _create_tab_body(thumbnail_tab)

    status_var = tk.StringVar(value="Cargando credenciales...")
    registered_var = tk.StringVar(value="")

    lbl_status = ctk.CTkLabel(about_body, textvariable=status_var, font=ctk.CTkFont(size=12))
    lbl_status.grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))

    lbl_registered = ctk.CTkLabel(
        about_body,
        textvariable=registered_var,
        font=ctk.CTkFont(size=11),
        text_color="#9aa4b2",
    )
    lbl_registered.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 12))

    button_row = ctk.CTkFrame(about_body, fg_color="transparent")
    button_row.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
    for column in range(3):
        button_row.grid_columnconfigure(column, weight=1)

    DEFAULT_REDIRECT = "http://localhost:4850"

    def populate_oauth_fields_from_path(path: Path | None):
        if not path:
            return
        info = _extract_oauth_info(path)
        if not info:
            return
        if info.get("client_id"):
            client_id_var.set(info["client_id"])
        if info.get("client_secret"):
            client_secret_var.set(info["client_secret"])
        uris = info.get("redirect_uris") or []
        if uris:
            redirect_var.set(uris[0])
        else:
            redirect_var.set(DEFAULT_REDIRECT)

    def refresh_status():
        candidates = available_credentials()
        active = find_active_credentials_file()
        if active:
            status_var.set(f"Activa: {active.name}")
            populate_oauth_fields_from_path(active)
        else:
            status_var.set("No hay credenciales activas.")
        if candidates:
            listed = ", ".join(p.name for p in candidates)
            registered_var.set(f"Registradas ({len(candidates)}): {listed}")
        else:
            registered_var.set("No hay credenciales registradas.")

    def _start_oauth_callback_monitor(target_path: Path, client_id: str, client_secret: str, redirect: str):
        def monitor():
            last_timestamp = None
            while True:
                if not CALLBACK_FILE.exists():
                    time.sleep(0.5)
                    continue
                try:
                    payload = json.loads(CALLBACK_FILE.read_text(encoding="utf-8"))
                except Exception:
                    time.sleep(0.5)
                    continue
                timestamp = payload.get("timestamp")
                if not timestamp or timestamp == last_timestamp:
                    time.sleep(0.5)
                    continue
                last_timestamp = timestamp
                code = payload.get("code")
                if not code:
                    time.sleep(0.5)
                    continue
                try:
                    tokens = exchange_code_for_tokens(client_id, client_secret, code, redirect)
                except Exception as exc:
                    mostrar_error(f"Error automático intercambiando código: {exc}")
                    log(f"Intento automático fallido: {exc}")
                    time.sleep(5)
                    continue
                try:
                    credentials_data = json.loads(target_path.read_text(encoding="utf-8"))
                except Exception as exc:
                    mostrar_error(f"No se leyó {target_path.name}: {exc}")
                    log(f"Error leyendo credencial: {exc}")
                    return
                credentials_data.setdefault("scopes", list(DEFAULT_SCOPES))
                credentials_data.update(
                    {
                        "refresh_token": tokens.get("refresh_token"),
                        "token_uri": tokens.get("token_uri") or credentials_data.get("token_uri"),
                        "access_token": tokens.get("access_token") or credentials_data.get("access_token"),
                    }
                )
                installed = credentials_data.get("installed")
                if isinstance(installed, dict):
                    installed.setdefault("scopes", list(DEFAULT_SCOPES))
                    refresh_token = tokens.get("refresh_token")
                    if refresh_token:
                        installed["refresh_token"] = refresh_token
                try:
                    target_path.write_text(json.dumps(credentials_data, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception as exc:
                    mostrar_error(f"No se guardaron tokens: {exc}")
                    log(f"Error guardando tokens en {target_path.name}: {exc}")
                    return
                CALLBACK_FILE.unlink(missing_ok=True)
                helpers.log_seccion(log, None, "OAuth automática")
                log(f"Refresh token guardado en {target_path.name}.")
                refresh_status()
                break

        threading.Thread(target=monitor, daemon=True).start()

    def _start_oauth_flow(target_path: Path):
        _ensure_oauth_server()
        client_id = client_id_var.get().strip()
        client_secret = client_secret_var.get().strip()
        redirect = redirect_var.get().strip() or DEFAULT_REDIRECT
        if not (client_id and client_secret):
            mostrar_error("Faltan Client ID o Client Secret en el archivo.")
            return
        helpers.log_seccion(log, None, "OAuth automática")
        log(f"Servidor OAuth activo en localhost:{REDIRECT_PORT}. Abriendo navegador...")
        try:
            oauth_url = build_oauth_url(client_id, redirect, list(DEFAULT_SCOPES))
        except Exception as exc:
            mostrar_error(f"No se generó la URL automática: {exc}")
            log(f"Error generando URL automática: {exc}")
            return
        oauth_url_var.set(oauth_url)
        webbrowser.open(oauth_url)
        CALLBACK_FILE.unlink(missing_ok=True)
        _start_oauth_callback_monitor(target_path, client_id, client_secret, redirect)

    def registrar():
        source = seleccionar_archivo("Seleccionar JSON de credenciales YouTube", [("JSON", "*.json")])
        if not source:
            return
        try:
            target = register_credentials(source)
            helpers.log_seccion(log, None, "Credenciales")
            log(f"Credencial registrada: {target.name}")
            log("Listo para subir videos.")
            populate_oauth_fields_from_path(target)
            _start_oauth_flow(target)
            refresh_status()
        except Exception as exc:
            mostrar_error(str(exc))
            log(f"Error registrando credenciales: {exc}")

    def mostrar_activa():
        try:
            creds = load_active_credentials()
            helpers.log_seccion(log, None, "Credencial activa")
            log(f"client_id: {creds.client_id}")
            log(f"scopes: {', '.join(creds.scopes)}")
        except Exception as exc:
            mostrar_error(str(exc))
            log(f"No hay credencial activa: {exc}")
            refresh_status()

    ctk.CTkButton(button_row, text="Registrar credenciales", command=registrar, height=42).grid(
        row=0, column=0, sticky="ew", padx=(0, 8)
    )
    ctk.CTkButton(button_row, text="Refrescar estado", command=refresh_status, height=42).grid(
        row=0, column=1, sticky="ew", padx=(0, 8)
    )
    ctk.CTkButton(button_row, text="Mostrar activa", command=mostrar_activa, height=42).grid(
        row=0, column=2, sticky="ew"
    )

    oauth_frame = ctk.CTkFrame(about_body, fg_color="transparent")
    oauth_frame.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 8))
    oauth_frame.grid_columnconfigure(1, weight=1)

    ctk.CTkLabel(
        oauth_frame,
        text="Genera la URL de autorización y cambia el código por un refresh token.",
        font=ctk.CTkFont(size=12),
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

    client_id_var = tk.StringVar()
    client_secret_var = tk.StringVar()
    redirect_var = tk.StringVar(value=DEFAULT_REDIRECT)
    oauth_url_var = tk.StringVar(value="Aquí aparecerá la URL generada.")
    oauth_code_var = tk.StringVar()

    def create_oauth_row(label_text, widget, row_index):
        ctk.CTkLabel(oauth_frame, text=label_text, font=ctk.CTkFont(size=11)).grid(
            row=row_index, column=0, sticky="w", pady=(0, 4)
        )
        widget.grid(row=row_index, column=1, sticky="ew", pady=(0, 4))

    create_oauth_row("Client ID", ctk.CTkEntry(oauth_frame, textvariable=client_id_var), 1)
    create_oauth_row("Client Secret", ctk.CTkEntry(oauth_frame, textvariable=client_secret_var), 2)
    create_oauth_row(
        "Redirect URI", ctk.CTkEntry(oauth_frame, textvariable=redirect_var), 3
    )
    url_entry = ctk.CTkEntry(
        oauth_frame, textvariable=oauth_url_var, state="readonly"
    )
    create_oauth_row("URL autoriz.", url_entry, 4)

    def generar_url():
        cid = client_id_var.get().strip()
        secret = client_secret_var.get().strip()
        redirect = redirect_var.get().strip() or DEFAULT_REDIRECT
        if not cid or not secret:
            mostrar_error("Falta Client ID o Client Secret.")
            return
        url = build_oauth_url(cid, redirect, ["https://www.googleapis.com/auth/youtube.upload"])
        oauth_url_var.set(url)
        log("URL de autorización generada.")

    def abrir_url():
        url = oauth_url_var.get()
        if not url or url.startswith("Aquí"):
            mostrar_error("Genera primero la URL.")
            return
        webbrowser.open(url)

    btn_row = ctk.CTkFrame(oauth_frame, fg_color="transparent")
    btn_row.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 8))
    btn_row.grid_columnconfigure((0, 1, 2), weight=1)

    ctk.CTkButton(btn_row, text="Generar URL", command=generar_url, height=32).grid(
        row=0, column=0, sticky="ew"
    )
    ctk.CTkButton(btn_row, text="Abrir navegador", command=abrir_url, height=32).grid(
        row=0, column=1, sticky="ew", padx=4
    )

    create_oauth_row("Código", ctk.CTkEntry(oauth_frame, textvariable=oauth_code_var), 6)

    def intercambiar_codigo():
        code = oauth_code_var.get().strip()
        cid = client_id_var.get().strip()
        secret = client_secret_var.get().strip()
        redirect = redirect_var.get().strip() or DEFAULT_REDIRECT
        if not (code and cid and secret):
            mostrar_error("Ingresa código, client ID y client secret.")
            return
        try:
            tokens = exchange_code_for_tokens(cid, secret, code, redirect)
        except Exception as exc:
            mostrar_error(f"Error intercambiando código: {exc}")
            return
        message = (
            "Tokens recibidos:\n"
            f"refresh_token: {tokens.get('refresh_token')}\n"
            f"access_token: {tokens.get('access_token')}\n"
            f"token_uri: {tokens.get('token_uri')}"
        )
        mostrar_info(message)
        log("Tokens OAuth obtenidos. Agrega refresh_token al JSON y regístralo.")

    ctk.CTkButton(oauth_frame, text="Intercambiar código", command=intercambiar_codigo, height=32).grid(
        row=7, column=0, columnspan=2, sticky="ew"
    )

    config_row_index = 0

    def create_config_row(label_text, widget):
        nonlocal config_row_index
        frame = ctk.CTkFrame(config_body, fg_color="transparent")
        frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(frame, text=label_text, font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w")
        widget.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        frame.grid(row=config_row_index, column=0, sticky="ew", pady=4)
        config_row_index += 1

    privacy_var = tk.StringVar(value="public")
    entry_tags = ctk.CTkEntry(config_body, placeholder_text="etiqueta1, etiqueta2")
    entry_title_template = ctk.CTkEntry(config_body, placeholder_text="Título por defecto")
    switch_short = ctk.CTkSwitch(
        config_body,
        text="Forzar formato Short (≤60s / vertical)",
        variable=tk.BooleanVar(value=False),
    )

    create_config_row(
        "Privacidad por defecto",
        ctk.CTkOptionMenu(config_body, values=["public", "unlisted", "private"], variable=privacy_var),
    )
    create_config_row("Plantilla de título", entry_title_template)
    tags_row = ctk.CTkFrame(config_body, fg_color="transparent")
    tags_row.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(tags_row, text="Etiquetas comunes", font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w")
    entry_tags.grid(row=1, column=0, sticky="ew", pady=(4, 0))
    tags_row.grid(row=config_row_index, column=0, sticky="ew", pady=(4, 8))
    config_row_index += 1
    switch_short.grid(row=config_row_index, column=0, sticky="w", pady=(0, 12))
    config_row_index += 1
    ctk.CTkLabel(
        config_body,
        text="Estos valores ayudarán a prellenar los formularios de subida.",
        font=ctk.CTkFont(size=11),
        text_color="#9aa4b2",
    ).grid(row=config_row_index, column=0, sticky="w")
    config_row_index += 1

    video_path_var = tk.StringVar(value="Ningún archivo seleccionado")
    title_var = tk.StringVar()
    privacy_upload_var = tk.StringVar(value="public")
    tags_upload_var = tk.StringVar()
    duration_var = tk.StringVar(value="00:00")
    is_short_var = tk.BooleanVar(value=True)
    model_text_var = tk.StringVar(value="gpt-4o-mini")
    video_id_var = tk.StringVar(value=youtube_state.get("last_video_id") or "")
    last_video_label_var = tk.StringVar(
        value=f"Último video ID: {youtube_state.get('last_video_id') or 'ninguno'}"
    )
    privacy_upload_var.set(privacy_var.get())
    privacy_var.trace_add("write", lambda *_: privacy_upload_var.set(privacy_var.get()))

    def seleccionar_video_para_subida():
        path = seleccionar_archivo(
            "Seleccionar video para subir",
            [("Videos", "*.mp4;*.mkv;*.mov;*.avi;*.flv;*.webm")],
        )
        if not path:
            return
        video_path_var.set(path)
        try:
            dur = obtener_duracion_segundos(path)
        except Exception as exc:
            log(f"No se pudo obtener duración del video: {exc}")
        else:
            duration_var.set(_format_mm_ss(dur))
        log("========================================")
        log(f"Video listo para subir: {path}")

    select_row = ctk.CTkFrame(upload_body, fg_color="transparent")
    select_row.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(select_row, text="Archivo", font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w")
    ctk.CTkEntry(select_row, textvariable=video_path_var, state="readonly").grid(
        row=0, column=1, sticky="ew", padx=(8, 0)
    )
    ctk.CTkButton(select_row, text="Examinar", command=seleccionar_video_para_subida, width=100).grid(
        row=0, column=2, padx=(8, 0)
    )
    upload_body.grid_columnconfigure(0, weight=1)
    upload_row_index = 0
    select_row.grid(row=upload_row_index, column=0, sticky="ew", pady=(4, 8), padx=(4, 0))
    upload_row_index += 1

    def create_field(label_text, widget):
        nonlocal upload_row_index
        frame = ctk.CTkFrame(upload_body, fg_color="transparent")
        frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(frame, text=label_text, font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w")
        widget.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        frame.grid(row=upload_row_index, column=0, sticky="ew", pady=4, padx=(4, 0))
        upload_row_index += 1

    title_frame = ctk.CTkFrame(upload_body, fg_color="transparent")
    title_frame.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(title_frame, text="Título", font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w")
    ctk.CTkEntry(
        title_frame,
        textvariable=title_var,
        placeholder_text=entry_title_template.get().strip() or "Título para YouTube",
    ).grid(row=0, column=1, sticky="ew", padx=(8, 0))
    title_frame.grid(row=upload_row_index, column=0, sticky="ew", pady=4, padx=(4, 0))
    upload_row_index += 1
    create_field("Etiquetas (coma separados)", ctk.CTkEntry(upload_body, textvariable=tags_upload_var))

    desc_frame = ctk.CTkFrame(upload_body, fg_color="transparent")
    desc_frame.grid(row=upload_row_index, column=0, sticky="nsew", pady=(6, 8), padx=(4, 0))
    upload_row_index += 1
    desc_frame.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(desc_frame, text="Descripción", font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w")
    description_box = ctk.CTkTextbox(desc_frame, height=120, corner_radius=8)
    description_box.configure(wrap="word")
    description_box.grid(row=1, column=0, sticky="nsew", pady=(4, 0))

    ai_controls = ctk.CTkFrame(desc_frame, fg_color="transparent")
    ai_controls.grid(row=2, column=0, sticky="ew", pady=(8, 0))
    ai_controls.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(ai_controls, text="Modelo IA", font=ctk.CTkFont(size=12)).grid(row=0, column=1, sticky="e", padx=(8, 0))
    ctk.CTkOptionMenu(ai_controls, values=["gpt-4o-mini", "gpt-4o"], variable=model_text_var).grid(
        row=0, column=2, sticky="w", padx=(4, 0)
    )

    def _fill_textbox(box: ctk.CTkTextbox, value: str):
        box.configure(state="normal")
        box.delete("1.0", "end")
        if value:
            box.insert("end", value.strip())

    def generar_metadata_youtube():
        path = video_path_var.get()
        if path.startswith("Ningún"):
            mostrar_error("Selecciona un video primero.")
            return
        if stop_control and stop_control.is_busy():
            mostrar_error("Ya hay un proceso en curso.")
            return
        if stop_control:
            stop_control.clear_stop()
            stop_control.set_busy(True)
        helpers.log_seccion(log, None, "IA YouTube")

        def run():
            try:
                result = generar_textos_youtube(path, None, model=model_text_var.get(), idioma="es", logs=log)
                if result.get("titulo"):
                    title_var.set(result.get("titulo"))
                _fill_textbox(description_box, desc_with_hashtags)
                _fill_textbox(summary_box, result.get("resumen", ""))
                keywords = result.get("palabras", "")
                formatted_hashtags = ""
                if keywords:
                    entries = [kw.strip("# ").strip() for kw in re.split(r"[,\n]+", keywords) if kw.strip()]
                    hashtagged = [f"#{entry}" for entry in entries if entry]
                    if hashtagged:
                        formatted_hashtags = ",".join(hashtagged)
                        tags_upload_var.set(formatted_hashtags)
                desc_with_hashtags = result.get("descripcion", "")
                if formatted_hashtags:
                    desc_with_hashtags = f"{desc_with_hashtags}\n\n{formatted_hashtags}"
                log("Metadatos generados con IA.")
            except Exception as exc:
                helpers.log_seccion(log, None, "Error IA YouTube")
                log(f"Error IA YouTube: {exc}")
            finally:
                if stop_control:
                    stop_control.set_busy(False)

        threading.Thread(target=run, daemon=True).start()

    btn_metadata_ia = ctk.CTkButton(
        ai_controls,
        text="Generar título + descripción (IA)",
        command=generar_metadata_youtube,
        height=36,
    )
    btn_metadata_ia.grid(row=0, column=0, sticky="w")

    summary_frame = ctk.CTkFrame(upload_body, fg_color="transparent")
    summary_frame.grid(row=upload_row_index, column=0, sticky="nsew", pady=(0, 8), padx=(4, 0))
    upload_row_index += 1
    summary_frame.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(summary_frame, text="Resumen (IA)", font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w")
    summary_box = ctk.CTkTextbox(summary_frame, height=80, corner_radius=8)
    summary_box.configure(wrap="word")
    summary_box.grid(row=1, column=0, sticky="nsew", pady=(4, 0))

    create_field(
        "Privacidad",
        ctk.CTkOptionMenu(upload_body, values=["public", "unlisted", "private"], variable=privacy_upload_var),
    )

    duration_frame = ctk.CTkFrame(upload_body, fg_color="transparent")
    duration_frame.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(duration_frame, text="Duración (mm:ss)", font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w")
    ctk.CTkEntry(duration_frame, textvariable=duration_var).grid(row=0, column=1, sticky="ew", padx=(8, 0))
    duration_frame.grid(row=upload_row_index, column=0, sticky="ew", pady=(4, 4), padx=(4, 0))
    upload_row_index += 1

    switch_short_upload = ctk.CTkSwitch(upload_body, text="Es Short (≤60s / 9:16)", variable=is_short_var)
    switch_short_upload.grid(row=upload_row_index, column=0, sticky="w", pady=(4, 8), padx=(4, 0))
    upload_row_index += 1

    ctk.CTkLabel(
        upload_body,
        text="Requisitos: videos verticales (9:16), ≤60 s para Shorts y metadata completa.",
        font=ctk.CTkFont(size=11),
        text_color="#9aa4b2",
    ).grid(row=upload_row_index, column=0, sticky="w", pady=(0, 12), padx=(4, 0))
    upload_row_index += 1

    def subir_video():
        if video_path_var.get().startswith("Ningún"):
            mostrar_error("Selecciona un archivo primero.")
            return
        title_value = title_var.get().strip() or entry_title_template.get().strip()
        if not title_value:
            mostrar_error("Agrega un título.")
            return
        description_value = description_box.get("1.0", "end").strip()
        if not description_value:
            mostrar_error("Agrega una descripción.")
            return
        try:
            seconds = _parse_mm_ss(duration_var.get())
        except ValueError as exc:
            mostrar_error(str(exc))
            return
        if is_short_var.get() and seconds > 60:
            mostrar_error("Un Short no puede exceder 60 segundos.")
            return
        tags_list = [tag.strip() for tag in tags_upload_var.get().split(",") if tag.strip()]
        if not tags_list:
            tags_list = [tag.strip() for tag in entry_tags.get().split(",") if tag.strip()]

        privacy_value = privacy_upload_var.get()
        target_path = Path(video_path_var.get())

        def run_upload():
            helpers.log_seccion(log, None, "Subida de video")
            log(f"Título: {title_value}")
            log(f"Archivo: {target_path}")
            log(f"Duración declarada: {duration_var.get()} ({seconds:.1f}s)")
            log(f"Privacidad: {privacy_value}")
            try:
                upload_result = upload_video(
                    target_path,
                    title_value,
                    description_value,
                    tags_list,
                    privacy=privacy_value,
                    is_short=is_short_var.get(),
                    log_fn=log,
                )
                log(f"Subida exitosa: https://youtu.be/{upload_result}")
                youtube_state["last_video_id"] = upload_result
                video_id_var.set(upload_result)
                last_video_label_var.set(f"Último video ID: {upload_result}")
            except YouTubeUploadError as exc:
                helpers.log_seccion(log, None, "Error YouTube")
                log(f"Error subiendo video: {exc}")
            except Exception as exc:
                helpers.log_seccion(log, None, "Error inesperado")
                log(f"Error inesperado: {exc}")

        threading.Thread(target=run_upload, daemon=True).start()

    ctk.CTkButton(upload_body, text="Subir video", command=subir_video, height=44).grid(
        row=upload_row_index, column=0, sticky="ew", pady=(8, 0), padx=(4, 0)
    )

    thumbnail_path_var = tk.StringVar(value="Ninguna miniatura seleccionada")

    def seleccionar_miniatura():
        path = seleccionar_archivo(
            "Seleccionar miniatura",
            [("Imágenes", "*.jpg;*.jpeg;*.png;*.webp")],
        )
        if not path:
            return
        thumbnail_path_var.set(path)

    def refrescar_videos_youtube():
        videos_status_var.set("Cargando lista desde YouTube...")
        def run_list():
            try:
                videos = listar_videos_subidos(25, log_fn=log)
                _render_videos(videos)
                videos_status_var.set(f"{len(videos)} videos listados")
            except Exception as exc:
                videos_status_var.set("Error al listar videos")
                mostrar_error(f"No se pudo obtener la lista: {exc}")
                log(f"Error listando videos: {exc}")
        threading.Thread(target=run_list, daemon=True).start()

    def _clear_video_rows():
        for child in videos_container.winfo_children():
            child.destroy()

    def _seleccionar_video_youtube(video):
        video_id_var.set(video["video_id"])
        last_video_label_var.set(f"Último video ID: {video['video_id']} ({video['title'][:30]})")

    def _render_videos(videos):
        _clear_video_rows()
        if not videos:
            lbl = ctk.CTkLabel(videos_container, text="No se encontraron videos.", font=ctk.CTkFont(size=12))
            lbl.grid(row=0, column=0, sticky="w", pady=6)
            return
        for idx, video in enumerate(videos, start=1):
            frame = ctk.CTkFrame(videos_container, fg_color="transparent")
            frame.grid(row=idx-1, column=0, sticky="ew", pady=(0, 6))
            frame.grid_columnconfigure(1, weight=1)
            title = video.get("title", "sin título")
            info = f"{video.get('duration_formatted')} • {'Short' if video.get('is_short') else 'Normal'}"
            ctk.CTkLabel(
                frame,
                text=f"{idx}. {title}",
                font=ctk.CTkFont(size=11),
                wraplength=360,
                anchor="w",
            ).grid(row=0, column=0, columnspan=2, sticky="w")
            ctk.CTkLabel(
                frame,
                text=info,
                font=ctk.CTkFont(size=10),
                text_color="#9aa4b2",
            ).grid(row=1, column=0, sticky="w", pady=(2, 0))
            ctk.CTkButton(
                frame,
                text="Usar ID",
                width=120,
                command=lambda v=video: _seleccionar_video_youtube(v),
            ).grid(row=1, column=1, sticky="e", padx=(4, 0))

    def subir_miniatura():
        path = thumbnail_path_var.get()
        if not path or path.startswith("Ninguna"):
            mostrar_error("Selecciona una miniatura primero.")
            return
        video_id = (video_id_var.get() or youtube_state.get("last_video_id") or "").strip()
        if not video_id:
            mostrar_error("Ingresa el ID del video o sube uno para usar su ID.")
            return
        target_path = Path(path)
        if not target_path.exists():
            mostrar_error("No se encontró la miniatura seleccionada.")
            return

        def run_thumb():
            helpers.log_seccion(log, None, "Miniatura")
            log(f"Subiendo miniatura para video {video_id}")
            try:
                set_thumbnail(video_id, target_path, log_fn=log)
                log("Miniatura cargada con éxito.")
            except YouTubeUploadError as exc:
                helpers.log_seccion(log, None, "Error Miniatura")
                log(f"Error miniatura: {exc}")
            except Exception as exc:
                helpers.log_seccion(log, None, "Error inesperado")
                log(f"Error inesperado en miniatura: {exc}")

        threading.Thread(target=run_thumb, daemon=True).start()

    select_thumb = ctk.CTkFrame(thumbnail_body, fg_color="transparent")
    select_thumb.grid_columnconfigure(1, weight=1)
    select_thumb.grid(row=0, column=0, sticky="ew", pady=(4, 8), padx=(4, 0))
    ctk.CTkLabel(select_thumb, text="Archivo", font=ctk.CTkFont(size=12)).grid(
        row=0, column=0, sticky="w"
    )
    ctk.CTkEntry(select_thumb, textvariable=thumbnail_path_var, state="readonly").grid(
        row=0, column=1, sticky="ew", padx=(8, 0)
    )
    ctk.CTkButton(select_thumb, text="Examinar", command=seleccionar_miniatura, width=100).grid(
        row=0, column=2, padx=(8, 0)
    )

    video_id_frame = ctk.CTkFrame(thumbnail_body, fg_color="transparent")
    video_id_frame.grid_columnconfigure(1, weight=1)
    video_id_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8), padx=(4, 0))
    ctk.CTkLabel(video_id_frame, text="Video ID", font=ctk.CTkFont(size=12)).grid(
        row=0, column=0, sticky="w"
    )
    ctk.CTkEntry(video_id_frame, textvariable=video_id_var).grid(
        row=0, column=1, sticky="ew", padx=(8, 0)
    )
    ctk.CTkLabel(
        video_id_frame,
        textvariable=last_video_label_var,
        font=ctk.CTkFont(size=11),
        text_color="#9aa4b2",
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

    videos_status_var = tk.StringVar(value="Lista no cargada")
    videos_scroll = ctk.CTkScrollableFrame(thumbnail_body, corner_radius=12, height=220)
    videos_scroll.grid(row=2, column=0, sticky="nsew", pady=(0, 8), padx=(4, 0))
    videos_scroll.grid_columnconfigure(0, weight=1)

    videos_list_frame = ctk.CTkFrame(videos_scroll, fg_color="transparent")
    videos_list_frame.grid(row=0, column=0, sticky="nsew")
    videos_list_frame.grid_columnconfigure(0, weight=1)

    btn_refresh_videos = ctk.CTkButton(
        videos_list_frame,
        text="Refrescar lista de YouTube",
        command=lambda: refrescar_videos_youtube(),
        height=34,
    )
    btn_refresh_videos.grid(row=0, column=0, sticky="ew", pady=(0, 8))

    lbl_videos_status = ctk.CTkLabel(
        videos_list_frame,
        textvariable=videos_status_var,
        font=ctk.CTkFont(size=11),
        text_color="#9aa4b2",
    )
    lbl_videos_status.grid(row=1, column=0, sticky="w", pady=(0, 8))

    videos_container = ctk.CTkFrame(videos_list_frame, fg_color="transparent")
    videos_container.grid(row=2, column=0, sticky="nsew")
    videos_container.grid_columnconfigure(0, weight=1)

    ctk.CTkButton(
        thumbnail_body,
        text="Subir miniatura",
        command=subir_miniatura,
        height=44,
    ).grid(row=2, column=0, sticky="ew", padx=(4, 0))

    refresh_status()

    return {}
