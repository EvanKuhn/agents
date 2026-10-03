# The agent loop: sends the conversation to the model, runs any tools it asks
# for, adds the results to the history, and repeats until the model answers
# without calling a tool. This is the ReAct pattern: the model reasons, acts
# (calls a tool), observes the result, and reasons again.
#
# The model's thinking is saved in the history along with its replies, so in
# each round it can see why it made its earlier tool calls, not just what they
# returned. (Model templates like qwen3's include that earlier thinking only
# for the current question, so it doesn't pile up across the conversation.)
#
# For a structured answer, run_structured_turn() runs the same loop, then asks
# for the answer again as JSON. That last request passes a JSON schema as
# Ollama's `format` param, which constrains the reply to match it. It has to be
# a separate request: with `format` set the model can only produce JSON, so it
# can't call tools. The reply is then validated with pydantic, which can check
# more than the schema can (e.g. "at most 12 words"); if it fails, the errors
# are sent back and the model tries again.
#
# This module does no printing. It reports progress to an AgentObserver, so
# the same loop can drive the terminal chat (see chat.py) or run silently.

import json
from collections.abc import Callable
from dataclasses import dataclass, field

import ollama
from pydantic import BaseModel, ValidationError

from .tools import run_tool

# Tool result for a call the model already made this turn, instead of running it again
REPEATED_CALL_ERROR = (
    "Error: you already made this exact call for this question, and its result is above. "
    "Use that result, or try something different."
)

# Added to the last tool result when the round limit is reached
ROUND_LIMIT_NOTE = (
    "\n\n[Tool limit reached: you've used all {max_rounds} rounds of tool calls for this "
    "question. Don't call any more tools. Answer with what you've found so far, and say if "
    "the answer is incomplete.]"
)

# Asks for the answer as JSON, after the tool loop has finished
STRUCTURED_REQUEST = (
    "Now give your final answer as JSON matching this schema, with no other text:\n{schema}"
)

# Sent back when the model's JSON fails validation
VALIDATION_ERROR = (
    "Your JSON didn't pass validation:\n{errors}\n"
    "Reply again with corrected JSON matching the schema, with no other text."
)


class StructuredOutputError(Exception):
    """
    The model's JSON still failed validation after every retry.
    """


@dataclass
class Reply:
    """
    One reply from the model, built up as it streams in.
    - text        : the reply text so far
    - thinking    : the model's thinking so far (thinking models only)
    - tool_calls  : tools the model asked for so far
    - token_count : output tokens, including thinking; approximate while streaming, exact once done
    - thinking_now: whether the latest chunk was thinking rather than text
    - done        : whether the reply is complete
    """

    text: str = ""
    thinking: str = ""
    tool_calls: list = field(default_factory=list)
    token_count: int = 0
    thinking_now: bool = False
    done: bool = False


class AgentObserver:
    """
    Receives updates as the agent works. Every method does nothing by default,
    so a subclass only overrides the ones it cares about.
    """

    def turn_started(self) -> None:
        """
        The agent is starting on a new user message. The replies and tool
        calls that follow, until run_turn() returns, all belong to this turn.
        """

    def reply_started(self, round_number: int | None) -> None:
        """
        A request to the model is starting. round_number counts from 1 while
        tools are offered, and is None for a request without tools.
        """

    def reply_updated(self, reply: Reply) -> None:
        """
        More of the reply has streamed in.
        """

    def reply_finished(self, reply: Reply) -> None:
        """
        The reply is complete.
        """

    def tool_called(self, name: str, arguments: dict, result: str) -> None:
        """
        A tool call has been handled, with the result sent back to the model.
        """

    def validation_failed(self, errors: str) -> None:
        """
        A structured reply failed validation; the errors are being sent back
        so the model can try again.
        """


