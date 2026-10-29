"""Colors, fonts, Flet ThemeData for dark-first minimal look."""
import flet as ft

BG = "#0F0F10"
BG_SURFACE = "#17171A"
BG_SURFACE_2 = "#1E1E22"
BORDER = "#2A2A2E"

ACCENT = "#6366F1"  # indigo
ACCENT_HOVER = "#7C7FF5"

TEXT_PRIMARY = "#E7E7E9"
TEXT_SECONDARY = "#9B9BA3"
TEXT_MUTED = "#6B6B74"

CODE_BG = "#0B0B0D"

USER_BUBBLE = ACCENT
ASSISTANT_BUBBLE = BG_SURFACE_2

FONT_MONO = "Consolas, monospace"


def build_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=ACCENT,
            surface=BG_SURFACE,
            background=BG,
            on_primary="#FFFFFF",
            on_surface=TEXT_PRIMARY,
            on_background=TEXT_PRIMARY,
        ),
        scrollbar_theme=ft.ScrollbarTheme(
            thumb_color={"": BORDER},
            track_color={"": "transparent"},
        ),
    )
