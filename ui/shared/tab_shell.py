import customtkinter as ctk


def create_tab_shell(parent, *, padx=6, pady=6, scroll_kwargs=None):
    """
    Build a tab shell that ensures every screen can scroll when content exceeds the panel height.

    Returns (container_frame, scrollable_frame). The `scrollable_frame` is where the tab
    adds its widgets.
    """
    scroll_kwargs = scroll_kwargs or {}
    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.grid(row=0, column=0, sticky="nsew", padx=padx, pady=pady)
    container.grid_columnconfigure(0, weight=1)
    container.grid_rowconfigure(0, weight=1)

    scroll_args = {"corner_radius": 12, "fg_color": "transparent"}
    scroll_args.update(scroll_kwargs)
    scroll_area = ctk.CTkScrollableFrame(container, **scroll_args)
    scroll_area.grid(row=0, column=0, sticky="nsew")
    scroll_area.grid_columnconfigure(0, weight=1)

    return container, scroll_area
