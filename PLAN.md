# Agent Build Plan

An incremental plan for building up a local Ollama-based agent, from a raw API
call to multi-agent orchestration. Recommended build order: 1→2→3→4→5→6→7→13,
then 8→9→10 for memory, then 11→12→14 as stretch goals.

## Steps

- [x] **1. Hello world / raw API call.** Send a single prompt to Ollama's
      `/api/generate` or `/api/chat` endpoint and print the response. Goal:
      understand the wire format, streaming vs. non-streaming, and basic
      params (temperature, model selection).

- [x] **2. Working memory (conversation history).** Wrap the raw call in a
      loop that keeps a list of messages and resends the full history each
      turn. This is where you learn about context windows and truncation —
      worth deliberately overflowing the window once to see what happens.

- [x] **3. System prompts / persona control.** Small but distinct step:
      separate "identity and instructions" from "conversation," and see how
      much it steers behavior.

- [x] **4. Basic tool use.** Define a couple of functions (e.g., calculator,
      current time, file read), describe them to the model, parse its request
      to call one, execute it, and feed the result back in. Ollama's
      tool-calling support varies by model, so this step doubles as a lesson
      in model selection (e.g., Llama 3.1/3.2, Qwen2.5, or Mistral variants
      with function-calling support).

- [ ] **5. Multi-step tool loop / ReAct-style reasoning.** Instead of one
      tool call per turn, let the agent chain several calls (think → act →
      observe → think again) until it decides it's done. This is the core
      "agent loop" and a good place to add a max-iteration safety valve.

- [ ] **6. Structured output / validation.** Force JSON-schema-constrained
      responses (Ollama supports a `format` param) so tool calls and final
      answers are machine-parseable instead of regex-scraped from text.

- [ ] **7. Procedural memory / skills.** Let the agent load reusable
      "recipes" — named prompts or tool sequences stored as files — and
      choose among them. This is basically a lightweight plugin system for
      prompts.

- [ ] **8. Episodic memory (logs + vector DB).** Persist past conversations,
      embed them (Ollama can serve embedding models like `nomic-embed-text`),
      and store in something like Chroma or SQLite+sqlite-vec (both trivial
      to run locally, no extra infra). Add a retrieval step that pulls
      relevant past exchanges into context.

- [ ] **9. RAG over external documents.** Separate from episodic memory:
      chunk and embed your own docs, retrieve top-k before generation. Good
      step to also explore chunking strategy and re-ranking.

- [ ] **10. Long-term/semantic memory consolidation.** A step beyond raw
       episodic logs: periodically summarize or extract "facts" from past
       conversations into a compact profile/knowledge store, so memory
       doesn't just grow unboundedly.

- [ ] **11. Planning / task decomposition.** Before acting, have the agent
       produce an explicit plan (subtasks) for complex requests, then execute
       and revise the plan as it learns things — distinct from the reactive
       tool loop in step 5.

- [ ] **12. Multi-agent orchestration.** Split into specialized sub-agents
       (e.g., researcher + writer + critic) coordinated by a controller —
       natural extension once single-agent tool use is solid.

- [ ] **13. Guardrails / evaluation harness.** Add basic checks: cost/token
       tracking, loop-detection, a small eval set of test prompts you rerun
       after each change to catch regressions as you add complexity.

- [ ] **14. Simple UI or API wrapper.** Wrap the whole thing in a minimal CLI
       REPL or a FastAPI server — useful once the internals are stable and
       you want to actually use the thing.

## More Ideas

- [X] Support automated formatting, linting, and type checking (try `ruff` and `ty`)
- [X] Add Makefile with useful commands
- [ ] Temperature setting
- [ ] More tools (see TODOs in tools.py)
- [ ] Optionally show thinking, tool calls, API request/response, etc
- [ ] Context management and compaction
- [ ] Refactoring / code cleanup

## Questions
- What's the difference between Ollama, LM Studio, and OpenRouter?
  - OpenRouter is for switching between hosted models, typically frontier models.
  - Ollama is for running local models, targeted at devs. Lightweight.
  - LM Studio is also for running local models, but more for non-technical people. Nice UI.
