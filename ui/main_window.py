import os
import json
import re
import time
import threading
import customtkinter as ctk
import tkinter as tk
from tkinter import colorchooser
from PIL import Image, ImageTk, ImageDraw
from moviepy import VideoFileClip
import winsound
from core.extractor import extraer_audio
from core.workflow import procesar_corte_individual, procesar_srt, procesar_quemar_srt
from core.ai_tiktok import generar_descripcion_tiktok, generar_recomendaciones_clips
from core.youtube_downloader import descargar_audio_youtube, descargar_video_youtube_mp4
from core.utils import obtener_duracion_segundos, nombre_base_fuente
from core import stop_control


class SimpleVideoPlayer:
    def __init__(self, master, log_fn=None):
        self.master = master
        self.log_fn = log_fn
        self.label = tk.Label(master, bg="#000000", fg="#ffffff")
        self.label.pack(fill="both", expand=True)
        self.master.bind("<Configure>", self._on_resize)
        self.clip = None
        self.duration = 0.0
        self.fps = 25
        self.playing = False
        self.current_t = 0.0
        self._start_time = 0.0
        self._after_id = None
        self._photo = None
        self._target_size = None

    def show_placeholder(self, text):
        self.label.configure(text=text, image="")

    def load(self, path):
        self.stop()
        if self.clip:
            try:
                self.clip.close()
            except Exception:
                pass
        self.clip = None
        try:
            self.show_placeholder("Cargando vista previa...")
            self.clip = VideoFileClip(path, audio=False)
            self.duration = float(self.clip.duration or 0.0)
            self.fps = int(self.clip.fps or 25)
            self.current_t = 0.0
            self.master.update_idletasks()
            self.label.update_idletasks()
            self._target_size = (
                max(2, self.label.winfo_width()),
                max(2, self.label.winfo_height()),
            )
            self.master.after(50, lambda: self._render_frame(self.current_t))
            self.master.after(200, lambda: self._render_frame(self.current_t))
            self.master.after(600, lambda: self._render_frame(self.current_t))
        except Exception as e:
            if self.log_fn:
                self.log_fn(f"Error cargando preview: {e}")
            self.show_placeholder("No se pudo cargar la vista previa.")

    def _render_frame(self, t):
        if not self.clip:
            return
        try:
            t = max(0.0, min(float(t), max(0.0, self.duration - 0.001)))
            frame = self.clip.get_frame(t)
            image = Image.fromarray(frame)
            if self._target_size:
                w, h = self._target_size
            else:
                w = max(2, self.label.winfo_width())
                h = max(2, self.label.winfo_height())
            img_w, img_h = image.size
            scale = min(w / img_w, h / img_h)
            new_w = max(1, int(img_w * scale))
            new_h = max(1, int(img_h * scale))
            image = image.resize((new_w, new_h), Image.LANCZOS)
            self._photo = ImageTk.PhotoImage(image)
            self.label.configure(image=self._photo, text="")
        except Exception as e:
            if self.log_fn:
                self.log_fn(f"Preview error: {e}")
            self.label.configure(text="No se pudo renderizar la vista previa.", image="")

    def play(self):
        if not self.clip or self.playing:
            return
        self.playing = True
        self._start_time = time.perf_counter() - self.current_t
        self._schedule_next()

    def pause(self):
        self.playing = False
        if self._after_id:
            self.master.after_cancel(self._after_id)
            self._after_id = None

    def stop(self):
        self.pause()
        self.current_t = 0.0
        if self.clip:
            self._render_frame(self.current_t)

    def seek(self, t):
        if not self.clip:
            return
        self.current_t = max(0.0, min(float(t), self.duration))
        if self.playing:
            self._start_time = time.perf_counter() - self.current_t
        self._render_frame(self.current_t)

    def _schedule_next(self):
        if not self.playing or not self.clip:
            return
        self.current_t = time.perf_counter() - self._start_time
        if self.current_t >= self.duration:
            self.stop()
            return
        self._render_frame(self.current_t)
        delay = max(15, int(1000 / max(1, self.fps)))
        self._after_id = self.master.after(delay, self._schedule_next)

    def _on_resize(self, _event):
        self._target_size = (
            max(2, self.label.winfo_width()),
            max(2, self.label.winfo_height()),
        )
        if self.clip and not self.playing:
            self._render_frame(self.current_t)


