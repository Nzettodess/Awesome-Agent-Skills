"""GitHub Copilot SDK implementation for reverse engineering."""

import asyncio
from collections.abc import Callable
from typing import Any

from .base_engineer import BaseEngineer

# Timeout for waiting on Copilot session completion (10 minutes)
_SESSION_TIMEOUT = 600


def tool_output_text(result: Any) -> str | None:
    """The text a Copilot tool returned, from a ToolResult or its wire form."""
    if result is None:
        return None
    if isinstance(result, dict):
        text = result.get("textResultForLlm") or result.get("text_result_for_llm")
        return str(text) if text else None
    text = getattr(result, "text_result_for_llm", None)
    return str(text) if text else None


class CopilotEngineer(BaseEngineer):
    """Uses GitHub Copilot SDK to analyze HAR files and generate API scripts."""

    # Populated by CopilotAutoEngineer before building the shared agent prompt.
    agent_provider: str
    mcp_run_id: str
    headless: bool
    start_url: str | None

    def __init__(
        self,
        run_id: str,
        har_path: Any,
        prompt: str,
        copilot_model: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(run_id=run_id, har_path=har_path, prompt=prompt, **kwargs)
        self.copilot_model = copilot_model or "gpt-5"

    def _build_ask_user_tool(self) -> Any:
        """Build the ask_user_question custom tool for Copilot sessions."""
        try:
            from copilot import define_tool
        except ImportError:
            raise ImportError(
                "GitHub Copilot SDK not installed. From source: uv sync --extra copilot. Installed: pip install 'reverse-api-engineer[copilot]'"
            ) from None

        from pydantic import BaseModel, Field

        class QuestionOption(BaseModel):
            label: str = Field(description="Display text for this option")
            description: str = Field(default="", description="Explanation of what this option means")

        class Question(BaseModel):
            question: str = Field(description="The question to ask the user")
            header: str = Field(default="", description="Short label for context")
            options: list[QuestionOption] = Field(default_factory=list, description="Available choices")
            multiSelect: bool = Field(default=False, description="Allow multiple selections")

        class AskUserParams(BaseModel):
            questions: list[Question] = Field(description="Questions to ask the user")

        # Capture self for use in the tool handler
        engineer = self

        @define_tool(description="Ask the user a clarifying question. Use when you need user input to proceed.")
        async def ask_user_question(params: AskUserParams) -> str:
            # Convert pydantic models to dicts for the shared method
            question_dicts = [q.model_dump() for q in params.questions]
            answers = await engineer._ask_user_questions(question_dicts)
            return "\n".join(f"{k}: {v}" for k, v in answers.items())

        return ask_user_question

    async def _open_copilot_session(self, client: Any, **config: Any) -> Any:
        """A new Copilot session, or the saved one when resuming: the Copilot CLI keeps sessions between runs."""
        if self.resume_session:
            session = await client.resume_session(self.resume_session, **config)
        else:
            session = await client.create_session(**config)
        self._record_session(session.session_id)
        return session

    def _event_handler(self, done: asyncio.Event, errors: list[str]) -> Callable[[Any], None]:
        """Streams a session's text, reasoning and usage into the UI; ``done`` is set once the session is idle.

        The SDK may call this from another thread, hence ``call_soon_threadsafe`` for the event.
        """
        loop = asyncio.get_running_loop()

        def on_event(event: Any) -> None:
            kind = getattr(event.type, "value", str(event.type))
            data = getattr(event, "data", None)
            if kind == "assistant.message_delta":
                delta = getattr(data, "delta_content", "") or ""
                if delta and (stream_text := getattr(self.ui, "stream_text", None)):
                    stream_text(delta)
            elif kind == "assistant.reasoning_delta":
                delta = getattr(data, "delta_content", "") or ""
                if delta and (stream_thinking := getattr(self.ui, "stream_thinking", None)):
                    stream_thinking(delta)
            elif kind == "assistant.reasoning":
                if (content := getattr(data, "content", "") or "") and (thinking_note := getattr(self.ui, "thinking_note", None)):
                    thinking_note(content)
            elif kind == "assistant.message":
                content = getattr(data, "content", "") or ""
                if content.strip():
                    self.ui.thinking(content)
                    self.message_store.save_thinking(content)
            elif kind == "assistant.usage":
                for key in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens"):
                    value = getattr(data, key, None)
                    if isinstance(value, int):
                        self.usage_metadata[key] = self.usage_metadata.get(key, 0) + value
            elif kind == "session.error":
                errors.append(str(getattr(data, "message", "") or "Copilot session error"))
                loop.call_soon_threadsafe(done.set)  # an error need not be followed by idle
            elif kind == "session.compaction_start":
                self.ui.console.print("  [dim]session compacting...[/dim]")
            elif kind == "session.compaction_complete":
                self.ui.console.print("  [dim]session compaction complete[/dim]")
            elif kind == "session.idle":
                loop.call_soon_threadsafe(done.set)

        return on_event

    async def analyze_and_generate(self) -> dict[str, Any] | None:
        """Run the reverse engineering analysis with GitHub Copilot."""
        try:
            from copilot import CopilotClient, PermissionHandler
        except ImportError:
            self.ui.error(
                "GitHub Copilot SDK not installed. From source: uv sync --extra copilot. Installed: pip install 'reverse-api-engineer[copilot]'"
            )
            return None

        self.ui.header(self.run_id, self.prompt, self.copilot_model, self.sdk, mode="engineer")
        self.ui.start_analysis()

        system_prompt, user_message = self._build_prompts()
        opening = await self._opening_message(user_message)
        if not opening:
            return {}
        prompt = opening if self.resume_session else f"{system_prompt}\n\n{user_message}"

        done_event = asyncio.Event()
        errors: list[str] = []

        client = None
        try:
            ask_user_tool = self._build_ask_user_tool()

            client = CopilotClient(use_logged_in_user=True)
            await client.start()

            session = await self._open_copilot_session(
                client,
                model=self.copilot_model,
                streaming=True,
                infinite_sessions={"enabled": True},
                tools=[ask_user_tool],
                on_permission_request=PermissionHandler.approve_all,
            )

            session.on(self._event_handler(done_event, errors))

            await session.send(prompt)

            # Wait for session to complete with timeout protection
            try:
                await asyncio.wait_for(done_event.wait(), timeout=_SESSION_TIMEOUT)
            except TimeoutError:
                self.ui.error(f"Session timed out after {_SESSION_TIMEOUT // 60} minutes")
                self.message_store.save_error("Session timed out")
                return None

            if errors:
                self.ui.error(errors[-1])
                self.message_store.save_error(errors[-1])
                return None

            # Build result
            script_path = str(self.scripts_dir / self._get_client_filename())
            local_path = str(self.local_scripts_dir / self._get_client_filename()) if self.local_scripts_dir else None
            self.ui.success(script_path, local_path)

            # GitHub subscription: cost is $0 (included in Copilot subscription)
            self.usage_metadata["estimated_cost_usd"] = 0.0
            self._report_usage()

            # Display usage if available
            input_tokens = self.usage_metadata.get("input_tokens", 0)
            output_tokens = self.usage_metadata.get("output_tokens", 0)
            if input_tokens > 0 or output_tokens > 0:
                self.ui.console.print("  [dim]Usage:[/dim]")
                if input_tokens > 0:
                    self.ui.console.print(f"  [dim]  input: {input_tokens:,} tokens[/dim]")
                if output_tokens > 0:
                    self.ui.console.print(f"  [dim]  output: {output_tokens:,} tokens[/dim]")
                self.ui.console.print("  [dim]  cost: $0.00 (Copilot subscription)[/dim]")

            result: dict[str, Any] = {
                "script_path": script_path,
                "usage": self.usage_metadata,
            }
            self.message_store.save_result(result)
            return result

        except Exception as e:
            self.ui.error(str(e))
            self.message_store.save_error(str(e))
            self.ui.console.print("\n[dim]Make sure GitHub Copilot CLI is installed and you are logged in: gh auth login[/dim]")
            return None

        finally:
            # Always stop the client to avoid resource leaks
            if client is not None:
                try:
                    await client.stop()
                except Exception:
                    pass
