# AGENTS.md — Guide for AI Coding Agents

## Quick Context

`certlib.log` is a **single-module Python library** in `src/certlib/log.py`. It extends stdlib `logging` with structured JSON output (see `StructuredLogsFormatter`) and modern message/data handling (see `xm(...)`/`ExtendedMessage`). Runtime dependencies are **stdlib only**.

## Where to Work

- Main implementation + primary docs source: `src/certlib/log.py` (module docstring is the User's Guide).
- Main test coverage: `tests/test_certlib_log.py` (single comprehensive pytest file).
- Docs config/source: `docs/mkdocs.yml`, `docs/doc-src/*`.
- Dev dependency pins: `dev/dev-requirements.txt`.
- Do not edit generated docs output in `docs/site/*`.

## Core Invariants

- Public API names are explicitly controlled by `__all__` near the top of `src/certlib/log.py`.
- `StructuredLogsFormatter` requires `"system"`, `"component"`, `"component_type"` to be covered by `defaults` and/or `auto_makers` (or mapped to `None` explicitly).
- "Void" values are falsy values except numeric zero/`False` (`None`, `""`, `[]`, `{}` are void) and are excluded from top-level output.
- Auto-makers are registered on `logging.LogRecord`; each formatter instance isolates its own auto-made attributes of log records via unique `auto_made_record_attr_prefix` (which is not included in actual output data).
- Treat initialized `StructuredLogsFormatter` public attrs as read-only/immutable; customize by implementing hook methods in a subclass, do not monkey-patch.

## StructuredLogsFormatter Initialization (Compatibility-Critical)

- `StructuredLogsFormatter.__init__` supports three forms for its own args: direct kwargs, mapping as first positional arg, and `ast.literal_eval`-able string as first positional arg.
- The string-first-arg form is a *literal string of formatter kwargs mapping* (parsed via `ast.literal_eval`), **not** a full INI/`fileConfig` text.
- Base `logging.Formatter` argument slots (`fmt`, `datefmt`, `style`, `validate`; positional or keyword) are accepted only with defaults (`None`, `None`, `'%'`, `True`) and only if they do not conflict with `StructuredLogsFormatter` args. Their meaning is ignored.
- This compatibility path prevents `TypeError` when constructor calls come from `logging.config.fileConfig` internals; do not remove/simplify it.

## xm / ExtendedMessage Initialization (Compatibility-Critical)

- `xm(...)` is a convenience alias for `ExtendedMessage(...)`, intended for `logger.<level>(xm(...))`.
- All positional and keyword args are optional.
- First positional arg, if given, is either a message pattern (non-mapping, stored in `ExtendedMessage.pattern`) or a mapping of output data items (as an alternative to keyword args, stored in `ExtendedMessage.data`); extra positional args (stored in `ExtendedMessage.args`) are allowed only for the message-pattern variant.
- Keyword args – **except** `exc_info`, `stack_info`, `stacklevel` – are used both for message formatting and output data items. Allowed only for the message-pattern call variant. They are stored in `ExtendedMessage.data`.
- `exc_info`, `stack_info`, `stacklevel` are special kwargs handled by internal machinery; they are **not** in `ExtendedMessage.data`, but are stored in dedicated `ExtendedMessage` fields. They are allowed for *both* call variants.
- Function/method *values* (**not** just arbitrary callables) passed for formatting/data (i.e., all argument values and items of the first-arg mapping if any; but **not** the first positional arg object itself, and **not** the `exc_info`/`stack_info`/`stacklevel` kwargs) are lazy-called at format time. Examples: `xm('x={}', func)`, `xm({'k': func})`, `xm(k=func)`.

## Test and Validation Conventions

- Module-level `autouse` fixtures clean global auto-maker state and restore log-record factory after each test.
- `ListLogHandler` captures serialized JSON; `output_list` deserializes for assertions.
- `ImportableWrapper`/`CallableImportableWrapper` expose test helpers, in particular via `__repr__` returning synthetic importable dotted names.
- Tests explicitly cover all three `StructuredLogsFormatter` constructor input forms.
- Docstring + `README.md` snippets are validated by `TestSnippetsInDocumentation`. All snippets must be covered (or explicitly declared as ignored) or tests will fail.

## Developer Commands

```bash
bash dev-install.bash
pytest
mypy -p certlib.log
mypy tests/test_certlib_log.py
mkdocs build -f docs/mkdocs.yml
bash dev-regen.bash
bash dev-regen-with-upgrade.bash
```

## Change-to-Validation Mapping

- Changed runtime behavior in `src/certlib/log.py` -> run `pytest`.
- Changed type signatures/typing-sensitive logic -> run both mypy commands.
- Changed docstrings/`README.md` examples -> run `pytest` (covers snippet tests).
