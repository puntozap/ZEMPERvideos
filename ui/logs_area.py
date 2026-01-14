import tkinter as tk
from tkinter.scrolledtext import ScrolledText

class LogsArea:
    def __init__(self, master):
        self.txt_logs = ScrolledText(master, wrap="word", height=14, state="disabled")
        self.txt_logs.pack(fill="both", expand=True, padx=10, pady=8)

    def log(self, msg: str):
        self.txt_logs.config(state="normal")
        self.txt_logs.insert(tk.END, msg + "\n")
        self.txt_logs.see(tk.END)
        self.txt_logs.config(state="disabled")

    def limpiar(self):
        self.txt_logs.config(state="normal")
        self.txt_logs.delete("1.0", tk.END)
        self.txt_logs.config(state="disabled")
