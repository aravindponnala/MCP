from typing import List, Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion
from prompt_toolkit.document import Document
from prompt_toolkit.buffer import Buffer

from core.cli_chat import CliChat


class CommandAutoSuggest(AutoSuggest):
    def __init__(self, prompts: List):
        self.prompt_dict = {p.name: p for p in prompts}

    def get_suggestion(
        self, buffer: Buffer, document: Document
    ) -> Optional[Suggestion]:
        text = document.text
        if not text.startswith("/"):
            return None
        parts = text[1:].split()
        if len(parts) == 1 and parts[0] in self.prompt_dict:
            prompt = self.prompt_dict[parts[0]]
            if prompt.arguments:
                return Suggestion(f" {prompt.arguments[0].name}")
        return None


class UnifiedCompleter(Completer):
    def __init__(self):
        self.prompts: List = []
        self.prompt_dict: dict = {}
        self.resources: List[str] = []

    def update_prompts(self, prompts: List):
        self.prompts = prompts
        self.prompt_dict = {p.name: p for p in prompts}

    def update_resources(self, resources: List[str]):
        self.resources = resources

    def get_completions(self, document, complete_event):
        text = document.text
        text_before_cursor = document.text_before_cursor

        # Resource mention via @
        if "@" in text_before_cursor:
            last_at = text_before_cursor.rfind("@")
            prefix = text_before_cursor[last_at + 1:]
            for resource_id in self.resources:
                if resource_id.lower().startswith(prefix.lower()):
                    yield Completion(
                        resource_id,
                        start_position=-len(prefix),
                        display=resource_id,
                        display_meta="Resource",
                    )
            return

        # Slash command completions
        if text.startswith("/"):
            parts = text[1:].split()

            # Complete command name
            if len(parts) <= 1 and not text.endswith(" "):
                cmd_prefix = parts[0] if parts else ""
                for prompt in self.prompts:
                    if prompt.name.startswith(cmd_prefix):
                        yield Completion(
                            prompt.name,
                            start_position=-len(cmd_prefix),
                            display=f"/{prompt.name}",
                            display_meta=prompt.description or "",
                        )
                return

            # Complete first argument (resource ID) after command
            if len(parts) == 1 and text.endswith(" "):
                for resource_id in self.resources:
                    yield Completion(resource_id, start_position=0, display=resource_id)
                return

            # Complete partial resource ID in second position
            if len(parts) >= 2:
                prefix = parts[-1]
                for resource_id in self.resources:
                    if resource_id.lower().startswith(prefix.lower()):
                        yield Completion(
                            resource_id,
                            start_position=-len(prefix),
                            display=resource_id,
                        )
                return


class CliApp:
    def __init__(self, agent: CliChat):
        self.agent = agent
        self.resources: List[str] = []
        self.prompts: List = []

        self.completer = UnifiedCompleter()
        self.command_autosuggester = CommandAutoSuggest([])

        self.kb = KeyBindings()

        @self.kb.add("/")
        def _(event):
            buf = event.app.current_buffer
            buf.insert_text("/")
            if buf.document.is_cursor_at_the_end and buf.text == "/":
                buf.start_completion(select_first=False)

        @self.kb.add("@")
        def _(event):
            buf = event.app.current_buffer
            buf.insert_text("@")
            if buf.document.is_cursor_at_the_end:
                buf.start_completion(select_first=False)

        @self.kb.add(" ")
        def _(event):
            buf = event.app.current_buffer
            text = buf.text
            buf.insert_text(" ")
            if text.startswith("/"):
                parts = text[1:].split()
                if len(parts) == 1:
                    buf.start_completion(select_first=False)

        self.session = PromptSession(
            completer=self.completer,
            history=InMemoryHistory(),
            key_bindings=self.kb,
            style=Style.from_dict(
                {
                    "prompt": "#aaaaaa",
                    "completion-menu.completion": "bg:#222222 #ffffff",
                    "completion-menu.completion.current": "bg:#444444 #ffffff",
                }
            ),
            complete_while_typing=True,
            complete_in_thread=True,
            auto_suggest=self.command_autosuggester,
        )

    async def initialize(self):
        await self.refresh_resources()
        await self.refresh_prompts()

    async def refresh_resources(self):
        try:
            self.resources = await self.agent.list_docs_ids()
            self.completer.update_resources(self.resources)
        except Exception as e:
            print(f"Error refreshing resources: {e}")

    async def refresh_prompts(self):
        try:
            self.prompts = await self.agent.list_prompts()
            self.completer.update_prompts(self.prompts)
            self.command_autosuggester = CommandAutoSuggest(self.prompts)
            self.session.auto_suggest = self.command_autosuggester
        except Exception as e:
            print(f"Error refreshing prompts: {e}")

    async def run(self):
        while True:
            try:
                user_input = await self.session.prompt_async("> ")
                if not user_input.strip():
                    continue
                response = await self.agent.run(user_input)
                print(f"\nResponse:\n{response}\n")
            except KeyboardInterrupt:
                print("\nExiting.")
                break
