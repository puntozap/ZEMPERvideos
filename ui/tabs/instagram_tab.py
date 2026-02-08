import os
import json
import threading
import time
import urllib.parse
import customtkinter as ctk
from tkinter import filedialog

from ui.shared.tab_shell import create_tab_shell
from ui.shared import helpers
from core.instagram_api import InstagramUploader
from core.ai_instagram import generar_descripcion_instagram
from core.instagram_auth import exchange_long_lived_token
from core.instagram_oauth import oauth_login_flow

CONFIG_PATH = "credentials/instagram_config.json"

def _load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_config(data):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def create_instagram_tab(parent, context):
    """
    Crea la pestaña de Instagram con subpestañas para Configuración y Subida.
    """
    # Layout base
    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    # Shell con scroll
    container, scroll_body = create_tab_shell(parent, padx=10, pady=10)
    
    # Configurar layout para panel lateral de logs
    container.grid_columnconfigure(0, weight=1)
    container.grid_columnconfigure(1, weight=0)

    # Panel de Actividad (Log)
    log_card, _, log_local = helpers.create_log_panel(
        container,
        title="Actividad Instagram",
        height=0, # Altura automática
        mirror_fn=context.get("log"),
    )
    log_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
    
    # Actualizar el contexto para que las funciones usen este log local
    context["log"] = log_local
    
    # Tabview para sub-pestañas
    tabview = ctk.CTkTabview(scroll_body)
    tabview.pack(fill="both", expand=True, padx=5, pady=5)
    
    tab_upload = tabview.add("Subir Reel")
    tab_config = tabview.add("Configuración")
    
    _setup_config_tab(tab_config, context)
    _setup_upload_tab(tab_upload, context)

def _setup_config_tab(parent, context):
    log = context.get("log", print)
    config = _load_config()

    ctk.CTkLabel(parent, text="Credenciales Instagram Graph API", font=("Arial", 16, "bold")).pack(pady=(15, 5))
    ctk.CTkLabel(parent, text="Necesitas un Token de Usuario y el ID de tu cuenta de Instagram Business.", text_color="gray").pack(pady=(0, 15))

    ctk.CTkLabel(parent, text="Instagram Account ID:").pack(anchor="w", padx=20)
    entry_id = ctk.CTkEntry(parent, width=400, placeholder_text="Ej: 17841400000000000")
    entry_id.pack(anchor="w", padx=20, pady=(0, 10))
    entry_id.insert(0, config.get("account_id", ""))

    ctk.CTkLabel(parent, text="Access Token:").pack(anchor="w", padx=20)
    entry_token = ctk.CTkEntry(parent, width=400, placeholder_text="EAAG...")
    entry_token.pack(anchor="w", padx=20, pady=(0, 10))
    entry_token.insert(0, config.get("access_token", ""))

    ctk.CTkLabel(parent, text="Redirect URI:").pack(anchor="w", padx=20)
    entry_redirect = ctk.CTkEntry(parent, width=400, placeholder_text="http://127.0.0.1:8766/callback")
    entry_redirect.pack(anchor="w", padx=20, pady=(0, 10))
    entry_redirect.insert(0, config.get("redirect_uri", "http://127.0.0.1:8766/callback"))

    ctk.CTkLabel(parent, text="Scopes:").pack(anchor="w", padx=20)
    entry_scopes = ctk.CTkEntry(parent, width=400)
    entry_scopes.pack(anchor="w", padx=20, pady=(0, 10))
    entry_scopes.insert(0, config.get("scopes", "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement"))

    ctk.CTkLabel(parent, text="App ID (opcional):").pack(anchor="w", padx=20)
    entry_app_id = ctk.CTkEntry(parent, width=400, placeholder_text="App ID")
    entry_app_id.pack(anchor="w", padx=20, pady=(0, 10))
    entry_app_id.insert(0, config.get("app_id", ""))

    ctk.CTkLabel(parent, text="App Secret (opcional):").pack(anchor="w", padx=20)
    entry_app_secret = ctk.CTkEntry(parent, width=400, show="*", placeholder_text="App Secret")
    entry_app_secret.pack(anchor="w", padx=20, pady=(0, 10))
    entry_app_secret.insert(0, config.get("app_secret", ""))

    expires_at = config.get("token_expires_at")
    expires_txt = "Token: sin expiración registrada"
    if expires_at:
        try:
            expires_txt = "Token expira: " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(expires_at)))
        except Exception:
            expires_txt = f"Token expira: {expires_at}"
    lbl_exp = ctk.CTkLabel(parent, text=expires_txt, text_color="gray")
    lbl_exp.pack(anchor="w", padx=20, pady=(0, 10))

    def save():
        data = {
            "account_id": entry_id.get().strip(),
            "access_token": entry_token.get().strip(),
            "app_id": entry_app_id.get().strip(),
            "app_secret": entry_app_secret.get().strip(),
            "token_expires_at": config.get("token_expires_at"),
            "redirect_uri": entry_redirect.get().strip(),
            "scopes": entry_scopes.get().strip(),
        }
        _save_config(data)
        log("✅ Configuración de Instagram guardada.")

    def renovar():
        try:
            data = exchange_long_lived_token(
                short_lived_token=entry_token.get().strip(),
                app_id=entry_app_id.get().strip(),
                app_secret=entry_app_secret.get().strip(),
            )
            new_token = data.get("access_token", "")
            entry_token.delete(0, "end")
            entry_token.insert(0, new_token)
            config["token_expires_at"] = data.get("expires_at")
            save()
            if data.get("expires_at"):
                lbl_exp.configure(
                    text="Token expira: "
                    + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(data["expires_at"])))
                )
            log("✅ Token renovado (long-lived).")
        except Exception as e:
            log(f"❌ Error renovando token: {e}")

    def conectar():
        def _run():
            try:
                redirect_uri = entry_redirect.get().strip()
                parsed = urllib.parse.urlparse(redirect_uri)
                if parsed.hostname in ("127.0.0.1", "localhost"):
                    listen_host = parsed.hostname
                    listen_port = parsed.port or 80
                else:
                    # Cuando usamos ngrok (https), el servidor local sigue escuchando en 127.0.0.1:8766
                    listen_host = "127.0.0.1"
                    listen_port = 8766
                data = oauth_login_flow(
                    app_id=entry_app_id.get().strip(),
                    app_secret=entry_app_secret.get().strip(),
                    redirect_uri=redirect_uri,
                    scopes=entry_scopes.get().strip(),
                    log_fn=log,
                    timeout_sec=600,
                    listen_host=listen_host,
                    listen_port=listen_port,
                )
                entry_token.delete(0, "end")
                entry_token.insert(0, data.get("access_token", ""))
                config["token_expires_at"] = data.get("expires_at")
                save()
                if data.get("expires_at"):
                    lbl_exp.configure(
                        text="Token expira: "
                        + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(data["expires_at"])))
                    )
                log("✅ OAuth completado. Token guardado.")
            except Exception as e:
                log(f"❌ Error OAuth: {e}")

        threading.Thread(target=_run, daemon=True).start()

    ctk.CTkButton(parent, text="Guardar Credenciales", command=save).pack(pady=(10, 6))
    ctk.CTkButton(parent, text="Conectar con Facebook (OAuth)", command=conectar).pack(pady=(0, 6))
    ctk.CTkButton(parent, text="Renovar token (60 días)", command=renovar).pack(pady=(0, 20))

