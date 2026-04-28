# Coding Conventions

## Functions & Modules

- Max 40 lines per function. If it grows longer, extract a helper.
- One responsibility per function. If the name needs "and", split it.
- Name pattern: `verb_noun` — `build_outline`, `publish_post`, `validate_token`.
- One module per tool (`tools/build_outline.py`), one module per node (`graph/nodes/drafter.py`).
- Never import from `archive/` into `src/` — those are tutorial scripts, not production code.

## Types

- Type hints on every function signature. No bare `Any` unless truly unavoidable; add a comment explaining why.
- Pydantic models for all data crossing module or layer boundaries.
  - Class names: `CamelCase` (`AgentState`, `DraftOutput`)
  - Field names: `snake_case` (`post_text`, `eval_score`)
  - Use `model_validator` over custom `__init__`
  - Never use `dict` as a function parameter where a Pydantic model fits
- Enums for fixed value sets (`PostStatus`, `ReviewVerdict`) — never raw strings.

## Imports

```python
# stdlib
import os
from pathlib import Path

# third-party
import structlog
from pydantic import BaseModel

# local
from linkedin_agent.schemas import AgentState
```

- Absolute imports only (`from linkedin_agent.tools.build_outline import ...`)
- No wildcard imports (`from module import *`)

## Error Handling

- Raise specific exceptions, not bare `Exception`.
- At system boundaries (API endpoints, DB calls, LLM calls) catch and convert to domain errors.
- Never swallow exceptions silently — at minimum log with `logger.exception(...)`.
- Use `Result` pattern or explicit `Optional` returns for expected failures; exceptions for unexpected ones.

## Logging

- `structlog` everywhere in `src/`. No `print()` in source code.
- `print()` is allowed only in `scripts/`.
- Log at the right level: `debug` for tracing internals, `info` for events, `warning` for recoverable issues, `error` for failures.
- Always include context: `logger.info("draft_complete", tokens=n, cost=c, topic=topic)`

## Tests

```python
def test_build_outline_returns_three_sections():
    # Arrange
    state = AgentState(topic="RAG systems", ...)

    # Act
    result = build_outline(state)

    # Assert
    assert len(result.sections) == 3
```

- One behaviour per test. Name pattern: `test_<unit>_<condition>_<expected>`.
- Fixtures in `conftest.py` — no duplicated setup across test files.
- LLM tests use VCR cassettes (`@pytest.mark.vcr`). Commit cassettes. CI must not hit live APIs.
- No `time.sleep()` in tests. Use dependency injection or mocks for time-dependent logic.

## Git

- Never amend a pushed commit. Always create a new commit.
- Never use `--no-verify`. If a pre-commit hook fails, fix the underlying issue.
- Commit messages: `<type>: <short description>` — `feat:`, `fix:`, `test:`, `chore:`, `docs:`
- One logical change per commit.