def iniciar_app(procesar_video_fn):
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    ventana = ctk.CTk()
    ventana.title("Transcriptor de Video")
    ventana.geometry("980x680")
    ventana.minsize(820, 600)
    ventana.state("zoomed")

    root = ctk.CTkFrame(master=ventana, corner_radius=14)
    root.pack(fill="both", expand=True, padx=24, pady=24)
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)

    estado = {"path": None, "es_audio": False, "fondo_path": None}
    rango = {"duracion": 0.0}
    rango_ind = {"duracion": 0.0}

    def log(msg):
        txt_logs.configure(state="normal")
        txt_logs.insert("end", msg + "\n")
        txt_logs.see("end")
        txt_logs.configure(state="disabled")

    def beep_fin():
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

    def alerta_busy():
        popup = ctk.CTkToplevel(ventana)
        popup.title("Proceso en ejecucion")
        popup.geometry("360x160")
        popup.resizable(False, False)
        popup.grab_set()
        lbl = ctk.CTkLabel(
            popup,
            text="Ya hay un proceso en ejecucion.\nEspera a que termine o presiona Detener.",
            font=ctk.CTkFont(size=12)
        )
        lbl.pack(padx=16, pady=(24, 12))
        btn_ok = ctk.CTkButton(popup, text="OK", command=popup.destroy, width=120)
        btn_ok.pack(pady=(0, 16))

    def _es_dentro_output(path: str) -> bool:
        try:
            output_root = os.path.abspath("output")
            return os.path.commonpath([os.path.abspath(path), output_root]) == output_root
        except Exception:
            return False

    def _renombrar_relacionados(old_base: str, new_base: str):
        if not old_base or not new_base or old_base == new_base:
            return
        output_root = os.path.abspath("output")
        targets = [
            os.path.join(output_root, "videos"),
            os.path.join(output_root, "audios"),
            os.path.join(output_root, "subtitulos"),
            os.path.join(output_root, "downloads"),
        ]
        for base_dir in targets:
            if not os.path.exists(base_dir):
                continue
            old_dir = os.path.join(base_dir, old_base)
            new_dir = os.path.join(base_dir, new_base)
            if os.path.isdir(old_dir) and not os.path.exists(new_dir):
                try:
                    os.rename(old_dir, new_dir)
                except Exception as e:
                    log(f"No se pudo renombrar carpeta {old_dir}: {e}")
                    continue
            # Renombrar archivos que contengan el nombre anterior
            for root_dir, _dirs, files in os.walk(base_dir):
                for fname in files:
                    if old_base not in fname:
                        continue
                    src = os.path.join(root_dir, fname)
                    dst_name = fname.replace(old_base, new_base)
                    dst = os.path.join(root_dir, dst_name)
                    if src == dst:
                        continue
                    if os.path.exists(dst):
                        continue
                    try:
                        os.rename(src, dst)
                    except Exception as e:
                        log(f"No se pudo renombrar {src}: {e}")

    def _renombrar_si_largo(path: str):
        if not path:
            return None
        max_name = 80
        base = os.path.basename(path)
        if len(base) <= max_name:
            return path
        dirname = os.path.dirname(path)
        stem, ext = os.path.splitext(base)
        in_output = _es_dentro_output(path)
        old_base = os.path.splitext(os.path.basename(path))[0]
        while len(os.path.basename(path)) > max_name:
            dialog = ctk.CTkInputDialog(
                text="El nombre es muy largo. Escribe un nombre mas corto:",
                title="Renombrar archivo"
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
                    log("Ese nombre ya existe. Usa otro.")
                    continue
                os.rename(path, nuevo_path)
                path = nuevo_path
                if in_output:
                    new_base = os.path.splitext(os.path.basename(path))[0]
                    _renombrar_relacionados(old_base, new_base)
                    old_base = new_base
            except Exception as e:
                log(f"No se pudo renombrar: {e}")
                return None
        return path

    def log_seccion(titulo):
        tabs.set("Actividad")
        log("")
        log("========================================")
        log(f"=== {titulo}")
        log("========================================")

    def limpiar_entry(entry):
        entry.delete(0, "end")
        entry.focus_set()

    def abrir_transcripciones():
        folder = os.path.abspath("output/transcripciones")
        if not os.path.exists(folder):
            os.makedirs(folder)
        os.startfile(folder)

    def abrir_subtitulos():
        folder = os.path.abspath(os.path.join("output", "subtitulos"))
        if not os.path.exists(folder):
            os.makedirs(folder)
        os.startfile(folder)

    def abrir_videos():
        folder = os.path.abspath("output/videos")
        if not os.path.exists(folder):
            os.makedirs(folder)
        os.startfile(folder)

    def abrir_audios():
        folder = os.path.abspath("output/audios")
        if not os.path.exists(folder):
            os.makedirs(folder)
        os.startfile(folder)

    def abrir_descargas():
        folder = os.path.abspath(os.path.join("output", "downloads"))
        if not os.path.exists(folder):
            os.makedirs(folder)
        os.startfile(folder)

    def eliminar_audios(log_fn=None):
        folder = os.path.abspath("output/audios")
        if not os.path.exists(folder):
            return
        count = 0
        for root_dir, _dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith((".mp3", ".wav", ".webm", ".mp4")):
                    try:
                        os.remove(os.path.join(root_dir, f))
                        count += 1
                    except Exception as e:
                        if log_fn:
                            log_fn(f"No se pudo borrar {f}: {e}")
        if log_fn:
            log_fn(f"{count} audios eliminados de output/audios/")

    def leer_minutos():
        try:
            valor = float(entry_minutos.get().strip().replace(",", "."))
            return valor if valor > 0 else 5
        except Exception:
            return 5

    def leer_rango_minutos():
        if rango["duracion"] <= 0:
            return None, None
        inicio = slider_inicio.get()
        fin = slider_fin.get()
        return inicio / 60.0, fin / 60.0

    def iniciar_proceso():
        if not estado["path"]:
            log("Selecciona un video primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("Corte")
        minutos = leer_minutos()
        inicio_min, fin_min = leer_rango_minutos()
        vertical = vertical_var.get()
        orden = orden_var.get()
        try:
            recorte_total = float(entry_recorte_total.get().strip().replace(",", "."))
        except Exception:
            recorte_total = 0.12
        recorte_top = recorte_total
        recorte_bottom = recorte_total
        fondo_path = estado["fondo_path"] if fondo_var.get() else None
        fondo_estilo = fondo_estilo_var.get().lower()
        try:
            fondo_escala = float(entry_fondo_escala.get().strip().replace(",", "."))
        except Exception:
            fondo_escala = 0.92
        def run_corte():
            try:
                procesar_video_fn(
                    estado["path"],
                    False,
                    False,
                    minutos,
                    inicio_min,
                    fin_min,
                    True,
                    vertical,
                    orden,
                    recorte_top,
                    recorte_bottom,
                    False,
                    fondo_path,
                    fondo_estilo,
                    fondo_escala,
                    True
                )
                log("Finalizado proceso de corte.")
                log("Fin de la automatizacion.")
                beep_fin()
            except Exception as e:
                log(f"Error en corte: {e}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run_corte, daemon=True).start()

    def format_time(seconds):
        seconds = max(0, float(seconds))
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def actualizar_etiquetas_rango():
        inicio = slider_inicio.get()
        fin = slider_fin.get()
        lbl_inicio_val.configure(text=format_time(inicio))
        lbl_fin_val.configure(text=format_time(fin))
        lbl_duracion_val.configure(text=format_time(rango["duracion"]))

    def actualizar_etiquetas_rango_ind():
        inicio = slider_inicio_ind.get()
        fin = slider_fin_ind.get()
        lbl_inicio_val_ind.configure(text=format_time(inicio))
        lbl_fin_val_ind.configure(text=format_time(fin))
        lbl_duracion_val_ind.configure(text=format_time(rango_ind["duracion"]))

    def on_inicio_change(value):
        if value > slider_fin.get():
            slider_fin.set(value)
        actualizar_etiquetas_rango()

    def on_fin_change(value):
        if value < slider_inicio.get():
            slider_inicio.set(value)
        actualizar_etiquetas_rango()

    def on_inicio_ind_change(value):
        if value > slider_fin_ind.get():
            slider_fin_ind.set(value)
        actualizar_etiquetas_rango_ind()

    def on_fin_ind_change(value):
        if value < slider_inicio_ind.get():
            slider_inicio_ind.set(value)
        actualizar_etiquetas_rango_ind()

    def set_preview_enabled(enabled: bool):
        estado["es_audio"] = False
        state = "normal" if enabled else "disabled"
        slider_inicio.configure(state=state)
        slider_fin.configure(state=state)
        if not enabled:
            slider_inicio.set(0)
            slider_fin.set(0)
            rango["duracion"] = 0.0
            actualizar_etiquetas_rango()
            try:
                video_player.stop()
            except Exception:
                pass

    def cargar_video_preview(path):
        log("Cargando vista previa...")
        video_player.load(path)
        try:
            duracion = obtener_duracion_segundos(path)
        except Exception:
            duracion = 0.0
        rango["duracion"] = max(0.0, duracion)
        slider_inicio.configure(from_=0, to=rango["duracion"])
        slider_fin.configure(from_=0, to=rango["duracion"])
        slider_inicio.set(0)
        slider_fin.set(rango["duracion"])
        actualizar_etiquetas_rango()

    def cargar_rango_individual(path):
        try:
            duracion = obtener_duracion_segundos(path)
        except Exception:
            duracion = 0.0
        rango_ind["duracion"] = max(0.0, duracion)
        slider_inicio_ind.configure(from_=0, to=rango_ind["duracion"])
        slider_fin_ind.configure(from_=0, to=rango_ind["duracion"])
        slider_inicio_ind.set(0)
        slider_fin_ind.set(rango_ind["duracion"])
        actualizar_etiquetas_rango_ind()

    header = ctk.CTkFrame(root, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
    header.grid_columnconfigure(0, weight=1)

    title = ctk.CTkLabel(
        header,
        text="Transcriptor de Video",
        font=ctk.CTkFont(size=26, weight="bold")
    )
    title.grid(row=0, column=0, sticky="w")

    subtitle = ctk.CTkLabel(
        header,
        text="Divide por minutos y marca el rango con sliders.",
        font=ctk.CTkFont(size=13)
    )
    subtitle.grid(row=1, column=0, sticky="w", pady=(2, 0))

    tabs = ctk.CTkTabview(root, corner_radius=12)
    tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=(6, 10))
    tabs.add("Corte")
    tabs.add("Subtitulos")
    tabs.add("IA generadores")
    tabs.add("Descargas")
    tabs.add("Actividad")

    tab_corte_main = tabs.tab("Corte")
    tab_sub_main = tabs.tab("Subtitulos")
    tab_ia_main = tabs.tab("IA generadores")
    tab_desc_main = tabs.tab("Descargas")
    tab_act = tabs.tab("Actividad")

    corte_tabs = ctk.CTkTabview(tab_corte_main, corner_radius=10)
    corte_tabs.pack(fill="both", expand=True, padx=6, pady=6)
    corte_tabs.add("Corte editado")
    corte_tabs.add("Corte individual")

    sub_tabs = ctk.CTkTabview(tab_sub_main, corner_radius=10)
    sub_tabs.pack(fill="both", expand=True, padx=6, pady=6)
    sub_tabs.add("Generar subtitulos")
    sub_tabs.add("Subtitular video")

    ia_tabs = ctk.CTkTabview(tab_ia_main, corner_radius=10)
    ia_tabs.pack(fill="both", expand=True, padx=6, pady=6)
    ia_tabs.add("IA Clips")
    ia_tabs.add("IA TikTok")

    desc_tabs = ctk.CTkTabview(tab_desc_main, corner_radius=10)
    desc_tabs.pack(fill="both", expand=True, padx=6, pady=6)
    desc_tabs.add("Audio MP3")
    desc_tabs.add("YouTube MP3")
    desc_tabs.add("YouTube MP4")

    tab_corte = corte_tabs.tab("Corte editado")
    tab_ind = corte_tabs.tab("Corte individual")
    tab_srt = sub_tabs.tab("Generar subtitulos")
    tab_sub = sub_tabs.tab("Subtitular video")
    tab_clips = ia_tabs.tab("IA Clips")
    tab_ai = ia_tabs.tab("IA TikTok")
    tab_audio = desc_tabs.tab("Audio MP3")
    tab_youtube = desc_tabs.tab("YouTube MP3")
    tab_youtube_mp4 = desc_tabs.tab("YouTube MP4")
    tab_corte.grid_columnconfigure(0, weight=1)
    tab_corte.grid_rowconfigure(0, weight=1)

    corte_scroll = ctk.CTkScrollableFrame(tab_corte, corner_radius=0)
    corte_scroll.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
    corte_scroll.grid_columnconfigure(0, weight=1)

    # --- Corte: configuracion + acciones ---
    top = ctk.CTkFrame(corte_scroll, corner_radius=12)
    top.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 12))
    top.grid_columnconfigure(0, weight=1)
    top.grid_columnconfigure(1, weight=1)

    config = ctk.CTkFrame(top, corner_radius=10)
    config.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    config.grid_columnconfigure(0, weight=1)

    lbl_conf = ctk.CTkLabel(config, text="Configuracion", font=ctk.CTkFont(size=15, weight="bold"))
    lbl_conf.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

    row_min = ctk.CTkFrame(config, fg_color="transparent")
    row_min.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))
    row_min.grid_columnconfigure(1, weight=1)

    lbl_minutos = ctk.CTkLabel(row_min, text="Minutos por parte", font=ctk.CTkFont(size=13))
    lbl_minutos.grid(row=0, column=0, sticky="w")

    entry_minutos = ctk.CTkEntry(row_min, width=120)
    entry_minutos.insert(0, "5")
    entry_minutos.grid(row=0, column=1, sticky="e")

    btn_clear_min = ctk.CTkButton(
        row_min,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_minutos)
    )
    btn_clear_min.grid(row=0, column=2, sticky="e", padx=(8, 0))

    hint = ctk.CTkLabel(config, text="Puedes usar decimales. Ej: 2.5", font=ctk.CTkFont(size=12), text_color="#9aa4b2")
    hint.grid(row=2, column=0, sticky="w", padx=14, pady=(0, 12))

    vertical_var = ctk.BooleanVar(value=False)
    chk_vertical = ctk.CTkCheckBox(
        config,
        text="Generar formato TikTok (9:16, izquierda arriba / derecha abajo)",
        variable=vertical_var
    )
    chk_vertical.grid(row=3, column=0, sticky="w", padx=14, pady=(0, 12))

    orden_var = ctk.StringVar(value="LR")
    lbl_orden = ctk.CTkLabel(config, text="Orden vertical:", font=ctk.CTkFont(size=13))
    lbl_orden.grid(row=4, column=0, sticky="w", padx=14, pady=(0, 6))

    rb_lr = ctk.CTkRadioButton(
        config,
        text="Izquierda arriba / Derecha abajo",
        variable=orden_var,
        value="LR"
    )
    rb_lr.grid(row=5, column=0, sticky="w", padx=14, pady=(0, 4))

    rb_rl = ctk.CTkRadioButton(
        config,
        text="Derecha arriba / Izquierda abajo",
        variable=orden_var,
        value="RL"
    )
    rb_rl.grid(row=6, column=0, sticky="w", padx=14, pady=(0, 12))

    rb_alt = ctk.CTkRadioButton(
        config,
        text="Intercalado (alterna por cada parte)",
        variable=orden_var,
        value="ALT"
    )
    rb_alt.grid(row=7, column=0, sticky="w", padx=14, pady=(0, 12))

    fondo_var = ctk.BooleanVar(value=False)
    chk_fondo = ctk.CTkCheckBox(
        config,
        text="Aplicar imagen de fondo",
        variable=fondo_var
    )
    chk_fondo.grid(row=9, column=0, sticky="w", padx=14, pady=(0, 8))

    row_fondo = ctk.CTkFrame(config, fg_color="transparent")
    row_fondo.grid(row=10, column=0, sticky="ew", padx=14, pady=(0, 10))
    row_fondo.grid_columnconfigure(1, weight=1)

    def seleccionar_fondo():
        from ui.dialogs import seleccionar_imagen
        img = seleccionar_imagen()
        if img:
            estado["fondo_path"] = img
            lbl_fondo.configure(text=os.path.basename(img))

    btn_fondo = ctk.CTkButton(
        row_fondo,
        text="Seleccionar imagen",
        command=seleccionar_fondo,
        height=28,
        width=150
    )
    btn_fondo.grid(row=0, column=0, sticky="w")

    lbl_fondo = ctk.CTkLabel(row_fondo, text="(sin imagen)", font=ctk.CTkFont(size=12))
    lbl_fondo.grid(row=0, column=1, sticky="w", padx=(8, 0))

    fondo_estilo_var = ctk.StringVar(value="Fill")
    lbl_estilo = ctk.CTkLabel(config, text="Estilo de fondo:", font=ctk.CTkFont(size=12))
    lbl_estilo.grid(row=11, column=0, sticky="w", padx=14, pady=(0, 6))

    opt_estilo = ctk.CTkOptionMenu(
        config,
        values=["Fill", "Fit", "Blur"],
        variable=fondo_estilo_var
    )
    opt_estilo.grid(row=12, column=0, sticky="w", padx=14, pady=(0, 12))

    row_fondo_escala = ctk.CTkFrame(config, fg_color="transparent")
    row_fondo_escala.grid(row=13, column=0, sticky="ew", padx=14, pady=(0, 10))
    row_fondo_escala.grid_columnconfigure(1, weight=1)

    lbl_fondo_escala = ctk.CTkLabel(row_fondo_escala, text="Tamaño video sobre fondo", font=ctk.CTkFont(size=12))
    lbl_fondo_escala.grid(row=0, column=0, sticky="w")

    entry_fondo_escala = ctk.CTkEntry(row_fondo_escala, width=80)
    entry_fondo_escala.insert(0, "0.92")
    entry_fondo_escala.grid(row=0, column=1, sticky="w", padx=(6, 0))

    btn_clear_fondo = ctk.CTkButton(
        row_fondo_escala,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_fondo_escala)
    )
    btn_clear_fondo.grid(row=0, column=2, sticky="e", padx=(8, 0))

    row_recorte = ctk.CTkFrame(config, fg_color="transparent")
    row_recorte.grid(row=14, column=0, sticky="ew", padx=14, pady=(0, 10))
    row_recorte.grid_columnconfigure(1, weight=1)

    lbl_recorte = ctk.CTkLabel(row_recorte, text="Recorte total", font=ctk.CTkFont(size=12))
    lbl_recorte.grid(row=0, column=0, sticky="w")

    entry_recorte_total = ctk.CTkEntry(row_recorte, width=80)
    entry_recorte_total.insert(0, "0.12")
    entry_recorte_total.grid(row=0, column=1, sticky="w", padx=(6, 0))

    btn_clear_recorte = ctk.CTkButton(
        row_recorte,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_recorte_total)
    )
    btn_clear_recorte.grid(row=0, column=2, sticky="e", padx=(8, 0))

    hint_recorte = ctk.CTkLabel(
        config,
        text="Ajusta si queda espacio negro. Valores 0.05 - 0.20",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2"
    )
    hint_recorte.grid(row=15, column=0, sticky="w", padx=14, pady=(0, 12))

    actions = ctk.CTkFrame(top, corner_radius=10)
    actions.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
    actions.grid_columnconfigure(0, weight=1)

    lbl_acc = ctk.CTkLabel(actions, text="Seleccion y ejecucion", font=ctk.CTkFont(size=15, weight="bold"))
    lbl_acc.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

    def on_click_local():
        from ui.dialogs import seleccionar_video
        video = seleccionar_video()
        if video:
            estado["path"] = video
            estado["es_audio"] = False
            set_preview_enabled(True)
            cargar_video_preview(video)
            log(f"Video seleccionado: {video}")

    btn_local = ctk.CTkButton(actions, text="Seleccionar Video Local", command=on_click_local, height=44)
    btn_local.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))

    btn_iniciar = ctk.CTkButton(actions, text="Cortar", command=iniciar_proceso, height=46)
    btn_iniciar.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 8))

    btn_abrir_videos = ctk.CTkButton(actions, text="Abrir Carpeta de Videos", command=abrir_videos, height=40)
    btn_abrir_videos.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 12))

    # --- Corte: preview ---
    preview_card = ctk.CTkFrame(corte_scroll, corner_radius=12)
    preview_card.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
    preview_card.grid_columnconfigure(0, weight=1)
    preview_card.grid_rowconfigure(1, weight=1)

    lbl_preview = ctk.CTkLabel(preview_card, text="Vista previa", font=ctk.CTkFont(size=15, weight="bold"))
    lbl_preview.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

    video_container = ctk.CTkFrame(preview_card, corner_radius=8)
    video_container.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 10))
    video_container.configure(height=300)
    video_container.grid_propagate(False)

    video_host = tk.Frame(video_container, bg="#000000")
    video_host.pack(fill="both", expand=True)
    video_host.pack_propagate(False)

    video_player = SimpleVideoPlayer(video_host, log_fn=log)

    controls = ctk.CTkFrame(preview_card, fg_color="transparent")
    controls.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
    controls.grid_columnconfigure(1, weight=1)

    btn_play = ctk.CTkButton(controls, text="Play", width=80, height=28, command=lambda: video_player.play())
    btn_play.grid(row=0, column=0, sticky="w")

    btn_pause = ctk.CTkButton(controls, text="Pause", width=80, height=28, command=lambda: video_player.pause())
    btn_pause.grid(row=0, column=1, sticky="w", padx=(8, 0))

    range_card = ctk.CTkFrame(preview_card, fg_color="transparent")
    range_card.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))
    range_card.grid_columnconfigure(1, weight=1)

    lbl_inicio = ctk.CTkLabel(range_card, text="Inicio", font=ctk.CTkFont(size=12))
    lbl_inicio.grid(row=0, column=0, sticky="w")
    lbl_inicio_val = ctk.CTkLabel(range_card, text="00:00", font=ctk.CTkFont(size=12))
    lbl_inicio_val.grid(row=0, column=2, sticky="e")

    slider_inicio = ctk.CTkSlider(range_card, from_=0, to=1, command=on_inicio_change)
    slider_inicio.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 6))

    lbl_fin = ctk.CTkLabel(range_card, text="Fin", font=ctk.CTkFont(size=12))
    lbl_fin.grid(row=2, column=0, sticky="w")
    lbl_fin_val = ctk.CTkLabel(range_card, text="00:00", font=ctk.CTkFont(size=12))
    lbl_fin_val.grid(row=2, column=2, sticky="e")

    slider_fin = ctk.CTkSlider(range_card, from_=0, to=1, command=on_fin_change)
    slider_fin.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 6))

    lbl_duracion = ctk.CTkLabel(range_card, text="Duracion", font=ctk.CTkFont(size=12))
    lbl_duracion.grid(row=4, column=0, sticky="w")
    lbl_duracion_val = ctk.CTkLabel(range_card, text="00:00", font=ctk.CTkFont(size=12))
    lbl_duracion_val.grid(row=4, column=2, sticky="e")

    # --- Corte individual ---
    tab_ind.grid_columnconfigure(0, weight=1)
    tab_ind.grid_rowconfigure(0, weight=1)

    ind_scroll = ctk.CTkScrollableFrame(tab_ind, corner_radius=0)
    ind_scroll.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
    ind_scroll.grid_columnconfigure(0, weight=1)

    ind_card = ctk.CTkFrame(ind_scroll, corner_radius=12)
    ind_card.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    ind_card.grid_columnconfigure(0, weight=1)

    lbl_ind_title = ctk.CTkLabel(
        ind_card,
        text="Corte individual vertical (9:16)",
        font=ctk.CTkFont(size=18, weight="bold")
    )
    lbl_ind_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_ind_hint = ctk.CTkLabel(
        ind_card,
        text="Elige el punto de recorte (centro, izquierda o derecha) y corta por minutos.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2"
    )
    lbl_ind_hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    ind_select = ctk.CTkFrame(ind_card, fg_color="transparent")
    ind_select.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
    ind_select.grid_columnconfigure(1, weight=1)

    def on_click_individual_video():
        from ui.dialogs import seleccionar_video
        video = seleccionar_video()
        if video:
            video = _renombrar_si_largo(video)
            if not video:
                return
            estado["path"] = video
            estado["es_audio"] = False
            set_preview_enabled(True)
            cargar_video_preview(video)
            cargar_rango_individual(video)
            log(f"Video seleccionado: {video}")

    btn_ind_video = ctk.CTkButton(
        ind_select,
        text="Seleccionar Video",
        command=on_click_individual_video,
        height=40
    )
    btn_ind_video.grid(row=0, column=0, sticky="w")

    lbl_ind_file = ctk.CTkLabel(
        ind_select,
        text="(usa el mismo rango de la pestaña Corte)",
        font=ctk.CTkFont(size=12)
    )
    lbl_ind_file.grid(row=0, column=1, sticky="w", padx=(12, 0))

    ind_min_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    ind_min_row.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
    ind_min_row.grid_columnconfigure(1, weight=1)

    lbl_ind_min = ctk.CTkLabel(ind_min_row, text="Minutos por parte", font=ctk.CTkFont(size=13))
    lbl_ind_min.grid(row=0, column=0, sticky="w")

    entry_ind_min = ctk.CTkEntry(ind_min_row, width=120)
    entry_ind_min.insert(0, "5")
    entry_ind_min.grid(row=0, column=1, sticky="e")

    btn_clear_ind_min = ctk.CTkButton(
        ind_min_row,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_ind_min)
    )
    btn_clear_ind_min.grid(row=0, column=2, sticky="e", padx=(8, 0))

    pos_var = ctk.StringVar(value="C")
    lbl_pos = ctk.CTkLabel(ind_card, text="Posicion de recorte:", font=ctk.CTkFont(size=13))
    lbl_pos.grid(row=4, column=0, sticky="w", padx=16, pady=(0, 6))

    rb_pos_c = ctk.CTkRadioButton(ind_card, text="Centro", variable=pos_var, value="C")
    rb_pos_c.grid(row=5, column=0, sticky="w", padx=16, pady=(0, 4))
    rb_pos_l = ctk.CTkRadioButton(ind_card, text="Izquierda", variable=pos_var, value="L")
    rb_pos_l.grid(row=6, column=0, sticky="w", padx=16, pady=(0, 4))
    rb_pos_r = ctk.CTkRadioButton(ind_card, text="Derecha", variable=pos_var, value="R")
    rb_pos_r.grid(row=7, column=0, sticky="w", padx=16, pady=(0, 12))

    zoom_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    zoom_row.grid(row=8, column=0, sticky="ew", padx=16, pady=(0, 10))
    zoom_row.grid_columnconfigure(1, weight=1)

    lbl_zoom = ctk.CTkLabel(zoom_row, text="Zoom (alejar/acercar)", font=ctk.CTkFont(size=12))
    lbl_zoom.grid(row=0, column=0, sticky="w")

    entry_zoom = ctk.CTkEntry(zoom_row, width=80)
    entry_zoom.insert(0, "1.0")
    entry_zoom.grid(row=0, column=1, sticky="w", padx=(6, 0))

    btn_clear_zoom = ctk.CTkButton(
        zoom_row,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_zoom)
    )
    btn_clear_zoom.grid(row=0, column=2, sticky="e", padx=(8, 0))

    zoom_slider_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    zoom_slider_row.grid(row=9, column=0, sticky="ew", padx=16, pady=(0, 12))
    zoom_slider_row.grid_columnconfigure(1, weight=1)

    lbl_zoom_min = ctk.CTkLabel(zoom_slider_row, text="0.7", font=ctk.CTkFont(size=11))
    lbl_zoom_min.grid(row=0, column=0, sticky="w")

    lbl_zoom_val = ctk.CTkLabel(zoom_slider_row, text="1.00", font=ctk.CTkFont(size=11))
    lbl_zoom_val.grid(row=0, column=2, sticky="e")

    def on_zoom_change(value):
        try:
            v = float(value)
        except Exception:
            v = 1.0
        lbl_zoom_val.configure(text=f"{v:.2f}")
        entry_zoom.delete(0, "end")
        entry_zoom.insert(0, f"{v:.2f}")

    slider_zoom = ctk.CTkSlider(zoom_slider_row, from_=0.7, to=1.3, command=on_zoom_change)
    slider_zoom.set(1.0)
    slider_zoom.grid(row=0, column=1, sticky="ew", padx=(8, 8))

    lbl_zoom_max = ctk.CTkLabel(zoom_slider_row, text="1.3", font=ctk.CTkFont(size=11))
    lbl_zoom_max.grid(row=0, column=3, sticky="e")

    color_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    color_row.grid(row=10, column=0, sticky="ew", padx=16, pady=(0, 12))
    color_row.grid_columnconfigure(1, weight=1)

    lbl_color = ctk.CTkLabel(color_row, text="Color de relleno (hex)", font=ctk.CTkFont(size=12))
    lbl_color.grid(row=0, column=0, sticky="w")

    entry_color = ctk.CTkEntry(color_row, width=120)
    entry_color.insert(0, "#000000")
    entry_color.grid(row=0, column=1, sticky="w", padx=(6, 0))

    def elegir_color():
        color = colorchooser.askcolor(title="Seleccionar color de relleno")
        if color and color[1]:
            entry_color.delete(0, "end")
            entry_color.insert(0, color[1])

    btn_pick_color = ctk.CTkButton(
        color_row,
        text="Elegir",
        width=80,
        height=28,
        command=elegir_color
    )
    btn_pick_color.grid(row=0, column=2, sticky="e", padx=(8, 0))

    btn_clear_color = ctk.CTkButton(
        color_row,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_color)
    )
    btn_clear_color.grid(row=0, column=3, sticky="e", padx=(8, 0))

    motion_var = ctk.BooleanVar(value=False)
    chk_motion = ctk.CTkCheckBox(
        ind_card,
        text="Zoom in/out cada 30s",
        variable=motion_var
    )
    chk_motion.grid(row=11, column=0, sticky="w", padx=16, pady=(0, 8))

    motion_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    motion_row.grid(row=12, column=0, sticky="ew", padx=16, pady=(0, 12))
    motion_row.grid_columnconfigure(1, weight=1)

    lbl_motion = ctk.CTkLabel(motion_row, text="Intensidad zoom", font=ctk.CTkFont(size=12))
    lbl_motion.grid(row=0, column=0, sticky="w")

    entry_motion = ctk.CTkEntry(motion_row, width=80)
    entry_motion.insert(0, "0.08")
    entry_motion.grid(row=0, column=1, sticky="w", padx=(6, 0))

    btn_clear_motion = ctk.CTkButton(
        motion_row,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_motion)
    )
    btn_clear_motion.grid(row=0, column=2, sticky="e", padx=(8, 0))

    motion_period_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    motion_period_row.grid(row=13, column=0, sticky="ew", padx=16, pady=(0, 12))
    motion_period_row.grid_columnconfigure(1, weight=1)

    lbl_motion_period = ctk.CTkLabel(motion_period_row, text="Ciclo (seg)", font=ctk.CTkFont(size=12))
    lbl_motion_period.grid(row=0, column=0, sticky="w")

    entry_motion_period = ctk.CTkEntry(motion_period_row, width=80)
    entry_motion_period.insert(0, "30")
    entry_motion_period.grid(row=0, column=1, sticky="w", padx=(6, 0))

    outro_var = ctk.BooleanVar(value=False)
    chk_outro = ctk.CTkCheckBox(
        ind_card,
        text="Agregar tarjeta final (imagen + texto)",
        variable=outro_var
    )
    chk_outro.grid(row=14, column=0, sticky="w", padx=16, pady=(0, 8))

    outro_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    outro_row.grid(row=15, column=0, sticky="ew", padx=16, pady=(0, 12))
    outro_row.grid_columnconfigure(1, weight=1)

    outro_state = {"image": None}

    def on_click_outro_image():
        from ui.dialogs import seleccionar_imagen
        img = seleccionar_imagen()
        if img:
            outro_state["image"] = img
            lbl_outro_img.configure(text=os.path.basename(img))
            log(f"Imagen outro: {img}")

    btn_outro_img = ctk.CTkButton(
        outro_row,
        text="Seleccionar imagen",
        command=on_click_outro_image,
        height=28,
        width=150
    )
    btn_outro_img.grid(row=0, column=0, sticky="w")

    lbl_outro_img = ctk.CTkLabel(outro_row, text="(sin imagen)", font=ctk.CTkFont(size=12))
    lbl_outro_img.grid(row=0, column=1, sticky="w", padx=(8, 0))

    outro_text_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    outro_text_row.grid(row=16, column=0, sticky="ew", padx=16, pady=(0, 12))
    outro_text_row.grid_columnconfigure(1, weight=1)

    lbl_outro_text = ctk.CTkLabel(outro_text_row, text="Texto final", font=ctk.CTkFont(size=12))
    lbl_outro_text.grid(row=0, column=0, sticky="w")

    entry_outro_text = ctk.CTkEntry(outro_text_row)
    entry_outro_text.grid(row=0, column=1, sticky="ew", padx=(8, 0))

    outro_conf_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    outro_conf_row.grid(row=17, column=0, sticky="ew", padx=16, pady=(0, 12))
    outro_conf_row.grid_columnconfigure(1, weight=1)

    lbl_outro_secs = ctk.CTkLabel(outro_conf_row, text="Duracion (seg)", font=ctk.CTkFont(size=12))
    lbl_outro_secs.grid(row=0, column=0, sticky="w")

    entry_outro_secs = ctk.CTkEntry(outro_conf_row, width=80)
    entry_outro_secs.insert(0, "3")
    entry_outro_secs.grid(row=0, column=1, sticky="w", padx=(8, 0))

    lbl_outro_font = ctk.CTkLabel(outro_conf_row, text="Tamano texto", font=ctk.CTkFont(size=12))
    lbl_outro_font.grid(row=1, column=0, sticky="w", pady=(8, 0))

    entry_outro_font = ctk.CTkEntry(outro_conf_row, width=80)
    entry_outro_font.insert(0, "54")
    entry_outro_font.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

    outro_color_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    outro_color_row.grid(row=18, column=0, sticky="ew", padx=16, pady=(0, 12))
    outro_color_row.grid_columnconfigure(1, weight=1)

    lbl_outro_color = ctk.CTkLabel(outro_color_row, text="Color texto (hex)", font=ctk.CTkFont(size=12))
    lbl_outro_color.grid(row=0, column=0, sticky="w")

    entry_outro_color = ctk.CTkEntry(outro_color_row, width=120)
    entry_outro_color.insert(0, "#FFFFFF")
    entry_outro_color.grid(row=0, column=1, sticky="w", padx=(6, 0))

    range_ind_card = ctk.CTkFrame(ind_card, fg_color="transparent")
    range_ind_card.grid(row=19, column=0, sticky="ew", padx=16, pady=(0, 14))
    range_ind_card.grid_columnconfigure(1, weight=1)

    lbl_inicio_ind = ctk.CTkLabel(range_ind_card, text="Inicio", font=ctk.CTkFont(size=12))
    lbl_inicio_ind.grid(row=0, column=0, sticky="w")
    lbl_inicio_val_ind = ctk.CTkLabel(range_ind_card, text="00:00", font=ctk.CTkFont(size=12))
    lbl_inicio_val_ind.grid(row=0, column=2, sticky="e")

    slider_inicio_ind = ctk.CTkSlider(range_ind_card, from_=0, to=1, command=on_inicio_ind_change)
    slider_inicio_ind.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 6))

    lbl_fin_ind = ctk.CTkLabel(range_ind_card, text="Fin", font=ctk.CTkFont(size=12))
    lbl_fin_ind.grid(row=2, column=0, sticky="w")
    lbl_fin_val_ind = ctk.CTkLabel(range_ind_card, text="00:00", font=ctk.CTkFont(size=12))
    lbl_fin_val_ind.grid(row=2, column=2, sticky="e")

    slider_fin_ind = ctk.CTkSlider(range_ind_card, from_=0, to=1, command=on_fin_ind_change)
    slider_fin_ind.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 6))

    lbl_duracion_ind = ctk.CTkLabel(range_ind_card, text="Duracion", font=ctk.CTkFont(size=12))
    lbl_duracion_ind.grid(row=4, column=0, sticky="w")
    lbl_duracion_val_ind = ctk.CTkLabel(range_ind_card, text="00:00", font=ctk.CTkFont(size=12))
    lbl_duracion_val_ind.grid(row=4, column=2, sticky="e")

    def leer_minutos_ind():
        try:
            valor = float(entry_ind_min.get().strip().replace(",", "."))
            return valor if valor > 0 else 5
        except Exception:
            return 5

    def leer_rango_minutos_ind():
        if rango_ind["duracion"] <= 0:
            return None, None
        inicio = slider_inicio_ind.get()
        fin = slider_fin_ind.get()
        return inicio / 60.0, fin / 60.0

    def iniciar_corte_individual():
        if not estado["path"]:
            log("Selecciona un video primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("Corte individual")
        minutos = leer_minutos_ind()
        inicio_min, fin_min = leer_rango_minutos_ind()
        posicion = pos_var.get()
        try:
            zoom = float(entry_zoom.get().strip().replace(",", "."))
        except Exception:
            zoom = slider_zoom.get()
        color = entry_color.get().strip() or "#000000"
        motion = motion_var.get()
        try:
            motion_amount = float(entry_motion.get().strip().replace(",", "."))
        except Exception:
            motion_amount = 0.08
        try:
            motion_period = float(entry_motion_period.get().strip().replace(",", "."))
        except Exception:
            motion_period = 30.0
        outro_enabled = outro_var.get()
        outro_image = outro_state.get("image")
        outro_text = entry_outro_text.get().strip()
        try:
            outro_seconds = float(entry_outro_secs.get().strip().replace(",", "."))
        except Exception:
            outro_seconds = 3.0
        try:
            outro_font = int(entry_outro_font.get().strip())
        except Exception:
            outro_font = 54
        outro_color = entry_outro_color.get().strip() or "#FFFFFF"

        def run_individual():
            try:
                procesar_corte_individual(
                    estado["path"],
                    minutos,
                    inicio_min,
                    fin_min,
                    posicion,
                    zoom,
                    color,
                    motion,
                    motion_amount,
                    motion_period,
                    outro_enabled,
                    outro_image,
                    outro_text,
                    outro_seconds,
                    outro_font,
                    outro_color,
                    None,
                    log
                )
                log("Finalizado proceso de corte individual.")
                log("Fin de la automatizacion.")
                beep_fin()
            except Exception as e:
                log(f"Error en corte individual: {e}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run_individual, daemon=True).start()

    btn_ind_run = ctk.CTkButton(
        ind_card,
        text="Cortar vertical",
        command=iniciar_corte_individual,
        height=46
    )
    btn_ind_run.grid(row=20, column=0, sticky="ew", padx=16, pady=(0, 8))

    btn_ind_open = ctk.CTkButton(
        ind_card,
        text="Abrir Carpeta de Videos",
        command=abrir_videos,
        height=40
    )
    btn_ind_open.grid(row=21, column=0, sticky="ew", padx=16, pady=(0, 16))

    # --- SRT ---
    tab_srt.grid_columnconfigure(0, weight=1)
    tab_srt.grid_rowconfigure(0, weight=1)

    srt_scroll = ctk.CTkScrollableFrame(tab_srt, corner_radius=0)
    srt_scroll.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
    srt_scroll.grid_columnconfigure(0, weight=1)

    srt_card = ctk.CTkFrame(srt_scroll, corner_radius=12)
    srt_card.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    srt_card.grid_columnconfigure(0, weight=1)

    lbl_srt_title = ctk.CTkLabel(
        srt_card,
        text="Generar subtitulos (.srt)",
        font=ctk.CTkFont(size=18, weight="bold")
    )
    lbl_srt_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_srt_hint = ctk.CTkLabel(
        srt_card,
        text="Selecciona un video o audio y configura el modelo/idioma.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2"
    )
    lbl_srt_hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    srt_state = {"items": []}

    srt_select = ctk.CTkFrame(srt_card, fg_color="transparent")
    srt_select.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
    srt_select.grid_columnconfigure(1, weight=1)

    def on_click_srt_video():
        from ui.dialogs import seleccionar_videos
        videos = seleccionar_videos()
        if videos:
            items = []
            for v in videos[:3]:
                v = _renombrar_si_largo(v)
                if v:
                    items.append((v, False))
            if not items:
                return
            srt_state["items"] = items
            lbl_srt_file.configure(text=f"{len(items)} video(s) seleccionados")
            for v, _ in items:
                log(f"Video seleccionado: {v}")

    def on_click_srt_audio():
        from ui.dialogs import seleccionar_audios
        audios = seleccionar_audios()
        if audios:
            items = []
            for a in audios[:3]:
                a = _renombrar_si_largo(a)
                if a:
                    items.append((a, True))
            if not items:
                return
            srt_state["items"] = items
            lbl_srt_file.configure(text=f"{len(items)} audio(s) seleccionados")
            for a, _ in items:
                log(f"Audio seleccionado: {a}")

    btn_srt_video = ctk.CTkButton(
        srt_select,
        text="Seleccionar Video",
        command=on_click_srt_video,
        height=40
    )
    btn_srt_video.grid(row=0, column=0, sticky="w")

    btn_srt_audio = ctk.CTkButton(
        srt_select,
        text="Seleccionar Audio",
        command=on_click_srt_audio,
        height=40
    )
    btn_srt_audio.grid(row=0, column=1, sticky="w", padx=(12, 0))

    lbl_srt_file = ctk.CTkLabel(
        srt_select,
        text="(sin archivo seleccionado)",
        font=ctk.CTkFont(size=12)
    )
    lbl_srt_file.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

    srt_conf = ctk.CTkFrame(srt_card, fg_color="transparent")
    srt_conf.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
    srt_conf.grid_columnconfigure(1, weight=1)

    lbl_model = ctk.CTkLabel(srt_conf, text="Modelo", font=ctk.CTkFont(size=12))
    lbl_model.grid(row=0, column=0, sticky="w")

    model_var = ctk.StringVar(value="base")
    opt_model = ctk.CTkOptionMenu(
        srt_conf,
        values=["tiny", "base", "small", "medium", "large"],
        variable=model_var
    )
    opt_model.grid(row=0, column=1, sticky="w", padx=(8, 0))

    lbl_idioma = ctk.CTkLabel(srt_conf, text="Idioma", font=ctk.CTkFont(size=12))
    lbl_idioma.grid(row=1, column=0, sticky="w", pady=(8, 0))

    idioma_var = ctk.StringVar(value="auto")
    opt_idioma = ctk.CTkOptionMenu(
        srt_conf,
        values=["auto", "es", "en", "pt", "fr"],
        variable=idioma_var
    )
    opt_idioma.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

    adv_var = ctk.BooleanVar(value=False)
    chk_adv = ctk.CTkCheckBox(
        srt_card,
        text="Opciones avanzadas",
        variable=adv_var
    )
    chk_adv.grid(row=4, column=0, sticky="w", padx=16, pady=(0, 8))

    adv_card = ctk.CTkFrame(srt_card, fg_color="transparent")
    adv_card.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 12))
    adv_card.grid_columnconfigure(1, weight=1)

    lbl_temp = ctk.CTkLabel(adv_card, text="Temperature", font=ctk.CTkFont(size=12))
    lbl_temp.grid(row=0, column=0, sticky="w")

    entry_temp = ctk.CTkEntry(adv_card, width=80)
    entry_temp.insert(0, "0.0")
    entry_temp.grid(row=0, column=1, sticky="w", padx=(8, 0))

    btn_clear_temp = ctk.CTkButton(
        adv_card,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_temp)
    )
    btn_clear_temp.grid(row=0, column=2, sticky="e", padx=(8, 0))

    lbl_beam = ctk.CTkLabel(adv_card, text="Beam size", font=ctk.CTkFont(size=12))
    lbl_beam.grid(row=1, column=0, sticky="w", pady=(8, 0))

    entry_beam = ctk.CTkEntry(adv_card, width=80)
    entry_beam.insert(0, "5")
    entry_beam.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

    btn_clear_beam = ctk.CTkButton(
        adv_card,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_beam)
    )
    btn_clear_beam.grid(row=1, column=2, sticky="e", padx=(8, 0), pady=(8, 0))

    def _toggle_adv():
        adv_card.grid_remove() if not adv_var.get() else adv_card.grid()

    adv_var.trace_add("write", lambda *_: _toggle_adv())
    _toggle_adv()

    def iniciar_srt():
        if not srt_state["items"]:
            log("Selecciona videos o audio primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("SRT")
        idioma = idioma_var.get()
        if idioma == "auto":
            idioma = ""
        model = model_var.get()
        temperature = None
        beam_size = None
        if adv_var.get():
            try:
                temperature = float(entry_temp.get().strip().replace(",", "."))
            except Exception:
                temperature = None
            try:
                beam_size = int(entry_beam.get().strip())
            except Exception:
                beam_size = None

        def run_srt():
            try:
                for idx, (path, is_audio) in enumerate(srt_state["items"], start=1):
                    if stop_control.should_stop():
                        log("⛔ Proceso detenido por el usuario.")
                        return
                    log(f"Transcribiendo {idx}/{len(srt_state['items'])}...")
                    procesar_srt(
                        path,
                        is_audio,
                        idioma,
                        model,
                        temperature,
                        beam_size,
                        log
                    )
                log("Finalizado proceso de SRT.")
                log("Fin de la automatizacion.")
                beep_fin()
            except Exception as e:
                log(f"Error en SRT: {e}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run_srt, daemon=True).start()

    btn_srt_run = ctk.CTkButton(
        srt_card,
        text="Generar SRT",
        command=iniciar_srt,
        height=46
    )
    btn_srt_run.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 8))

    btn_srt_open = ctk.CTkButton(
        srt_card,
        text="Abrir Carpeta de Subtitulos",
        command=abrir_subtitulos,
        height=40
    )
    btn_srt_open.grid(row=7, column=0, sticky="ew", padx=16, pady=(0, 16))

    # --- Subtitular video ---
    tab_sub.grid_columnconfigure(0, weight=1)
    tab_sub.grid_rowconfigure(0, weight=1)

    sub_scroll = ctk.CTkScrollableFrame(tab_sub, corner_radius=0)
    sub_scroll.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
    sub_scroll.grid_columnconfigure(0, weight=1)

    sub_card = ctk.CTkFrame(sub_scroll, corner_radius=12)
    sub_card.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    sub_card.grid_columnconfigure(0, weight=2)
    sub_card.grid_columnconfigure(1, weight=0)

    lbl_sub_title = ctk.CTkLabel(
        sub_card,
        text="Quemar SRT en video (TikTok listo)",
        font=ctk.CTkFont(size=18, weight="bold")
    )
    lbl_sub_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_sub_hint = ctk.CTkLabel(
        sub_card,
        text="Selecciona el video vertical y el archivo .srt para quemar los subtitulos.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2"
    )
    lbl_sub_hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    sub_left = ctk.CTkFrame(sub_card, fg_color="transparent")
    sub_left.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
    sub_left.grid_columnconfigure(1, weight=1)

    sub_state = {"videos": [], "srts": []}

    sub_select = ctk.CTkFrame(sub_left, fg_color="transparent")
    sub_select.grid(row=0, column=0, sticky="ew", pady=(0, 12))
    sub_select.grid_columnconfigure(1, weight=1)

    pos_row = ctk.CTkFrame(sub_left, fg_color="transparent")
    pos_row.grid(row=1, column=0, sticky="ew", pady=(0, 12))
    pos_row.grid_columnconfigure(1, weight=1)

    lbl_pos_sub = ctk.CTkLabel(pos_row, text="Posicion de subtitulo", font=ctk.CTkFont(size=12))
    lbl_pos_sub.grid(row=0, column=0, sticky="w")

    pos_sub_var = ctk.StringVar(value="bottom")
    opt_pos_sub = ctk.CTkOptionMenu(
        pos_row,
        values=["top", "top-center", "center", "bottom-center", "bottom"],
        variable=pos_sub_var
    )
    opt_pos_sub.grid(row=0, column=1, sticky="w", padx=(8, 0))

    preview_card = ctk.CTkFrame(sub_card, corner_radius=10)
    preview_card.grid(row=0, column=1, rowspan=5, sticky="n", padx=(0, 16), pady=16)
    preview_card.grid_columnconfigure(0, weight=1)
    preview_card.grid_rowconfigure(1, weight=1)

    lbl_prev = ctk.CTkLabel(preview_card, text="Vista previa (TikTok)", font=ctk.CTkFont(size=12))
    lbl_prev.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

    prev_container = tk.Frame(preview_card, bg="#111111", width=320, height=568)
    prev_container.grid(row=1, column=0, sticky="n", padx=12, pady=(0, 12))
    prev_container.grid_propagate(False)

    prev_label = tk.Label(prev_container, bg="#111111")
    prev_label.pack(fill="both", expand=True)
    sub_preview_img = {"img": None}
    prev_state = {"last_w": 0, "last_h": 0, "last_pos": None, "last_video": None, "after_id": None}
    PREVIEW_W = 320
    PREVIEW_H = 568

    def _get_preview_font_lines():
        try:
            font_size = int(entry_font.get().strip())
        except Exception:
            font_size = 46
        try:
            max_lines = int(entry_max_lines.get().strip())
        except Exception:
            max_lines = 2
        if font_size < 10:
            font_size = 10
        if max_lines < 1:
            max_lines = 1
        return font_size, max_lines

    def _preview_block(inner_h, is_vertical, font_size, max_lines, pos):
        safe_area = int(inner_h * (0.22 if is_vertical else 0.10))
        center_offset = int(inner_h * (0.00 if is_vertical else 0.00))
        line_height = font_size * 1.25
        subtitle_height = line_height * max_lines
        if pos == "top":
            y = safe_area
        elif pos == "top-center":
            y = (safe_area + (inner_h - subtitle_height) / 2) / 2
        elif pos == "center":
            y = (inner_h - subtitle_height) / 2 + center_offset
        else:
            bottom_y = inner_h - safe_area - subtitle_height
            if pos == "bottom-center":
                center_y = (inner_h - subtitle_height) / 2
                y = (center_y + bottom_y) / 2
            else:
                y = bottom_y
        y0 = max(0, int(y))
        y1 = min(inner_h - 1, int(y + subtitle_height))
        return y0, y1

    def _render_preview_image(frame_image):
        w = PREVIEW_W
        h = PREVIEW_H
        pad = 16
        inner_w = max(2, w - pad * 2)
        inner_h = max(2, h - pad * 2)
        radius = 22

        canvas = Image.new("RGB", (w, h), color="#1a1a1a")
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle([2, 2, w - 3, h - 3], radius=radius, outline="#3a3a3a", width=3, fill="#0f0f0f")
        screen = Image.new("RGB", (inner_w, inner_h), color="#000000")

        is_vertical = True
        if frame_image is not None:
            img_w, img_h = frame_image.size
            is_vertical = img_h >= img_w
            scale = min(inner_w / img_w, inner_h / img_h)
            new_w = max(1, int(img_w * scale))
            new_h = max(1, int(img_h * scale))
            frame_image = frame_image.resize((new_w, new_h), Image.LANCZOS)
            x0 = (inner_w - new_w) // 2
            y0 = (inner_h - new_h) // 2
            screen.paste(frame_image, (x0, y0))

        font_size, max_lines = _get_preview_font_lines()
        y0, y1 = _preview_block(inner_h, is_vertical, font_size, max_lines, pos_sub_var.get())
        draw_screen = ImageDraw.Draw(screen)
        draw_screen.rectangle([8, y0, inner_w - 8, y1], outline=(255, 214, 0), width=3)

        canvas.paste(screen, (pad, pad))
        return canvas

    def actualizar_preview_sub():
        video_path = sub_state.get("video")
        pos_now = pos_sub_var.get()
        w = PREVIEW_W
        h = PREVIEW_H
        if (
            w == prev_state["last_w"]
            and h == prev_state["last_h"]
            and prev_state["last_pos"] == pos_now
            and prev_state["last_video"] == video_path
            and sub_preview_img["img"] is not None
        ):
            return
        prev_state["last_w"] = w
        prev_state["last_h"] = h
        prev_state["last_pos"] = pos_now
        prev_state["last_video"] = video_path
        if not video_path:
            image = _render_preview_image(None)
            sub_preview_img["img"] = ImageTk.PhotoImage(image)
            prev_label.configure(image=sub_preview_img["img"], text="")
            return
        try:
            clip = VideoFileClip(video_path, audio=False)
            dur = float(clip.duration or 0.0)
            t = 1.0 if dur >= 1.0 else max(0.0, dur - 0.01)
            frame = clip.get_frame(t)
            clip.close()
            frame_img = Image.fromarray(frame)
            image = _render_preview_image(frame_img)
            sub_preview_img["img"] = ImageTk.PhotoImage(image)
            prev_label.configure(image=sub_preview_img["img"], text="")
        except Exception as e:
            prev_label.configure(text=f"Preview error: {e}", image="")

    def on_click_sub_video():
        from ui.dialogs import seleccionar_videos
        videos = seleccionar_videos()
        if videos:
            items = []
            for v in videos:
                v = _renombrar_si_largo(v)
                if v:
                    items.append(v)
            if not items:
                return
            sub_state["videos"] = items
            if len(items) == 1:
                lbl_sub_video.configure(text=os.path.basename(items[0]))
                actualizar_preview_sub()
            else:
                lbl_sub_video.configure(text=f"{len(items)} video(s) seleccionados")
            for v in items:
                log(f"Video seleccionado: {v}")

    def on_click_sub_srt():
        from ui.dialogs import seleccionar_archivos
        srts = seleccionar_archivos("Seleccionar SRT", [("Subtitles", "*.srt")])
        if srts:
            items = []
            for s in srts:
                s = _renombrar_si_largo(s)
                if s:
                    items.append(s)
            if not items:
                return
            sub_state["srts"] = items
            if len(items) == 1:
                lbl_sub_srt.configure(text=os.path.basename(items[0]))
            else:
                lbl_sub_srt.configure(text=f"{len(items)} srt(s) seleccionados")
            for s in items:
                log(f"SRT seleccionado: {s}")

    pos_sub_var.trace_add("write", lambda *_: actualizar_preview_sub())
    def _schedule_preview_update(_e=None):
        if prev_state["after_id"]:
            prev_container.after_cancel(prev_state["after_id"])
        prev_state["after_id"] = prev_container.after(120, actualizar_preview_sub)

    prev_container.bind("<Configure>", _schedule_preview_update)

    btn_sub_video = ctk.CTkButton(
        sub_select,
        text="Seleccionar Video",
        command=on_click_sub_video,
        height=40
    )
    btn_sub_video.grid(row=0, column=0, sticky="w")

    btn_sub_srt = ctk.CTkButton(
        sub_select,
        text="Seleccionar SRT",
        command=on_click_sub_srt,
        height=40
    )
    btn_sub_srt.grid(row=0, column=1, sticky="w", padx=(12, 0))

    lbl_sub_video = ctk.CTkLabel(
        sub_select,
        text="(sin video seleccionado)",
        font=ctk.CTkFont(size=12)
    )
    lbl_sub_video.grid(row=1, column=0, sticky="w", pady=(8, 0))

    lbl_sub_srt = ctk.CTkLabel(
        sub_select,
        text="(sin srt seleccionado)",
        font=ctk.CTkFont(size=12)
    )
    lbl_sub_srt.grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(8, 0))

    txt_style_row = ctk.CTkFrame(sub_left, fg_color="transparent")
    txt_style_row.grid(row=2, column=0, sticky="ew", pady=(0, 12))
    txt_style_row.grid_columnconfigure(1, weight=1)

    lbl_font = ctk.CTkLabel(txt_style_row, text="Tamano de texto", font=ctk.CTkFont(size=12))
    lbl_font.grid(row=0, column=0, sticky="w")

    entry_font = ctk.CTkEntry(txt_style_row, width=80)
    entry_font.insert(0, "46")
    entry_font.grid(row=0, column=1, sticky="w", padx=(8, 0))

    lbl_outline = ctk.CTkLabel(txt_style_row, text="Borde", font=ctk.CTkFont(size=12))
    lbl_outline.grid(row=1, column=0, sticky="w", pady=(8, 0))

    entry_outline = ctk.CTkEntry(txt_style_row, width=80)
    entry_outline.insert(0, "2")
    entry_outline.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

    lbl_shadow = ctk.CTkLabel(txt_style_row, text="Sombra", font=ctk.CTkFont(size=12))
    lbl_shadow.grid(row=2, column=0, sticky="w", pady=(8, 0))

    entry_shadow = ctk.CTkEntry(txt_style_row, width=80)
    entry_shadow.insert(0, "1")
    entry_shadow.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

    wrap_row = ctk.CTkFrame(sub_left, fg_color="transparent")
    wrap_row.grid(row=3, column=0, sticky="ew", pady=(0, 12))
    wrap_row.grid_columnconfigure(1, weight=1)

    lbl_max_chars = ctk.CTkLabel(wrap_row, text="Max caracteres por linea", font=ctk.CTkFont(size=12))
    lbl_max_chars.grid(row=0, column=0, sticky="w")

    entry_max_chars = ctk.CTkEntry(wrap_row, width=80)
    entry_max_chars.insert(0, "32")
    entry_max_chars.grid(row=0, column=1, sticky="w", padx=(8, 0))

    lbl_max_lines = ctk.CTkLabel(wrap_row, text="Max lineas", font=ctk.CTkFont(size=12))
    lbl_max_lines.grid(row=1, column=0, sticky="w", pady=(8, 0))

    entry_max_lines = ctk.CTkEntry(wrap_row, width=80)
    entry_max_lines.insert(0, "2")
    entry_max_lines.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

    entry_font.bind("<KeyRelease>", lambda _e: actualizar_preview_sub())
    entry_max_lines.bind("<KeyRelease>", lambda _e: actualizar_preview_sub())

    force_pos_var = ctk.BooleanVar(value=True)
    chk_force_pos = ctk.CTkCheckBox(
        sub_left,
        text="Forzar posicion del SRT",
        variable=force_pos_var
    )
    chk_force_pos.grid(row=4, column=0, sticky="w", pady=(0, 12))

    use_ass_var = ctk.BooleanVar(value=True)
    chk_use_ass = ctk.CTkCheckBox(
        sub_left,
        text="Usar ASS (más estable)",
        variable=use_ass_var
    )
    chk_use_ass.grid(row=5, column=0, sticky="w", pady=(0, 12))

    def iniciar_subtitulado():
        if not sub_state["videos"] or not sub_state["srts"]:
            log("Selecciona video(s) y SRT(s) primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("Subtitular video")
        pos = "center"
        pos_sub_var.set("center")
        try:
            font_size = int(entry_font.get().strip())
        except Exception:
            font_size = 46
        try:
            outline = int(entry_outline.get().strip())
        except Exception:
            outline = 2
        try:
            shadow = int(entry_shadow.get().strip())
        except Exception:
            shadow = 1
        try:
            max_chars = int(entry_max_chars.get().strip())
        except Exception:
            max_chars = 32
        try:
            max_lines = int(entry_max_lines.get().strip())
        except Exception:
            max_lines = 2
        if font_size < 10:
            font_size = 10
        if outline < 0:
            outline = 0
        if shadow < 0:
            shadow = 0

        def _norm_name(path: str) -> str:
            base = os.path.splitext(os.path.basename(path))[0].lower()
            base = re.sub(r"[^a-z0-9]+", " ", base).strip()
            for suf in ["_original", "_completo", "_srt", "_subt", "_sub", "original", "completo"]:
                base = base.replace(suf.replace("_", " "), "").strip()
            return base

        def run_sub():
            try:
                videos = sub_state["videos"]
                srts = sub_state["srts"]
                if len(videos) == 1 and len(srts) == 1:
                    procesar_quemar_srt(
                        videos[0],
                        srts[0],
                        pos,
                        font_size,
                        outline,
                        shadow,
                        True,
                        max_chars,
                        max_lines,
                        use_ass_var.get(),
                        log
                    )
                else:
                    srt_map = {}
                    for s in srts:
                        srt_map[_norm_name(s)] = s
                    for idx, v in enumerate(videos, start=1):
                        if stop_control.should_stop():
                            log("⛔ Proceso detenido por el usuario.")
                            return
                        key = _norm_name(v)
                        srt_match = srt_map.get(key)
                        if not srt_match:
                            log(f"No se encontro SRT para: {os.path.basename(v)}")
                            continue
                        log(f"Subtitulando {idx}/{len(videos)}: {os.path.basename(v)}")
                        procesar_quemar_srt(
                            v,
                            srt_match,
                            pos,
                            font_size,
                            outline,
                            shadow,
                            True,
                            max_chars,
                            max_lines,
                            use_ass_var.get(),
                            log
                        )
                log("Finalizado proceso de subtitular video.")
                log("Fin de la automatizacion.")
                beep_fin()
            except Exception as e:
                log(f"Error subtitulando: {e}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run_sub, daemon=True).start()

    btn_sub_run = ctk.CTkButton(
        sub_left,
        text="Quemar SRT",
        command=iniciar_subtitulado,
        height=46
    )
    btn_sub_run.grid(row=5, column=0, sticky="ew", pady=(0, 8))

    btn_sub_open = ctk.CTkButton(
        sub_left,
        text="Abrir Carpeta de Videos",
        command=abrir_videos,
        height=40
    )
    btn_sub_open.grid(row=6, column=0, sticky="ew", pady=(0, 8))

    # --- IA Clips ---
    tab_clips.grid_columnconfigure(0, weight=1)
    tab_clips.grid_rowconfigure(0, weight=1)

    clips_scroll = ctk.CTkScrollableFrame(tab_clips, corner_radius=0)
    clips_scroll.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
    clips_scroll.grid_columnconfigure(0, weight=1)

    clips_card = ctk.CTkFrame(clips_scroll, corner_radius=12)
    clips_card.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    clips_card.grid_columnconfigure(0, weight=1)

    lbl_clips_title = ctk.CTkLabel(
        clips_card,
        text="IA Clips: Rangos virales desde SRT",
        font=ctk.CTkFont(size=18, weight="bold")
    )
    lbl_clips_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_clips_hint = ctk.CTkLabel(
        clips_card,
        text="Selecciona un SRT y genera rangos recomendados con IA.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2"
    )
    lbl_clips_hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    clips_state = {"srt": None}

    clips_select = ctk.CTkFrame(clips_card, fg_color="transparent")
    clips_select.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
    clips_select.grid_columnconfigure(1, weight=1)

    def on_click_clips_srt():
        from ui.dialogs import seleccionar_archivo
        srt = seleccionar_archivo("Seleccionar SRT", [("Subtitles", "*.srt")])
        if srt:
            srt = _renombrar_si_largo(srt)
            if not srt:
                return
            clips_state["srt"] = srt
            lbl_clips_srt.configure(text=os.path.basename(srt))
            log(f"SRT seleccionado: {srt}")

    btn_clips_srt = ctk.CTkButton(
        clips_select,
        text="Seleccionar SRT",
        command=on_click_clips_srt,
        height=40
    )
    btn_clips_srt.grid(row=0, column=0, sticky="w")

    lbl_clips_srt = ctk.CTkLabel(
        clips_select,
        text="(sin srt seleccionado)",
        font=ctk.CTkFont(size=12)
    )
    lbl_clips_srt.grid(row=0, column=1, sticky="w", padx=(12, 0))

    clips_conf = ctk.CTkFrame(clips_card, fg_color="transparent")
    clips_conf.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
    clips_conf.grid_columnconfigure(1, weight=1)

    lbl_model_clips = ctk.CTkLabel(clips_conf, text="Modelo", font=ctk.CTkFont(size=12))
    lbl_model_clips.grid(row=0, column=0, sticky="w")

    model_clips_var = ctk.StringVar(value="gpt-4o-mini")
    opt_model_clips = ctk.CTkOptionMenu(
        clips_conf,
        values=["gpt-4o-mini", "gpt-4o"],
        variable=model_clips_var
    )
    opt_model_clips.grid(row=0, column=1, sticky="w", padx=(8, 0))

    clips_out = ctk.CTkFrame(clips_card)
    clips_out.grid(row=4, column=0, sticky="nsew", padx=16, pady=(0, 12))
    clips_out.grid_columnconfigure(0, weight=1)

    lbl_clips_out = ctk.CTkLabel(clips_out, text="Resultado", font=ctk.CTkFont(size=12))
    lbl_clips_out.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))

    txt_clips = ctk.CTkTextbox(clips_out, height=220)
    txt_clips.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
    txt_clips.configure(state="disabled")

    lbl_json = ctk.CTkLabel(clips_card, text="JSON: (sin generar)", font=ctk.CTkFont(size=12))
    lbl_json.grid(row=5, column=0, sticky="w", padx=16, pady=(0, 8))

    def iniciar_ai_clips():
        if not clips_state["srt"]:
            log("Selecciona un SRT primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("IA Clips")
        model = model_clips_var.get()

        def run_clips():
            try:
                result = generar_recomendaciones_clips(clips_state["srt"], None, model, log)
                data = result.get("data", {})
                json_path = result.get("json_path", "")
                text_out = result.get("text", "")
                txt_clips.configure(state="normal")
                txt_clips.delete("1.0", "end")
                txt_clips.insert("end", text_out.strip())
                txt_clips.configure(state="disabled")
                if json_path:
                    lbl_json.configure(text=f"JSON creado: {json_path}")
                    log(f"JSON creado: {json_path}")
                log("Finalizado proceso IA Clips.")
                log("Fin de la automatizacion.")
                beep_fin()
            except Exception as e:
                log(f"Error IA Clips: {e}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run_clips, daemon=True).start()

    btn_clips_run = ctk.CTkButton(
        clips_card,
        text="Generar recomendaciones",
        command=iniciar_ai_clips,
        height=46
    )
    btn_clips_run.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 16))

    # --- IA TikTok ---
    tab_ai.grid_columnconfigure(0, weight=1)
    tab_ai.grid_rowconfigure(0, weight=1)

    ai_scroll = ctk.CTkScrollableFrame(tab_ai, corner_radius=0)
    ai_scroll.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
    ai_scroll.grid_columnconfigure(0, weight=1)

    ai_card = ctk.CTkFrame(ai_scroll, corner_radius=12)
    ai_card.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    ai_card.grid_columnconfigure(0, weight=1)

    lbl_ai_title = ctk.CTkLabel(
        ai_card,
        text="IA TikTok: Resumen + Descripción + Hashtags",
        font=ctk.CTkFont(size=18, weight="bold")
    )
    lbl_ai_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_ai_hint = ctk.CTkLabel(
        ai_card,
        text="Sube un SRT y genera texto listo para copiar.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2"
    )
    lbl_ai_hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    ai_state = {"srt": None}

    ai_select = ctk.CTkFrame(ai_card, fg_color="transparent")
    ai_select.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
    ai_select.grid_columnconfigure(1, weight=1)

    def on_click_ai_srt():
        from ui.dialogs import seleccionar_archivo
        srt = seleccionar_archivo("Seleccionar SRT", [("Subtitles", "*.srt")])
        if srt:
            ai_state["srt"] = srt
            lbl_ai_srt.configure(text=os.path.basename(srt))
            log(f"SRT seleccionado: {srt}")

    btn_ai_srt = ctk.CTkButton(
        ai_select,
        text="Seleccionar SRT",
        command=on_click_ai_srt,
        height=40
    )
    btn_ai_srt.grid(row=0, column=0, sticky="w")

    lbl_ai_srt = ctk.CTkLabel(
        ai_select,
        text="(sin srt seleccionado)",
        font=ctk.CTkFont(size=12)
    )
    lbl_ai_srt.grid(row=0, column=1, sticky="w", padx=(12, 0))

    ai_conf = ctk.CTkFrame(ai_card, fg_color="transparent")
    ai_conf.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
    ai_conf.grid_columnconfigure(1, weight=1)

    lbl_key = ctk.CTkLabel(ai_conf, text="API key (desde .env)", font=ctk.CTkFont(size=12))
    lbl_key.grid(row=0, column=0, sticky="w")

    lbl_key_hint = ctk.CTkLabel(
        ai_conf,
        text="Usa OPENAI_API_KEY en el archivo .env",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2"
    )
    lbl_key_hint.grid(row=0, column=1, sticky="w", padx=(8, 0))

    lbl_model_ai = ctk.CTkLabel(ai_conf, text="Modelo", font=ctk.CTkFont(size=12))
    lbl_model_ai.grid(row=1, column=0, sticky="w", pady=(8, 0))

    model_ai_var = ctk.StringVar(value="gpt-4o-mini")
    opt_model_ai = ctk.CTkOptionMenu(
        ai_conf,
        values=["gpt-4o-mini", "gpt-4o"],
        variable=model_ai_var
    )
    opt_model_ai.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

    def _set_textbox(tb, text):
        tb.configure(state="normal")
        tb.delete("1.0", "end")
        tb.insert("end", text)
        tb.configure(state="disabled")

    def _copy_text(text):
        ventana.clipboard_clear()
        ventana.clipboard_append(text)
        ventana.update_idletasks()

    out_frame = ctk.CTkFrame(ai_card)
    out_frame.grid(row=4, column=0, sticky="nsew", padx=16, pady=(0, 12))
    out_frame.grid_columnconfigure(0, weight=1)

    lbl_title_ai = ctk.CTkLabel(out_frame, text="Titulo (clickbait)", font=ctk.CTkFont(size=12))
    lbl_title_ai.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
    txt_title_ai = ctk.CTkTextbox(out_frame, height=50)
    txt_title_ai.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

    lbl_res = ctk.CTkLabel(out_frame, text="Resumen", font=ctk.CTkFont(size=12))
    lbl_res.grid(row=2, column=0, sticky="w", padx=10, pady=(6, 4))
    txt_res = ctk.CTkTextbox(out_frame, height=80)
    txt_res.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 6))

    lbl_desc = ctk.CTkLabel(out_frame, text="Descripción", font=ctk.CTkFont(size=12))
    lbl_desc.grid(row=4, column=0, sticky="w", padx=10, pady=(6, 4))
    txt_desc = ctk.CTkTextbox(out_frame, height=110)
    txt_desc.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 6))

    lbl_tags = ctk.CTkLabel(out_frame, text="Hashtags", font=ctk.CTkFont(size=12))
    lbl_tags.grid(row=6, column=0, sticky="w", padx=10, pady=(6, 4))
    txt_tags = ctk.CTkTextbox(out_frame, height=70)
    txt_tags.grid(row=7, column=0, sticky="ew", padx=10, pady=(0, 10))

    def iniciar_ai():
        if not ai_state["srt"]:
            log("Selecciona un SRT primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("IA TikTok")
        model = model_ai_var.get()

        def run_ai():
            try:
                result = generar_descripcion_tiktok(ai_state["srt"], None, model, log)
                _set_textbox(txt_title_ai, result.get("titulo", ""))
                _set_textbox(txt_res, result.get("resumen", ""))
                _set_textbox(txt_desc, result.get("descripcion", ""))
                _set_textbox(txt_tags, result.get("hashtags", ""))
                log("Finalizado proceso IA TikTok.")
                log("Fin de la automatizacion.")
                beep_fin()
            except Exception as e:
                log(f"Error IA TikTok: {e}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run_ai, daemon=True).start()

    btn_ai_run = ctk.CTkButton(
        ai_card,
        text="Generar texto",
        command=iniciar_ai,
        height=46
    )
    btn_ai_run.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 8))

    btn_copy_desc = ctk.CTkButton(
        ai_card,
        text="Copiar descripción + hashtags",
        command=lambda: _copy_text((txt_desc.get("1.0", "end").strip() + "\n" + txt_tags.get("1.0", "end").strip()).strip()),
        height=40
    )
    btn_copy_desc.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 16))

    # --- Actividad ---
    # --- Audio MP3 ---
    tab_audio.grid_columnconfigure(0, weight=1)
    tab_audio.grid_rowconfigure(0, weight=1)

    audio_card = ctk.CTkFrame(tab_audio, corner_radius=12)
    audio_card.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
    audio_card.grid_columnconfigure(0, weight=1)

    lbl_audio_title = ctk.CTkLabel(
        audio_card,
        text="Extraer audio en MP3",
        font=ctk.CTkFont(size=18, weight="bold")
    )
    lbl_audio_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_audio_hint = ctk.CTkLabel(
        audio_card,
        text="Selecciona un video local y guarda el MP3 sin generar WAV.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2"
    )
    lbl_audio_hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    audio_state = {"video_path": None}

    audio_select_row = ctk.CTkFrame(audio_card, fg_color="transparent")
    audio_select_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
    audio_select_row.grid_columnconfigure(1, weight=1)

    def on_click_audio_video():
        from ui.dialogs import seleccionar_video
        video = seleccionar_video()
        if video:
            video = _renombrar_si_largo(video)
            if not video:
                return
            audio_state["video_path"] = video
            lbl_audio_file.configure(text=os.path.basename(video))
            log(f"Video seleccionado para MP3: {video}")

    btn_audio_video = ctk.CTkButton(
        audio_select_row,
        text="Seleccionar Video",
        command=on_click_audio_video,
        height=40
    )
    btn_audio_video.grid(row=0, column=0, sticky="w")

    lbl_audio_file = ctk.CTkLabel(
        audio_select_row,
        text="(ningun video seleccionado)",
        font=ctk.CTkFont(size=12)
    )
    lbl_audio_file.grid(row=0, column=1, sticky="w", padx=(12, 0))

    def extraer_audio_mp3():
        video_path = audio_state.get("video_path")
        if not video_path:
            log("Selecciona un video para extraer el audio.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("Audio MP3")
        base_name = nombre_base_fuente(video_path)
        audio_dir_base = os.path.join("output", "audios", base_name)
        os.makedirs(audio_dir_base, exist_ok=True)
        out_path = os.path.join(audio_dir_base, f"{base_name}_original.mp3")
        log("Extrayendo audio en MP3...")
        try:
            extraer_audio(video_path, out_path, log)
            log(f"✅ Audio MP3 guardado: {out_path}")
            log("Finalizado proceso de audio MP3.")
            log("Fin de la automatizacion.")
            beep_fin()
        except Exception as e:
            log(f"Error extrayendo MP3: {e}")
        finally:
            stop_control.set_busy(False)

    def iniciar_audio_mp3():
        threading.Thread(target=extraer_audio_mp3, daemon=True).start()

    btn_audio_extraer = ctk.CTkButton(
        audio_card,
        text="Extraer MP3",
        command=iniciar_audio_mp3,
        height=46
    )
    btn_audio_extraer.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))

    btn_audio_open = ctk.CTkButton(
        audio_card,
        text="Abrir Carpeta de Audios",
        command=abrir_audios,
        height=40
    )
    btn_audio_open.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))

    # --- YouTube MP3 ---
    tab_youtube.grid_columnconfigure(0, weight=1)
    tab_youtube.grid_rowconfigure(0, weight=1)

    yt_card = ctk.CTkFrame(tab_youtube, corner_radius=12)
    yt_card.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
    yt_card.grid_columnconfigure(0, weight=1)

    lbl_yt_title = ctk.CTkLabel(
        yt_card,
        text="Extraer audio de YouTube (MP3)",
        font=ctk.CTkFont(size=18, weight="bold")
    )
    lbl_yt_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_yt_hint = ctk.CTkLabel(
        yt_card,
        text="Pega el link y descarga el audio en MP3.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2"
    )
    lbl_yt_hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    yt_row = ctk.CTkFrame(yt_card, fg_color="transparent")
    yt_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
    yt_row.grid_columnconfigure(0, weight=1)

    yt_entry = ctk.CTkEntry(yt_row, placeholder_text="https://www.youtube.com/watch?v=...")
    yt_entry.grid(row=0, column=0, sticky="ew")

    btn_clear_yt = ctk.CTkButton(
        yt_row,
        text="Limpiar",
        width=90,
        height=28,
        command=lambda: limpiar_entry(yt_entry)
    )
    btn_clear_yt.grid(row=0, column=1, sticky="e", padx=(8, 0))

    def descargar_mp3_youtube():
        url = yt_entry.get().strip()
        if not url:
            log("Pega un link de YouTube primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("YouTube MP3")
        log("Descargando audio de YouTube...")
        try:
            out_path = descargar_audio_youtube(url, log_fn=log)
            log(f"✅ Audio MP3 guardado: {out_path}")
            log("Finalizado proceso de YouTube MP3.")
            log("Fin de la automatizacion.")
            beep_fin()
        except Exception as e:
            log(f"Error descargando MP3 de YouTube: {e}")
        finally:
            stop_control.set_busy(False)

    def iniciar_descarga_youtube():
        threading.Thread(target=descargar_mp3_youtube, daemon=True).start()

    btn_yt = ctk.CTkButton(
        yt_card,
        text="Descargar MP3",
        command=iniciar_descarga_youtube,
        height=46
    )
    btn_yt.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))

    btn_yt_open = ctk.CTkButton(
        yt_card,
        text="Abrir Descargas YouTube",
        command=abrir_descargas,
        height=40
    )
    btn_yt_open.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))

    # --- YouTube MP4 ---
    tab_youtube_mp4.grid_columnconfigure(0, weight=1)
    tab_youtube_mp4.grid_rowconfigure(0, weight=1)

    yt_mp4_card = ctk.CTkFrame(tab_youtube_mp4, corner_radius=12)
    yt_mp4_card.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
    yt_mp4_card.grid_columnconfigure(0, weight=1)

    lbl_yt_mp4_title = ctk.CTkLabel(
        yt_mp4_card,
        text="Descargar video de YouTube (MP4)",
        font=ctk.CTkFont(size=18, weight="bold")
    )
    lbl_yt_mp4_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_yt_mp4_hint = ctk.CTkLabel(
        yt_mp4_card,
        text="Pega el link y descarga el video en MP4.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2"
    )
    lbl_yt_mp4_hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    yt_mp4_row = ctk.CTkFrame(yt_mp4_card, fg_color="transparent")
    yt_mp4_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
    yt_mp4_row.grid_columnconfigure(0, weight=1)

    yt_mp4_entry = ctk.CTkEntry(yt_mp4_row, placeholder_text="https://www.youtube.com/watch?v=...")
    yt_mp4_entry.grid(row=0, column=0, sticky="ew")

    btn_clear_yt_mp4 = ctk.CTkButton(
        yt_mp4_row,
        text="Limpiar",
        width=90,
        height=28,
        command=lambda: limpiar_entry(yt_mp4_entry)
    )
    btn_clear_yt_mp4.grid(row=0, column=1, sticky="e", padx=(8, 0))

    def descargar_mp4_youtube():
        url = yt_mp4_entry.get().strip()
        if not url:
            log("Pega un link de YouTube primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("YouTube MP4")
        log("Descargando video de YouTube...")
        try:
            out_path = descargar_video_youtube_mp4(url, log_fn=log)
            log(f"✅ Video MP4 guardado: {out_path}")
            log("Finalizado proceso de YouTube MP4.")
            log("Fin de la automatizacion.")
            beep_fin()
        except Exception as e:
            log(f"Error descargando MP4 de YouTube: {e}")
        finally:
            stop_control.set_busy(False)

    def iniciar_descarga_youtube_mp4():
        threading.Thread(target=descargar_mp4_youtube, daemon=True).start()

    btn_yt_mp4 = ctk.CTkButton(
        yt_mp4_card,
        text="Descargar MP4",
        command=iniciar_descarga_youtube_mp4,
        height=46
    )
    btn_yt_mp4.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))

    btn_yt_mp4_open = ctk.CTkButton(
        yt_mp4_card,
        text="Abrir Descargas YouTube",
        command=abrir_descargas,
        height=40
    )
    btn_yt_mp4_open.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))

    # --- Actividad ---
    tab_act.grid_columnconfigure(0, weight=2)
    tab_act.grid_columnconfigure(1, weight=1)
    tab_act.grid_rowconfigure(0, weight=1)

    logs_card = ctk.CTkFrame(tab_act, corner_radius=12)
    logs_card.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    logs_card.grid_rowconfigure(1, weight=1)
    logs_card.grid_columnconfigure(0, weight=1)

    lbl_logs = ctk.CTkLabel(logs_card, text="Actividad", font=ctk.CTkFont(size=15, weight="bold"))
    lbl_logs.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

    txt_logs = ctk.CTkTextbox(logs_card, corner_radius=8)
    txt_logs.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
    txt_logs.configure(state="disabled")

    tools = ctk.CTkFrame(tab_act, corner_radius=12)
    tools.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
    tools.grid_columnconfigure(0, weight=1)

    lbl_tools = ctk.CTkLabel(tools, text="Herramientas", font=ctk.CTkFont(size=15, weight="bold"))
    lbl_tools.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

    btn_abrir = ctk.CTkButton(tools, text="Abrir Transcripciones", command=abrir_transcripciones, height=40)
    btn_abrir.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))

    btn_eliminar = ctk.CTkButton(
        tools,
        text="Eliminar Audios",
        command=lambda: eliminar_audios(log),
        fg_color="#b91c1c",
        hover_color="#991b1b",
        height=40
    )
    btn_eliminar.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))

    btn_stop = ctk.CTkButton(
        tools,
        text="Detener procesos",
        command=lambda: stop_control.request_stop(log),
        fg_color="#b45309",
        hover_color="#92400e",
        height=40
    )
    btn_stop.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 12))

    set_preview_enabled(True)
    actualizar_etiquetas_rango()
    actualizar_etiquetas_rango_ind()
    ventana.after(150, lambda: getattr(corte_scroll, "_parent_canvas", None) and corte_scroll._parent_canvas.yview_moveto(0))

    return ventana, None, log, None