def _setup_upload_tab(parent, context):
    log = context.get("log", print)
    
    ctk.CTkLabel(parent, text="Publicar Reel", font=("Arial", 16, "bold")).pack(pady=15)

    # Selector de archivo
    frame_file = ctk.CTkFrame(parent, fg_color="transparent")
    frame_file.pack(fill="x", padx=20, pady=5)
    entry_file = ctk.CTkEntry(frame_file, placeholder_text="Selecciona un video vertical (.mp4)")
    entry_file.pack(side="left", fill="x", expand=True, padx=(0, 10))
    batch_state = {"paths": []}
    lbl_batch = ctk.CTkLabel(parent, text="Lote: (sin videos)", text_color="gray")
    lbl_batch.pack(anchor="w", padx=20, pady=(4, 0))
    
    def browse():
        f = filedialog.askopenfilename(filetypes=[("MP4 Video", "*.mp4")])
        if f:
            entry_file.delete(0, "end")
            entry_file.insert(0, f)

    def browse_batch():
        files = filedialog.askopenfilenames(filetypes=[("MP4 Video", "*.mp4")])
        if files:
            batch_state["paths"] = list(files)
            lbl_batch.configure(text=f"Lote: {len(files)} video(s) seleccionado(s)")

    btns = ctk.CTkFrame(frame_file, fg_color="transparent")
    btns.pack(side="right")
    ctk.CTkButton(btns, text="Examinar", width=100, command=browse).pack(side="left", padx=(0, 8))
    ctk.CTkButton(btns, text="Lote", width=80, command=browse_batch).pack(side="left")

    # Caption
    ctk.CTkLabel(parent, text="Descripción (Caption):").pack(anchor="w", padx=20, pady=(10, 0))
    txt_caption = ctk.CTkTextbox(parent, height=100)
    txt_caption.pack(fill="x", padx=20, pady=(5, 10))

    ai_row = ctk.CTkFrame(parent, fg_color="transparent")
    ai_row.pack(fill="x", padx=20, pady=(0, 6))
    ai_row.grid_columnconfigure(3, weight=1)

    ctk.CTkLabel(ai_row, text="Hashtags IA:", font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w")
    entry_hashtags = ctk.CTkEntry(ai_row, width=80)
    entry_hashtags.insert(0, "8")
    entry_hashtags.grid(row=0, column=1, sticky="w", padx=(8, 12))

    ctk.CTkLabel(ai_row, text="Menciones (opcional):", font=ctk.CTkFont(size=12)).grid(row=0, column=2, sticky="w")
    entry_mentions = ctk.CTkEntry(ai_row)
    entry_mentions.grid(row=0, column=3, sticky="ew", padx=(8, 0))

    def _build_caption(ai_result: dict, extra_mentions: str) -> str:
        parts = []
        if ai_result.get("descripcion"):
            parts.append(ai_result["descripcion"])
        if ai_result.get("hashtags"):
            parts.append(ai_result["hashtags"])
        if ai_result.get("menciones"):
            parts.append(ai_result["menciones"])
        if extra_mentions:
            parts.append(extra_mentions)
        return "\n".join(p for p in parts if p)

    def _get_hashtags_count() -> int:
        raw = entry_hashtags.get().strip()
        try:
            value = int(raw)
        except Exception:
            value = 8
        return max(1, min(20, value))

    def generar_caption_ia():
        video_path = entry_file.get().strip()
        if not video_path or not os.path.exists(video_path):
            log("❌ Archivo no válido para IA.")
            return
        def _run():
            try:
                ai = generar_descripcion_instagram(
                    video_path,
                    hashtags=_get_hashtags_count(),
                    logs=log,
                )
                caption = _build_caption(ai, entry_mentions.get().strip())
                txt_caption.delete("1.0", "end")
                txt_caption.insert("1.0", caption)
                log("✅ Descripción IA generada.")
            except Exception as e:
                log(f"❌ Error IA: {e}")
        threading.Thread(target=_run, daemon=True).start()

    ctk.CTkButton(parent, text="✨ Generar descripción con IA", command=generar_caption_ia).pack(pady=(0, 10))

    chk_feed = ctk.CTkCheckBox(parent, text="Publicar también en el Feed")
    chk_feed.pack(anchor="w", padx=20, pady=5)
    chk_feed.select()

    def process_upload():
        video_path = entry_file.get().strip()
        caption = txt_caption.get("1.0", "end").strip()
        share_feed = bool(chk_feed.get())
        config = _load_config()

        if not video_path or not os.path.exists(video_path):
            log("❌ Archivo no válido.")
            return
        if not config.get("account_id") or not config.get("access_token"):
            log("❌ Faltan credenciales en la pestaña Configuración.")
            return

        def _update_tokens(data: dict):
            fresh = _load_config()
            fresh["access_token"] = data.get("access_token", fresh.get("access_token"))
            if data.get("expires_at"):
                fresh["token_expires_at"] = data.get("expires_at")
            _save_config(fresh)

        def _run():
            uploader = InstagramUploader(
                config["access_token"],
                config["account_id"],
                app_id=config.get("app_id"),
                app_secret=config.get("app_secret"),
                token_expires_at=config.get("token_expires_at"),
                on_token_update=_update_tokens,
            )
            uploader.upload_reel_resumable(video_path, caption, share_feed, log_fn=log)
        
        threading.Thread(target=_run, daemon=True).start()

    def process_batch():
        config = _load_config()
        share_feed = bool(chk_feed.get())
        if not config.get("account_id") or not config.get("access_token"):
            log("❌ Faltan credenciales en la pestaña Configuración.")
            return
        files = batch_state.get("paths") or []
        if not files:
            log("❌ No hay videos en el lote.")
            return

        def _update_tokens(data: dict):
            fresh = _load_config()
            fresh["access_token"] = data.get("access_token", fresh.get("access_token"))
            if data.get("expires_at"):
                fresh["token_expires_at"] = data.get("expires_at")
            _save_config(fresh)

        def _run():
            uploader = InstagramUploader(
                config["access_token"],
                config["account_id"],
                app_id=config.get("app_id"),
                app_secret=config.get("app_secret"),
                token_expires_at=config.get("token_expires_at"),
                on_token_update=_update_tokens,
            )
            total = len(files)
            for idx, path in enumerate(files, start=1):
                if not os.path.exists(path):
                    log(f"❌ [{idx}/{total}] Archivo no encontrado: {path}")
                    continue
                try:
                    log(f"[{idx}/{total}] Generando descripción IA...")
                    ai = generar_descripcion_instagram(
                        path,
                        hashtags=_get_hashtags_count(),
                        logs=log,
                    )
                    caption = _build_caption(ai, entry_mentions.get().strip())
                except Exception as e:
                    log(f"❌ [{idx}/{total}] Error IA: {e}")
                    continue
                log(f"[{idx}/{total}] Subiendo a Instagram...")
                uploader.upload_reel_resumable(path, caption, share_feed, log_fn=log)
            log("✅ Lote finalizado.")

        threading.Thread(target=_run, daemon=True).start()

    ctk.CTkButton(parent, text="🚀 Publicar en Instagram", command=process_upload, fg_color="#E1306C", hover_color="#C13584").pack(pady=(10, 8))
    ctk.CTkButton(parent, text="📦 Subir lote con IA", command=process_batch).pack(pady=(0, 20))
