"""Lightweight local fallback for CustomTkinter-style widgets.

This keeps the app runnable without the external `customtkinter` package.
It intentionally covers only the widget surface used by this project.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

__all__ = [
    "CTk",
    "CTkButton",
    "CTkEntry",
    "CTkFrame",
    "CTkLabel",
    "CTkProgressBar",
    "CTkScrollableFrame",
    "CTkTextbox",
    "CTkFont",
    "set_appearance_mode",
    "set_default_color_theme",
]


def set_appearance_mode(_mode: str) -> None:
    return None


def set_default_color_theme(_theme: str) -> None:
    return None


def _strip_custom_kwargs(kwargs: dict) -> None:
    for key in (
        "corner_radius",
        "fg_color",
        "border_width",
        "hover_color",
        "text_color",
        "scrollbar_button_color",
        "scrollbar_button_hover_color",
        "button_color",
        "progress_color",
        "indeterminate_speed",
        "determinate_speed",
        "border_spacing",
    ):
        kwargs.pop(key, None)


class CTk(tk.Tk):
    pass


class CTkFrame(tk.Frame):
    def __init__(self, master=None, **kwargs):
        _strip_custom_kwargs(kwargs)
        super().__init__(master, **kwargs)


class CTkScrollableFrame(tk.Frame):
    """Scrollable frame dung Canvas + Scrollbar thay the CTkScrollableFrame that."""

    def __init__(self, master=None, **kwargs):
        _strip_custom_kwargs(kwargs)
        super().__init__(master, **kwargs)

        self._canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self._scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(self._canvas)
        self._window_id = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<Button-4>", self._on_mousewheel)
        self.bind_all("<Button-5>", self._on_mousewheel)

    def _on_inner_configure(self, _event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._window_id, width=event.width)

    def _on_mousewheel(self, event):
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # Forward grid layout methods to _inner so child widgets appear inside scroll area
    def grid_columnconfigure(self, index, **kwargs):
        return self._inner.grid_columnconfigure(index, **kwargs)

    def grid_rowconfigure(self, index, **kwargs):
        return self._inner.grid_rowconfigure(index, **kwargs)

    def winfo_children(self):
        return self._inner.winfo_children()


class CTkLabel(tk.Label):
    def __init__(self, master=None, **kwargs):
        _strip_custom_kwargs(kwargs)
        super().__init__(master, **kwargs)


class CTkEntry(tk.Entry):
    def __init__(self, master=None, **kwargs):
        _strip_custom_kwargs(kwargs)
        kwargs.pop("height", None)
        super().__init__(master, **kwargs)


class CTkTextbox(tk.Text):
    def __init__(self, master=None, **kwargs):
        _strip_custom_kwargs(kwargs)
        kwargs.pop("height", None)
        super().__init__(master, **kwargs)


class CTkButton(tk.Button):
    def __init__(self, master=None, **kwargs):
        _strip_custom_kwargs(kwargs)
        kwargs.pop("height", None)
        super().__init__(master, **kwargs)


class CTkProgressBar(ttk.Progressbar):
    def __init__(self, master=None, **kwargs):
        _strip_custom_kwargs(kwargs)
        kwargs.setdefault("mode", "indeterminate")
        kwargs.setdefault("maximum", 100)
        super().__init__(master, **kwargs)

    def set(self, value: float) -> None:
        try:
            self["value"] = float(value) * 100
        except Exception:
            self["value"] = 0


class CTkFont(tkfont.Font):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("family", "TkDefaultFont")
        super().__init__(*args, **kwargs)