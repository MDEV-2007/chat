"""Chat history sidebar."""
import flet as ft

from core import db
from ui import theme


class Sidebar(ft.Container):
    def __init__(self, on_select_chat, on_new_chat):
        self.on_select_chat = on_select_chat
        self.on_new_chat = on_new_chat
        self.selected_chat_id = None

        self.list_view = ft.ListView(expand=True, spacing=2, padding=ft.padding.only(top=8))

        new_chat_btn = ft.Container(
            content=ft.Row(
                [ft.Icon(ft.icons.ADD, size=16, color=theme.TEXT_PRIMARY), ft.Text("New Chat", size=13, color=theme.TEXT_PRIMARY)],
                spacing=8,
            ),
            padding=10,
            border_radius=8,
            bgcolor=theme.BG_SURFACE_2,
            on_click=lambda e: self.on_new_chat(),
            ink=True,
        )

        super().__init__(
            width=260,
            bgcolor=theme.BG_SURFACE,
            padding=10,
            content=ft.Column(
                [new_chat_btn, ft.Container(height=8), self.list_view],
                expand=True,
            ),
        )

    def refresh(self, active_chat_id=None):
        self.selected_chat_id = active_chat_id
        chats = db.list_chats()
        self.list_view.controls.clear()
        for chat in chats:
            is_active = chat["id"] == active_chat_id
            self.list_view.controls.append(self._row(chat, is_active))
        self.update()

    def _row(self, chat, is_active) -> ft.Control:
        return ft.Container(
            content=ft.Text(
                chat["title"] or "New Chat",
                size=13,
                color=theme.TEXT_PRIMARY if is_active else theme.TEXT_SECONDARY,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            padding=ft.padding.symmetric(horizontal=10, vertical=9),
            border_radius=8,
            bgcolor=theme.BG_SURFACE_2 if is_active else None,
            on_click=lambda e, cid=chat["id"]: self.on_select_chat(cid),
            ink=True,
        )
