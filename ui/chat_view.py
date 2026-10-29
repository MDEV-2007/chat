"""Message stream rendering: user bubbles right, assistant left, markdown+code."""
import re

import flet as ft

from ui import theme

CODE_FENCE_RE = re.compile(r"```(\w*)\n?(.*?)```", re.S)


def _parse_segments(text: str) -> list[tuple[str, str, str]]:
    """Splits text into ('text', '', chunk) / ('code', lang, chunk) segments."""
    segments = []
    last = 0
    for m in CODE_FENCE_RE.finditer(text):
        if m.start() > last:
            segments.append(("text", "", text[last:m.start()]))
        segments.append(("code", m.group(1) or "", m.group(2)))
        last = m.end()
    if last < len(text):
        segments.append(("text", "", text[last:]))
    if not segments:
        segments.append(("text", "", text))
    return segments


class ChatView(ft.Container):
    def __init__(self):
        self.list_view = ft.ListView(expand=True, spacing=18, padding=24, auto_scroll=True)
        super().__init__(expand=True, content=self.list_view, bgcolor=theme.BG)

    def clear(self):
        self.list_view.controls.clear()
        self.update()

    def add_user_message(self, content: str, image_path: str | None = None):
        items = []
        if image_path:
            items.append(
                ft.Image(src=image_path, width=220, border_radius=8, fit=ft.ImageFit.CONTAIN)
            )
        items.append(ft.Text(content, size=14, color="#FFFFFF", selectable=True))

        bubble = ft.Container(
            content=ft.Column(items, spacing=8, tight=True),
            bgcolor=theme.USER_BUBBLE,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=ft.border_radius.only(top_left=16, top_right=16, bottom_left=16, bottom_right=4),
            width=560,
        )
        row = ft.Row([bubble], alignment=ft.MainAxisAlignment.END)
        self.list_view.controls.append(row)
        self.update()

    def _code_block(self, lang: str, code: str) -> ft.Control:
        code = code.rstrip("\n")

        def copy_click(e):
            e.control.page.set_clipboard(code)
            e.control.page.open(ft.SnackBar(content=ft.Text("Copied"), duration=1200))

        header = ft.Row(
            [
                ft.Text(lang or "code", size=11, color=theme.TEXT_MUTED, font_family=theme.FONT_MONO),
                ft.IconButton(
                    icon=ft.icons.CONTENT_COPY,
                    icon_size=14,
                    icon_color=theme.TEXT_SECONDARY,
                    tooltip="Copy",
                    on_click=copy_click,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        body = ft.Markdown(
            f"```{lang}\n{code}\n```",
            selectable=True,
            code_theme="atom-one-dark",
            code_style=ft.TextStyle(font_family=theme.FONT_MONO, size=13),
        )
        return ft.Container(
            content=ft.Column([header, body], spacing=4, tight=True),
            bgcolor=theme.CODE_BG,
            border=ft.border.all(1, theme.BORDER),
            border_radius=8,
            padding=ft.padding.only(left=12, right=4, top=2, bottom=10),
        )

    def _render_segments(self, content: str) -> ft.Column:
        controls = []
        for kind, lang, chunk in _parse_segments(content):
            if kind == "code":
                controls.append(self._code_block(lang, chunk))
            elif chunk.strip():
                controls.append(
                    ft.Markdown(
                        chunk,
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                    )
                )
        if not controls:
            controls.append(ft.Text("", selectable=True))
        return ft.Column(controls, spacing=8, tight=True)

    def add_assistant_message(self, content: str = "") -> ft.Container:
        """Returns the bubble container; use update_streaming/finalize to refresh it.
        bubble.data holds live control refs: thinking_text, streaming_md."""
        thinking_text = ft.Text("Thinking... 0.0s", size=12, color=theme.TEXT_MUTED)
        thinking_row = ft.Row(
            [ft.ProgressRing(width=14, height=14, stroke_width=2, color=theme.ACCENT), thinking_text],
            spacing=8,
        )
        bubble = ft.Container(
            content=self._render_segments(content) if content else thinking_row,
            bgcolor=theme.ASSISTANT_BUBBLE,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=ft.border_radius.only(top_left=16, top_right=16, bottom_left=4, bottom_right=16),
            width=680,
        )
        bubble.data = {"thinking_text": thinking_text, "streaming_md": None}
        row = ft.Row([bubble], alignment=ft.MainAxisAlignment.START)
        self.list_view.controls.append(row)
        self.update()
        return bubble

    def update_thinking_elapsed(self, bubble: ft.Container, elapsed: float):
        """Ticks the 'Thinking... N.Ns' label while waiting for the first token."""
        data = bubble.data or {}
        if data.get("streaming_md") is not None:
            return
        text_ctrl = data.get("thinking_text")
        if text_ctrl and text_ctrl.page:
            text_ctrl.value = f"Thinking... {elapsed:.1f}s"
            text_ctrl.update()

    def update_streaming(self, bubble: ft.Container, content: str):
        """Cheap streaming update: plain Text, no markdown parsing (that's O(len) per
        update and was competing with scroll gestures on the UI thread). Markdown/code
        rendering happens once, at finalize_assistant_message."""
        data = bubble.data or {}
        text_ctrl = data.get("streaming_text")
        if text_ctrl is None:
            text_ctrl = ft.Text(content, size=14, color=theme.TEXT_PRIMARY, selectable=False)
            data["streaming_text"] = text_ctrl
            bubble.data = data
            bubble.content = text_ctrl
            bubble.update()
        else:
            text_ctrl.value = content
            text_ctrl.update()

    def finalize_assistant_message(self, bubble: ft.Container, content: str, stats_text: str | None = None):
        """Final render with per-code-block copy buttons, called once streaming ends."""
        segments = self._render_segments(content)
        if stats_text:
            segments.controls.append(
                ft.Text(stats_text, size=11, color=theme.TEXT_MUTED)
            )
        bubble.content = segments
        bubble.data = None
        bubble.update()
        self.scroll_to_end()

    def scroll_to_end(self):
        if self.list_view.controls and self.list_view.page:
            self.list_view.scroll_to(offset=-1, duration=0)

    def add_tool_call(self, name: str, args: dict):
        args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
        row = ft.Row(
            [
                ft.Icon(ft.icons.BUILD_OUTLINED, size=13, color=theme.TEXT_MUTED),
                ft.Text(
                    f"{name}({args_str})",
                    size=12,
                    color=theme.TEXT_MUTED,
                    font_family=theme.FONT_MONO,
                    selectable=True,
                ),
            ],
            spacing=6,
        )
        self.list_view.controls.append(row)
        self.update()

    def add_tool_result(self, name: str, result: dict):
        ok = result.get("ok", True)
        summary = "ok" if ok else f"error: {result.get('error', '?')}"
        row = ft.Row(
            [
                ft.Icon(
                    ft.icons.CHECK_CIRCLE_OUTLINE if ok else ft.icons.ERROR_OUTLINE,
                    size=13,
                    color=theme.TEXT_MUTED if ok else "#E06C75",
                ),
                ft.Text(
                    f"{name} -> {summary}",
                    size=12,
                    color=theme.TEXT_MUTED if ok else "#E06C75",
                    font_family=theme.FONT_MONO,
                    selectable=True,
                ),
            ],
            spacing=6,
        )
        self.list_view.controls.append(row)
        self.update()
