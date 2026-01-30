import os
import threading
import time
import customtkinter as ctk

from core.tiktok_api import (
    oauth_login_flow,
    load_tokens,
    save_tokens,
    get_valid_access_token,
    init_upload_inbox,
    init_upload_direct,
    upload_video,
)
from ui.shared import helpers


def create_tab(parent, context):
    log = context["log"]
    alerta_busy = context["alerta_busy"]
    stop_control = context["stop_control"]
    beep_fin = context["beep_fin"]
    renombrar_si_largo = context["renombrar_si_largo"]

    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
    container.grid_columnconfigure(0, weight=1)
    container.grid_columnconfigure(1, weight=0)
    container.grid_rowconfigure(0, weight=1)

    left = ctk.CTkFrame(container, fg_color="transparent")
    left.grid(row=0, column=0, sticky="nsew")
    left.grid_columnconfigure(0, weight=1)
    left.grid_rowconfigure(0, weight=1)

    scroll = ctk.CTkScrollableFrame(left, corner_radius=0)
    scroll.grid(row=0, column=0, sticky="nsew")
    scroll.grid_columnconfigure(0, weight=1)

    card = ctk.CTkFrame(scroll, corner_radius=12)
    card.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    card.grid_columnconfigure(0, weight=1)

    lbl_title = ctk.CTkLabel(card, text="Subir a TikTok", font=ctk.CTkFont(size=18, weight="bold"))
    lbl_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_hint = ctk.CTkLabel(
        card,
        text="Conecta tu cuenta y sube videos a borrador o publica directo.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2",
    )
    lbl_hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    auth_card = ctk.CTkFrame(card, corner_radius=10)
    auth_card.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
    auth_card.grid_columnconfigure(1, weight=1)

    lbl_key = ctk.CTkLabel(auth_card, text="Client Key", font=ctk.CTkFont(size=12))
    lbl_key.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))
    entry_key = ctk.CTkEntry(auth_card)
    entry_key.grid(row=0, column=1, sticky="ew", padx=12, pady=(12, 6))
    entry_key.insert(0, os.getenv("TIKTOK_CLIENT_KEY", ""))

    lbl_secret = ctk.CTkLabel(auth_card, text="Client Secret", font=ctk.CTkFont(size=12))
    lbl_secret.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 6))
    entry_secret = ctk.CTkEntry(auth_card, show="*")
    entry_secret.grid(row=1, column=1, sticky="ew", padx=12, pady=(0, 6))
    entry_secret.insert(0, os.getenv("TIKTOK_CLIENT_SECRET", ""))

    lbl_redirect = ctk.CTkLabel(auth_card, text="Redirect URI", font=ctk.CTkFont(size=12))
    lbl_redirect.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 6))
    entry_redirect = ctk.CTkEntry(auth_card)
    entry_redirect.grid(row=2, column=1, sticky="ew", padx=12, pady=(0, 6))
    entry_redirect.insert(0, "http://127.0.0.1:8765/callback")

    lbl_scopes = ctk.CTkLabel(auth_card, text="Scopes", font=ctk.CTkFont(size=12))
    lbl_scopes.grid(row=3, column=0, sticky="w", padx=12, pady=(0, 12))
    entry_scopes = ctk.CTkEntry(auth_card)
    entry_scopes.grid(row=3, column=1, sticky="ew", padx=12, pady=(0, 12))
    entry_scopes.insert(0, "video.upload,video.publish")

    status_var = ctk.StringVar(value="Estado: sin conectar")
    lbl_status = ctk.CTkLabel(auth_card, textvariable=status_var, font=ctk.CTkFont(size=12))
    lbl_status.grid(row=4, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 12))

    pkce_var = ctk.BooleanVar(value=False)
    chk_pkce = ctk.CTkCheckBox(
        auth_card,
        text="Usar PKCE (si falla, desactivar)",
        variable=pkce_var,
    )
    chk_pkce.grid(row=5, column=0, sticky="w", padx=12, pady=(0, 12))

    tokens_state = {"tokens": load_tokens()}

    def _update_status():
        tokens = tokens_state.get("tokens")
        if not tokens:
            status_var.set("Estado: sin conectar")
            return
        expires_in = tokens.get("expires_in", 0)
        created_at = tokens.get("created_at", 0)
        remain = max(0, int(created_at) + int(expires_in) - int(time.time()))
        mins = max(0, remain // 60)
        status_var.set(f"Estado: conectado (expira en {mins} min)")

    _update_status()

    def conectar():
        if stop_control.is_busy():
            alerta_busy()
            return
        client_key = entry_key.get().strip()
        client_secret = entry_secret.get().strip()
        redirect_uri = entry_redirect.get().strip()
        scopes = entry_scopes.get().strip() or "video.upload,video.publish"
        if not client_key or not client_secret:
            log("Completa Client Key y Client Secret.")
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("TikTok OAuth")

        def run_login():
            try:
                tokens = oauth_login_flow(
                    client_key,
                    client_secret,
                    redirect_uri,
                    scopes,
                    use_pkce=pkce_var.get(),
                    log_fn=log,
                    timeout_sec=600,
                )
                tokens_state["tokens"] = tokens
                save_tokens(tokens)
                _update_status()
                log(f"Token guardado en {os.path.abspath('output/tiktok_tokens.json')}")
                beep_fin()
            except Exception as e:
                log(f"Error OAuth: {e}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run_login, daemon=True).start()

    btn_connect = ctk.CTkButton(auth_card, text="Conectar cuenta", command=conectar, height=40)
    btn_connect.grid(row=6, column=0, sticky="w", padx=12, pady=(0, 12))

    def refrescar():
        if stop_control.is_busy():
            alerta_busy()
            return
        client_key = entry_key.get().strip()
        client_secret = entry_secret.get().strip()
        if not client_key or not client_secret:
            log("Completa Client Key y Client Secret.")
            return
        tokens = tokens_state.get("tokens")
        if not tokens:
            log("No hay tokens guardados.")
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("TikTok Refresh")

        def run_refresh():
            try:
                new_tokens = get_valid_access_token(client_key, client_secret, tokens, log_fn=log)
                tokens_state["tokens"] = new_tokens
                save_tokens(new_tokens)
                _update_status()
                log("Token actualizado.")
                beep_fin()
            except Exception as e:
                log(f"Error refresh: {e}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run_refresh, daemon=True).start()

    btn_refresh = ctk.CTkButton(auth_card, text="Refrescar token", command=refrescar, height=32)
    btn_refresh.grid(row=6, column=1, sticky="e", padx=12, pady=(0, 12))

    upload_card = ctk.CTkFrame(card, corner_radius=10)
    upload_card.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 16))
    upload_card.grid_columnconfigure(1, weight=1)

    lbl_video = ctk.CTkLabel(upload_card, text="Video", font=ctk.CTkFont(size=12))
    lbl_video.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))

    video_state = {"path": None}

    lbl_video_name = ctk.CTkLabel(upload_card, text="(sin video)", font=ctk.CTkFont(size=12))
    lbl_video_name.grid(row=0, column=1, sticky="w", padx=12, pady=(12, 6))

    def seleccionar_video():
        from ui.dialogs import seleccionar_video
        video = seleccionar_video()
        if video:
            video = renombrar_si_largo(video)
            if not video:
                return
            video_state["path"] = video
            lbl_video_name.configure(text=os.path.basename(video))
            log(f"Video seleccionado: {video}")

    btn_video = ctk.CTkButton(upload_card, text="Seleccionar video", command=seleccionar_video, height=36)
    btn_video.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

    lbl_mode = ctk.CTkLabel(upload_card, text="Modo", font=ctk.CTkFont(size=12))
    lbl_mode.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 6))

    modo_var = ctk.StringVar(value="Inbox (borrador)")
    opt_modo = ctk.CTkOptionMenu(upload_card, values=["Inbox (borrador)", "Publicar directo"], variable=modo_var)
    opt_modo.grid(row=2, column=1, sticky="w", padx=12, pady=(0, 6))

    lbl_caption = ctk.CTkLabel(upload_card, text="Caption", font=ctk.CTkFont(size=12))
    lbl_caption.grid(row=3, column=0, sticky="w", padx=12, pady=(0, 6))
    entry_caption = ctk.CTkEntry(upload_card)
    entry_caption.grid(row=3, column=1, sticky="ew", padx=12, pady=(0, 6))

    lbl_priv = ctk.CTkLabel(upload_card, text="Privacidad", font=ctk.CTkFont(size=12))
    lbl_priv.grid(row=4, column=0, sticky="w", padx=12, pady=(0, 6))
    priv_var = ctk.StringVar(value="PUBLIC")
    opt_priv = ctk.CTkOptionMenu(upload_card, values=["PUBLIC", "FRIENDS", "PRIVATE"], variable=priv_var)
    opt_priv.grid(row=4, column=1, sticky="w", padx=12, pady=(0, 6))

    disable_comment_var = ctk.BooleanVar(value=False)
    disable_duet_var = ctk.BooleanVar(value=False)
    disable_stitch_var = ctk.BooleanVar(value=False)

    chk_comment = ctk.CTkCheckBox(upload_card, text="Desactivar comentarios", variable=disable_comment_var)
    chk_comment.grid(row=5, column=0, sticky="w", padx=12, pady=(0, 4))
    chk_duet = ctk.CTkCheckBox(upload_card, text="Desactivar duetos", variable=disable_duet_var)
    chk_duet.grid(row=6, column=0, sticky="w", padx=12, pady=(0, 4))
    chk_stitch = ctk.CTkCheckBox(upload_card, text="Desactivar stitch", variable=disable_stitch_var)
    chk_stitch.grid(row=7, column=0, sticky="w", padx=12, pady=(0, 10))

    def subir_video():
        if stop_control.is_busy():
            alerta_busy()
            return
        if not video_state["path"]:
            log("Selecciona un video primero.")
            return
        client_key = entry_key.get().strip()
        client_secret = entry_secret.get().strip()
        if not client_key or not client_secret:
            log("Completa Client Key y Client Secret.")
            return
        tokens = tokens_state.get("tokens")
        if not tokens:
            log("Conecta tu cuenta TikTok primero.")
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("Subir a TikTok")

        def run_upload():
            try:
                tokens_valid = get_valid_access_token(client_key, client_secret, tokens, log_fn=log)
                tokens_state["tokens"] = tokens_valid
                save_tokens(tokens_valid)
                access_token = tokens_valid.get("access_token")
                if not access_token:
                    raise RuntimeError("Token invalido.")
                mode = modo_var.get()
                if mode.startswith("Inbox"):
                    log("Inicializando upload Inbox...")
                    init_data = init_upload_inbox(access_token, video_state["path"])
                else:
                    log("Inicializando upload Directo...")
                    init_data = init_upload_direct(
                        access_token,
                        video_state["path"],
                        entry_caption.get().strip(),
                        priv_var.get(),
                        disable_comment_var.get(),
                        disable_duet_var.get(),
                        disable_stitch_var.get(),
                    )
                upload_url = init_data.get("upload_url")
                video_id = init_data.get("video_id")
                if not upload_url:
                    raise RuntimeError(f"Respuesta init sin upload_url: {init_data}")
                if video_id:
                    log(f"Video ID: {video_id}")
                upload_video(upload_url, video_state["path"], log_fn=log)
                log("Subida finalizada.")
                log("Fin de la automatizacion.")
                beep_fin()
            except Exception as e:
                log(f"Error al subir: {e}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run_upload, daemon=True).start()

    btn_upload = ctk.CTkButton(upload_card, text="Subir a TikTok", command=subir_video, height=44)
    btn_upload.grid(row=8, column=0, sticky="ew", padx=12, pady=(0, 12))

    log_card, _log_widget, log_local = helpers.create_log_panel(
        container,
        title="Actividad",
        height=220,
        mirror_fn=context.get("log_global"),
    )
    log_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

    def log_seccion(titulo):
        log_local("")
        log_local("========================================")
        log_local(f"=== {titulo}")
        log_local("========================================")

    log = log_local

    return {"scroll": scroll}
