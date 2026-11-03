# Routine Rebels

[![CI](https://github.com/agupta5555/SSW555-Routine-Rebels/actions/workflows/ci.yml/badge.svg)](https://github.com/agupta5555/SSW555-Routine-Rebels/actions/workflows/ci.yml)

Routine Rebels is a daily routine tracker that helps people record habits,
monitor their progress, and build consistent routines.

## Team

- Aryan Gupta
- Nikunj Patel
- Neil Motiani
- Aarnav Hariramani

## Local development

```bash
uv sync --extra dev
uv run flask --app app run --debug
```

Run the same checks used by CI:

```bash
uv run ruff check .
uv run pytest -v
```

## Daily completions

Use **Mark complete** beside a habit to record today's completion. The button
shows **Completed today** afterward. Repeated submissions record the date only
once; simultaneous submissions preserve existing history. Completion dates use
the server's local calendar day and are stored as a JSON list in `completed_dates`.

US-09 regression tests: `uv run pytest tests/test_us09_duplicate_completions.py`.
