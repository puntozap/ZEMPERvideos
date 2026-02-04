from __future__ import annotations

import tkinter as tk


class Tooltip:
    """
    Minimal tooltip for Tk/CustomTkinter widgets.

    Usage:
        Tooltip(widget, "text")
    """

    def __init__(self, widget: tk.Widget, text: str, *, delay_ms: int = 450):
        self.widget = widget
        self.text = text or ""
        self.delay_ms = max(0, int(delay_ms))
        self._after_id = None
        self._tip: tk.Toplevel | None = None

        widget.bind("<Enter>", self._on_enter, add=True)
        widget.bind("<Leave>", self._on_leave, add=True)
        widget.bind("<ButtonPress>", self._on_leave, add=True)

    def _on_enter(self, event=None):
        if not self.text:
            return
        self._cancel()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _on_leave(self, event=None):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = None

    def _show(self):
        if self._tip or not self.text:
            return
        try:
            x = self.widget.winfo_pointerx() + 12
            y = self.widget.winfo_pointery() + 12
        except Exception:
            x = y = 0
        tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        tip.attributes("-topmost", True)

        label = tk.Label(
            tip,
            text=self.text,
            justify="left",
            background="#111317",
            foreground="#e6e6e6",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=6,
            wraplength=520,
        )
        label.pack()
        self._tip = tip

    def _hide(self):
        if self._tip is None:
            return
        try:
            self._tip.destroy()
        except Exception:
            pass
        self._tip = None

