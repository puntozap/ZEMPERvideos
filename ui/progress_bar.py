import tkinter as tk
from tkinter import ttk

class ProgressBarUI:
    def __init__(self, master):
        self.progress = ttk.Progressbar(master, orient="horizontal", length=550, mode="determinate")
        self.progress.pack(pady=10)

    def actualizar(self, valor, maximo=100):
        self.progress["maximum"] = maximo
        self.progress["value"] = valor
        self.progress.update_idletasks()

    def reset(self):
        self.actualizar(0, 100)
