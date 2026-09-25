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
# This module does no printing. It reports progress to an AgentObserver, so
# the same loop can drive the terminal chat (see chat.py) or run silently.

import json
from collections.abc import Callable
from dataclasses import dataclass, field

import ollama

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


@dataclass
class Reply:
    """
    One reply from the model, built up as it streams in.
    - text        : the reply text so far
    - thinking    : the model's thinking so far (thinking models only)
    - tool_calls  : tools the model asked for so far
    - token_count : output tokens; approximate while streaming, exact once done
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

    def _request(self, tools: list[Callable[..., str]] | None, round_number: int | None) -> Reply:
        """
        Send the conversation to the model, stream its reply to the observer,
        and save the reply (with its thinking and tool calls) to the history.

        Args:
            tools: Tool functions to offer, or None to offer none.
            round_number: Round number to report to the observer, or None.

        Returns:
            The complete reply.
        """
        self.observer.reply_started(round_number)
        stream = self.client.chat(
            model=self.model, messages=self.messages, stream=True, think=self.think, tools=tools
        )

        reply = Reply()
        for chunk in stream:
            message = chunk["message"]
            content = message["content"]
            thinking = message.get("thinking") or ""
            reply.text += content
            reply.thinking += thinking
            reply.thinking_now = bool(thinking) and not content
            if content:
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
