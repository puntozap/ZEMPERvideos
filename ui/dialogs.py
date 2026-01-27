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

def seleccionar_imagen():
    return filedialog.askopenfilename(
        title="Seleccionar imagen de fondo",
        filetypes=[
            ("Imagenes", "*.png;*.jpg;*.jpeg;*.webp"),
            ("Todos", "*.*"),
        ],
    )

def seleccionar_archivo(title: str, filetypes):
    return filedialog.askopenfilename(
        title=title,
        filetypes=filetypes,
    )

def mostrar_info(msg: str):
    messagebox.showinfo("Información", msg)

def mostrar_error(msg: str):
    messagebox.showerror("Error", msg)
