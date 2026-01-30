import os
import customtkinter as ctk


def log_to_widget(txt_logs, msg):
    if txt_logs is None:
        return
    txt_logs.configure(state="normal")
    txt_logs.insert("end", msg + "\n")
    txt_logs.see("end")
    txt_logs.configure(state="disabled")


def log_seccion(log_fn, tabs, titulo):
    try:
        tabs.set("Actividad")
    except Exception:
        pass
    log_fn("")
    log_fn("========================================")
    log_fn(f"=== {titulo}")
    log_fn("========================================")


def limpiar_entry(entry):
    entry.delete(0, "end")
    entry.focus_set()


def alerta_busy(ventana):
    popup = ctk.CTkToplevel(ventana)
    popup.title("Proceso en ejecucion")
    popup.geometry("360x160")
    popup.resizable(False, False)
    popup.grab_set()
    lbl = ctk.CTkLabel(
        popup,
        text="Ya hay un proceso en ejecucion.\nEspera a que termine o presiona Detener.",
        font=ctk.CTkFont(size=12),
    )
    lbl.pack(padx=16, pady=(24, 12))
    btn_ok = ctk.CTkButton(popup, text="OK", command=popup.destroy, width=120)
    btn_ok.pack(pady=(0, 16))


def _open_output_dir(relative_path):
    folder = os.path.abspath(relative_path)
    if not os.path.exists(folder):
        os.makedirs(folder)
    os.startfile(folder)


def abrir_transcripciones():
    _open_output_dir("output")


def abrir_subtitulos():
    _open_output_dir("output")


def abrir_videos():
    _open_output_dir("output")


def abrir_audios():
    _open_output_dir("output")


def abrir_descargas():
    _open_output_dir("output")


def _es_dentro_output(path: str) -> bool:
    try:
        output_root = os.path.abspath("output")
        return os.path.commonpath([os.path.abspath(path), output_root]) == output_root
    except Exception:
        return False


def _renombrar_relacionados(old_base: str, new_base: str, log_fn=None):
    if not old_base or not new_base or old_base == new_base:
        return
    output_root = os.path.abspath("output")
    old_dir = os.path.join(output_root, old_base)
    new_dir = os.path.join(output_root, new_base)
    if os.path.isdir(old_dir) and not os.path.exists(new_dir):
        try:
            os.rename(old_dir, new_dir)
        except Exception as e:
            if log_fn:
                log_fn(f"No se pudo renombrar carpeta {old_dir}: {e}")


def renombrar_si_largo(path: str, log_fn=None):
    if not path:
        return None
    max_name = 80
    base = os.path.basename(path)
    if len(base) <= max_name:
        return path
    dirname = os.path.dirname(path)
    _stem, ext = os.path.splitext(base)
    in_output = _es_dentro_output(path)
    old_base = os.path.splitext(os.path.basename(path))[0]
    while len(os.path.basename(path)) > max_name:
        dialog = ctk.CTkInputDialog(
            text="El nombre es muy largo. Escribe un nombre mas corto:",
            title="Renombrar archivo",
        )
        nuevo = dialog.get_input()
        if not nuevo:
            return None
        nuevo = nuevo.strip()
        if not nuevo:
            continue
        if not nuevo.lower().endswith(ext.lower()):
            nuevo = nuevo + ext
        nuevo_path = os.path.join(dirname, nuevo)
        try:
            if os.path.exists(nuevo_path):
                if log_fn:
                    log_fn("Ese nombre ya existe. Usa otro.")
                continue
            os.rename(path, nuevo_path)
            path = nuevo_path
            if in_output:
                new_base = os.path.splitext(os.path.basename(path))[0]
                _renombrar_relacionados(old_base, new_base, log_fn=log_fn)
                old_base = new_base
        except Exception as e:
            if log_fn:
                log_fn(f"No se pudo renombrar: {e}")
            return None
    return path


def create_log_card(parent, title="Actividad", height=160, mirror_fn=None):
    card = ctk.CTkFrame(parent, corner_radius=12)
    card.grid_columnconfigure(0, weight=1)
    card.grid_rowconfigure(1, weight=1)

    lbl = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=15, weight="bold"))
    lbl.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

    txt_logs = ctk.CTkTextbox(card, height=height, corner_radius=8)
    txt_logs.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
    txt_logs.configure(state="disabled")

    def log_fn(msg):
        log_to_widget(txt_logs, msg)
        if mirror_fn:
            mirror_fn(msg)

    return card, txt_logs, log_fn


def create_log_panel(parent, title="Actividad", width=260, height=220, mirror_fn=None):
    card, txt_logs, log_fn = create_log_card(parent, title=title, height=height, mirror_fn=mirror_fn)
    card.configure(width=width)
    card.grid_propagate(False)
    return card, txt_logs, log_fn
