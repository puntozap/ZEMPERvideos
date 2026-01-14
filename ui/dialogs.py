from tkinter import filedialog, messagebox

def seleccionar_video():
    return filedialog.askopenfilename(
        title="Seleccionar video",
        filetypes=[
            ("Videos", "*.mp4;*.mkv;*.mov;*.avi;*.flv;*.webm"),
            ("Todos", "*.*"),
        ],
    )

def seleccionar_audio():
    return filedialog.askopenfilename(
        title="Seleccionar audio",
        filetypes=[
            ("Audio", "*.wav;*.mp3;*.m4a;*.flac;*.ogg;*.webm;*.mp4"),
            ("Todos", "*.*"),
        ],
    )

def mostrar_info(msg: str):
    messagebox.showinfo("Información", msg)

def mostrar_error(msg: str):
    messagebox.showerror("Error", msg)
