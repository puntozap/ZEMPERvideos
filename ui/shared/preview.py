import time
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
from moviepy import VideoFileClip


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


def create_subtitle_preview(preview_card, pos_sub_var, get_font_lines, get_video_path):
    lbl_prev = ctk.CTkLabel(preview_card, text="Vista previa (TikTok)", font=ctk.CTkFont(size=12))
    lbl_prev.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

    prev_container = tk.Frame(preview_card, bg="#111111", width=320, height=568)
    prev_container.grid(row=1, column=0, sticky="n", padx=12, pady=(0, 12))
    prev_container.grid_propagate(False)

    prev_label = tk.Label(prev_container, bg="#111111")
    prev_label.pack(fill="both", expand=True)
    sub_preview_img = {"img": None}
    prev_state = {"last_w": 0, "last_h": 0, "last_pos": None, "last_video": None, "after_id": None}
    preview_w = 320
    preview_h = 568

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
        w = preview_w
        h = preview_h
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

        font_size, max_lines = get_font_lines()
        y0, y1 = _preview_block(inner_h, is_vertical, font_size, max_lines, pos_sub_var.get())
        draw_screen = ImageDraw.Draw(screen)
        draw_screen.rectangle([8, y0, inner_w - 8, y1], outline=(255, 214, 0), width=3)

        canvas.paste(screen, (pad, pad))
        return canvas

    def update_preview():
        video_path = get_video_path()
        pos_now = pos_sub_var.get()
        w = preview_w
        h = preview_h
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

    def schedule_preview_update(_e=None):
        if prev_state["after_id"]:
            prev_container.after_cancel(prev_state["after_id"])
        prev_state["after_id"] = prev_container.after(120, update_preview)

    pos_sub_var.trace_add("write", lambda *_: update_preview())
    prev_container.bind("<Configure>", schedule_preview_update)

    return {
        "container": prev_container,
        "label": prev_label,
        "update": update_preview,
    }
