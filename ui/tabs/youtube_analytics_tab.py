from __future__ import annotations

from datetime import date, timedelta
import threading
import webbrowser

import customtkinter as ctk
import tkinter as tk

from core.youtube_api import (
    listar_videos_subidos,
    obtener_estadisticas_video,
    obtener_vistas_por_pais,
    listar_comentarios_video,
    obtener_videos_mas_comentados,
)
from ui.shared import helpers
from ui.shared.tooltip import Tooltip


def _safe_int(value: str, default: int = 0) -> int:
    try:
        return int((value or "").strip())
    except Exception:
        return default


def _truncate(text: str, max_len: int = 70) -> str:
    s = (text or "").replace("\n", " ").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def create_tab(parent, context):
    log_global = context.get("log_global") or context.get("log")
    stop_control = context.get("stop_control")

    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
    container.grid_columnconfigure(0, weight=1)
    container.grid_columnconfigure(1, weight=0)
    container.grid_rowconfigure(0, weight=1)

    # Right activity panel (always visible on the right).
    log_card, _txt, log = helpers.create_log_panel(
        container,
        title="Actividad Analitica",
        height=520,
        mirror_fn=log_global,
    )
    log_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

    main = ctk.CTkFrame(container, corner_radius=12)
    main.grid(row=0, column=0, sticky="nsew")
    main.grid_columnconfigure(0, weight=1)
    main.grid_rowconfigure(1, weight=1)

    # Top area: left = date range, right = filters/actions.
    top = ctk.CTkFrame(main, fg_color="transparent")
    top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
    top.grid_columnconfigure(0, weight=0)
    top.grid_columnconfigure(1, weight=1)

    start_var = tk.StringVar(value=(date.today() - timedelta(days=30)).isoformat())
    end_var = tk.StringVar(value=date.today().isoformat())

    dates = ctk.CTkFrame(top, corner_radius=10, fg_color="#1e1e22")
    dates.grid(row=0, column=0, sticky="w")
    dates.grid_columnconfigure(1, weight=1)
    dates.grid_columnconfigure(3, weight=1)
    ctk.CTkLabel(dates, text="Desde:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=(10, 6), pady=10)
    ctk.CTkEntry(dates, textvariable=start_var, width=120, placeholder_text="YYYY-MM-DD").grid(row=0, column=1, sticky="ew", pady=10)
    ctk.CTkLabel(dates, text="Hasta:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, sticky="w", padx=(12, 6), pady=10)
    ctk.CTkEntry(dates, textvariable=end_var, width=120, placeholder_text="YYYY-MM-DD").grid(row=0, column=3, sticky="ew", pady=10, padx=(0, 10))

    videos_limit_var = tk.StringVar(value="0")  # 0 = all (guardrail inside core)
    comments_limit_var = tk.StringVar(value="20")  # 0 = all (guardrail inside core)
    include_replies_var = tk.BooleanVar(value=False)
    query_var = tk.StringVar(value="")

    # Horizontal-scrollable filters area (X scroll) to avoid clipping on small windows.
    filters_outer = ctk.CTkFrame(top, corner_radius=10, fg_color="#1e1e22")
    filters_outer.grid(row=0, column=1, sticky="ew", padx=(12, 0))
    filters_outer.grid_columnconfigure(0, weight=1)
    # Keep the filters row compact; the canvas provides horizontal scrolling only.
    filters_canvas = tk.Canvas(filters_outer, highlightthickness=0, bg="#1e1e22", height=78)
    filters_canvas.grid(row=0, column=0, sticky="ew")
    filters_scroll_x = ctk.CTkScrollbar(filters_outer, orientation="horizontal", command=filters_canvas.xview)
    filters_scroll_x.grid(row=1, column=0, sticky="ew")
    filters_canvas.configure(xscrollcommand=filters_scroll_x.set)

    filters = ctk.CTkFrame(filters_canvas, fg_color="transparent")
    filters_window = filters_canvas.create_window((0, 0), window=filters, anchor="nw")

    def _sync_filters_scroll(_event=None):
        try:
            bbox = filters_canvas.bbox("all")
            if bbox:
                filters_canvas.configure(scrollregion=bbox)
                # Keep the inner frame height in sync so it doesn't collapse.
                req_h = max(1, filters.winfo_reqheight())
                filters_canvas.itemconfigure(filters_window, height=req_h)
                # Hide the horizontal scrollbar if not needed.
                if bbox[2] <= filters_canvas.winfo_width():
                    filters_scroll_x.grid_remove()
                else:
                    filters_scroll_x.grid()
        except Exception:
            pass

    filters.bind("<Configure>", _sync_filters_scroll)
    filters_outer.bind("<Configure>", lambda e: filters_canvas.configure(width=e.width))

    for col in range(9):
        filters.grid_columnconfigure(col, weight=0)
    filters.grid_columnconfigure(3, weight=1)

    ctk.CTkLabel(filters, text="Videos:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=(10, 6), pady=(10, 4))
    ctk.CTkEntry(filters, textvariable=videos_limit_var, width=70).grid(row=0, column=1, sticky="w", pady=(10, 4))
    ctk.CTkLabel(filters, text="(0=all)", text_color="#9aa4b2").grid(row=0, column=2, sticky="w", padx=(6, 12), pady=(10, 4))
    ctk.CTkEntry(filters, textvariable=query_var, placeholder_text="Buscar titulo...").grid(row=0, column=3, sticky="ew", pady=(10, 4))
    btn_load = ctk.CTkButton(filters, text="Cargar", width=110)
    btn_load.grid(row=0, column=4, sticky="e", padx=(12, 10), pady=(10, 4))

    ctk.CTkLabel(filters, text="Comentarios:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", padx=(10, 6), pady=(0, 10))
    ctk.CTkEntry(filters, textvariable=comments_limit_var, width=70).grid(row=1, column=1, sticky="w", pady=(0, 10))
    ctk.CTkLabel(filters, text="(0=all)", text_color="#9aa4b2").grid(row=1, column=2, sticky="w", padx=(6, 12), pady=(0, 10))
    ctk.CTkCheckBox(filters, text="Incluir respuestas", variable=include_replies_var).grid(row=1, column=3, sticky="w", pady=(0, 10))
    btn_refresh = ctk.CTkButton(filters, text="Refrescar", width=110)
    btn_refresh.grid(row=1, column=4, sticky="e", padx=(12, 10), pady=(0, 10))

    btn_copy_titles = ctk.CTkButton(filters, text="Copiar titulos", width=140)
    btn_copy_titles.grid(row=0, column=8, sticky="e", padx=(10, 10), pady=(10, 4))

    btn_clear_search = ctk.CTkButton(filters, text="Limpiar buscador", width=160)
    btn_clear_search.grid(row=1, column=8, sticky="e", padx=(10, 10), pady=(0, 10))

    # "Most commented" list controls
    most_limit_var = tk.StringVar(value="50")
    ctk.CTkLabel(filters, text="Top comentados:", font=ctk.CTkFont(weight="bold")).grid(
        row=0, column=5, sticky="w", padx=(6, 6), pady=(10, 4)
    )
    ctk.CTkEntry(filters, textvariable=most_limit_var, width=70).grid(row=0, column=6, sticky="w", pady=(10, 4))
    ctk.CTkLabel(filters, text="(0=all)", text_color="#9aa4b2").grid(row=0, column=7, sticky="w", padx=(6, 0), pady=(10, 4))
    btn_load_most = ctk.CTkButton(filters, text="Cargar comentados", width=160)
    btn_load_most.grid(row=1, column=5, columnspan=3, sticky="e", padx=(6, 10), pady=(0, 10))

    # Bottom area: left list (scroll) and right details (scroll).
    bottom = ctk.CTkFrame(main, fg_color="transparent")
    bottom.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
    bottom.grid_columnconfigure(0, weight=0)
    bottom.grid_columnconfigure(1, weight=1)
    bottom.grid_rowconfigure(0, weight=1)

    list_card = ctk.CTkFrame(bottom, corner_radius=10, fg_color="#1e1e22")
    list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
    list_card.grid_rowconfigure(2, weight=1)
    list_card.grid_columnconfigure(0, weight=1)
    list_card.configure(width=320)
    list_card.grid_propagate(False)

    list_mode_var = tk.StringVar(value="Videos (publicos)")
    ctk.CTkLabel(list_card, textvariable=list_mode_var, font=ctk.CTkFont(size=13, weight="bold")).grid(
        row=0, column=0, sticky="w", padx=10, pady=(10, 6)
    )
    ctk.CTkEntry(list_card, textvariable=query_var, placeholder_text="Buscar...").grid(
        row=1, column=0, sticky="ew", padx=10, pady=(0, 10)
    )
    list_scroll = ctk.CTkScrollableFrame(list_card, corner_radius=8, fg_color="#1c1c1f")
    list_scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
    list_scroll.grid_columnconfigure(0, weight=1)

    details = ctk.CTkScrollableFrame(bottom, corner_radius=10, fg_color="#1e1e22")
    details.grid(row=0, column=1, sticky="nsew")
    details.grid_columnconfigure(0, weight=1)

    # Details widgets
    selected_title_var = tk.StringVar(value="Selecciona un video para ver detalles.")
    stats_var = tk.StringVar(value="Views: - | Likes: - | Comments: -")
    title_label = ctk.CTkLabel(
        details,
        textvariable=selected_title_var,
        font=ctk.CTkFont(size=14, weight="bold"),
        wraplength=760,
        justify="left",
    )
    title_label.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))

    link_var = tk.StringVar(value="")
    link_row = ctk.CTkFrame(details, fg_color="transparent")
    link_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
    link_row.grid_columnconfigure(0, weight=1)
    link_entry = ctk.CTkEntry(link_row, textvariable=link_var, state="readonly")
    link_entry.grid(row=0, column=0, sticky="ew")
    ctk.CTkButton(
        link_row,
        text="Abrir",
        width=90,
        command=lambda: link_var.get() and webbrowser.open(link_var.get()),
    ).grid(row=0, column=1, sticky="e", padx=(8, 0))

    ctk.CTkLabel(details, textvariable=stats_var, text_color="#d7d8de").grid(
        row=2, column=0, sticky="w", padx=12, pady=(0, 10)
    )

    decision_box = ctk.CTkTextbox(details, height=120, corner_radius=8)
    decision_box.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))
    decision_box.configure(state="disabled")

    geo_box = ctk.CTkTextbox(details, height=140, corner_radius=8)
    geo_box.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 10))
    geo_box.configure(state="disabled")

    comments_box = ctk.CTkTextbox(details, height=520, corner_radius=8)
    comments_box.grid(row=5, column=0, sticky="nsew", padx=12, pady=(0, 12))
    comments_box.configure(state="disabled")

    selected_video_id: str | None = None
    video_items: list[dict] = []
    list_buttons: list[ctk.CTkButton] = []
    comments_period_map: dict[str, int] = {}

    def _set_box(box: ctk.CTkTextbox, text: str) -> None:
        box.configure(state="normal")
        box.delete("1.0", "end")
        if text:
            box.insert("1.0", text)
        box.configure(state="disabled")

    def _set_decision(text: str) -> None:
        _set_box(decision_box, text)

    def _render_list() -> None:
        for btn in list_buttons:
            btn.destroy()
        list_buttons.clear()

        q = (query_var.get() or "").strip().lower()
        shown = 0
        for item in video_items:
            title = item.get("title") or ""
            if q and q not in title.lower():
                continue
            tag = "Short" if item.get("is_short") else "Video"
            vid = item.get("video_id") or ""
            comments_period = item.get("comments_period")
            comments_total = item.get("comments_total")
            if comments_period is not None:
                label = f"[{tag}] {_truncate(title, 56)}  ({comments_period})"
            elif comments_total is not None:
                label = f"[{tag}] {_truncate(title, 56)}  ({comments_total})"
            else:
                label = f"[{tag}] {_truncate(title, 64)}"

            def _on_click(v_id=str(vid), v_title=str(title), v_tag=str(tag)) -> None:
                nonlocal selected_video_id
                selected_video_id = v_id
                selected_title_var.set(f"[{v_tag}] {v_title} ({v_id})")
                threading.Thread(target=_fetch_details, daemon=True).start()

            btn = ctk.CTkButton(list_scroll, text=label, anchor="w", command=_on_click, fg_color="#2a70d9")
            btn.grid(row=shown, column=0, sticky="ew", pady=(0, 6))
            Tooltip(btn, f"[{tag}] {title}")
            list_buttons.append(btn)
            shown += 1

    def _load_videos() -> None:
        if stop_control and stop_control.is_busy():
            log("Ya hay un proceso en curso.")
            return
        if stop_control:
            stop_control.set_busy(True)
        try:
            limit = _safe_int(videos_limit_var.get(), 0)
            log("Cargando lista de videos publicos (puede tardar)...")
            # 0 => all (guardrail inside core)
            videos = listar_videos_subidos(max_results=limit, only_public=True, log_fn=log)
            # Sort newest first if published_at is available.
            videos.sort(key=lambda v: (v.get("published_at") or ""), reverse=True)

            nonlocal video_items
            video_items = videos
            list_mode_var.set("Videos (publicos)")
            comments_period_map.clear()
            _render_list()
            log(f"Videos cargados: {len(videos)} (incluye largos y shorts).")
        except Exception as exc:
            log(f"Error cargando videos: {exc}")
        finally:
            if stop_control:
                stop_control.set_busy(False)

    def _fetch_details() -> None:
        if not selected_video_id:
            return
        if stop_control and stop_control.is_busy():
            # Allow refresh button to retrigger after current finishes.
            return
        if stop_control:
            stop_control.set_busy(True)
        try:
            vid = selected_video_id
            log(f"Consultando detalles: {vid}")

            stats = obtener_estadisticas_video(vid, log_fn=log)
            stats_var.set(
                f"Views: {stats.get('view_count', 0)} | Likes: {stats.get('like_count', 0)} | Comments: {stats.get('comment_count', 0)}"
            )
            link_var.set(f"https://www.youtube.com/watch?v={vid}")

            period_comments = comments_period_map.get(vid)
            is_short = False
            for it in video_items:
                if str(it.get("video_id") or "") == vid:
                    is_short = bool(it.get("is_short"))
                    break
            decision_lines = ["== Decision (basado en comentarios) =="]
            if period_comments is not None:
                decision_lines.append(f"Comentarios en el rango: {period_comments}")
            total_comments = int(stats.get("comment_count", 0) or 0)
            decision_lines.append(f"Comentarios totales: {total_comments}")
            decision_lines.append("")
            if period_comments is None:
                decision_lines.append("Tip: usa 'Cargar comentados' para ver ranking por rango.")
            else:
                if period_comments >= 100:
                    decision_lines.append("Muy alto: responde/pinea comentarios clave y crea un follow-up inmediato.")
                elif period_comments >= 30:
                    decision_lines.append("Alto: responde preguntas recurrentes y considera un video/short de seguimiento.")
                elif period_comments >= 10:
                    decision_lines.append("Medio: participa en la conversación; prueba un CTA en el próximo contenido.")
                else:
                    decision_lines.append("Bajo: revisa titulo/miniatura/gancho o publica en otro horario.")
                if is_short and period_comments >= 10:
                    decision_lines.append("Short con buena conversación: prueba serie/parte 2 con el mismo tema.")
            _set_decision("\n".join(decision_lines))

            countries = obtener_vistas_por_pais(
                video_id=vid,
                start_date=start_var.get(),
                end_date=end_var.get(),
                max_results=10,
                log_fn=log,
            )
            geo_lines = ["== Vistas por pais =="]
            if not countries:
                geo_lines.append("(sin datos)")
            else:
                for entry in countries:
                    geo_lines.append(f"- {entry.get('country')}: {entry.get('views')}")
            _set_box(geo_box, "\n".join(geo_lines))

            limit = _safe_int(comments_limit_var.get(), 20)
            include_replies = bool(include_replies_var.get())
            if limit <= 0:
                log("Cargando todos los comentarios (guardrail interno)...")
            else:
                log(f"Cargando comentarios: {limit}")
            comments = listar_comentarios_video(
                video_id=vid,
                max_results=limit,
                include_replies=include_replies,
                start_date=start_var.get(),
                end_date=end_var.get(),
                log_fn=log,
            )
            comment_lines = ["== Comentarios =="]
            if not comments:
                comment_lines.append("(sin comentarios en este rango o deshabilitados)")
                comment_lines.append(f"Rango: {start_var.get()} a {end_var.get()}")
            else:
                for idx, c in enumerate(comments, start=1):
                    author = c.get("author") or ""
                    published = c.get("published_at") or ""
                    text = (c.get("text") or "").strip()
                    comment_lines.append(f"{idx}. {author} ({published})")
                    comment_lines.append(text)
                    comment_lines.append("")
            _set_box(comments_box, "\n".join(comment_lines))
            log("Listo.")
        except Exception as exc:
            log(f"Error Analytics: {exc}")
        finally:
            if stop_control:
                stop_control.set_busy(False)

    def _load_most_commented() -> None:
        if stop_control and stop_control.is_busy():
            log("Ya hay un proceso en curso.")
            return
        if stop_control:
            stop_control.set_busy(True)
        try:
            limit = _safe_int(most_limit_var.get(), 50)
            log("Cargando videos mas comentados (por rango)...")
            items = obtener_videos_mas_comentados(
                start_date=start_var.get(),
                end_date=end_var.get(),
                max_results=limit,
                only_public=True,
                log_fn=log,
            )
            # If Analytics failed, we may get comments_total instead of comments_period.
            if items and "comments_period" in items[0]:
                items.sort(key=lambda r: int(r.get("comments_period") or 0), reverse=True)
                mode_label = "Videos con comentarios (rango)"
            else:
                items.sort(key=lambda r: int(r.get("comments_total") or 0), reverse=True)
                mode_label = "Videos con comentarios (total)"
            nonlocal video_items
            video_items = items
            comments_period_map.clear()
            for it in items:
                vid = str(it.get("video_id") or "")
                if not vid:
                    continue
                try:
                    comments_period_map[vid] = int(it.get("comments_period") or 0)
                except Exception:
                    comments_period_map[vid] = 0
            list_mode_var.set(mode_label)
            _render_list()
            log(f"Cargados: {len(items)} videos con comentarios (ordenados).")
        except Exception as exc:
            log(f"Error cargando comentados: {exc}")
        finally:
            if stop_control:
                stop_control.set_busy(False)

    def _refresh_selected() -> None:
        if not selected_video_id:
            log("Selecciona un video de la lista primero.")
            return
        threading.Thread(target=_fetch_details, daemon=True).start()

    btn_load.configure(command=lambda: threading.Thread(target=_load_videos, daemon=True).start())
    btn_refresh.configure(command=_refresh_selected)
    btn_load_most.configure(command=lambda: threading.Thread(target=_load_most_commented, daemon=True).start())

    btn_clear_search.configure(command=lambda: query_var.set(""))

    def _copy_titles() -> None:
        if not video_items:
            log("No hay videos cargados para copiar.")
            return
        lines: list[str] = []
        for item in video_items:
            title = str(item.get("title") or "").strip()
            vid = str(item.get("video_id") or "").strip()
            if not title:
                continue
            if vid:
                lines.append(f"{title} - https://www.youtube.com/watch?v={vid}")
            else:
                lines.append(title)
        text = "\n".join(lines)
        try:
            parent.clipboard_clear()
            parent.clipboard_append(text)
            parent.update_idletasks()
            log(f"Copiados {len(lines)} titulos al portapapeles.")
        except Exception as exc:
            log(f"No se pudo copiar al portapapeles: {exc}")

    btn_copy_titles.configure(command=_copy_titles)
    query_var.trace_add("write", lambda *_: _render_list())

    return {"load_videos": _load_videos, "refresh": _refresh_selected}
