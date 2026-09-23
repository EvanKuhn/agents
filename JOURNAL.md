# Journal

## Sept 22, 2026

This is the first day of building an AI agent, or more accurately (I think?), a harness.
I'm using Ollama to run models locally, Python to interact with the models via the
ollama package, and Claude as my coding sidekick. I built a small proof-of-concept earlier,
which makes a single call to the LLM and prints the results.

## Progress
I was able to accomplish today:

- Add `PLAN.md` to list and track project milestones.
- Add a loop to the agent, and add in-context memory. Previous messages are saved and fed back into the model within the current conversation.
- Render agent output as markdown, and include a status bar (showing time, token count, and status).
- Support thinking models.
- Support personas (socratic, terse, pirate)
- Support basic tool use (calculator, list files, read file, get time)
- Add initial system prompt

## Learnings

### Ollama API Format

Ollama uses structured JSON for API input and output. The format they use is based on work by OpenAI:

- OpenAI's [Chat Completions API](https://developers.openai.com/api/reference/chat-completions/overview) (March 2023) introduced a messages array of `{role, content}` objects using `system`/`user`/`assistant`. This replaced the older single-string prompt APIs, and almost everyone copied it.
- OpenAI's [function calling](https://developers.openai.com/api/docs/guides/function-calling) (June 2023) expected function calls to be passed using a JSON schema. Each tool has `name`, `description`, and `parameters` fields, which the model can reference for tool calls.

Ollama's native `/api/chat` format is heavily influenced by OpenAI's work, but not identical. However,
Ollama does provide an OpenAI-compatible endpoint at `/v1/chat/completions`, which allows software written
for the OpenAI API to instead use Ollama.

### Model Types and Tool Use

The biggest learning today was around tool use. Though it's unsurprising in hindsight, I was unaware
of the extent to which different models succeed or fail with tool use. For example, qwen3 succeeded
quite well, while llama3.1 struggled significantly. Deepseek-r1 also had trouble, though in one case
it failed to return; so either it entered an infinite loop, or something else went wrong during the
test.

Other failure modes include: calling tools too frequently, or not at all; pretending to call tools;
and hallucinating tool output. Models also may not trust tool output. For example, llama3.1 did not
believe the date was 2026, as its training had completed in Dec 2023.

The system prompt can have a large effect on successful tool use. The models need to be told that
they have access tools, what those tools are, guidance on how to use them, and instruction to
trust tool output.

There are a number of things that can affect tool usage:

- The model training, targeted fine-tuning, and reinforcement learning.
- The model's ability to follow precise instructions (as function calls require absolute correctness).
- Judgment about which tool to call, and when to call it. Larger models typically excel here.
- Long context and multi-step reliability. Models that handle these better will excel. Lost context will affect results.
- Distilled models tend to fail on unfamiliar toolsets.
- Harness quality: clear tool descriptions, useful error messages, sensible defaults, and a quality agent loop all affect tool use success.

### Ollama Tool Definition Parsing

Another notable learning is that the Ollama API parses the Python function definition and docstring
to create a JSON tool definition that is passed to the model. Ollama requires that we use
[Google-style function docstrings](https://google.github.io/styleguide/pyguide.html#383-functions-and-methods). Ollama parses the following:

- **Name**: the function's name becomes the tool's name.
- **Type hints**: these become the parameter types, e.g. expression: str.
- **Docstring**: the summary becomes the tool's description, and each line under Args: becomes a parameter description. Anything under Returns: or Raises: is skipped.

This is done via the `convert_function_to_tool()` method in [`ollama/_utils.py`](https://github.com/ollama/ollama-python/blob/b28b1e8a8cf5436d06805e5bb211904e9ff53ef9/ollama/_utils.py#L56).

### Chain-of-Thought Reasoning

Chain-of-thought reasoning is a technique that models use to reason through complex queries and produce
more accurate results. Rather than generating an answer immediately, the model is trained to think
step-by-step, producing an internal monologue of "thoughts". This allows the model to reason in smaller
steps, which it can then compose into a final answer.

Chain-of-thought produces higher quality responses with fewer errors and hallucinations, though of course
it does require more time and higher token usage.

Google Researchers published the foundational paper [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903) in January 2022, in which they demonstrated that large language models could perform multi-step math and logic if the user provided a few step-by-step examples in the prompt. Later, in May 2022, they showed that simply adding the phrase _"Let's think step by step"_ in the prompt could unlock similar reasoning capabilities.

## Terminology

This work has exposed me to a number of new terms, which require clarification. For completeness, I've also included some of the more basic terms (model, assistant). Definitions were shamelessly copied from Claude:

**Model**\
The trained neural network: learned weights plus the architecture that uses them. It takes input (text, images, tokens) and produces output, usually by predicting one token at a time. On its own it has no memory between calls, no tools, and no goals. Examples: Llama 3, Claude Opus, GPT-5, Qwen. Sometimes "model" means the weights file, such as a GGUF you run in Ollama. Sometimes it means the hosted service behind an API.

**Assistant**\
Two related meanings:

1. **A role in a conversation.** In chat formats, `assistant` marks the model's turns, as opposed to `user`, `system` and `tool`.
2. **A product built for conversation.** A model tuned to follow instructions and chat helpfully, usually wrapped in an app. Examples: ChatGPT, the Claude app, Siri. An assistant mostly responds to you one turn at a time.

**Agent**\
A system in which a model acts in a **loop**. It decides what to do, calls tools, looks at the results, and repeats until the goal is reached, with little human input between steps. The key difference from an assistant is **autonomy over several steps**. An agent doesn't just answer. It takes actions such as running code, browsing, or editing files. Examples: Claude Code, coding agents, research agents. The line between "assistant" and "agent" is blurry, since many assistants now use tools.

**Framework**\
A software library for **building** AI applications and agents. It supplies ready-made parts such as prompt templates, tool definitions, memory, retrieval, multi-agent coordination, and adapters for different model providers. Examples: LangChain, LlamaIndex, CrewAI, the Claude Agent SDK, the Vercel AI SDK. You write code *with* a framework.

**Harness**\
The code **around** a model that turns it into a working agent or evaluation setup. It builds the prompt, provides the tools, runs the loop, executes tool calls, feeds results back, enforces permissions, and manages context. The term comes from "test harness." In evaluation, the harness runs a model through benchmark tasks and scores it. In agents, it's the scaffolding that makes a model act. For example, Claude Code is a harness around a Claude model. The same model can do much better or worse depending on its harness.

**Runtime**\
The software that actually **executes** something. There are two common meanings:

1. **Inference runtime:** the engine that loads model weights and generates output on hardware. Examples: llama.cpp (which Ollama uses internally), vLLM, TensorRT-LLM, ONNX Runtime.
2. **Agent runtime:** the environment where an agent runs and keeps its state, such as a hosted service that runs agent loops, stores sessions, and provides sandboxes. Example: Anthropic's Managed Agents.

**How they fit together**\
Take Claude Code as an example:

* The **model** (Claude Opus) generates text and tool calls.
* It runs on Anthropic's **inference runtime** on their servers.
* Claude Code is the **harness**: it runs the loop, executes tools, and manages permissions and context.
* The result behaves as an **agent**, because it completes multi-step coding tasks on its own.
* It was built with, and is exposed as, the Claude Agent SDK, a **framework** you can use to build your own agents.
* Its conversation turns are labeled with the **assistant** role, and in casual use people call the whole thing a coding assistant.

A local setup follows the same pattern: a Llama **model** served by Ollama's llama.cpp **runtime**, driven by a LangChain-based (**framework**) **harness** that you wrote, which together make an **agent**.
