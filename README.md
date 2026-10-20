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
