import os
import threading
import tkinter as tk

import customtkinter as ctk

from core.drive_config import set_drive_folder_id
from core.whatsapp import (
    delete_drive_file,
    ensure_media_url,
    enviar_mensajes_whatsapp,
    generar_mensajes_whatsapp,
    upload_media_to_drive,
)
from ui.dialogs import mostrar_error, mostrar_info, seleccionar_archivo
from ui.shared import helpers

DEFAULT_INTERVAL_SECONDS = 30


def _clean_number(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit() or ch == "+")


class ContactRow:
    def __init__(self, parent, data, global_message_var, global_media_var, remove_callback):
        self.data = data
        self.global_message_var = global_message_var
        self.global_media_var = global_media_var
        self.remove_callback = remove_callback
        self._suppress_message_trace = False

        self.frame = ctk.CTkFrame(parent, corner_radius=10, fg_color="#26292f", border_width=1, border_color="#444b55")
        self.frame.grid_columnconfigure(0, weight=1)

        top_row = ctk.CTkFrame(self.frame, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="ew")
        top_row.grid_columnconfigure(1, weight=1)
        lbl_number = ctk.CTkLabel(top_row, text="Número:", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_number.grid(row=0, column=0, sticky="w")
        self.number_var = tk.StringVar(value=self.data.get("number", ""))
        entry_number = ctk.CTkEntry(top_row, textvariable=self.number_var, placeholder_text="+59812345678")
        entry_number.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        entry_number.bind("<FocusOut>", self._sync_number)
        btn_remove = ctk.CTkButton(top_row, text="Eliminar", fg_color="#aa4444", width=110, command=self._remove)
        btn_remove.grid(row=0, column=2, sticky="e", padx=(6, 0))

        lbl_msg = ctk.CTkLabel(self.frame, text="Mensaje", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_msg.grid(row=1, column=0, sticky="w", pady=(8, 2))
        self.message_box = ctk.CTkTextbox(self.frame, height=80, corner_radius=6, fg_color="#1e1e22", border_width=1)
        self.message_box.grid(row=2, column=0, sticky="ew")
        self.message_box.bind("<KeyRelease>", self._on_message_change)
        self.btn_message_reset = ctk.CTkButton(
            self.frame, text="Usar mensaje global", width=200, command=self.reset_message
        )
        self.btn_message_reset.grid(row=3, column=0, sticky="e", pady=(4, 0))

        lbl_media = ctk.CTkLabel(self.frame, text="Media del contacto", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_media.grid(row=4, column=0, sticky="w", pady=(10, 2))
        self.media_label_var = tk.StringVar()
        self.media_label = ctk.CTkLabel(self.frame, textvariable=self.media_label_var, text_color="#c7c9d0")
        self.media_label.grid(row=5, column=0, sticky="w")
        media_buttons = ctk.CTkFrame(self.frame, fg_color="transparent")
        media_buttons.grid(row=6, column=0, sticky="ew", pady=(4, 4))
        media_buttons.grid_columnconfigure(0, weight=1)
        media_buttons.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(media_buttons, text="Seleccionar media", command=self._select_media).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        self.btn_media_reset = ctk.CTkButton(media_buttons, text="Usar media global", command=self.reset_media)
        self.btn_media_reset.grid(row=0, column=1, sticky="ew")

        if self.data.get("custom_message") and self.data.get("message"):
            self.set_custom_message(self.data["message"])
        else:
            self.apply_global_message(self.global_message_var.get())

        self._update_media_label()

    def _sync_number(self, *_):
        self.data["number"] = self.number_var.get().strip()

    def _on_message_change(self, *_):
        if self._suppress_message_trace:
            return
        text = self.message_box.get("1.0", "end").strip()
        self.data["message"] = text
        global_text = self.global_message_var.get().strip()
        self.data["custom_message"] = bool(text and text != global_text)

    def reset_message(self):
        self.data["custom_message"] = False
        self.apply_global_message(self.global_message_var.get())

    def set_custom_message(self, text: str):
        self._set_message_text(text or "", mark_custom=True)

    def apply_global_message(self, text: str):
        if self.data.get("custom_message"):
            return
        self._set_message_text(text or "", mark_custom=False)

    def _set_message_text(self, text: str, mark_custom: bool | None = None):
        self._suppress_message_trace = True
        self.message_box.delete("1.0", "end")
        if text:
            self.message_box.insert("1.0", text)
        self._suppress_message_trace = False
        self.data["message"] = text
        if mark_custom is not None:
            self.data["custom_message"] = mark_custom

    def _select_media(self):
        path = seleccionar_archivo("Seleccionar media para el contacto", [("Media", "*.mp4;*.mov;*.avi;*.jpg;*.png;*.webp")])
        if not path:
            return
        self.data["media_path"] = path
        self.data["custom_media"] = True
        self._update_media_label()

    def reset_media(self):
        self.data["custom_media"] = False
        self.data["media_path"] = ""
        self._update_media_label()

    def _update_media_label(self):
        if self.data.get("custom_media") and self.data.get("media_path"):
            label = f"Personal: {os.path.basename(self.data['media_path'])}"
            self.btn_media_reset.configure(state="normal")
        else:
            global_path = self.global_media_var.get().strip()
            if global_path:
                label = f"Global: {os.path.basename(global_path)}"
            else:
                label = "Sin media global"
            self.btn_media_reset.configure(state="disabled")
        self.media_label_var.set(label)

    def apply_global_media(self, path: str | None):
        if self.data.get("custom_media"):
            return
        self._update_media_label()

    def _remove(self):
        if self.remove_callback:
            self.remove_callback(self)

    def destroy(self):
        self.frame.destroy()


def create_tab(parent, context):
    log_global = context.get("log_global")
    stop_control = context.get("stop_control")
    whatsapp_state = context.setdefault("whatsapp_state", {})
    whatsapp_state.setdefault("contacts", [])
    whatsapp_state.setdefault("global_message", "")
    whatsapp_state.setdefault("global_media", "")
    whatsapp_state.setdefault("use_drive", False)
    whatsapp_state.setdefault("drive_folder", "")

    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
    container.grid_columnconfigure(0, weight=1)
    container.grid_columnconfigure(1, weight=0)
    container.grid_rowconfigure(0, weight=1)

    log_card, _, log_fn = helpers.create_log_panel(
        container,
        title="Actividad WhatsApp",
        height=420,
        mirror_fn=log_global,
    )
    log_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

    main_area = ctk.CTkFrame(container, fg_color="transparent")
    main_area.grid(row=0, column=0, sticky="nsew")
    main_area.grid_columnconfigure(0, weight=1)
    main_area.grid_rowconfigure(0, weight=1)

    tabview = ctk.CTkTabview(main_area, corner_radius=12)
    tabview.grid(row=0, column=0, sticky="nsew")
    tabview.add("Números")
    tabview.add("Media global")
    tabview.add("Mensaje global")

    numbers_card = tabview.tab("Números")
    numbers_card.grid_columnconfigure(0, weight=1)
    numbers_card.grid_rowconfigure(3, weight=1)

    lbl_numbers = ctk.CTkLabel(numbers_card, text="Números", font=ctk.CTkFont(size=16, weight="bold"))
    lbl_numbers.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))

    entry_frame = ctk.CTkFrame(numbers_card, fg_color="transparent")
    entry_frame.grid(row=1, column=0, sticky="ew", padx=12)
    entry_frame.grid_columnconfigure(0, weight=1)
    entry_number = ctk.CTkEntry(entry_frame, placeholder_text="59812345678")
    entry_number.grid(row=0, column=0, sticky="ew", pady=6)
    btn_add = ctk.CTkButton(entry_frame, text="Agregar número", width=160)
    btn_add.grid(row=0, column=1, padx=(6, 0))

    helper_frame = ctk.CTkFrame(numbers_card, fg_color="transparent")
    helper_frame.grid(row=2, column=0, sticky="ew", padx=12)
    btn_clear = ctk.CTkButton(helper_frame, text="Limpiar lista", fg_color="#2d5ea6")
    btn_clear.grid(row=0, column=0, pady=(0, 6))

    contacts_container = ctk.CTkScrollableFrame(numbers_card, corner_radius=6, fg_color="#1c1c1f")
    contacts_container.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
    contacts_container.grid_columnconfigure(0, weight=1)
    contacts_container.grid_rowconfigure(0, weight=1)
    contacts_container.configure(height=260)

    contact_rows: list[ContactRow] = []
    global_message_var = tk.StringVar(value=whatsapp_state.get("global_message", ""))
    global_media_var = tk.StringVar(value=whatsapp_state.get("global_media", ""))

    def _layout_contact_rows():
        for idx, row in enumerate(contact_rows):
            row.frame.grid(row=idx, column=0, sticky="ew", pady=(0, 8))

    def _remove_row(row: ContactRow):
        if row not in contact_rows:
            return
        contact_rows.remove(row)
        try:
            whatsapp_state["contacts"].remove(row.data)
        except Exception:
            pass
        row.destroy()
        _layout_contact_rows()

    def _add_contact():
        raw = entry_number.get().strip()
        cleaned = _clean_number(raw)
        if not cleaned:
            return
        if any(cleaned == contact.get("number") for contact in whatsapp_state["contacts"]):
            return
        contact_data = {
            "number": cleaned,
            "message": global_message_var.get(),
            "custom_message": False,
            "media_path": "",
            "custom_media": False,
        }
        whatsapp_state["contacts"].append(contact_data)
        row = ContactRow(
            contacts_container,
            contact_data,
            global_message_var,
            global_media_var,
            remove_callback=_remove_row,
        )
        contact_rows.append(row)
        _layout_contact_rows()
        entry_number.delete(0, "end")

    def _clear_contacts():
        for row in contact_rows[:]:
            _remove_row(row)

    btn_add.configure(command=_add_contact)
    btn_clear.configure(command=_clear_contacts)

    for contact in whatsapp_state["contacts"]:
        contact.setdefault("number", "")
        contact.setdefault("message", global_message_var.get())
        contact.setdefault("custom_message", False)
        contact.setdefault("media_path", "")
        contact.setdefault("custom_media", False)
        row = ContactRow(
            contacts_container,
            contact,
            global_message_var,
            global_media_var,
            remove_callback=_remove_row,
        )
        contact_rows.append(row)
    _layout_contact_rows()

    media_card = tabview.tab("Media global")
    media_card.grid_columnconfigure(0, weight=1)

    lbl_media_title = ctk.CTkLabel(media_card, text="Imagen / Video", font=ctk.CTkFont(size=16, weight="bold"))
    lbl_media_title.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))

    media_entry = ctk.CTkEntry(media_card, textvariable=global_media_var, state="readonly")
    media_entry.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))

    btn_select_media = ctk.CTkButton(media_card, text="Seleccionar video/imagen")
    btn_select_media.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))

    btn_clear_media = ctk.CTkButton(media_card, text="Borrar media", fg_color="#aa4444")
    btn_clear_media.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))

    drive_var = tk.BooleanVar(value=whatsapp_state.get("use_drive", False))
    drive_folder_var = context.get("drive_folder_var")
    if drive_folder_var is None:
        drive_folder_var = tk.StringVar(value=whatsapp_state.get("drive_folder", ""))
    else:
        whatsapp_state["drive_folder"] = drive_folder_var.get().strip()
    drive_checkbox = ctk.CTkCheckBox(media_card, text="Subir a Google Drive", variable=drive_var)
    drive_checkbox.grid(row=4, column=0, sticky="w", padx=12, pady=(0, 6))

    lbl_folder = ctk.CTkLabel(media_card, text="ID carpeta Drive (opcional)", font=ctk.CTkFont(size=12))
    lbl_folder.grid(row=5, column=0, sticky="w", padx=12, pady=(4, 0))
    entry_folder = ctk.CTkEntry(media_card, textvariable=drive_folder_var, placeholder_text="Carpeta compartida")
    entry_folder.grid(row=6, column=0, sticky="ew", padx=12, pady=(0, 6))

    def _on_drive_change(*_):
        whatsapp_state["use_drive"] = drive_var.get()

    def _on_folder_change(*_):
        whatsapp_state["drive_folder"] = drive_folder_var.get().strip()

    drive_var.trace_add("write", _on_drive_change)
    drive_folder_var.trace_add("write", _on_folder_change)
    entry_folder.bind("<FocusOut>", lambda *_: set_drive_folder_id(drive_folder_var.get().strip()))
    entry_folder.bind("<Return>", lambda *_: set_drive_folder_id(drive_folder_var.get().strip()))

    message_card = tabview.tab("Mensaje global")
    message_card.grid_columnconfigure(0, weight=1)
    message_card.grid_columnconfigure(1, weight=0)

    lbl_message_title = ctk.CTkLabel(message_card, text="Mensaje global", font=ctk.CTkFont(size=16, weight="bold"))
    lbl_message_title.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))

    btn_generate = ctk.CTkButton(message_card, text="Generar con IA", width=160)
    btn_generate.grid(row=0, column=1, sticky="e", padx=(0, 12), pady=(12, 4))

    global_message_textbox = ctk.CTkTextbox(message_card, height=140, corner_radius=6)
    global_message_textbox.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12)
    global_message_textbox.configure(state="normal")

    interval_frame = ctk.CTkFrame(message_card, fg_color="transparent")
    interval_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(8, 0))
    interval_frame.grid_columnconfigure(0, weight=1)
    lbl_interval_message = ctk.CTkLabel(interval_frame, text="Intervalo segundos entre envíos", font=ctk.CTkFont(size=12))
    lbl_interval_message.grid(row=0, column=0, sticky="w")
    entry_interval_send = ctk.CTkEntry(interval_frame, placeholder_text=str(DEFAULT_INTERVAL_SECONDS), width=120)
    entry_interval_send.grid(row=0, column=1, sticky="e")
    entry_interval_send.insert(0, str(whatsapp_state.get("interval_seconds", DEFAULT_INTERVAL_SECONDS)))

    btn_send = ctk.CTkButton(message_card, text="Enviar mensajes (WhatsApp)", fg_color="#2d7a2d")
    btn_send.grid(row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 12))

    suppress_global_trace = False

    def _set_global_message_text(value: str):
        nonlocal suppress_global_trace
        text = (value or "").strip()
        whatsapp_state["global_message"] = text
        suppress_global_trace = True
        global_message_textbox.delete("1.0", "end")
        if text:
            global_message_textbox.insert("1.0", text)
        suppress_global_trace = False
        global_message_var.set(text)
        for row in contact_rows:
            row.apply_global_message(text)

    def _on_global_message_edit(event=None):
        nonlocal suppress_global_trace
        if suppress_global_trace:
            return
        text = global_message_textbox.get("1.0", "end").strip()
        whatsapp_state["global_message"] = text
        global_message_var.set(text)
        for row in contact_rows:
            row.apply_global_message(text)

    global_message_textbox.bind("<KeyRelease>", _on_global_message_edit)
    _set_global_message_text(whatsapp_state.get("global_message", ""))

    def _select_global_media():
        path = seleccionar_archivo("Seleccionar video o imagen", [("Media", "*.mp4;*.mov;*.avi;*.jpg;*.png;*.webp")])
        if not path:
            return
        whatsapp_state["global_media"] = path
        global_media_var.set(path)
        for row in contact_rows:
            row.apply_global_media(path)

    def _clear_global_media():
        whatsapp_state["global_media"] = ""
        global_media_var.set("")
        for row in contact_rows:
            row.apply_global_media("")

    btn_select_media.configure(command=_select_global_media)
    btn_clear_media.configure(command=_clear_global_media)

    def run_generar():
        try:
            stop_control.set_busy(True)
            video_path = whatsapp_state.get("global_media") or ""
            if not video_path:
                raise ValueError("Selecciona un video o imagen primero.")
            cantidad = max(1, len(contact_rows))
            messages = generar_mensajes_whatsapp(video_path=video_path, cantidad=cantidad, logs=log_fn)
            if not messages:
                raise RuntimeError("OpenAI no devolvió mensajes.")
            _set_global_message_text(messages[0])
        except Exception as exc:
            if log_fn:
                log_fn(f"Error WhatsApp/Drive: {exc}")
            mostrar_error(str(exc))
        finally:
            stop_control.set_busy(False)

    btn_generate.configure(command=lambda: threading.Thread(target=run_generar, daemon=True).start())

    def run_envio():
        drive_file_ids: list[str] = []
        media_cache: dict[str, tuple[str, str | None]] = {}
        try:
            stop_control.set_busy(True)
            if not whatsapp_state["contacts"]:
                raise ValueError("Agrega al menos un número.")
            global_message = whatsapp_state.get("global_message", "").strip()
            use_drive = drive_var.get()
            drive_folder = drive_folder_var.get().strip() or None
            try:
                interval = float(entry_interval_send.get().strip() or DEFAULT_INTERVAL_SECONDS)
            except ValueError:
                interval = DEFAULT_INTERVAL_SECONDS
            interval = max(0.0, interval)
            whatsapp_state["interval_seconds"] = interval

            def _resolve_media(source: str | None) -> tuple[str | None, str | None]:
                if not source:
                    return None, None
                trimmed = source.strip()
                if not trimmed:
                    return None, None
                if trimmed in media_cache:
                    return media_cache[trimmed]
                lower = trimmed.lower()
                file_id = None
                if lower.startswith("http://") or lower.startswith("https://"):
                    url = ensure_media_url(trimmed, logs=log_fn)
                elif use_drive:
                    file_id, url = upload_media_to_drive(trimmed, logs=log_fn, folder_id=drive_folder)
                    drive_file_ids.append(file_id)
                else:
                    url = ensure_media_url(trimmed, logs=log_fn)
                if not url:
                    raise RuntimeError("No se pudo obtener una URL para la media.")
                media_cache[trimmed] = (url, file_id)
                return url, file_id

            entries: list[dict] = []
            for contact in whatsapp_state["contacts"]:
                number = contact.get("number", "").strip()
                if not number:
                    raise ValueError("Uno de los números está vacío.")
                message = contact.get("message", "").strip() if contact.get("custom_message") else global_message
                if not message:
                    raise ValueError(f"Falta mensaje para {number}.")
                media_source = (
                    contact.get("media_path") if contact.get("custom_media") else whatsapp_state.get("global_media")
                )
                media_url = None
                if media_source:
                    media_url, _ = _resolve_media(media_source)
                    if not media_url:
                        raise RuntimeError(f"No se pudo obtener URL para {number}.")
                entries.append({"number": number, "message": message, "media_url": media_url})

            enviar_mensajes_whatsapp(
                entries=entries,
                interval_seconds=interval,
                log_fn=log_fn,
                stop_control=stop_control,
            )
            mostrar_info("Envío finalizado.")
        except Exception as exc:
            mostrar_error(str(exc))
            if log_fn:
                log_fn(f"Error WhatsApp/Drive: {exc}")
        finally:
            stop_control.set_busy(False)
            unique_ids = list(dict.fromkeys([fid for fid in drive_file_ids if fid]))
            for fid in unique_ids:
                try:
                    delete_drive_file(fid, logs=log_fn)
                except Exception as exc:
                    if log_fn:
                        log_fn(f"No se pudo eliminar el archivo de Drive ({fid}): {exc}")

    btn_send.configure(command=lambda: threading.Thread(target=run_envio, daemon=True).start())

    return {
        "numbers_card": numbers_card,
        "media_card": media_card,
        "message_card": message_card,
    }
