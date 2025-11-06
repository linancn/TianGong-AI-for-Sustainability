# Test Suite Structure

The tests are organised to mirror the project layout so contributors can quickly
locate the relevant checks:

- `tests/llm/` – unit tests for LLM clients and adapters (for example
  OpenAI Deep Research).
- `tests/workflows/` – integration-style workflows that orchestrate multiple
  services and adapters.
- `tests/scripts/` – smoke tests covering repository scripts and CLI helpers.
- Root-level modules (`test_cli.py`, `test_services.py`, etc.) cover the rest of
  the stack.

When adding new functionality, prefer placing tests in the matching subdirectory
and note whether they are unit or workflow/integration tests. This keeps future
expansions (e.g., additional LLM providers) predictable and prevents suites from
overlapping responsibilities.
