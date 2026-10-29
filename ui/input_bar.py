"""Bottom input: auto-expanding textfield, image attach, send."""
import flet as ft

from ui import theme


class InputBar(ft.Container):
    def __init__(self, on_send, on_attach_image):
        self.on_send = on_send
        self.on_attach_image = on_attach_image
        self.attached_image_path: str | None = None

        self.attachment_label = ft.Text("", size=11, color=theme.TEXT_SECONDARY, visible=False)

        self.text_field = ft.TextField(
            hint_text="Message... (Shift+Enter for newline)",
            multiline=True,
            min_lines=1,
            max_lines=8,
            border_color=theme.BORDER,
            focused_border_color=theme.ACCENT,
            bgcolor=theme.BG_SURFACE_2,
            color=theme.TEXT_PRIMARY,
            hint_style=ft.TextStyle(color=theme.TEXT_MUTED),
            text_size=14,
            expand=True,
            shift_enter=True,
            on_submit=self._submit,
        )

        self.file_picker = ft.FilePicker(on_result=self._file_picked)

        attach_btn = ft.IconButton(
            icon=ft.icons.IMAGE_OUTLINED,
            icon_color=theme.TEXT_SECONDARY,
            tooltip="Attach image",
            on_click=lambda e: self.file_picker.pick_files(
                allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE
            ),
        )

        send_btn = ft.IconButton(
            icon=ft.icons.ARROW_UPWARD,
            icon_color="#FFFFFF",
            bgcolor=theme.ACCENT,
            tooltip="Send",
            on_click=self._submit,
        )

        super().__init__(
            padding=ft.padding.symmetric(horizontal=20, vertical=16),
            bgcolor=theme.BG,
            content=ft.Column(
                [
                    self.attachment_label,
                    ft.Row(
                        [self.file_picker, attach_btn, self.text_field, send_btn],
                        vertical_alignment=ft.CrossAxisAlignment.END,
                        spacing=8,
                    ),
                ],
                spacing=4,
                tight=True,
            ),
        )

    def _file_picked(self, e: ft.FilePickerResultEvent):
        if e.files:
            self.attached_image_path = e.files[0].path
            self.attachment_label.value = f"\U0001F4CE {e.files[0].name}"
            self.attachment_label.visible = True
            self.attachment_label.update()
            if self.on_attach_image:
                self.on_attach_image(self.attached_image_path)

    def clear_attachment(self):
        self.attached_image_path = None
        self.attachment_label.visible = False
        self.attachment_label.update()

    def _submit(self, e):
        text = self.text_field.value.strip() if self.text_field.value else ""
        if not text:
            return
        image_path = self.attached_image_path
        self.text_field.value = ""
        self.text_field.update()
        self.clear_attachment()
        if self.on_send:
            self.on_send(text, image_path)

    def set_enabled(self, enabled: bool):
        self.text_field.disabled = not enabled
        self.text_field.update()
