"""Model switcher dropdown: shows kind icon + model name."""
import flet as ft

from core.config import guess_kind, KIND_ICON
from ui import theme


class ModelSwitcher(ft.Container):
    def __init__(self, models: list[str], current_model: str, on_change):
        self.on_change = on_change
        self.models = models

        self.dropdown = ft.Dropdown(
            value=current_model if current_model in models else (models[0] if models else None),
            options=[ft.dropdown.Option(m, text=f"{KIND_ICON[guess_kind(m)]}  {m}") for m in models],
            width=260,
            border_color=theme.BORDER,
            bgcolor=theme.BG_SURFACE_2,
            color=theme.TEXT_PRIMARY,
            text_size=13,
            content_padding=10,
            on_change=self._changed,
        )

        super().__init__(content=self.dropdown)

    def _changed(self, e):
        if self.on_change:
            self.on_change(self.dropdown.value)

    def set_models(self, models: list[str]):
        self.models = models
        self.dropdown.options = [
            ft.dropdown.Option(m, text=f"{KIND_ICON[guess_kind(m)]}  {m}") for m in models
        ]
        self.update()

    def set_value(self, model: str):
        self.dropdown.value = model
        self.update()

    @property
    def value(self) -> str:
        return self.dropdown.value
