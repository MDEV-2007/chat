"""Super Chat - local Ollama desktop app. Flet entry point."""
import asyncio
import time

import flet as ft

from core import agent, db, memory
from core.config import DEFAULT_MODEL, VISION_MODELS, guess_kind
from core.ollama_client import list_models_info, stream_chat_text
from ui import theme
from ui.chat_view import ChatView
from ui.input_bar import InputBar
from ui.model_switcher import ModelSwitcher
from ui.sidebar import Sidebar


class AppState:
    def __init__(self):
        self.chat_id: int | None = None
        self.streaming: bool = False
        self.cancel_requested: bool = False


async def main(page: ft.Page):
    page.title = "Super Chat"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = theme.build_theme()
    page.bgcolor = theme.BG
    page.padding = 0
    page.window.min_width = 900
    page.window.min_height = 600

    db.init_db()
    state = AppState()

    try:
        models_info = await list_models_info()
    except Exception:
        models_info = {}
    models = list(models_info.keys()) or [DEFAULT_MODEL]

    def model_supports_tools(model_name: str) -> bool:
        return "tools" in models_info.get(model_name, [])

    chat_view = ChatView()
    input_bar = InputBar(on_send=None, on_attach_image=None)
    model_switcher = ModelSwitcher(models, DEFAULT_MODEL, on_change=None)
    system_prompt_field = ft.TextField(
        multiline=True,
        min_lines=2,
        max_lines=6,
        border_color=theme.BORDER,
        bgcolor=theme.BG_SURFACE_2,
        color=theme.TEXT_PRIMARY,
        text_size=13,
        hint_text="System prompt for this chat...",
        hint_style=ft.TextStyle(color=theme.TEXT_MUTED),
    )
    profile_list = ft.Column(spacing=4, tight=True)
    profile_new_field = ft.TextField(
        hint_text="e.g. I'm building a CNC pattern-generator app...",
        border_color=theme.BORDER,
        bgcolor=theme.BG_SURFACE_2,
        color=theme.TEXT_PRIMARY,
        text_size=13,
        expand=True,
    )

    def refresh_profile_list():
        profile_list.controls.clear()
        for fact in db.list_profile_facts():
            profile_list.controls.append(
                ft.Row(
                    [
                        ft.Text(fact["content"], size=12, color=theme.TEXT_SECONDARY, expand=True),
                        ft.IconButton(
                            icon=ft.icons.CLOSE,
                            icon_size=14,
                            icon_color=theme.TEXT_MUTED,
                            on_click=lambda e, fid=fact["id"]: delete_fact(fid),
                        ),
                    ]
                )
            )
        if profile_list.page:
            profile_list.update()

    def add_fact(e=None):
        content = (profile_new_field.value or "").strip()
        if not content:
            return
        db.add_profile_fact(content)
        profile_new_field.value = ""
        profile_new_field.update()
        refresh_profile_list()

    def delete_fact(fact_id: int):
        db.delete_profile_fact(fact_id)
        refresh_profile_list()

    advanced_panel = ft.Container(
        content=ft.Column(
            [
                ft.Text("System Prompt", size=12, weight=ft.FontWeight.BOLD, color=theme.TEXT_SECONDARY),
                system_prompt_field,
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Save",
                            bgcolor=theme.ACCENT,
                            color="#FFFFFF",
                            on_click=lambda e: save_system_prompt(),
                        ),
                        ft.PopupMenuButton(
                            content=ft.Text("Presets", size=12, color=theme.TEXT_SECONDARY),
                            items=[
                                ft.PopupMenuItem(
                                    text=p["name"],
                                    on_click=lambda e, content=p["content"]: apply_preset(content),
                                )
                                for p in db.list_presets()
                            ],
                        ),
                        ft.TextButton(
                            "Set as global default",
                            on_click=lambda e: set_global_default(),
                        ),
                    ],
                    spacing=8,
                ),
                ft.Divider(color=theme.BORDER, height=1),
                ft.Text("Profile (facts remembered across all chats)", size=12, weight=ft.FontWeight.BOLD, color=theme.TEXT_SECONDARY),
                profile_list,
                ft.Row(
                    [
                        profile_new_field,
                        ft.IconButton(icon=ft.icons.ADD, icon_color=theme.ACCENT, on_click=add_fact),
                    ]
                ),
            ],
            spacing=8,
        ),
        padding=16,
        bgcolor=theme.BG_SURFACE,
        border=ft.border.only(bottom=ft.BorderSide(1, theme.BORDER)),
        visible=False,
    )
    refresh_profile_list()

    def apply_preset(content: str):
        system_prompt_field.value = content
        system_prompt_field.update()

    def save_system_prompt():
        if state.chat_id is not None:
            db.update_chat_system_prompt(state.chat_id, system_prompt_field.value or "")
        advanced_panel.visible = False
        advanced_panel.update()

    def set_global_default():
        db.set_setting("default_system_prompt", system_prompt_field.value or "")
        page.open(ft.SnackBar(content=ft.Text("Global default system prompt saved"), duration=1500))

    def toggle_advanced(e=None):
        advanced_panel.visible = not advanced_panel.visible
        advanced_panel.update()

    advanced_btn = ft.OutlinedButton(
        "Advanced",
        icon=ft.icons.TUNE,
        on_click=toggle_advanced,
        style=ft.ButtonStyle(color=theme.TEXT_SECONDARY),
    )

    top_bar = ft.Container(
        content=ft.Row(
            [model_switcher, ft.Container(expand=True), advanced_btn],
            alignment=ft.MainAxisAlignment.START,
        ),
        padding=ft.padding.symmetric(horizontal=20, vertical=14),
        bgcolor=theme.BG_SURFACE,
        border=ft.border.only(bottom=ft.BorderSide(1, theme.BORDER)),
    )

    def load_chat(chat_id: int):
        state.chat_id = chat_id
        chat = db.get_chat(chat_id)
        model_switcher.set_value(chat["model"] or DEFAULT_MODEL)
        system_prompt_field.value = chat["system_prompt"] or ""
        chat_view.clear()
        for msg in db.list_messages(chat_id):
            if msg["role"] == "user":
                chat_view.add_user_message(msg["content"], msg["image_path"])
            else:
                chat_view.add_assistant_message(msg["content"])
        sidebar.refresh(active_chat_id=chat_id)
        page.update()

    def new_chat():
        default_prompt = db.get_setting("default_system_prompt", "")
        chat_id = db.create_chat(title="New Chat", model=model_switcher.value, system_prompt=default_prompt)
        load_chat(chat_id)

    def on_model_change(model_name: str):
        if state.chat_id is not None:
            db.update_chat_model(state.chat_id, model_name)

    model_switcher.on_change = on_model_change

    sidebar = Sidebar(on_select_chat=load_chat, on_new_chat=new_chat)

    def on_attach_image(path: str):
        vision_model = next((m for m in models if guess_kind(m) == "vision"), None)
        if vision_model and guess_kind(model_switcher.value) != "vision":
            def confirm(e):
                model_switcher.set_value(vision_model)
                on_model_change(vision_model)
                dlg.open = False
                page.update()

            def cancel(e):
                dlg.open = False
                page.update()

            dlg = ft.AlertDialog(
                title=ft.Text("Switch model?"),
                content=ft.Text(f"Image attached. Switch to vision model '{vision_model}'?"),
                actions=[
                    ft.TextButton("Cancel", on_click=cancel),
                    ft.TextButton("Switch", on_click=confirm),
                ],
            )
            page.dialog = dlg
            dlg.open = True
            page.update()

    input_bar.on_attach_image = on_attach_image

    async def build_history(chat_id: int, latest_user_text: str) -> list[dict]:
        chat = db.get_chat(chat_id)
        history = []

        profile_facts = db.list_profile_facts()
        if profile_facts:
            facts_block = "Known facts about the user (apply where relevant):\n" + "\n".join(
                f"- {f['content']}" for f in profile_facts
            )
            history.append({"role": "system", "content": facts_block})

        try:
            memory_hits = await memory.semantic_search(latest_user_text, exclude_chat_id=chat_id)
        except Exception:
            memory_hits = []
        memory_block = memory.format_memory_block(memory_hits)
        if memory_block:
            history.append({"role": "system", "content": memory_block})

        if chat["system_prompt"]:
            history.append({"role": "system", "content": chat["system_prompt"]})
        for msg in db.list_messages(chat_id):
            history.append({"role": msg["role"], "content": msg["content"]})
        return history

    async def send_message(text: str, image_path: str | None):
        if state.chat_id is None:
            new_chat()
        chat_id = state.chat_id

        chat = db.get_chat(chat_id)
        if not db.list_messages(chat_id) and (not chat["title"] or chat["title"] == "New Chat"):
            title = text[:40] + ("..." if len(text) > 40 else "")
            db.update_chat_title(chat_id, title)
            sidebar.refresh(active_chat_id=chat_id)

        user_msg_id = db.add_message(chat_id, "user", text, image_path)
        chat_view.add_user_message(text, image_path)
        page.run_task(memory.embed_and_store_message, user_msg_id, text)

        history = await build_history(chat_id, text)
        bubble = chat_view.add_assistant_message("")

        state.streaming = True
        state.cancel_requested = False
        input_bar.set_enabled(False)

        images_b64 = None
        if image_path:
            import base64
            with open(image_path, "rb") as f:
                images_b64 = [base64.b64encode(f.read()).decode()]

        t_start = time.monotonic()
        stop_ticker = {"stop": False}

        async def tick_thinking():
            while not stop_ticker["stop"]:
                await asyncio.sleep(0.2)
                if not stop_ticker["stop"]:
                    chat_view.update_thinking_elapsed(bubble, time.monotonic() - t_start)

        page.run_task(tick_thinking)

        UPDATE_INTERVAL = 0.08  # throttle UI re-renders during streaming
        last_update = 0.0
        full_response = ""
        stats: dict = {}
        try:
            if model_supports_tools(model_switcher.value) and not image_path:
                def on_tool_call(name, args):
                    chat_view.add_tool_call(name, args)

                def on_tool_result(name, result):
                    chat_view.add_tool_result(name, result)

                async for delta in agent.run_agent_turn(
                    model_switcher.value, history, on_tool_call, on_tool_result, stats=stats
                ):
                    if state.cancel_requested:
                        break
                    full_response += delta
                    now = time.monotonic()
                    if now - last_update >= UPDATE_INTERVAL:
                        chat_view.update_streaming(bubble, full_response)
                        last_update = now
            else:
                async for delta in stream_chat_text(model_switcher.value, history, images_b64, stats=stats):
                    if state.cancel_requested:
                        break
                    full_response += delta
                    now = time.monotonic()
                    if now - last_update >= UPDATE_INTERVAL:
                        chat_view.update_streaming(bubble, full_response)
                        last_update = now
        except Exception as ex:
            full_response += f"\n\n_Error: {ex}_"
        finally:
            stop_ticker["stop"] = True
            stats_text = None
            eval_count = stats.get("eval_count")
            eval_duration = stats.get("eval_duration")
            if eval_count and eval_duration:
                seconds = eval_duration / 1e9
                tok_per_sec = eval_count / seconds if seconds > 0 else 0
                stats_text = f"{eval_count} token · {seconds:.1f}s · {tok_per_sec:.0f} tok/s"
            chat_view.finalize_assistant_message(bubble, full_response, stats_text)
            if full_response.strip():
                assistant_msg_id = db.add_message(chat_id, "assistant", full_response)
                page.run_task(memory.embed_and_store_message, assistant_msg_id, full_response)
            state.streaming = False
            input_bar.set_enabled(True)
            page.update()

    def on_send(text: str, image_path: str | None):
        page.run_task(send_message, text, image_path)

    input_bar.on_send = on_send

    def close_dialog(dlg: ft.AlertDialog):
        dlg.open = False
        page.update()

    def open_model_switcher_dialog():
        def pick(model_name: str):
            model_switcher.set_value(model_name)
            on_model_change(model_name)
            close_dialog(dlg)

        results = ft.Column(scroll=ft.ScrollMode.AUTO, height=320, spacing=2)

        def refresh_results(query: str = ""):
            results.controls.clear()
            q = query.lower()
            for m in models:
                if q and q not in m.lower():
                    continue
                results.controls.append(
                    ft.Container(
                        content=ft.Text(m, size=13, color=theme.TEXT_PRIMARY),
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                        border_radius=6,
                        bgcolor=theme.BG_SURFACE_2,
                        on_click=lambda e, mm=m: pick(mm),
                        ink=True,
                    )
                )
            if results.page:
                results.update()

        search = ft.TextField(
            hint_text="Search models...",
            autofocus=True,
            border_color=theme.BORDER,
            bgcolor=theme.BG_SURFACE_2,
            color=theme.TEXT_PRIMARY,
            on_change=lambda e: refresh_results(search.value or ""),
        )
        refresh_results()

        dlg = ft.AlertDialog(
            title=ft.Text("Switch Model"),
            content=ft.Container(content=ft.Column([search, results], spacing=10, tight=True), width=380),
            actions=[ft.TextButton("Cancel", on_click=lambda e: close_dialog(dlg))],
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    def open_chat_search_dialog():
        def pick(chat_id: int):
            close_dialog(dlg)
            load_chat(chat_id)

        results = ft.Column(scroll=ft.ScrollMode.AUTO, height=320, spacing=2)
        all_chats = db.list_chats()

        def refresh_results(query: str = ""):
            results.controls.clear()
            q = query.lower()
            for c in all_chats:
                title = c["title"] or "New Chat"
                if q and q not in title.lower():
                    continue
                results.controls.append(
                    ft.Container(
                        content=ft.Text(title, size=13, color=theme.TEXT_PRIMARY, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                        border_radius=6,
                        bgcolor=theme.BG_SURFACE_2,
                        on_click=lambda e, cid=c["id"]: pick(cid),
                        ink=True,
                    )
                )
            if results.page:
                results.update()

        search = ft.TextField(
            hint_text="Search chats...",
            autofocus=True,
            border_color=theme.BORDER,
            bgcolor=theme.BG_SURFACE_2,
            color=theme.TEXT_PRIMARY,
            on_change=lambda e: refresh_results(search.value or ""),
        )
        refresh_results()

        dlg = ft.AlertDialog(
            title=ft.Text("Search Chats"),
            content=ft.Container(content=ft.Column([search, results], spacing=10, tight=True), width=380),
            actions=[ft.TextButton("Cancel", on_click=lambda e: close_dialog(dlg))],
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    def on_keyboard(e: ft.KeyboardEvent):
        if e.ctrl and e.key == "N":
            new_chat()
        elif e.ctrl and e.key == "K":
            open_model_switcher_dialog()
        elif e.ctrl and e.key == "/":
            open_chat_search_dialog()
        elif e.key == "Escape" and state.streaming:
            state.cancel_requested = True

    page.on_keyboard_event = on_keyboard

    main_column = ft.Column(
        [top_bar, advanced_panel, chat_view, input_bar],
        expand=True,
        spacing=0,
    )

    page.add(
        ft.Row(
            [sidebar, ft.VerticalDivider(width=1, color=theme.BORDER), main_column],
            expand=True,
            spacing=0,
        )
    )

    chats = db.list_chats()
    if chats:
        load_chat(chats[0]["id"])
    else:
        new_chat()


ft.app(target=main)