class Agent:
    """
    Runs the agent loop over a conversation. Call run_turn() once per user
    message; the conversation history lives in self.messages.
    """

    def __init__(
        self,
        client: ollama.Client,
        model: str,
        messages: list,
        tools: list[Callable[..., str]] | None,
        think: bool,
        max_rounds: int,
        observer: AgentObserver | None = None,
    ) -> None:
        """
        Args:
            client: Ollama client to send requests with.
            model: Name of the model to use.
            messages: Starting conversation history, e.g. the system prompt.
            tools: Tool functions to offer the model, or None for no tools.
            think: Whether to ask the model to think (thinking models only).
            max_rounds: Most rounds of tool calls allowed per user message.
            observer: Receives progress updates; defaults to one that ignores them.
        """
        self.client = client
        self.model = model
        self.messages = messages
        self.tools = tools
        self.think = think
        self.max_rounds = max_rounds
        self.observer = observer or AgentObserver()

    def run_turn(self, user_input: str) -> str:
        """
        Add the user's message to the conversation and run the loop until the
        model answers without calling a tool, or the round limit is reached.

        Args:
            user_input: The user's message.

        Returns:
            The model's final answer.
        """
        self.observer.turn_started()
        self.messages.append({"role": "user", "content": user_input})

        # Calls made for this question, as (name, arguments) keys. Repeats are
        # only refused within one question: the same call could give a
        # different answer later (e.g. the time, or a file that's changed).
        calls_made: set[tuple[str, str]] = set()

        for round_number in range(1, self.max_rounds + 1):
            reply = self._request(
                tools=self.tools, round_number=round_number if self.tools else None
            )
            if not reply.tool_calls:
                return reply.text
            self._run_tool_calls(reply.tool_calls, calls_made)

        # The model still wanted tools after the last round. Tell it to stop,
        # and ask once more without tools so it has to answer.
        self.messages[-1]["content"] += ROUND_LIMIT_NOTE.format(max_rounds=self.max_rounds)
        return self._request(tools=None, round_number=None).text

    def run_structured_turn[T: BaseModel](
        self, user_input: str, schema: type[T], max_retries: int = 2, constrained: bool = True
    ) -> T:
        """
        Run a turn as run_turn() does, then ask for the answer as JSON
        matching the schema, and validate it. If it fails validation, send
        the errors back and ask again, up to max_retries times.

        Args:
            user_input: The user's message.
            schema: Pydantic model the answer must match.
            max_retries: Most extra attempts after the first fails validation.
            constrained: Whether to pass the schema as Ollama's `format` param.
                If False, the model is only asked for JSON, so it can reply
                with anything (useful for comparing the two).

        Returns:
            The validated answer.

        Raises:
            StructuredOutputError: The answer still failed validation after
                every retry.
        """
        self.run_turn(user_input)

        json_schema = schema.model_json_schema()
        self.messages.append(
            {"role": "user", "content": STRUCTURED_REQUEST.format(schema=json.dumps(json_schema))}
        )
        errors = ""
        for _ in range(max_retries + 1):
            reply = self._request(
                tools=None, round_number=None, format=json_schema if constrained else None
            )
            try:
                return schema.model_validate_json(_strip_code_fence(reply.text))
            except ValidationError as e:
                errors = _format_errors(e)
                self.observer.validation_failed(errors)
                self.messages.append(
                    {"role": "user", "content": VALIDATION_ERROR.format(errors=errors)}
                )

        raise StructuredOutputError(
            f"answer failed validation after {max_retries + 1} attempts:\n{errors}"
        )

    def _request(
        self,
        tools: list[Callable[..., str]] | None,
        round_number: int | None,
        format: dict | None = None,
    ) -> Reply:
        """
        Send the conversation to the model, stream its reply to the observer,
        and save the reply (with its thinking and tool calls) to the history.

        Args:
            tools: Tool functions to offer, or None to offer none.
            round_number: Round number to report to the observer, or None.
            format: JSON schema the reply must match, or None for free text.

        Returns:
            The complete reply.
        """
        self.observer.reply_started(round_number)
        stream = self.client.chat(
            model=self.model,
            messages=self.messages,
            stream=True,
            think=self.think,
            tools=tools,
            format=format,
        )

        reply = Reply()
        for chunk in stream:
            message = chunk["message"]
            content = message["content"]
            thinking = message.get("thinking") or ""
            reply.text += content
            reply.thinking += thinking
            reply.thinking_now = bool(thinking) and not content
            # Each streamed chunk is roughly one token, whether reply text or thinking
            if content or thinking:
                reply.token_count += 1

            # Tool calls can arrive in any chunk, so collect them as we go
            reply.tool_calls.extend(message.get("tool_calls") or [])

            if chunk.get("done"):
                # Ollama reports the exact output token count on the final
                # chunk; prefer it over our running approximation
                reply.done = True
                reply.token_count = chunk.get("eval_count") or reply.token_count
            self.observer.reply_updated(reply)

        self.observer.reply_finished(reply)
        self.messages.append(
            {
                "role": "assistant",
                "content": reply.text,
                "thinking": reply.thinking or None,
                "tool_calls": reply.tool_calls,
            }
        )
        return reply

    def _run_tool_calls(self, tool_calls: list, calls_made: set[tuple[str, str]]) -> None:
        """
        Run each tool call and add its result to the history. A call the model
        already made for this question isn't run again; it gets an error
        telling the model to use the earlier result.

        Args:
            tool_calls: Tool calls from the model's reply.
            calls_made: Calls made so far for this question; updated in place.
        """
        for call in tool_calls:
            name, arguments = call.function.name, call.function.arguments
            key = (name, json.dumps(arguments, sort_keys=True))
            if key in calls_made:
                result = REPEATED_CALL_ERROR
            else:
                calls_made.add(key)
                result = run_tool(name, arguments)
            self.observer.tool_called(name, arguments, result)
            self.messages.append({"role": "tool", "tool_name": name, "content": result})


def _strip_code_fence(text: str) -> str:
    """
    Return the text without a surrounding Markdown code fence, if it has one.
    Without `format`, models often wrap JSON in ```json ... ```.

    Args:
        text: The model's reply.

    Returns:
        The text inside the fence, or the whole text if there's no fence.
    """
    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```")
    return text.strip()


def _format_errors(error: ValidationError) -> str:
    """
    Turn a pydantic ValidationError into one line per problem, for the model. Eg:
    - score: Input should be less than or equal to 1

    Args:
        error: The validation error.

    Returns:
        The problems, one per line.
    """
    lines = []
    for problem in error.errors(include_url=False):
        location = ".".join(str(part) for part in problem["loc"]) or "(whole reply)"
        lines.append(f"- {location}: {problem['msg']}")
    return "\n".join(lines)
